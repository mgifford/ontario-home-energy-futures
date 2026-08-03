"""Scenario D: wait for lower solar cost (same household, three-year wait,
2% real annual solar-cost decline, reference electricity-price scenario).

Expected:
- Grid costs continue during the waiting period.
- Future solar price is lower in real terms.
- Lost solar savings are included.
- Result compares waiting with buying now.
"""

from ontario_home_energy_futures.model.decline import installed_cost_after_years
from ontario_home_energy_futures.model.financing import QuoteComponents
from ontario_home_energy_futures.model.scenario import (
    DeclineScenario,
    PriceScenario,
    evaluate_solar_purchase,
)

REFERENCE_PRICE = PriceScenario(
    id="reference", label="Reference", electricity_energy_real=0.015,
    fixed_delivery_real=0.020, variable_delivery_real=0.010, general_inflation=0.020,
)
TWO_PCT_DECLINE = DeclineScenario(id="two-pct", label="2% decline", real_annual_installed_cost_change=0.02)
QUOTE = QuoteComponents(panels=6720, inverter=2100, labour=4200, installer_overhead=3150)

COMMON = dict(
    base_annual_bill_cad=1800, price_scenario=REFERENCE_PRICE, decline_scenario=TWO_PCT_DECLINE,
    base_quote=QUOTE, group_discount_fraction=0.0, tax_rate=0.13, down_payment_fraction=1.0,
    annual_interest_rate=0.079, loan_term_years=10, is_cash=True, horizon_years=20,
    discount_rate=0.04, fixed_share=0.25, variable_share=0.15, energy_share=0.60,
    annual_grid_bill_after_solar_cad=400, annual_maintenance_cad=150,
    inverter_replacement_year=12, inverter_replacement_cost_cad=1800,
    annual_credits_used_cad=300, total_credits_expired_cad=0,
    total_solar_generation_kwh=8000, total_grid_imports_kwh=2000,
)


def test_future_solar_price_lower_in_real_terms():
    real_now, _ = installed_cost_after_years(base_cost=QUOTE.total(), annual_real_decline=0.02, years=0)
    real_in_3_years, _ = installed_cost_after_years(base_cost=QUOTE.total(), annual_real_decline=0.02, years=3)
    assert real_in_3_years < real_now


def test_grid_costs_continue_during_waiting_period():
    result = evaluate_solar_purchase(label="Wait 3 years", purchase_year_offset=3, **COMMON)
    for year in range(3):
        assert result.annual_cash_flows[year].grid_bill_nominal_cad > 0
        assert result.annual_cash_flows[year].solar_maintenance_nominal_cad == 0


def test_lost_solar_savings_included_via_higher_early_year_bills():
    buy_now = evaluate_solar_purchase(
        label="Buy now", purchase_year_offset=0, **{**COMMON, "decline_scenario": TWO_PCT_DECLINE}
    )
    wait_3yr = evaluate_solar_purchase(
        label="Wait 3 years", purchase_year_offset=3, **{**COMMON, "decline_scenario": TWO_PCT_DECLINE}
    )
    # Buying now should show lower grid bills in years 0-2 than waiting,
    # since solar is already offsetting consumption.
    for year in range(3):
        assert buy_now.annual_cash_flows[year].grid_bill_nominal_cad <= wait_3yr.annual_cash_flows[year].grid_bill_nominal_cad


def test_result_compares_waiting_with_buying_now():
    buy_now = evaluate_solar_purchase(label="Buy now", purchase_year_offset=0, **COMMON)
    wait_3yr = evaluate_solar_purchase(label="Wait 3 years", purchase_year_offset=3, **COMMON)
    assert buy_now.total_present_value_cad != wait_3yr.total_present_value_cad
    assert buy_now.purchase_year_offset == 0
    assert wait_3yr.purchase_year_offset == 3
