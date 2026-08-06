"""Electric-vehicle battery scenario model: managed charging, vehicle-to-
home (V2H), and vehicle-to-grid (V2G).

See the project brief's "Electric-car battery scenarios" section,
METHODOLOGY.md section 20, and ``assumptions/ev.yaml``. Only incremental
bidirectional-equipment cost is modelled - never the vehicle purchase
price. A vehicle away from home cannot dispatch, and driving-energy
requirement plus minimum departure charge are always reserved before any
capacity is considered available for grid export.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .value_streams import ValueStream, ValueStreamRevenueResult, calculate_value_stream_revenue


class EvMode(str, Enum):
    MANAGED_CHARGING = "managed_charging"
    VEHICLE_TO_HOME = "vehicle_to_home"
    VEHICLE_TO_GRID = "vehicle_to_grid"


@dataclass(frozen=True)
class VehicleSpec:
    battery_capacity_kwh: float
    minimum_departure_charge_kwh: float
    driving_energy_kwh_per_day: float
    arrival_hour: int  # 0-23, hour vehicle typically returns home
    departure_hour: int  # 0-23, hour vehicle typically leaves
    days_present_per_week: int
    charger_power_kw: float
    export_capability: bool


@dataclass(frozen=True)
class IncrementalEquipmentCost:
    bidirectional_charger_hardware_cad: float
    bidirectional_charger_installation_cad: float

    def total(self) -> float:
        return self.bidirectional_charger_hardware_cad + self.bidirectional_charger_installation_cad


def hours_present_per_day(vehicle: VehicleSpec) -> int:
    """Number of hours per day the vehicle is present at home, handling an
    overnight arrival/departure window (e.g. arrive 18:00, depart 07:00).
    """
    if vehicle.arrival_hour == vehicle.departure_hour:
        return 24
    if vehicle.arrival_hour < vehicle.departure_hour:
        return vehicle.departure_hour - vehicle.arrival_hour
    return (24 - vehicle.arrival_hour) + vehicle.departure_hour


def available_dispatch_kwh(vehicle: VehicleSpec, mode: EvMode) -> float:
    """Battery capacity available for household backup (V2H) or grid
    export (V2G) after reserving the minimum departure charge and the
    day's driving-energy requirement.

    Managed charging never has export capacity, by definition - it does
    not export at all, so this always returns 0 for that mode, matching
    "the EV cannot dispatch while away" being moot for a mode that never
    dispatches in the first place.
    """
    if mode == EvMode.MANAGED_CHARGING:
        return 0.0
    if mode in (EvMode.VEHICLE_TO_HOME, EvMode.VEHICLE_TO_GRID) and not vehicle.export_capability:
        return 0.0

    reserved = vehicle.minimum_departure_charge_kwh + vehicle.driving_energy_kwh_per_day
    available = vehicle.battery_capacity_kwh - reserved
    return max(0.0, available)


@dataclass(frozen=True)
class EvDispatchResult:
    mode: EvMode
    hours_present_today: int
    available_dispatch_kwh: float
    energy_dispatched_kwh: float
    gross_revenue_cad: float
    net_revenue_cad: float
    degradation_cost_cad: float
    incremental_equipment_cost_cad: float
    per_stream_results: list[ValueStreamRevenueResult]
    dispatch_rejected_reason: str | None


def dispatch_ev(
    *,
    vehicle: VehicleSpec,
    mode: EvMode,
    is_present_now: bool,
    requested_dispatch_kwh: float,
    value_streams: list[ValueStream],
    committed_kw: float,
    events_this_year: int,
    degradation_cad_per_kwh: float,
    incremental_equipment: IncrementalEquipmentCost | None = None,
) -> EvDispatchResult:
    """Dispatch an EV for grid services, enforcing:

    - the vehicle cannot dispatch while away (``is_present_now`` gate),
    - the minimum departure charge and daily driving energy are always
      reserved before any capacity is exportable,
    - managed-charging mode never exports,
    - vehicle-to-grid requires ``export_capability``.
    """
    equipment_cost = incremental_equipment.total() if incremental_equipment else 0.0

    if not is_present_now:
        return EvDispatchResult(
            mode=mode, hours_present_today=hours_present_per_day(vehicle), available_dispatch_kwh=0.0,
            energy_dispatched_kwh=0.0, gross_revenue_cad=0.0, net_revenue_cad=0.0,
            degradation_cost_cad=0.0, incremental_equipment_cost_cad=equipment_cost,
            per_stream_results=[], dispatch_rejected_reason="vehicle is away from home",
        )

    if requested_dispatch_kwh < 0:
        raise ValueError("requested_dispatch_kwh must be non-negative")

    available = available_dispatch_kwh(vehicle, mode)
    actual_dispatch = min(requested_dispatch_kwh, available)

    rejected_reason = None
    if mode == EvMode.MANAGED_CHARGING and requested_dispatch_kwh > 0:
        rejected_reason = "managed charging mode does not export"
    elif mode == EvMode.VEHICLE_TO_GRID and not vehicle.export_capability:
        rejected_reason = "vehicle lacks export capability for vehicle-to-grid"

    per_stream_results: list[ValueStreamRevenueResult] = []
    gross_total = 0.0
    for stream in value_streams:
        result = calculate_value_stream_revenue(
            stream, dispatched_kwh_for_grid=actual_dispatch, committed_kw=committed_kw,
            events_this_year=events_this_year,
        )
        per_stream_results.append(result)
        gross_total += result.gross_revenue_cad

    degradation_cost = actual_dispatch * degradation_cad_per_kwh
    net_revenue = gross_total - degradation_cost

    return EvDispatchResult(
        mode=mode,
        hours_present_today=hours_present_per_day(vehicle),
        available_dispatch_kwh=round(available, 2),
        energy_dispatched_kwh=round(actual_dispatch, 2),
        gross_revenue_cad=round(gross_total, 2),
        net_revenue_cad=round(net_revenue, 2),
        degradation_cost_cad=round(degradation_cost, 2),
        incremental_equipment_cost_cad=round(equipment_cost, 2),
        per_stream_results=per_stream_results,
        dispatch_rejected_reason=rejected_reason,
    )
