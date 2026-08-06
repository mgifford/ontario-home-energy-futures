"""Fixed-horizon fairness tests: the core correctness fix for this phase.

Every purchase-year decision must be evaluated over the same calendar
horizon - a household that waits must never receive a longer effective
window than one that buys now. See model/horizon.py and model/scenario_v2.py.
"""

from pathlib import Path

import pytest
import yaml

from ontario_home_energy_futures.model.collective_purchasing import load_collective_tiers
from ontario_home_energy_futures.model.compatibility import CompatibilityMatrix
from ontario_home_energy_futures.model.horizon import FixedHorizon, assert_same_horizon
from ontario_home_energy_futures.model.scenario import PriceScenario
from ontario_home_energy_futures.model.scenario_v2 import evaluate_no_action, evaluate_purchase_decision
from ontario_home_energy_futures.model.technology_decline import load_technology_components
from ontario_home_energy_futures.model.value_streams import ValueStreamStatus, filter_by_status, load_value_streams

REPO_ROOT = Path(__file__).parent.parent.parent

REFERENCE_PRICE = PriceScenario(
    id="reference", label="Reference", electricity_energy_real=0.015,
    fixed_delivery_real=0.020, variable_delivery_real=0.010, general_inflation=0.020,
)

BASE_COSTS = {
    "complete_installed_solar": 18000,
    "home_battery_hardware": 0,
}

COMMON = dict(
    base_annual_bill_cad=1800, price_scenario=REFERENCE_PRICE,
    technology_components=load_technology_components(REPO_ROOT / "assumptions" / "technology_components.yaml"),
    decline_tier="reference",
    collective_tier=load_collective_tiers(REPO_ROOT / "assumptions" / "collective_purchasing.yaml")["individual"],
    tax_rate=0.13, down_payment_fraction=1.0, annual_interest_rate=0.079, loan_term_years=10, is_cash=True,
    discount_rate=0.04, fixed_share=0.25, variable_share=0.15, energy_share=0.60,
    annual_grid_bill_after_purchase_cad=400, annual_maintenance_cad=150, replacement_year_offset=12,
    replacement_cost_cad=1800, annual_credits_used_cad=300,
    value_streams=[], compatibility=CompatibilityMatrix.from_yaml(REPO_ROOT / "assumptions" / "value_stream_compatibility.yaml"),
    committed_kw=0, events_this_year=0, total_solar_generation_kwh=8000, total_grid_imports_kwh=2000,
)


def test_buy_now_and_wait_ten_years_share_identical_calendar_end():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    buy_now = evaluate_purchase_decision(
        label="Buy now", horizon=horizon, purchase_year_offset=0, base_costs_by_component=BASE_COSTS, **COMMON
    )
    wait_ten = evaluate_purchase_decision(
        label="Wait 10 years", horizon=horizon, purchase_year_offset=10, base_costs_by_component=BASE_COSTS, **COMMON
    )
    assert buy_now.horizon.end_year == wait_ten.horizon.end_year == 2046
    assert_same_horizon(buy_now.horizon, wait_ten.horizon)


def test_every_decision_has_exactly_horizon_years_of_cash_flows():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    for offset in (0, 3, 10, 19):
        decision = evaluate_purchase_decision(
            label=f"Wait {offset}", horizon=horizon, purchase_year_offset=offset,
            base_costs_by_component=BASE_COSTS, **COMMON,
        )
        assert len(decision.annual_cash_flows) == 20
        assert decision.annual_cash_flows[0].calendar_year == 2026
        assert decision.annual_cash_flows[-1].calendar_year == 2045


def test_waiting_reduces_active_years_not_extends_window():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    buy_now = evaluate_purchase_decision(
        label="Buy now", horizon=horizon, purchase_year_offset=0, base_costs_by_component=BASE_COSTS, **COMMON
    )
    wait_three = evaluate_purchase_decision(
        label="Wait 3 years", horizon=horizon, purchase_year_offset=3, base_costs_by_component=BASE_COSTS, **COMMON
    )
    assert buy_now.years_active == 20
    assert wait_three.years_active == 17  # NOT 20 - this is the fairness fix


def test_grid_costs_incurred_before_installation_while_waiting():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    wait_three = evaluate_purchase_decision(
        label="Wait 3 years", horizon=horizon, purchase_year_offset=3, base_costs_by_component=BASE_COSTS, **COMMON
    )
    for offset in range(3):
        assert wait_three.annual_cash_flows[offset].grid_bill_nominal_cad > 0
        assert wait_three.annual_cash_flows[offset].maintenance_nominal_cad == 0


def test_no_action_decision_has_zero_installation_cost():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    no_action = evaluate_no_action(
        horizon=horizon, base_annual_bill_cad=1800, price_scenario=REFERENCE_PRICE, discount_rate=0.04,
        fixed_share=0.25, variable_share=0.15, energy_share=0.60,
    )
    assert no_action.initial_cost_cad == 0
    assert all(f.initial_purchase_cost_cad == 0 for f in no_action.annual_cash_flows)


def test_no_action_produces_same_horizon_as_purchase_decisions():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    no_action = evaluate_no_action(
        horizon=horizon, base_annual_bill_cad=1800, price_scenario=REFERENCE_PRICE, discount_rate=0.04,
        fixed_share=0.25, variable_share=0.15, energy_share=0.60,
    )
    buy_now = evaluate_purchase_decision(
        label="Buy now", horizon=horizon, purchase_year_offset=0, base_costs_by_component=BASE_COSTS, **COMMON
    )
    assert_same_horizon(no_action.horizon, buy_now.horizon)


def test_purchase_at_or_beyond_horizon_end_falls_back_to_no_action_shape():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    result = evaluate_purchase_decision(
        label="Wait 25 years (beyond horizon)", horizon=horizon, purchase_year_offset=25,
        base_costs_by_component=BASE_COSTS, **COMMON,
    )
    assert result.initial_cost_cad == 0
    assert len(result.annual_cash_flows) == 20


def test_residual_value_calculated_consistently_across_purchase_years():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    common_with_residual = {**COMMON, "residual_value_fraction": 0.20}
    buy_now = evaluate_purchase_decision(
        label="Buy now", horizon=horizon, purchase_year_offset=0, base_costs_by_component=BASE_COSTS,
        **common_with_residual,
    )
    wait_ten = evaluate_purchase_decision(
        label="Wait 10", horizon=horizon, purchase_year_offset=10, base_costs_by_component=BASE_COSTS,
        **common_with_residual,
    )
    # A system purchased later and used for fewer years within the SAME
    # window should show a smaller residual value than one bought now and
    # used the full window, not an equal or larger one.
    assert wait_ten.residual_value_cad <= buy_now.residual_value_cad
