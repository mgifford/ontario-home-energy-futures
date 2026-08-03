import pytest

from ontario_home_energy_futures.model.solar import (
    SolarSystemInputs,
    calculate_annual_monthly_production_kwh,
    estimate_direct_self_consumption_kwh,
    production_over_horizon_kwh,
)

YIELD = {m: 100.0 for m in range(1, 13)}
ORIENTATION_FACTORS = {"south": 1.0, "southeast": 0.96, "north": 0.65}
SHADING_FACTORS = {"none": 1.0, "light": 0.95, "heavy": 0.65}


def test_production_scales_with_capacity():
    inputs_small = SolarSystemInputs(
        capacity_kw_dc=4, orientation="south", shading="none",
        degradation_annual=0.005, inverter_efficiency=0.97, other_system_losses=0.14,
    )
    inputs_large = SolarSystemInputs(
        capacity_kw_dc=8, orientation="south", shading="none",
        degradation_annual=0.005, inverter_efficiency=0.97, other_system_losses=0.14,
    )
    small = calculate_annual_monthly_production_kwh(
        inputs_small, regional_monthly_yield_kwh_per_kw=YIELD,
        orientation_factors=ORIENTATION_FACTORS, shading_factors=SHADING_FACTORS, system_age_years=0,
    )
    large = calculate_annual_monthly_production_kwh(
        inputs_large, regional_monthly_yield_kwh_per_kw=YIELD,
        orientation_factors=ORIENTATION_FACTORS, shading_factors=SHADING_FACTORS, system_age_years=0,
    )
    assert large[1] == pytest.approx(2 * small[1])


def test_degradation_reduces_production_over_time():
    inputs = SolarSystemInputs(
        capacity_kw_dc=6, orientation="south", shading="none",
        degradation_annual=0.005, inverter_efficiency=0.97, other_system_losses=0.14,
    )
    year0 = calculate_annual_monthly_production_kwh(
        inputs, regional_monthly_yield_kwh_per_kw=YIELD,
        orientation_factors=ORIENTATION_FACTORS, shading_factors=SHADING_FACTORS, system_age_years=0,
    )
    year10 = calculate_annual_monthly_production_kwh(
        inputs, regional_monthly_yield_kwh_per_kw=YIELD,
        orientation_factors=ORIENTATION_FACTORS, shading_factors=SHADING_FACTORS, system_age_years=10,
    )
    assert year10[1] < year0[1]


def test_shading_reduces_production():
    inputs_none = SolarSystemInputs(
        capacity_kw_dc=6, orientation="south", shading="none",
        degradation_annual=0.005, inverter_efficiency=0.97, other_system_losses=0.14,
    )
    inputs_heavy = SolarSystemInputs(
        capacity_kw_dc=6, orientation="south", shading="heavy",
        degradation_annual=0.005, inverter_efficiency=0.97, other_system_losses=0.14,
    )
    no_shade = calculate_annual_monthly_production_kwh(
        inputs_none, regional_monthly_yield_kwh_per_kw=YIELD,
        orientation_factors=ORIENTATION_FACTORS, shading_factors=SHADING_FACTORS, system_age_years=0,
    )
    shaded = calculate_annual_monthly_production_kwh(
        inputs_heavy, regional_monthly_yield_kwh_per_kw=YIELD,
        orientation_factors=ORIENTATION_FACTORS, shading_factors=SHADING_FACTORS, system_age_years=0,
    )
    assert shaded[1] < no_shade[1]


def test_north_orientation_worse_than_south():
    inputs_south = SolarSystemInputs(
        capacity_kw_dc=6, orientation="south", shading="none",
        degradation_annual=0.005, inverter_efficiency=0.97, other_system_losses=0.14,
    )
    inputs_north = SolarSystemInputs(
        capacity_kw_dc=6, orientation="north", shading="none",
        degradation_annual=0.005, inverter_efficiency=0.97, other_system_losses=0.14,
    )
    south = calculate_annual_monthly_production_kwh(
        inputs_south, regional_monthly_yield_kwh_per_kw=YIELD,
        orientation_factors=ORIENTATION_FACTORS, shading_factors=SHADING_FACTORS, system_age_years=0,
    )
    north = calculate_annual_monthly_production_kwh(
        inputs_north, regional_monthly_yield_kwh_per_kw=YIELD,
        orientation_factors=ORIENTATION_FACTORS, shading_factors=SHADING_FACTORS, system_age_years=0,
    )
    assert north[1] < south[1]


def test_unknown_orientation_rejected():
    inputs = SolarSystemInputs(
        capacity_kw_dc=6, orientation="northwest", shading="none",
        degradation_annual=0.005, inverter_efficiency=0.97, other_system_losses=0.14,
    )
    with pytest.raises(ValueError):
        calculate_annual_monthly_production_kwh(
            inputs, regional_monthly_yield_kwh_per_kw=YIELD,
            orientation_factors=ORIENTATION_FACTORS, shading_factors=SHADING_FACTORS, system_age_years=0,
        )


def test_production_over_horizon_returns_all_years():
    inputs = SolarSystemInputs(
        capacity_kw_dc=6, orientation="south", shading="none",
        degradation_annual=0.005, inverter_efficiency=0.97, other_system_losses=0.14,
    )
    result = production_over_horizon_kwh(
        inputs, regional_monthly_yield_kwh_per_kw=YIELD,
        orientation_factors=ORIENTATION_FACTORS, shading_factors=SHADING_FACTORS, horizon_years=20,
    )
    assert set(result.keys()) == set(range(20))


def test_direct_self_consumption_never_exceeds_solar_or_demand():
    hourly_solar = {h: 1.0 / 14 for h in range(6, 20)}
    hourly_load = {h: 1.0 / 24 for h in range(24)}
    self_consumption = estimate_direct_self_consumption_kwh(
        monthly_solar_kwh=500, monthly_demand_kwh=100,
        hourly_solar_shape=hourly_solar, hourly_load_shape=hourly_load,
    )
    assert self_consumption <= 100
    assert self_consumption <= 500
