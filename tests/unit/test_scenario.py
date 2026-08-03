import pytest

from ontario_home_energy_futures.model.financing import QuoteComponents
from ontario_home_energy_futures.model.scenario import (
    DeclineScenario,
    PriceScenario,
    evaluate_grid_only,
    evaluate_solar_purchase,
)

REFERENCE_PRICE = PriceScenario(
    id="reference", label="Reference", electricity_energy_real=0.015,
    fixed_delivery_real=0.020, variable_delivery_real=0.010, general_inflation=0.020,
)
FLAT_DECLINE = DeclineScenario(id="flat", label="Flat", real_annual_installed_cost_change=0.0)
MODERATE_DECLINE = DeclineScenario(id="moderate", label="Moderate", real_annual_installed_cost_change=0.02)

QUOTE = QuoteComponents(
    panels=6720, inverter=2100, racking=1680, electrical_equipment=1260,
    labour=4200, design_and_engineering=630, permitting=420,
    utility_connection=840, installer_overhead=3150,
)


def test_grid_only_horizon_length():
    result = evaluate_grid_only(
        base_annual_bill_cad=1800, price_scenario=REFERENCE_PRICE, horizon_years=20,
        discount_rate=0.04, fixed_share=0.25, variable_share=0.15, energy_share=0.60,
    )
    assert len(result.annual_cash_flows) == 20
    assert result.initial_cost_cad == 0
    assert result.total_nominal_cad > 0


def test_grid_only_pv_less_than_nominal_with_positive_discount_rate():
    result = evaluate_grid_only(
        base_annual_bill_cad=1800, price_scenario=REFERENCE_PRICE, horizon_years=20,
        discount_rate=0.04, fixed_share=0.25, variable_share=0.15, energy_share=0.60,
    )
    assert result.total_present_value_cad < result.total_nominal_cad


def test_buy_now_has_initial_cost_in_purchase_year():
    result = evaluate_solar_purchase(
        label="Buy now", purchase_year_offset=0, base_annual_bill_cad=1800,
        price_scenario=REFERENCE_PRICE, decline_scenario=FLAT_DECLINE, base_quote=QUOTE,
        group_discount_fraction=0.0, tax_rate=0.13, down_payment_fraction=1.0,
        annual_interest_rate=0.079, loan_term_years=10, is_cash=True, horizon_years=20,
        discount_rate=0.04, fixed_share=0.25, variable_share=0.15, energy_share=0.60,
        annual_grid_bill_after_solar_cad=400, annual_maintenance_cad=150,
        inverter_replacement_year=12, inverter_replacement_cost_cad=1800,
        annual_credits_used_cad=300, total_credits_expired_cad=0,
        total_solar_generation_kwh=8000, total_grid_imports_kwh=2000,
    )
    assert result.initial_cost_cad > 0
    assert result.annual_cash_flows[0].total_nominal_cad >= result.initial_cost_cad


def test_group_discount_reduces_initial_cost():
    no_discount = evaluate_solar_purchase(
        label="Buy now", purchase_year_offset=0, base_annual_bill_cad=1800,
        price_scenario=REFERENCE_PRICE, decline_scenario=FLAT_DECLINE, base_quote=QUOTE,
        group_discount_fraction=0.0, tax_rate=0.13, down_payment_fraction=1.0,
        annual_interest_rate=0.079, loan_term_years=10, is_cash=True, horizon_years=20,
        discount_rate=0.04, fixed_share=0.25, variable_share=0.15, energy_share=0.60,
        annual_grid_bill_after_solar_cad=400, annual_maintenance_cad=150,
        inverter_replacement_year=12, inverter_replacement_cost_cad=1800,
        annual_credits_used_cad=300, total_credits_expired_cad=0,
        total_solar_generation_kwh=8000, total_grid_imports_kwh=2000,
    )
    with_discount = evaluate_solar_purchase(
        label="Buy now with 10% discount", purchase_year_offset=0, base_annual_bill_cad=1800,
        price_scenario=REFERENCE_PRICE, decline_scenario=FLAT_DECLINE, base_quote=QUOTE,
        group_discount_fraction=0.10, tax_rate=0.13, down_payment_fraction=1.0,
        annual_interest_rate=0.079, loan_term_years=10, is_cash=True, horizon_years=20,
        discount_rate=0.04, fixed_share=0.25, variable_share=0.15, energy_share=0.60,
        annual_grid_bill_after_solar_cad=400, annual_maintenance_cad=150,
        inverter_replacement_year=12, inverter_replacement_cost_cad=1800,
        annual_credits_used_cad=300, total_credits_expired_cad=0,
        total_solar_generation_kwh=8000, total_grid_imports_kwh=2000,
    )
    assert with_discount.initial_cost_cad < no_discount.initial_cost_cad
    assert with_discount.group_discount_cad > 0


