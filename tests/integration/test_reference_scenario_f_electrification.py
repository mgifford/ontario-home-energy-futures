"""Scenario F: electrification (add EV and heat pump; compare no solar,
solar, and delayed solar).

Expected:
- Household kWh increases.
- Provincial demand is not added directly to household kWh.
- Greater household consumption may increase usable solar value.
- Seasonal mismatch remains visible.
"""

from ontario_home_energy_futures.model.household import (
    ElectricVehicleInputs,
    HeatPumpInputs,
    HouseholdInputs,
    baseline_from_standard_profile,
    calculate_monthly_demand,
)
from ontario_home_energy_futures.model.solar import estimate_direct_self_consumption_kwh


def test_household_kwh_increases_with_electrification(household_loads_assumptions):
    seasonal_shape = household_loads_assumptions["seasonal_shape_annual_to_monthly"]
    seasonal_shape = {k: v for k, v in seasonal_shape.items() if isinstance(k, int)}

    baseline = baseline_from_standard_profile(700)
    no_electrification = HouseholdInputs(baseline_monthly_kwh=baseline)

    ev = ElectricVehicleInputs(annual_km=15000, efficiency_kwh_per_100km=18.0, home_charging_share=0.8)
    hp = HeatPumpInputs(annual_heating_kwh_equivalent=18000, seasonal_cop=2.8)
    with_electrification = HouseholdInputs(baseline_monthly_kwh=baseline, ev=ev, heat_pump=hp)

    demand_before = calculate_monthly_demand(no_electrification, seasonal_shape=seasonal_shape)
    demand_after = calculate_monthly_demand(with_electrification, seasonal_shape=seasonal_shape)

    assert sum(demand_after.values()) > sum(demand_before.values())


def test_provincial_demand_not_added_directly_to_household_kwh(ontario_assumptions):
    # The provincial demand-growth figure lives only in assumptions/ontario.yaml
    # and is never referenced by the household calculation function's inputs.
    provincial_growth = ontario_assumptions["provincial_demand_scenarios"]["growth_to_2050"]["reference"]
    assert provincial_growth == 0.65  # sanity: the documented figure is present

    baseline = baseline_from_standard_profile(700)
    inputs = HouseholdInputs(baseline_monthly_kwh=baseline)
    demand = calculate_monthly_demand(inputs, seasonal_shape={m: 1 / 12 for m in range(1, 13)})
    # Household demand must equal baseline exactly - no provincial-growth
    # term is applied anywhere in this calculation.
    assert demand == baseline


def test_higher_consumption_increases_usable_solar_self_consumption():
    hourly_solar = {h: 1.0 / 14 for h in range(6, 20)}
    hourly_load_low = {h: (1.0 / 24) for h in range(24)}
    hourly_load_high = {h: (1.0 / 24) * 1.5 if 6 <= h < 20 else (1.0 / 24) * 0.7 for h in range(24)}

    low_self_consumption = estimate_direct_self_consumption_kwh(
        monthly_solar_kwh=600, monthly_demand_kwh=400,
        hourly_solar_shape=hourly_solar, hourly_load_shape=hourly_load_low,
    )
    high_self_consumption = estimate_direct_self_consumption_kwh(
        monthly_solar_kwh=600, monthly_demand_kwh=700,
        hourly_solar_shape=hourly_solar, hourly_load_shape=hourly_load_high,
    )
    assert high_self_consumption >= low_self_consumption


def test_seasonal_mismatch_visible_between_winter_heating_and_summer_solar(solar_assumptions, household_loads_assumptions):
    # Winter heat-pump load is high while winter solar yield is low - the
    # mismatch should be visible by comparing January to July.
    yield_data = solar_assumptions["production"]["regional_monthly_yield_kwh_per_kw"]["ottawa"]
    assert yield_data[1] < yield_data[7]  # January solar << July solar

    seasonal_shape = household_loads_assumptions["seasonal_shape_annual_to_monthly"]
    seasonal_shape = {k: v for k, v in seasonal_shape.items() if isinstance(k, int)}
    assert seasonal_shape[1] > seasonal_shape[7]  # January household demand > July
