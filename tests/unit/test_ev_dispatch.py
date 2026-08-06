from pathlib import Path

import pytest

from ontario_home_energy_futures.model.ev_dispatch import (
    EvMode,
    IncrementalEquipmentCost,
    VehicleSpec,
    available_dispatch_kwh,
    dispatch_ev,
    hours_present_per_day,
)
from ontario_home_energy_futures.model.value_streams import load_value_streams

REPO_ROOT = Path(__file__).parent.parent.parent
VALUE_STREAMS_DIR = REPO_ROOT / "assumptions" / "value_streams"

VEHICLE = VehicleSpec(
    battery_capacity_kwh=75.0,
    minimum_departure_charge_kwh=30.0,
    driving_energy_kwh_per_day=12.0,
    arrival_hour=18,
    departure_hour=7,
    days_present_per_week=5,
    charger_power_kw=7.2,
    export_capability=True,
)

VEHICLE_NO_EXPORT = VehicleSpec(
    battery_capacity_kwh=75.0,
    minimum_departure_charge_kwh=30.0,
    driving_energy_kwh_per_day=12.0,
    arrival_hour=18,
    departure_hour=7,
    days_present_per_week=5,
    charger_power_kw=7.2,
    export_capability=False,
)


@pytest.fixture(scope="module")
def all_streams():
    return load_value_streams(VALUE_STREAMS_DIR)


def test_hours_present_overnight_window():
    assert hours_present_per_day(VEHICLE) == 13  # 18:00 -> 07:00


def test_hours_present_same_hour_means_always_present():
    vehicle = VehicleSpec(**{**VEHICLE.__dict__, "arrival_hour": 8, "departure_hour": 8})
    assert hours_present_per_day(vehicle) == 24


def test_managed_charging_never_has_export_capacity():
    assert available_dispatch_kwh(VEHICLE, EvMode.MANAGED_CHARGING) == 0.0


def test_driving_requirement_and_departure_charge_reserved_first():
    available = available_dispatch_kwh(VEHICLE, EvMode.VEHICLE_TO_GRID)
    # 75 - 30 (min departure) - 12 (driving) = 33
    assert available == pytest.approx(33.0)


def test_no_export_capability_vehicle_has_zero_v2g_availability():
    assert available_dispatch_kwh(VEHICLE_NO_EXPORT, EvMode.VEHICLE_TO_GRID) == 0.0


def test_vehicle_cannot_dispatch_while_away(all_streams):
    stream = all_streams["bidirectional-ev-export-revenue"]
    result = dispatch_ev(
        vehicle=VEHICLE, mode=EvMode.VEHICLE_TO_GRID, is_present_now=False,
        requested_dispatch_kwh=10, value_streams=[stream], committed_kw=5,
        events_this_year=15, degradation_cad_per_kwh=0.05,
    )
    assert result.energy_dispatched_kwh == 0
    assert result.gross_revenue_cad == 0
    assert result.dispatch_rejected_reason == "vehicle is away from home"


def test_minimum_departure_charge_preserved_in_dispatch_result(all_streams):
    stream = all_streams["bidirectional-ev-export-revenue"]
    result = dispatch_ev(
        vehicle=VEHICLE, mode=EvMode.VEHICLE_TO_GRID, is_present_now=True,
        requested_dispatch_kwh=999,  # try to over-dispatch
        value_streams=[stream], committed_kw=5, events_this_year=15, degradation_cad_per_kwh=0.05,
    )
    # Even an enormous request is capped at the 33 kWh available after
    # reserving departure charge + driving energy.
    assert result.energy_dispatched_kwh == pytest.approx(33.0)


def test_only_incremental_bidirectional_cost_included_not_vehicle_price():
    equipment = IncrementalEquipmentCost(
        bidirectional_charger_hardware_cad=4500, bidirectional_charger_installation_cad=2000
    )
    result = dispatch_ev(
        vehicle=VEHICLE, mode=EvMode.MANAGED_CHARGING, is_present_now=True,
        requested_dispatch_kwh=0, value_streams=[], committed_kw=0, events_this_year=0,
        degradation_cad_per_kwh=0.05, incremental_equipment=equipment,
    )
    assert result.incremental_equipment_cost_cad == 6500
    # Nowhere in this result does a vehicle purchase price appear.


def test_vehicle_to_grid_excluded_when_no_export_capability(all_streams):
    stream = all_streams["bidirectional-ev-export-revenue"]
    result = dispatch_ev(
        vehicle=VEHICLE_NO_EXPORT, mode=EvMode.VEHICLE_TO_GRID, is_present_now=True,
        requested_dispatch_kwh=10, value_streams=[stream], committed_kw=5,
        events_this_year=15, degradation_cad_per_kwh=0.05,
    )
    assert result.energy_dispatched_kwh == 0
    assert result.dispatch_rejected_reason is not None


def test_managed_charging_mode_never_exports(all_streams):
    stream = all_streams["bidirectional-ev-export-revenue"]
    result = dispatch_ev(
        vehicle=VEHICLE, mode=EvMode.MANAGED_CHARGING, is_present_now=True,
        requested_dispatch_kwh=10, value_streams=[stream], committed_kw=5,
        events_this_year=15, degradation_cad_per_kwh=0.05,
    )
    assert result.energy_dispatched_kwh == 0
    assert result.dispatch_rejected_reason == "managed charging mode does not export"


def test_gross_and_net_revenue_differ_with_degradation(all_streams):
    stream = all_streams["bidirectional-ev-export-revenue"]
    result = dispatch_ev(
        vehicle=VEHICLE, mode=EvMode.VEHICLE_TO_GRID, is_present_now=True,
        requested_dispatch_kwh=10, value_streams=[stream], committed_kw=5,
        events_this_year=15, degradation_cad_per_kwh=0.05,
    )
    assert result.net_revenue_cad < result.gross_revenue_cad
    assert result.degradation_cost_cad > 0


def test_negative_dispatch_rejected():
    with pytest.raises(ValueError):
        dispatch_ev(
            vehicle=VEHICLE, mode=EvMode.VEHICLE_TO_GRID, is_present_now=True,
            requested_dispatch_kwh=-1, value_streams=[], committed_kw=0, events_this_year=0,
            degradation_cad_per_kwh=0.05,
        )


def test_zero_driving_energy_maximizes_available_capacity():
    no_driving_vehicle = VehicleSpec(**{**VEHICLE.__dict__, "driving_energy_kwh_per_day": 0.0})
    available = available_dispatch_kwh(no_driving_vehicle, EvMode.VEHICLE_TO_HOME)
    assert available == pytest.approx(75.0 - 30.0)