def test_waiting_delays_initial_cost_year():
    result = evaluate_solar_purchase(
        label="Wait 3 years", purchase_year_offset=3, base_annual_bill_cad=1800,
        price_scenario=REFERENCE_PRICE, decline_scenario=MODERATE_DECLINE, base_quote=QUOTE,
        group_discount_fraction=0.0, tax_rate=0.13, down_payment_fraction=1.0,
        annual_interest_rate=0.079, loan_term_years=10, is_cash=True, horizon_years=20,
        discount_rate=0.04, fixed_share=0.25, variable_share=0.15, energy_share=0.60,
        annual_grid_bill_after_solar_cad=400, annual_maintenance_cad=150,
        inverter_replacement_year=12, inverter_replacement_cost_cad=1800,
        annual_credits_used_cad=300, total_credits_expired_cad=0,
        total_solar_generation_kwh=8000, total_grid_imports_kwh=2000,
    )
    # Years 0-2 should show grid-only-shaped bills (no maintenance, no solar cost).
    assert result.annual_cash_flows[0].solar_maintenance_nominal_cad == 0
    assert result.annual_cash_flows[1].solar_maintenance_nominal_cad == 0
    assert result.annual_cash_flows[2].solar_maintenance_nominal_cad == 0
    # Purchase happens in year 3.
    assert result.annual_cash_flows[3].total_nominal_cad >= result.initial_cost_cad


def test_financed_purchase_has_lower_initial_cost_than_cash():
    cash = evaluate_solar_purchase(
        label="Cash", purchase_year_offset=0, base_annual_bill_cad=1800,
        price_scenario=REFERENCE_PRICE, decline_scenario=FLAT_DECLINE, base_quote=QUOTE,
        group_discount_fraction=0.0, tax_rate=0.13, down_payment_fraction=1.0,
        annual_interest_rate=0.079, loan_term_years=10, is_cash=True, horizon_years=20,
        discount_rate=0.04, fixed_share=0.25, variable_share=0.15, energy_share=0.60,
        annual_grid_bill_after_solar_cad=400, annual_maintenance_cad=150,
        inverter_replacement_year=12, inverter_replacement_cost_cad=1800,
        annual_credits_used_cad=300, total_credits_expired_cad=0,
        total_solar_generation_kwh=8000, total_grid_imports_kwh=2000,
    )
    financed = evaluate_solar_purchase(
        label="Financed", purchase_year_offset=0, base_annual_bill_cad=1800,
        price_scenario=REFERENCE_PRICE, decline_scenario=FLAT_DECLINE, base_quote=QUOTE,
        group_discount_fraction=0.0, tax_rate=0.13, down_payment_fraction=0.10,
        annual_interest_rate=0.079, loan_term_years=10, is_cash=False, horizon_years=20,
        discount_rate=0.04, fixed_share=0.25, variable_share=0.15, energy_share=0.60,
        annual_grid_bill_after_solar_cad=400, annual_maintenance_cad=150,
        inverter_replacement_year=12, inverter_replacement_cost_cad=1800,
        annual_credits_used_cad=300, total_credits_expired_cad=0,
        total_solar_generation_kwh=8000, total_grid_imports_kwh=2000,
    )
    assert financed.initial_cost_cad < cash.initial_cost_cad
    assert financed.financing_interest_cad > 0
    assert cash.financing_interest_cad == 0
