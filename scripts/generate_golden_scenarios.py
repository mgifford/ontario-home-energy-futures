#!/usr/bin/env python3
"""Generate tests/fixtures/golden_scenarios.json by running the actual
Python model (model/scenario.py, model/waiting.py) and snapshotting its
real output.

This is deliberately NOT a hand-authored fixture: every "expected" value
below is produced by calling the real Python functions, so the fixture is
guaranteed to reflect Python's actual current behaviour. The companion JS
port (web/static/calculator.js) is then checked against these same
numbers by tests/js/test_golden_scenarios.mjs. If Python's behaviour
changes intentionally, re-run this script to regenerate the fixture
(after confirming the change was intentional, not a bug).

Usage:
    python3 scripts/generate_golden_scenarios.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ontario_home_energy_futures.model.collective_purchasing import (  # noqa: E402
    CollectiveTier,
    apply_collective_purchase,
)
from ontario_home_energy_futures.model.cost_of_inaction import (  # noqa: E402
    DecisionCostInputs,
    calculate_cost_of_inaction,
)
from ontario_home_energy_futures.model.decline import bill_component_after_years  # noqa: E402
from ontario_home_energy_futures.model.financing import (  # noqa: E402
    QuoteComponents,
    amortize_loan,
    apply_group_discount,
)
from ontario_home_energy_futures.model.net_metering import NetMeteringLedger  # noqa: E402
from ontario_home_energy_futures.model.scenario import (  # noqa: E402
    DeclineScenario,
    PriceScenario,
    evaluate_grid_only,
    evaluate_solar_purchase,
)
from ontario_home_energy_futures.model.solar import (  # noqa: E402
    SolarSystemInputs,
    calculate_annual_monthly_production_kwh,
)
from ontario_home_energy_futures.model.waiting import find_breakeven_decline_rate  # noqa: E402

REFERENCE_PRICE = PriceScenario(
    id="reference", label="Reference", electricity_energy_real=0.015,
    fixed_delivery_real=0.020, variable_delivery_real=0.010, general_inflation=0.020,
)
STRESS_PRICE = PriceScenario(
    id="stress", label="Stress", electricity_energy_real=0.050,
    fixed_delivery_real=0.050, variable_delivery_real=0.045, general_inflation=0.020,
)
FLAT_DECLINE = DeclineScenario(id="flat", label="Flat", real_annual_installed_cost_change=0.0)
MODERATE_DECLINE = DeclineScenario(id="moderate", label="Moderate", real_annual_installed_cost_change=0.02)

REFERENCE_QUOTE = QuoteComponents(
    panels=6720, inverter=2100, racking=1680, electrical_equipment=1260,
    labour=4200, design_and_engineering=630, permitting=420,
    utility_connection=840, installer_overhead=3150,
)

COMMON_SHARES = dict(fixed_share=0.30, variable_share=0.15, energy_share=0.55)


def _decision_result_to_dict(result) -> dict:
    return {
        "label": result.label,
        "purchase_year_offset": result.purchase_year_offset,
        "initial_cost_cad": result.initial_cost_cad,
        "financing_interest_cad": result.financing_interest_cad,
        "group_discount_cad": result.group_discount_cad,
        "total_nominal_cad": result.total_nominal_cad,
        "total_present_value_cad": result.total_present_value_cad,
        "simple_payback_years": result.simple_payback_years,
        "annual_cash_flows": [
            {
                "year": f.year,
                "grid_bill_nominal_cad": f.grid_bill_nominal_cad,
                "solar_maintenance_nominal_cad": f.solar_maintenance_nominal_cad,
                "financing_payment_nominal_cad": f.financing_payment_nominal_cad,
                "credits_used_nominal_cad": f.credits_used_nominal_cad,
                "total_nominal_cad": f.total_nominal_cad,
                "total_present_value_cad": f.total_present_value_cad,
            }
            for f in result.annual_cash_flows
        ],
    }


def build_cases() -> list[dict]:
    cases = []

    # Case 1: grid-only baseline, reference scenario, 20-year horizon.
    grid_only = evaluate_grid_only(
        base_annual_bill_cad=8400.0, price_scenario=REFERENCE_PRICE, horizon_years=20,
        discount_rate=0.04, **COMMON_SHARES,
    )
    cases.append({
        "name": "grid_only_reference_20yr",
        "function": "evaluate_grid_only",
        "inputs": {
            "base_annual_bill_cad": 8400.0, "price_scenario": "reference",
            "horizon_years": 20, "discount_rate": 0.04, **COMMON_SHARES,
        },
        "expected": _decision_result_to_dict(grid_only),
    })

    # Case 2: cash buy-now, no discount, flat decline.
    common_purchase_kwargs = dict(
        base_annual_bill_cad=8400.0, price_scenario=REFERENCE_PRICE, decline_scenario=FLAT_DECLINE,
        base_quote=REFERENCE_QUOTE, tax_rate=0.13, down_payment_fraction=1.0,
        annual_interest_rate=0.079, loan_term_years=10, horizon_years=20, discount_rate=0.04,
        **COMMON_SHARES,
        annual_grid_bill_after_solar_cad=2940.0, annual_maintenance_cad=150.0,
        inverter_replacement_year=12, inverter_replacement_cost_cad=1800.0,
        annual_credits_used_cad=2520.0, total_credits_expired_cad=0.0,
        total_solar_generation_kwh=9000.0, total_grid_imports_kwh=3360.0,
    )
    buy_now_cash = evaluate_solar_purchase(
        label="Buy solar now", purchase_year_offset=0, group_discount_fraction=0.0, is_cash=True,
        **common_purchase_kwargs,
    )
    cases.append({
        "name": "buy_now_cash_no_discount",
        "function": "evaluate_solar_purchase",
        "inputs": {
            "label": "Buy solar now", "purchase_year_offset": 0, "group_discount_fraction": 0.0,
            "is_cash": True, "price_scenario": "reference", "decline_scenario": "flat",
            "base_quote": REFERENCE_QUOTE.__dict__, **{k: v for k, v in common_purchase_kwargs.items()
            if k not in ("price_scenario", "decline_scenario", "base_quote")},
        },
        "expected": _decision_result_to_dict(buy_now_cash),
    })

    # Case 3: buy now with 10% group discount, cash.
    buy_now_10pct = evaluate_solar_purchase(
        label="Buy now, 10% group discount", purchase_year_offset=0, group_discount_fraction=0.10,
        is_cash=True, **common_purchase_kwargs,
    )
    cases.append({
        "name": "buy_now_cash_10pct_discount",
        "function": "evaluate_solar_purchase",
        "inputs": {
            "label": "Buy now, 10% group discount", "purchase_year_offset": 0,
            "group_discount_fraction": 0.10, "is_cash": True, "price_scenario": "reference",
            "decline_scenario": "flat", "base_quote": REFERENCE_QUOTE.__dict__,
            **{k: v for k, v in common_purchase_kwargs.items()
               if k not in ("price_scenario", "decline_scenario", "base_quote")},
        },
        "expected": _decision_result_to_dict(buy_now_10pct),
    })

    # Case 4: financed buy-now.
    financed_now = evaluate_solar_purchase(
        label="Buy now, financed", purchase_year_offset=0, group_discount_fraction=0.0, is_cash=False,
        **{**common_purchase_kwargs, "down_payment_fraction": 0.10},
    )
    cases.append({
        "name": "buy_now_financed",
        "function": "evaluate_solar_purchase",
        "inputs": {
            "label": "Buy now, financed", "purchase_year_offset": 0, "group_discount_fraction": 0.0,
            "is_cash": False, "price_scenario": "reference", "decline_scenario": "flat",
            "base_quote": REFERENCE_QUOTE.__dict__,
            **{k: v for k, v in {**common_purchase_kwargs, "down_payment_fraction": 0.10}.items()
               if k not in ("price_scenario", "decline_scenario", "base_quote")},
        },
        "expected": _decision_result_to_dict(financed_now),
    })

    # Case 5: wait 3 years, moderate decline.
    wait_3yr = evaluate_solar_purchase(
        label="Wait 3 years", purchase_year_offset=3, group_discount_fraction=0.0, is_cash=True,
        **{**common_purchase_kwargs, "decline_scenario": MODERATE_DECLINE},
    )
    cases.append({
        "name": "wait_3yr_moderate_decline",
        "function": "evaluate_solar_purchase",
        "inputs": {
            "label": "Wait 3 years", "purchase_year_offset": 3, "group_discount_fraction": 0.0,
            "is_cash": True, "price_scenario": "reference", "decline_scenario": "moderate",
            "base_quote": REFERENCE_QUOTE.__dict__,
            **{k: v for k, v in common_purchase_kwargs.items()
               if k not in ("price_scenario", "decline_scenario", "base_quote")},
        },
        "expected": _decision_result_to_dict(wait_3yr),
    })

    # Case 6: stress price scenario, 10-year horizon (edge: shorter horizon).
    grid_only_stress_10yr = evaluate_grid_only(
        base_annual_bill_cad=8400.0, price_scenario=STRESS_PRICE, horizon_years=10,
        discount_rate=0.06, **COMMON_SHARES,
    )
    cases.append({
        "name": "grid_only_stress_10yr",
        "function": "evaluate_grid_only",
        "inputs": {
            "base_annual_bill_cad": 8400.0, "price_scenario": "stress",
            "horizon_years": 10, "discount_rate": 0.06, **COMMON_SHARES,
        },
        "expected": _decision_result_to_dict(grid_only_stress_10yr),
    })

    # Case 7: zero-discount-rate edge case (present value == nominal).
    grid_only_zero_discount = evaluate_grid_only(
        base_annual_bill_cad=8400.0, price_scenario=REFERENCE_PRICE, horizon_years=5,
        discount_rate=0.0, **COMMON_SHARES,
    )
    cases.append({
        "name": "grid_only_zero_discount_rate",
        "function": "evaluate_grid_only",
        "inputs": {
            "base_annual_bill_cad": 8400.0, "price_scenario": "reference",
            "horizon_years": 5, "discount_rate": 0.0, **COMMON_SHARES,
        },
        "expected": _decision_result_to_dict(grid_only_zero_discount),
    })

    # Standalone unit-level cases for the smaller pure functions.
    standalone = {
        "bill_component_after_years": {
            "inputs": {"base_value": 4620.0, "annual_real_change": 0.015, "years": 10, "general_inflation": 0.02},
            "expected": list(bill_component_after_years(
                base_value=4620.0, annual_real_change=0.015, years=10, general_inflation=0.02
            )),
        },
        "apply_group_discount": {
            "inputs": {"quote": REFERENCE_QUOTE.__dict__, "discount_fraction": 0.10},
            "expected": apply_group_discount(REFERENCE_QUOTE, 0.10).__dict__,
        },
        "amortize_loan": {
            "inputs": {"principal": 18000.0, "annual_interest_rate": 0.079, "term_years": 10},
            "expected": {
                k: v for k, v in amortize_loan(
                    principal=18000.0, annual_interest_rate=0.079, term_years=10
                ).__dict__.items() if k != "balance_by_year"
            },
        },
        "solar_production": {
            "inputs": {
                "capacity_kw_dc": 7.2, "orientation": "south", "shading": "none",
                "degradation_annual": 0.005, "inverter_efficiency": 0.97, "other_system_losses": 0.14,
                "system_age_years": 0,
            },
            "expected": calculate_annual_monthly_production_kwh(
                SolarSystemInputs(
                    capacity_kw_dc=7.2, orientation="south", shading="none",
                    degradation_annual=0.005, inverter_efficiency=0.97, other_system_losses=0.14,
                ),
                regional_monthly_yield_kwh_per_kw={
                    1: 62, 2: 82, 3: 118, 4: 132, 5: 148, 6: 150,
                    7: 152, 8: 138, 9: 112, 10: 82, 11: 52, 12: 48,
                },
                orientation_factors={"south": 1.00, "southeast": 0.96, "southwest": 0.96, "east": 0.85, "west": 0.85, "north": 0.65},
                shading_factors={"none": 1.00, "light": 0.95, "moderate": 0.85, "heavy": 0.65},
                system_age_years=0,
            ),
        },
        "net_metering_ledger_two_months": {
            "inputs": {
                "export_credit_rate_cad_per_kwh": 0.076,
                "months": [
                    {"period": "2026-06", "solar_generation_kwh": 900, "household_demand_kwh": 700,
                     "direct_self_consumption_kwh": 300, "eligible_energy_rate_cad_per_kwh": 0.076,
                     "ineligible_charges_cad": 45},
                    {"period": "2026-07", "solar_generation_kwh": 0, "household_demand_kwh": 700,
                     "direct_self_consumption_kwh": 0, "eligible_energy_rate_cad_per_kwh": 0.076,
                     "ineligible_charges_cad": 45},
                ],
            },
            "expected": None,  # filled below
        },
        "apply_collective_purchase_group_10": {
            "inputs": {
                "tier": {
                    "id": "group_10", "label": "Ten-household group", "households": 10,
                    "reductions": {"hardware": 3, "labour": 5, "customer_acquisition": 40, "design": 20, "permitting": 10, "financing_fees": 0},
                    "overall_discount_cap_percent": 10,
                },
                "base_costs_by_component": {
                    "hardware": 10920.0, "labour": 4200.0, "design": 630.0,
                    "permitting": 420.0, "customer_acquisition": 3150.0, "financing_fees": 0.0,
                },
            },
            "expected": None,  # filled below
        },
        "apply_collective_purchase_group_20_capped": {
            "inputs": {
                "tier": {
                    "id": "group_20", "label": "Twenty-household group", "households": 20,
                    "reductions": {"hardware": 4, "labour": 6, "customer_acquisition": 50, "design": 25, "permitting": 12, "financing_fees": 0},
                    "overall_discount_cap_percent": 13,
                },
                "base_costs_by_component": {
                    "hardware": 10920.0, "labour": 4200.0, "design": 630.0,
                    "permitting": 420.0, "customer_acquisition": 3150.0, "financing_fees": 0.0,
                },
            },
            "expected": None,  # filled below
        },
        "calculate_cost_of_inaction_three_decisions": {
            "inputs": {
                "decisions": [
                    {"label": "Grid only", "total_nominal_cad": 29038.16, "total_present_value_cad": 22062.10,
                     "grid_imports_kwh": 0.0, "solar_generation_kwh": 0.0, "incentives_received_cad": 0.0,
                     "grid_service_revenue_cad": 0.0, "residual_value_cad": 0.0},
                    {"label": "Buy solar now", "total_nominal_cad": 32603.80, "total_present_value_cad": 25164.14,
                     "grid_imports_kwh": 3360.0, "solar_generation_kwh": 9000.0, "incentives_received_cad": 0.0,
                     "grid_service_revenue_cad": 0.0, "residual_value_cad": 0.0},
                    {"label": "Wait 3 years", "total_nominal_cad": 34202.63, "total_present_value_cad": 25891.02,
                     "grid_imports_kwh": 3360.0, "solar_generation_kwh": 9000.0, "incentives_received_cad": 0.0,
                     "grid_service_revenue_cad": 0.0, "residual_value_cad": 0.0},
                ],
            },
            "expected": None,  # filled below
        },
    }

    for case_name, tier_dict in (
        ("apply_collective_purchase_group_10", standalone["apply_collective_purchase_group_10"]["inputs"]),
        ("apply_collective_purchase_group_20_capped", standalone["apply_collective_purchase_group_20_capped"]["inputs"]),
    ):
        tier = CollectiveTier(
            id=tier_dict["tier"]["id"], label=tier_dict["tier"]["label"], households=tier_dict["tier"]["households"],
            reductions=tier_dict["tier"]["reductions"], overall_discount_cap_percent=tier_dict["tier"]["overall_discount_cap_percent"],
        )
        result = apply_collective_purchase(tier=tier, base_costs_by_component=tier_dict["base_costs_by_component"])
        standalone[case_name]["expected"] = {
            "total_base_cost": result.total_base_cost, "total_reduced_cost": result.total_reduced_cost,
            "total_reduction_cad": result.total_reduction_cad, "effective_discount_percent": result.effective_discount_percent,
            "capped": result.capped,
        }

    cost_of_inaction_inputs = [
        DecisionCostInputs(**d) for d in standalone["calculate_cost_of_inaction_three_decisions"]["inputs"]["decisions"]
    ]
    cost_of_inaction_results = calculate_cost_of_inaction(cost_of_inaction_inputs)
    standalone["calculate_cost_of_inaction_three_decisions"]["expected"] = {
        label: {
            "additional_nominal_cost_cad": b.additional_nominal_cost_cad,
            "additional_present_value_cad": b.additional_present_value_cad,
            "grid_electricity_purchased_while_waiting_kwh": b.grid_electricity_purchased_while_waiting_kwh,
            "solar_generation_forgone_kwh": b.solar_generation_forgone_kwh,
            "current_incentives_forgone_cad": b.current_incentives_forgone_cad,
        }
        for label, b in cost_of_inaction_results.items()
    }

    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.076)
    month_results = []
    for m in standalone["net_metering_ledger_two_months"]["inputs"]["months"]:
        r = ledger.process_month(**m)
        month_results.append({
            "period": r.period, "exported_kwh": r.exported_kwh, "grid_import_kwh": r.grid_import_kwh,
            "credit_created_cad": r.credit_created_cad, "credit_used_cad": r.credit_used_cad,
            "credit_expired_cad": r.credit_expired_cad, "credit_closing_balance_cad": r.credit_closing_balance_cad,
        })
    standalone["net_metering_ledger_two_months"]["expected"] = {
        "months": month_results,
        "effective_value_per_generated_kwh": ledger.effective_value_per_generated_kwh(),
    }

    def npv_cost_for_rate(rate: float) -> float:
        ds = DeclineScenario(id="sweep", label="sweep", real_annual_installed_cost_change=rate)
        result = evaluate_solar_purchase(
            label="sweep", purchase_year_offset=3, group_discount_fraction=0.0, is_cash=True,
            **{**common_purchase_kwargs, "decline_scenario": ds},
        )
        return result.total_present_value_cad

    breakeven = find_breakeven_decline_rate(
        npv_cost_for_decline_rate=npv_cost_for_rate, npv_cost_buy_now=buy_now_cash.total_present_value_cad
    )
    standalone["find_breakeven_decline_rate"] = {
        "inputs": {"wait_years_offset": 3, "npv_cost_buy_now": buy_now_cash.total_present_value_cad},
        "expected": breakeven,
    }

    return {"scenario_cases": cases, "standalone_cases": standalone}


def main() -> None:
    fixture = build_cases()
    output_path = REPO_ROOT / "tests" / "fixtures" / "golden_scenarios.json"
    output_path.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
    print(f"Wrote {output_path.relative_to(REPO_ROOT)}")
    print(f"  {len(fixture['scenario_cases'])} scenario cases")
    print(f"  {len(fixture['standalone_cases'])} standalone cases")


if __name__ == "__main__":
    main()
