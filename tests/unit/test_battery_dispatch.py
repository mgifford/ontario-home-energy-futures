from pathlib import Path

import pytest

from ontario_home_energy_futures.model.battery_dispatch import (
    BatterySpec,
    ReservePolicy,
    calculate_degradation,
    dispatch_for_grid_services,
)
from ontario_home_energy_futures.model.value_streams import load_value_streams

REPO_ROOT = Path(__file__).parent.parent.parent
VALUE_STREAMS_DIR = REPO_ROOT / "assumptions" / "value_streams"

BATTERY = BatterySpec(
    usable_capacity_kwh=13.5,
    max_continuous_output_kw=5.0,
    round_trip_efficiency=0.90,
    degradation_annual=0.02,
    expected_lifetime_throughput_kwh=40000,
    replacement_cost_cad=12000,
)


@pytest.fixture(scope="module")
def all_streams():
    return load_value_streams(VALUE_STREAMS_DIR)


def test_backup_only_policy_leaves_nothing_dispatchable():
    policy = ReservePolicy(id="backup_only", label="Backup only", minimum_reserve_fraction=1.0)
    assert policy.dispatchable_kwh(BATTERY) == 0
    assert policy.reserved_kwh(BATTERY) == BATTERY.usable_capacity_kwh


def test_maximum_participation_policy_leaves_most_dispatchable():
    policy = ReservePolicy(id="maximum", label="Maximum", minimum_reserve_fraction=0.20)
    assert policy.dispatchable_kwh(BATTERY) == pytest.approx(13.5 * 0.80)
    assert policy.reserved_kwh(BATTERY) == pytest.approx(13.5 * 0.20)


def test_dispatch_never_exceeds_reserve_respecting_capacity(all_streams):
    policy = ReservePolicy(id="conservative", label="Conservative", minimum_reserve_fraction=0.70)
    stream = all_streams["vpp-event-payment"]
    result = dispatch_for_grid_services(
        battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=999,  # way more than allowed
        value_streams=[stream], committed_kw=5, events_this_year=20, charging_price_cad_per_kwh=0.10,
    )
    max_allowed = policy.dispatchable_kwh(BATTERY)
    assert result.energy_discharged_for_grid_kwh <= max_allowed + 1e-9


def test_backup_only_policy_dispatches_zero_regardless_of_request(all_streams):
    policy = ReservePolicy(id="backup_only", label="Backup only", minimum_reserve_fraction=1.0)
    stream = all_streams["vpp-event-payment"]
    result = dispatch_for_grid_services(
        battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=10,
        value_streams=[stream], committed_kw=5, events_this_year=20, charging_price_cad_per_kwh=0.10,
    )
    assert result.energy_discharged_for_grid_kwh == 0
    assert result.gross_revenue_cad == 0
    assert result.net_revenue_cad == 0


def test_gross_and_net_revenue_differ_when_costs_present(all_streams):
    policy = ReservePolicy(id="balanced", label="Balanced", minimum_reserve_fraction=0.40)
    stream = all_streams["vpp-event-payment"]
    result = dispatch_for_grid_services(
        battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=5,
        value_streams=[stream], committed_kw=5, events_this_year=20, charging_price_cad_per_kwh=0.10,
    )
    assert result.gross_revenue_cad != result.net_revenue_cad
    assert result.net_revenue_cad < result.gross_revenue_cad


def test_charging_cost_deducted(all_streams):
    policy = ReservePolicy(id="balanced", label="Balanced", minimum_reserve_fraction=0.40)
    stream = all_streams["vpp-event-payment"]
    result = dispatch_for_grid_services(
        battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=5,
        value_streams=[stream], committed_kw=5, events_this_year=20, charging_price_cad_per_kwh=0.10,
    )
    assert result.charging_cost_cad > 0


def test_round_trip_losses_included(all_streams):
    policy = ReservePolicy(id="balanced", label="Balanced", minimum_reserve_fraction=0.40)
    stream = all_streams["vpp-event-payment"]
    result = dispatch_for_grid_services(
        battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=5,
        value_streams=[stream], committed_kw=5, events_this_year=20, charging_price_cad_per_kwh=0.10,
    )
    assert result.round_trip_loss_cost_cad > 0


