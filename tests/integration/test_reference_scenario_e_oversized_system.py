"""Scenario E: oversized system (low household consumption, large solar
system).

Expected:
- Exports are high.
- Some credits may expire.
- Financial value per generated kWh falls.
- The application warns that production is not equivalent to realized
  savings (verified here via the effective-value metric being materially
  below the retail rate, which is what the rendered warning is based on).
"""

from ontario_home_energy_futures.model.net_metering import NetMeteringLedger
from ontario_home_energy_futures.model.solar import SolarSystemInputs, calculate_annual_monthly_production_kwh


def test_oversized_system_high_exports_and_expired_credits(solar_assumptions):
    inputs = SolarSystemInputs(
        capacity_kw_dc=12.0, orientation="south", shading="none",
        degradation_annual=solar_assumptions["production"]["degradation_annual_default"],
        inverter_efficiency=solar_assumptions["production"]["inverter_efficiency_default"],
        other_system_losses=solar_assumptions["production"]["other_system_losses_default"],
    )
    yield_data = {int(k): float(v) for k, v in solar_assumptions["production"]["regional_monthly_yield_kwh_per_kw"]["ottawa"].items()}
    production = calculate_annual_monthly_production_kwh(
        inputs,
        regional_monthly_yield_kwh_per_kw=yield_data,
        orientation_factors=solar_assumptions["production"]["orientation_factors"],
        shading_factors=solar_assumptions["production"]["shading_estimate_factors"],
        system_age_years=0,
    )

    low_household_demand = 250.0  # kWh/month, well below production
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)

    for month in range(1, 13):
        solar_kwh = production[month]
        direct = min(solar_kwh, low_household_demand) * 0.3
        ledger.process_month(
            period=f"2026-{month:02d}", solar_generation_kwh=solar_kwh, household_demand_kwh=low_household_demand,
            direct_self_consumption_kwh=direct, eligible_energy_rate_cad_per_kwh=0.08, ineligible_charges_cad=40,
        )
    # Continue 6 more months without enough consumption to absorb all credit.
    for month in range(1, 7):
        solar_kwh = production[month]
        direct = min(solar_kwh, low_household_demand) * 0.3
        ledger.process_month(
            period=f"2027-{month:02d}", solar_generation_kwh=solar_kwh, household_demand_kwh=low_household_demand,
            direct_self_consumption_kwh=direct, eligible_energy_rate_cad_per_kwh=0.08, ineligible_charges_cad=40,
        )

    assert ledger.total_exported_kwh > ledger.total_direct_self_consumption_kwh
    assert ledger.total_credit_expired_cad > 0
    assert ledger.effective_value_per_generated_kwh() < 0.08  # below full retail rate
