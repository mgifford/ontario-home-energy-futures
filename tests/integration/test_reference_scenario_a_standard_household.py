"""Scenario A: standard household (Ottawa, Hydro Ottawa, 700 kWh/month, no
electrification, no solar). See METHODOLOGY.md and the project brief's
"Reference scenarios and expected behaviour" section.

Expected:
- Reconstructed bill contains electricity and non-electricity components.
- Fixed charges remain even when consumption is reduced.
- Results show nominal and real costs.
"""

from ontario_home_energy_futures.model.bill import DEFAULT_TOU_HOURLY_SHARES, calculate_tou_bill
from ontario_home_energy_futures.model.decline import bill_component_after_years


def test_bill_has_electricity_and_non_electricity_components(hydro_ottawa_rates):
    bill = calculate_tou_bill(
        period="2026-08", consumption_kwh=700, hourly_shares=DEFAULT_TOU_HOURLY_SHARES, rates=hydro_ottawa_rates
    )
    assert bill.electricity_energy_charge_cad > 0
    assert bill.non_electricity_charges_cad > 0
    assert bill.total_cad == round(
        bill.electricity_energy_charge_cad + bill.non_electricity_charges_cad + bill.rebate_cad + bill.tax_cad,
        4,
    )


def test_fixed_charges_remain_when_consumption_reduced(hydro_ottawa_rates):
    normal = calculate_tou_bill(
        period="2026-08", consumption_kwh=700, hourly_shares=DEFAULT_TOU_HOURLY_SHARES, rates=hydro_ottawa_rates
    )
    reduced = calculate_tou_bill(
        period="2026-08", consumption_kwh=50, hourly_shares=DEFAULT_TOU_HOURLY_SHARES, rates=hydro_ottawa_rates
    )
    zero = calculate_tou_bill(
        period="2026-08", consumption_kwh=0, hourly_shares=DEFAULT_TOU_HOURLY_SHARES, rates=hydro_ottawa_rates
    )
    assert normal.fixed_delivery_charge_cad == reduced.fixed_delivery_charge_cad == zero.fixed_delivery_charge_cad
    assert zero.fixed_delivery_charge_cad > 0


def test_nominal_and_real_costs_both_available():
    real, nominal = bill_component_after_years(
        base_value=1200, annual_real_change=0.015, years=10, general_inflation=0.02
    )
    assert real != nominal
    assert real > 0
    assert nominal > 0
