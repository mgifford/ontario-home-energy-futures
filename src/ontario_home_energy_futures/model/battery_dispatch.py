"""Monthly-aggregate home-battery grid-service dispatch model.

Computes gross and net revenue for battery bill-shifting and grid-service
value streams (demand response, VPP availability/event, dynamic export,
capacity, local flexibility) subject to a household-selected reserve
policy, at MONTHLY granularity - not full hourly dispatch optimization,
which remains explicitly deferred (see assumptions/batteries.yaml and
METHODOLOGY.md section 13/20).

    R_battery_net,y = R_availability,y + R_events,y + R_export,y + R_local_flexibility,y
                      - C_charging,y - C_losses,y - C_degradation,y
                      - C_aggregator,y - C_fees,y - C_penalties,y

Gross and net revenue are always reported as two separate fields, never
collapsed into one number.
"""

from __future__ import annotations

from dataclasses import dataclass

from .value_streams import ValueStream, ValueStreamRevenueResult, calculate_value_stream_revenue


@dataclass(frozen=True)
class BatterySpec:
    usable_capacity_kwh: float
    max_continuous_output_kw: float
    round_trip_efficiency: float
    degradation_annual: float
    expected_lifetime_throughput_kwh: float
    replacement_cost_cad: float


@dataclass(frozen=True)
class ReservePolicy:
    id: str
    label: str
    minimum_reserve_fraction: float

    def reserved_kwh(self, battery: BatterySpec) -> float:
        return battery.usable_capacity_kwh * self.minimum_reserve_fraction

    def dispatchable_kwh(self, battery: BatterySpec) -> float:
        return battery.usable_capacity_kwh * (1.0 - self.minimum_reserve_fraction)


@dataclass(frozen=True)
class DegradationResult:
    energy_discharged_household_kwh: float
    energy_discharged_grid_kwh: float
    annual_equivalent_full_cycles: float
    degradation_cost_household_cad: float
    degradation_cost_grid_cad: float


def calculate_degradation(
    *, battery: BatterySpec, energy_discharged_household_kwh: float, energy_discharged_grid_kwh: float
) -> DegradationResult:
    """Throughput-based degradation cost, attributed separately to
    household use versus grid-service dispatch, per the project brief's
    requirement to report "degradation attributed to grid participation"
    specifically (not blended into a single household+grid figure).

        C_degradation,t = E_discharged,t * (C_replacement / E_expected_lifetime_throughput)
    """
    if battery.expected_lifetime_throughput_kwh <= 0:
        raise ValueError("expected_lifetime_throughput_kwh must be positive")

    cost_per_kwh = battery.replacement_cost_cad / battery.expected_lifetime_throughput_kwh
    household_cost = energy_discharged_household_kwh * cost_per_kwh
    grid_cost = energy_discharged_grid_kwh * cost_per_kwh

    total_discharged = energy_discharged_household_kwh + energy_discharged_grid_kwh
    annual_equivalent_full_cycles = total_discharged / battery.usable_capacity_kwh if battery.usable_capacity_kwh else 0.0

    return DegradationResult(
        energy_discharged_household_kwh=round(energy_discharged_household_kwh, 2),
        energy_discharged_grid_kwh=round(energy_discharged_grid_kwh, 2),
        annual_equivalent_full_cycles=round(annual_equivalent_full_cycles, 3),
        degradation_cost_household_cad=round(household_cost, 2),
        degradation_cost_grid_cad=round(grid_cost, 2),
    )


@dataclass(frozen=True)
class BatteryDispatchResult:
    reserve_policy_id: str
    dispatchable_kwh: float
    reserved_kwh: float
    energy_discharged_for_grid_kwh: float
    gross_revenue_cad: float
    net_revenue_cad: float
    charging_cost_cad: float
    round_trip_loss_cost_cad: float
    degradation_cost_cad: float
    aggregator_fee_cad: float
    programme_fee_cad: float
    performance_penalty_cad: float
    per_stream_results: list[ValueStreamRevenueResult]
    estimated_backup_duration_hours: float | None


def dispatch_for_grid_services(
    *,
    battery: BatterySpec,
    reserve_policy: ReservePolicy,
    requested_dispatch_kwh: float,
    value_streams: list[ValueStream],
    committed_kw: float,
    events_this_year: int,
    charging_price_cad_per_kwh: float,
    critical_load_kw: float | None = None,
    performance_penalty_cad: float = 0.0,
) -> BatteryDispatchResult:
    """Dispatch battery energy to the requested value streams, never
    drawing state-of-charge below the reserve policy's floor.

    ``requested_dispatch_kwh`` is clamped to the reserve-respecting
    dispatchable capacity - this is the hard constraint that makes
    "reserved capacity cannot be dispatched" a structural guarantee rather
    than a UI suggestion.
    """
    dispatchable = reserve_policy.dispatchable_kwh(battery)
    reserved = reserve_policy.reserved_kwh(battery)

    actual_dispatch = min(requested_dispatch_kwh, dispatchable)
    if actual_dispatch < 0:
        raise ValueError("requested_dispatch_kwh must be non-negative")

    # Round-trip losses: energy must be drawn from the grid/solar to charge
    # the battery before it can later be discharged; losses are the
    # difference between charge-in and discharge-out.
    charge_in_kwh = actual_dispatch / battery.round_trip_efficiency if battery.round_trip_efficiency else actual_dispatch
    loss_kwh = charge_in_kwh - actual_dispatch
    charging_cost = charge_in_kwh * charging_price_cad_per_kwh
    round_trip_loss_cost = loss_kwh * charging_price_cad_per_kwh

    degradation = calculate_degradation(
        battery=battery, energy_discharged_household_kwh=0.0, energy_discharged_grid_kwh=actual_dispatch
    )

    per_stream_results: list[ValueStreamRevenueResult] = []
    gross_total = 0.0
    aggregator_fee_total = 0.0
    programme_fee_total = 0.0

    for stream in value_streams:
        result = calculate_value_stream_revenue(
            stream,
            dispatched_kwh_for_grid=actual_dispatch,
            committed_kw=committed_kw,
            events_this_year=events_this_year,
        )
        per_stream_results.append(result)
        gross_total += result.gross_revenue_cad
        aggregator_fee_total += result.aggregator_fee_cad
        programme_fee_total += result.annual_fee_cad

    net_revenue = (
        gross_total
        - charging_cost
        - round_trip_loss_cost
        - degradation.degradation_cost_grid_cad
        - aggregator_fee_total
        - programme_fee_total
        - performance_penalty_cad
    )

    backup_hours = None
    if critical_load_kw is not None and critical_load_kw > 0:
        backup_hours = round((reserved * battery.round_trip_efficiency) / critical_load_kw, 2)

    return BatteryDispatchResult(
        reserve_policy_id=reserve_policy.id,
        dispatchable_kwh=round(dispatchable, 2),
        reserved_kwh=round(reserved, 2),
        energy_discharged_for_grid_kwh=round(actual_dispatch, 2),
        gross_revenue_cad=round(gross_total, 2),
        net_revenue_cad=round(net_revenue, 2),
        charging_cost_cad=round(charging_cost, 2),
        round_trip_loss_cost_cad=round(round_trip_loss_cost, 2),
        degradation_cost_cad=degradation.degradation_cost_grid_cad,
        aggregator_fee_cad=round(aggregator_fee_total, 2),
        programme_fee_cad=round(programme_fee_total, 2),
        performance_penalty_cad=round(performance_penalty_cad, 2),
        per_stream_results=per_stream_results,
        estimated_backup_duration_hours=backup_hours,
    )