def test_aggregator_share_deducted(all_streams):
    policy = ReservePolicy(id="balanced", label="Balanced", minimum_reserve_fraction=0.40)
    stream = all_streams["vpp-event-payment"]  # 20% aggregator share
    result = dispatch_for_grid_services(
        battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=5,
        value_streams=[stream], committed_kw=5, events_this_year=20, charging_price_cad_per_kwh=0.10,
    )
    assert result.aggregator_fee_cad > 0


def test_negative_dispatch_request_rejected():
    policy = ReservePolicy(id="balanced", label="Balanced", minimum_reserve_fraction=0.40)
    with pytest.raises(ValueError):
        dispatch_for_grid_services(
            battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=-5,
            value_streams=[], committed_kw=5, events_this_year=0, charging_price_cad_per_kwh=0.10,
        )


def test_degradation_attributed_separately_household_vs_grid():
    result = calculate_degradation(
        battery=BATTERY, energy_discharged_household_kwh=1000, energy_discharged_grid_kwh=200
    )
    assert result.degradation_cost_household_cad > 0
    assert result.degradation_cost_grid_cad > 0
    assert result.degradation_cost_household_cad != result.degradation_cost_grid_cad
    # household discharged 5x more energy, so its degradation cost should be ~5x
    assert result.degradation_cost_household_cad == pytest.approx(result.degradation_cost_grid_cad * 5, rel=0.01)


def test_annual_equivalent_full_cycles_computed():
    result = calculate_degradation(
        battery=BATTERY, energy_discharged_household_kwh=BATTERY.usable_capacity_kwh * 2, energy_discharged_grid_kwh=0
    )
    assert result.annual_equivalent_full_cycles == pytest.approx(2.0, abs=0.01)


def test_backup_duration_reported_when_critical_load_given(all_streams):
    policy = ReservePolicy(id="conservative", label="Conservative", minimum_reserve_fraction=0.70)
    stream = all_streams["vpp-event-payment"]
    result = dispatch_for_grid_services(
        battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=1,
        value_streams=[stream], committed_kw=5, events_this_year=5, charging_price_cad_per_kwh=0.10,
        critical_load_kw=1.0,
    )
    assert result.estimated_backup_duration_hours is not None
    assert result.estimated_backup_duration_hours > 0


def test_performance_penalty_reduces_net_revenue(all_streams):
    policy = ReservePolicy(id="balanced", label="Balanced", minimum_reserve_fraction=0.40)
    stream = all_streams["vpp-event-payment"]
    no_penalty = dispatch_for_grid_services(
        battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=5,
        value_streams=[stream], committed_kw=5, events_this_year=20, charging_price_cad_per_kwh=0.10,
        performance_penalty_cad=0,
    )
    with_penalty = dispatch_for_grid_services(
        battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=5,
        value_streams=[stream], committed_kw=5, events_this_year=20, charging_price_cad_per_kwh=0.10,
        performance_penalty_cad=50,
    )
    assert with_penalty.net_revenue_cad == pytest.approx(no_penalty.net_revenue_cad - 50, abs=0.01)


def test_double_stream_stacking_sums_gross_revenue(all_streams):
    # vpp-availability + vpp-event are explicitly allowed to stack per the
    # compatibility matrix - confirming both streams' revenue is included
    # when passed together (compatibility filtering happens upstream in
    # scenario_v2.py, not inside dispatch_for_grid_services itself).
    policy = ReservePolicy(id="balanced", label="Balanced", minimum_reserve_fraction=0.40)
    availability = all_streams["vpp-availability-payment"]
    event = all_streams["vpp-event-payment"]
    result = dispatch_for_grid_services(
        battery=BATTERY, reserve_policy=policy, requested_dispatch_kwh=5,
        value_streams=[availability, event], committed_kw=5, events_this_year=20, charging_price_cad_per_kwh=0.10,
    )
    assert len(result.per_stream_results) == 2
