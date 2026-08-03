import pytest

from ontario_home_energy_futures.model.household import (
    ElectricVehicleInputs,
    HeatPumpInputs,
    HouseholdInputs,
    baseline_from_standard_profile,
    calculate_monthly_demand,
    spread_annual_kwh,
)

SEASONAL_SHAPE = {
    1: 0.1105, 2: 0.1000, 3: 0.0895, 4: 0.0737, 5: 0.0632, 6: 0.0684,
    7: 0.0789, 8: 0.0789, 9: 0.0684, 10: 0.0737, 11: 0.0895, 12: 0.1053,
}


def test_spread_annual_kwh_sums_to_annual_total():
    monthly = spread_annual_kwh(1200, SEASONAL_SHAPE)
    assert sum(monthly.values()) == pytest.approx(1200, abs=0.5)


def test_spread_annual_kwh_rejects_bad_shape():
    with pytest.raises(ValueError):
        spread_annual_kwh(1200, {1: 0.5})


def test_standard_profile_is_flat():
    baseline = baseline_from_standard_profile(700)
    assert all(v == 700 for v in baseline.values())
    assert len(baseline) == 12


def test_demand_with_no_additions_equals_baseline():
    baseline = baseline_from_standard_profile(700)
    inputs = HouseholdInputs(baseline_monthly_kwh=baseline)
    demand = calculate_monthly_demand(inputs, seasonal_shape=SEASONAL_SHAPE)
    assert demand == baseline


def test_ev_addition_increases_demand():
    baseline = baseline_from_standard_profile(700)
    ev = ElectricVehicleInputs(annual_km=15000, efficiency_kwh_per_100km=18.0, home_charging_share=0.8)
    inputs = HouseholdInputs(baseline_monthly_kwh=baseline, ev=ev)
    demand = calculate_monthly_demand(inputs, seasonal_shape=SEASONAL_SHAPE)
    assert sum(demand.values()) > sum(baseline.values())
    assert sum(demand.values()) - sum(baseline.values()) == pytest.approx(ev.annual_kwh(), abs=0.5)


def test_heat_pump_addition():
    baseline = baseline_from_standard_profile(700)
    hp = HeatPumpInputs(annual_heating_kwh_equivalent=18000, seasonal_cop=2.8)
    inputs = HouseholdInputs(baseline_monthly_kwh=baseline, heat_pump=hp)
    demand = calculate_monthly_demand(inputs, seasonal_shape=SEASONAL_SHAPE)
    added = sum(demand.values()) - sum(baseline.values())
    assert added == pytest.approx(18000 / 2.8, abs=0.5)


def test_efficiency_savings_reduce_demand():
    baseline = baseline_from_standard_profile(700)
    inputs = HouseholdInputs(baseline_monthly_kwh=baseline, efficiency_savings_annual_kwh=1200)
    demand = calculate_monthly_demand(inputs, seasonal_shape=SEASONAL_SHAPE)
    assert sum(demand.values()) < sum(baseline.values())


def test_provincial_demand_growth_not_conflated_with_household_demand():
    # This model has no code path that ingests a provincial demand-growth
    # percentage as a household consumption input; asserting the inputs
    # dataclass has no such field guards against that regression.
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(HouseholdInputs)}
    assert "provincial_demand_growth" not in field_names
    assert "system_demand_growth" not in field_names


def test_invalid_baseline_keys_rejected():
    with pytest.raises(ValueError):
        calculate_monthly_demand(
            HouseholdInputs(baseline_monthly_kwh={1: 100}), seasonal_shape=SEASONAL_SHAPE
        )
