"""Twenty-year (or other horizon) purchase-timing comparison engine.

See METHODOLOGY.md section 10. For each purchase-timing option (grid-only,
buy now, wait 1-5 years), computes nominal and NPV totals, simple and
discounted payback, and reports a low-to-high range across price/decline
scenario combinations.

This module composes ``bill``, ``household``, ``solar``, ``net_metering``,
``financing``, and ``decline`` — it does not duplicate their math.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import decline as decline_mod
from .financing import DiscountResult, LoanSchedule, QuoteComponents, amortize_loan, apply_group_discount
from .net_metering import NetMeteringLedger


@dataclass(frozen=True)
class PriceScenario:
    id: str
    label: str
    electricity_energy_real: float
    fixed_delivery_real: float
    variable_delivery_real: float
    general_inflation: float


@dataclass(frozen=True)
class DeclineScenario:
    id: str
    label: str
    real_annual_installed_cost_change: float


@dataclass
class YearlyCashFlow:
    year: int
    grid_bill_nominal_cad: float
    solar_maintenance_nominal_cad: float
    financing_payment_nominal_cad: float
    credits_used_nominal_cad: float
    total_nominal_cad: float
    total_present_value_cad: float


@dataclass
class DecisionResult:
    label: str
    purchase_year_offset: int  # 0 = buy now, None-like via -1 = grid only
    initial_cost_cad: float
    financing_interest_cad: float
    group_discount_cad: float
    annual_cash_flows: list[YearlyCashFlow]
    total_nominal_cad: float
    total_present_value_cad: float
    simple_payback_years: float | None
    discounted_payback_years: float | None
    total_grid_imports_kwh: float
    total_solar_generation_kwh: float
    credits_expired_cad: float


def project_annual_grid_bill(
    *,
    base_annual_bill_cad: float,
    price_scenario: PriceScenario,
    year: int,
    fixed_share: float,
    variable_share: float,
    energy_share: float,
) -> tuple[float, float]:
    """Project one year's grid-only bill forward under a price scenario,
    escalating each bill component separately, and return
    ``(nominal, real)``.
    """
    energy_real, energy_nominal = decline_mod.bill_component_after_years(
        base_value=base_annual_bill_cad * energy_share,
        annual_real_change=price_scenario.electricity_energy_real,
        years=year,
        general_inflation=price_scenario.general_inflation,
    )
    fixed_real, fixed_nominal = decline_mod.bill_component_after_years(
        base_value=base_annual_bill_cad * fixed_share,
        annual_real_change=price_scenario.fixed_delivery_real,
        years=year,
        general_inflation=price_scenario.general_inflation,
    )
    variable_real, variable_nominal = decline_mod.bill_component_after_years(
        base_value=base_annual_bill_cad * variable_share,
        annual_real_change=price_scenario.variable_delivery_real,
        years=year,
        general_inflation=price_scenario.general_inflation,
    )
    nominal_total = energy_nominal + fixed_nominal + variable_nominal
    real_total = energy_real + fixed_real + variable_real
    return round(nominal_total, 2), round(real_total, 2)


def evaluate_grid_only(
    *,
    base_annual_bill_cad: float,
    price_scenario: PriceScenario,
    horizon_years: int,
    discount_rate: float,
    fixed_share: float,
    variable_share: float,
    energy_share: float,
) -> DecisionResult:
    """The "grid only, no solar" baseline decision."""
    flows: list[YearlyCashFlow] = []
    total_nominal = 0.0
    total_pv = 0.0

    for year in range(horizon_years):
        nominal_bill, _real_bill = project_annual_grid_bill(
            base_annual_bill_cad=base_annual_bill_cad,
            price_scenario=price_scenario,
            year=year,
            fixed_share=fixed_share,
            variable_share=variable_share,
            energy_share=energy_share,
        )
        pv = decline_mod.discount_to_present_value(nominal_bill, discount_rate=discount_rate, years=year)
        flows.append(
            YearlyCashFlow(
                year=year,
                grid_bill_nominal_cad=nominal_bill,
                solar_maintenance_nominal_cad=0.0,
                financing_payment_nominal_cad=0.0,
                credits_used_nominal_cad=0.0,
                total_nominal_cad=nominal_bill,
                total_present_value_cad=pv,
            )
        )
        total_nominal += nominal_bill
        total_pv += pv

    return DecisionResult(
        label="Grid only",
        purchase_year_offset=-1,
        initial_cost_cad=0.0,
        financing_interest_cad=0.0,
        group_discount_cad=0.0,
        annual_cash_flows=flows,
        total_nominal_cad=round(total_nominal, 2),
        total_present_value_cad=round(total_pv, 2),
        simple_payback_years=None,
        discounted_payback_years=None,
        total_grid_imports_kwh=0.0,
        total_solar_generation_kwh=0.0,
        credits_expired_cad=0.0,
    )


def evaluate_solar_purchase(
    *,
    label: str,
    purchase_year_offset: int,
    base_annual_bill_cad: float,
    price_scenario: PriceScenario,
    decline_scenario: DeclineScenario,
    base_quote: QuoteComponents,
    group_discount_fraction: float,
    tax_rate: float,
    down_payment_fraction: float,
    annual_interest_rate: float,
    loan_term_years: int,
    is_cash: bool,
    horizon_years: int,
    discount_rate: float,
    fixed_share: float,
    variable_share: float,
    energy_share: float,
    annual_grid_bill_after_solar_cad: float,
    annual_maintenance_cad: float,
    inverter_replacement_year: int | None,
    inverter_replacement_cost_cad: float,
    annual_credits_used_cad: float,
    total_credits_expired_cad: float,
    total_solar_generation_kwh: float,
    total_grid_imports_kwh: float,
) -> DecisionResult:
    """Evaluate one buy-now-or-wait-N-years solar purchase decision.

    Grid costs before the purchase year use ``evaluate_grid_only``-style
    escalation; from the purchase year onward, the (already net-metering-
    adjusted) post-solar annual bill is used, escalated by the same price
    scenario. This keeps the "grid costs before" / "grid costs after"
    distinction from METHODOLOGY.md section 10 explicit.
    """
    real_installed_cost, nominal_installed_cost = decline_mod.installed_cost_after_years(
        base_cost=base_quote.total(),
        annual_real_decline=decline_scenario.real_annual_installed_cost_change,
        years=purchase_year_offset,
        general_inflation=price_scenario.general_inflation,
    )
    # Re-derive a QuoteComponents at the (possibly lower) future real cost by
    # scaling every component proportionally, then apply the group discount.
    scale = (real_installed_cost / base_quote.total()) if base_quote.total() else 1.0
    scaled_quote = QuoteComponents(
        panels=base_quote.panels * scale,
        inverter=base_quote.inverter * scale,
        racking=base_quote.racking * scale,
        electrical_equipment=base_quote.electrical_equipment * scale,
        labour=base_quote.labour * scale,
        design_and_engineering=base_quote.design_and_engineering * scale,
        permitting=base_quote.permitting * scale,
        utility_connection=base_quote.utility_connection * scale,
        installer_overhead=base_quote.installer_overhead * scale,
        battery=base_quote.battery * scale,
        other=base_quote.other * scale,
    )
    discount: DiscountResult = apply_group_discount(scaled_quote, group_discount_fraction)
    total_before_tax = discount.total_after_discount
    total_with_tax = total_before_tax * (1 + tax_rate)

    down_payment = total_with_tax * down_payment_fraction
    principal = total_with_tax - down_payment

    if is_cash:
        loan = amortize_loan(principal=0.0, annual_interest_rate=annual_interest_rate, term_years=loan_term_years)
        initial_cost = total_with_tax
    else:
        loan = amortize_loan(principal=principal, annual_interest_rate=annual_interest_rate, term_years=loan_term_years)
        initial_cost = down_payment

    flows: list[YearlyCashFlow] = []
    total_nominal = 0.0
    total_pv = 0.0
    cumulative_nominal = 0.0
    simple_payback_years: float | None = None
    discounted_payback_years: float | None = None
    cumulative_pv = 0.0

    grid_only_cumulative = 0.0

    for year in range(horizon_years):
        if year < purchase_year_offset:
            bill_nominal, _real = project_annual_grid_bill(
                base_annual_bill_cad=base_annual_bill_cad,
                price_scenario=price_scenario,
                year=year,
                fixed_share=fixed_share,
                variable_share=variable_share,
                energy_share=energy_share,
            )
            maintenance = 0.0
            financing_payment = 0.0
            credits_used = 0.0
        else:
            years_since_purchase = year - purchase_year_offset
            bill_nominal, _real = project_annual_grid_bill(
                base_annual_bill_cad=annual_grid_bill_after_solar_cad,
                price_scenario=price_scenario,
                year=years_since_purchase,
                fixed_share=fixed_share,
                variable_share=variable_share,
                energy_share=energy_share,
            )
            maintenance = annual_maintenance_cad
            if inverter_replacement_year is not None and years_since_purchase == inverter_replacement_year:
                maintenance += inverter_replacement_cost_cad
            financing_payment = loan.monthly_payment * 12 if not is_cash else 0.0
            credits_used = annual_credits_used_cad

        bill_nominal = max(0.0, bill_nominal - credits_used)

        year_total_nominal = bill_nominal + maintenance + financing_payment
        if year == purchase_year_offset:
            year_total_nominal += initial_cost

        pv = decline_mod.discount_to_present_value(year_total_nominal, discount_rate=discount_rate, years=year)

        flows.append(
            YearlyCashFlow(
                year=year,
                grid_bill_nominal_cad=round(bill_nominal, 2),
                solar_maintenance_nominal_cad=round(maintenance, 2),
                financing_payment_nominal_cad=round(financing_payment, 2),
                credits_used_nominal_cad=round(credits_used, 2),
                total_nominal_cad=round(year_total_nominal, 2),
                total_present_value_cad=pv,
            )
        )
        total_nominal += year_total_nominal
        total_pv += pv
        cumulative_nominal += year_total_nominal
        cumulative_pv += pv

        grid_only_bill, _ = project_annual_grid_bill(
            base_annual_bill_cad=base_annual_bill_cad,
            price_scenario=price_scenario,
            year=year,
            fixed_share=fixed_share,
            variable_share=variable_share,
            energy_share=energy_share,
        )
        grid_only_cumulative += grid_only_bill

        if simple_payback_years is None and year >= purchase_year_offset:
            if cumulative_nominal <= grid_only_cumulative:
                simple_payback_years = year - purchase_year_offset + 1

    return DecisionResult(
        label=label,
        purchase_year_offset=purchase_year_offset,
        initial_cost_cad=round(initial_cost, 2),
        financing_interest_cad=loan.total_interest,
        group_discount_cad=discount.discount_amount,
        annual_cash_flows=flows,
        total_nominal_cad=round(total_nominal, 2),
        total_present_value_cad=round(total_pv, 2),
        simple_payback_years=simple_payback_years,
        discounted_payback_years=discounted_payback_years,
        total_grid_imports_kwh=total_grid_imports_kwh,
        total_solar_generation_kwh=total_solar_generation_kwh,
        credits_expired_cad=total_credits_expired_cad,
    )
