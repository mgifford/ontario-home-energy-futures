"""Scenario B: solar now (same household, 7 kW system, user-entered quote,
cash purchase, no group discount).

Expected:
- Solar production varies by month.
- Direct consumption and exports are separate.
- Net-metering credits offset only eligible charges.
- Fixed bill charges remain.
- Unused credits can expire.
"""

from ontario_home_energy_futures.model.financing import QuoteComponents, apply_group_discount
from ontario_home_energy_futures.model.net_metering import NetMeteringLedger
from ontario_home_energy_futures.model.solar import SolarSystemInputs, calculate_annual_monthly_production_kwh


def test_solar_production_varies_by_month(solar_assumptions):
    inputs = SolarSystemInputs(
        capacity_kw_dc=7.0, orientation="south", shading="none",
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
    values = list(production.values())
    assert len(set(values)) > 1  # not flat across all 12 months
    assert production[7] > production[1]  # July > January production


def test_direct_consumption_and_exports_kept_separate():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    result = ledger.process_month(
        period="2026-06", solar_generation_kwh=900, household_demand_kwh=700,
        direct_self_consumption_kwh=300, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=45,
    )
    assert result.direct_self_consumption_kwh == 300
    assert result.exported_kwh == 600
    assert result.direct_self_consumption_kwh != result.exported_kwh


def test_credits_offset_only_eligible_charges():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    ledger.process_month(
        period="2026-06", solar_generation_kwh=1200, household_demand_kwh=300,
        direct_self_consumption_kwh=200, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=45,
    )
    result = ledger.process_month(
        period="2026-07", solar_generation_kwh=0, household_demand_kwh=700,
        direct_self_consumption_kwh=0, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=45,
    )
    assert result.eligible_charge_after_credits_cad < result.eligible_charge_before_credits_cad
    assert result.ineligible_charges_cad == 45  # untouched by credits


def test_no_group_discount_cash_purchase_full_price():
    quote = QuoteComponents(panels=6720, inverter=2100, labour=4200, installer_overhead=3150)
    result = apply_group_discount(quote, 0.0)
    assert result.discount_amount == 0
    assert result.total_after_discount == quote.total()


def test_unused_credits_can_expire():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    ledger.process_month(
        period="2026-01", solar_generation_kwh=1000, household_demand_kwh=100,
        direct_self_consumption_kwh=80, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=10,
    )
    for m in range(2, 13):
        ledger.process_month(
            period=f"2026-{m:02d}", solar_generation_kwh=0, household_demand_kwh=0,
            direct_self_consumption_kwh=0, eligible_energy_rate_cad_per_kwh=0.08,
            ineligible_charges_cad=0,
        )
    result = ledger.process_month(
        period="2027-01", solar_generation_kwh=0, household_demand_kwh=0,
        direct_self_consumption_kwh=0, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=0,
    )
    assert result.credit_expired_cad > 0
