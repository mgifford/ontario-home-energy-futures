"""Fixed-calendar purchase-timing comparison engine (Phase 2).

Fixes the fairness bug in ``model/scenario.py``: every decision here
(individual/group buy-now, wait N years, no-action) is evaluated over the
exact same ``FixedHorizon`` calendar window - a later purchase gets FEWER
active solar years within that shared window, never a fresh window of its
own. See ``model/horizon.py`` and METHODOLOGY.md section 10 (updated).

This module composes, rather than duplicates:
``model/horizon.py`` (shared calendar), ``model/technology_decline.py``
(per-component cost projection), ``model/collective_purchasing.py`` (group
discount), ``model/financing.py`` (amortization), ``model/decline.py``
(bill-component escalation, present-value discounting), and
``model/value_streams.py`` + ``model/compatibility.py`` (revenue, with
double-counting prevention).

``model/scenario.py`` (Phase 1) is untouched and still powers Phase 1
pages; this module is additive.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import decline as decline_mod
from .collective_purchasing import CollectiveTier, apply_collective_purchase
from .compatibility import CompatibilityMatrix
from .financing import LoanSchedule, amortize_loan
from .horizon import FixedHorizon, assert_same_horizon
from .scenario import PriceScenario
from .technology_decline import ComponentDeclineRates, project_component_cost
from .value_streams import ValueStream, ValueStreamStatus, calculate_value_stream_revenue


@dataclass(frozen=True)
class YearlyCashFlowV2:
    calendar_year: int
    year_offset: int
    grid_bill_nominal_cad: float
    maintenance_nominal_cad: float
    financing_payment_nominal_cad: float
    credits_used_nominal_cad: float
    grid_service_gross_revenue_cad: float
    grid_service_net_revenue_cad: float
    initial_purchase_cost_cad: float
    total_nominal_cad: float
    total_present_value_cad: float


@dataclass(frozen=True)
class DecisionResultV2:
    label: str
    purchase_year_offset: int | None  # None = no purchase within horizon
    horizon: FixedHorizon
    initial_cost_cad: float
    collective_discount_cad: float
    financing_interest_cad: float
    annual_cash_flows: list[YearlyCashFlowV2]
    total_nominal_cad: float
    total_present_value_cad: float
    total_grid_imports_kwh: float
    total_solar_generation_kwh: float
    total_incentives_cad: float
    total_grid_service_revenue_cad: float
    residual_value_cad: float
    years_active: int


def evaluate_no_action(
    *, horizon: FixedHorizon, base_annual_bill_cad: float, price_scenario: PriceScenario, discount_rate: float,
    fixed_share: float, variable_share: float, energy_share: float,
) -> DecisionResultV2:
    """The "do not purchase during the horizon" decision - contains no
    installation cost by construction.
    """
    flows: list[YearlyCashFlowV2] = []
    total_nominal = 0.0
    total_pv = 0.0

    for offset in horizon.year_offsets():
        nominal_bill = _project_bill(
            base_annual_bill_cad, price_scenario, offset, fixed_share, variable_share, energy_share
        )
        pv = decline_mod.discount_to_present_value(nominal_bill, discount_rate=discount_rate, years=offset)
        flows.append(
            YearlyCashFlowV2(
                calendar_year=horizon.calendar_year_for_offset(offset), year_offset=offset,
                grid_bill_nominal_cad=nominal_bill, maintenance_nominal_cad=0.0,
                financing_payment_nominal_cad=0.0, credits_used_nominal_cad=0.0,
                grid_service_gross_revenue_cad=0.0, grid_service_net_revenue_cad=0.0,
                initial_purchase_cost_cad=0.0, total_nominal_cad=nominal_bill, total_present_value_cad=pv,
            )
        )
        total_nominal += nominal_bill
        total_pv += pv

    return DecisionResultV2(
        label="No action", purchase_year_offset=None, horizon=horizon, initial_cost_cad=0.0,
        collective_discount_cad=0.0, financing_interest_cad=0.0, annual_cash_flows=flows,
        total_nominal_cad=round(total_nominal, 2), total_present_value_cad=round(total_pv, 2),
        total_grid_imports_kwh=0.0, total_solar_generation_kwh=0.0, total_incentives_cad=0.0,
        total_grid_service_revenue_cad=0.0, residual_value_cad=0.0, years_active=0,
    )


def _project_bill(
    base_annual_bill_cad: float, price_scenario: PriceScenario, year_offset: int,
    fixed_share: float, variable_share: float, energy_share: float,
) -> float:
    energy_real, energy_nominal = decline_mod.bill_component_after_years(
        base_value=base_annual_bill_cad * energy_share, annual_real_change=price_scenario.electricity_energy_real,
        years=year_offset, general_inflation=price_scenario.general_inflation,
    )
    fixed_real, fixed_nominal = decline_mod.bill_component_after_years(
        base_value=base_annual_bill_cad * fixed_share, annual_real_change=price_scenario.fixed_delivery_real,
        years=year_offset, general_inflation=price_scenario.general_inflation,
    )
    variable_real, variable_nominal = decline_mod.bill_component_after_years(
        base_value=base_annual_bill_cad * variable_share, annual_real_change=price_scenario.variable_delivery_real,
        years=year_offset, general_inflation=price_scenario.general_inflation,
    )
    return round(energy_nominal + fixed_nominal + variable_nominal, 2)


def evaluate_purchase_decision(
    *,
    label: str,
    horizon: FixedHorizon,
    purchase_year_offset: int,
    base_annual_bill_cad: float,
    price_scenario: PriceScenario,
    base_costs_by_component: dict[str, float],
    technology_components: dict[str, ComponentDeclineRates],
    decline_tier: str,
    collective_tier: CollectiveTier,
    tax_rate: float,
    down_payment_fraction: float,
    annual_interest_rate: float,
    loan_term_years: int,
    is_cash: bool,
    discount_rate: float,
    fixed_share: float,
    variable_share: float,
    energy_share: float,
    annual_grid_bill_after_purchase_cad: float,
    annual_maintenance_cad: float,
    replacement_year_offset: int | None,
    replacement_cost_cad: float,
    annual_credits_used_cad: float,
    value_streams: list[ValueStream],
    compatibility: CompatibilityMatrix,
    committed_kw: float,
    events_this_year: int,
    total_solar_generation_kwh: float,
    total_grid_imports_kwh: float,
    residual_value_fraction: float = 0.0,
) -> DecisionResultV2:
    """Evaluate one purchase-timing decision (individual or collective,
    buy-now or wait N years) within a SHARED ``horizon``.

    Grid-service revenue only accrues for years the purchase is active
    within the horizon AND only for value streams whose status is
    ``current`` (or explicitly included by the caller's ``value_streams``
    list - callers building a "current Ontario" bundle should pre-filter
    to current-only streams; this function does not filter by status
    itself, since bundle composition is the caller's responsibility).
    """
    if not horizon.is_purchase_within_horizon(purchase_year_offset):
        return evaluate_no_action(
            horizon=horizon, base_annual_bill_cad=base_annual_bill_cad, price_scenario=price_scenario,
            discount_rate=discount_rate, fixed_share=fixed_share, variable_share=variable_share,
            energy_share=energy_share,
        )

    # 1. Project each cost component's price at the purchase year using the
    #    per-component technology-decline model.
    projected = {}
    for component_id, base_cost in base_costs_by_component.items():
        if component_id in technology_components:
            proj = project_component_cost(
                component=technology_components[component_id], base_cost=base_cost, tier=decline_tier,
                years=purchase_year_offset, general_inflation=price_scenario.general_inflation,
            )
            projected[component_id] = proj.real_cost
        else:
            projected[component_id] = base_cost

    # 2. Apply the collective-purchasing discount to the projected costs.
    collective_result = apply_collective_purchase(tier=collective_tier, base_costs_by_component=projected)

    total_before_tax = collective_result.total_reduced_cost
    total_with_tax = total_before_tax * (1 + tax_rate)
    down_payment = total_with_tax * down_payment_fraction
    principal = total_with_tax - down_payment

    if is_cash:
        loan = amortize_loan(principal=0.0, annual_interest_rate=annual_interest_rate, term_years=loan_term_years)
        initial_cost = total_with_tax
    else:
        loan = amortize_loan(principal=principal, annual_interest_rate=annual_interest_rate, term_years=loan_term_years)
        initial_cost = down_payment

    # 3. Determine stackable value streams once, up front (compatibility
    #    matrix applied here, centrally - see model/compatibility.py).
    stream_ids = [s.id for s in value_streams]
    stackable_ids, excluded_pairs = compatibility.filter_stackable(stream_ids)
    stackable_streams = [s for s in value_streams if s.id in stackable_ids]

    years_active = horizon.years_active_for_purchase(purchase_year_offset)

    flows: list[YearlyCashFlowV2] = []
    total_nominal = 0.0
    total_pv = 0.0
    total_incentives = 0.0
    total_grid_service_revenue = 0.0

    for offset in horizon.year_offsets():
        calendar_year = horizon.calendar_year_for_offset(offset)

        if offset < purchase_year_offset:
            bill_nominal = _project_bill(
                base_annual_bill_cad, price_scenario, offset, fixed_share, variable_share, energy_share
            )
            maintenance = 0.0
            financing_payment = 0.0
            credits_used = 0.0
            gross_grid_service = 0.0
            net_grid_service = 0.0
        else:
            years_since_purchase = offset - purchase_year_offset
            bill_nominal = _project_bill(
                annual_grid_bill_after_purchase_cad, price_scenario, years_since_purchase,
                fixed_share, variable_share, energy_share,
            )
            maintenance = annual_maintenance_cad
            if replacement_year_offset is not None and years_since_purchase == replacement_year_offset:
                maintenance += replacement_cost_cad
            financing_payment = loan.monthly_payment * 12 if not is_cash else 0.0
            credits_used = annual_credits_used_cad

            gross_grid_service = 0.0
            net_grid_service = 0.0
            for stream in stackable_streams:
                result = calculate_value_stream_revenue(
                    stream, dispatched_kwh_for_grid=0.0, committed_kw=committed_kw,
                    events_this_year=events_this_year,
                )
                gross_grid_service += result.gross_revenue_cad
                net_grid_service += result.net_revenue_cad
                if stream.category == "incentive":
                    total_incentives += result.net_revenue_cad
            total_grid_service_revenue += net_grid_service

        bill_after_credits = max(0.0, bill_nominal - credits_used)
        year_total_nominal = bill_after_credits + maintenance + financing_payment - net_grid_service
        purchase_cost_this_year = 0.0
        if offset == purchase_year_offset:
            purchase_cost_this_year = initial_cost
            year_total_nominal += initial_cost

        pv = decline_mod.discount_to_present_value(year_total_nominal, discount_rate=discount_rate, years=offset)

        flows.append(
            YearlyCashFlowV2(
                calendar_year=calendar_year, year_offset=offset, grid_bill_nominal_cad=round(bill_after_credits, 2),
                maintenance_nominal_cad=round(maintenance, 2), financing_payment_nominal_cad=round(financing_payment, 2),
                credits_used_nominal_cad=round(credits_used, 2), grid_service_gross_revenue_cad=round(gross_grid_service, 2),
                grid_service_net_revenue_cad=round(net_grid_service, 2), initial_purchase_cost_cad=round(purchase_cost_this_year, 2),
                total_nominal_cad=round(year_total_nominal, 2), total_present_value_cad=pv,
            )
        )
        total_nominal += year_total_nominal
        total_pv += pv

    residual_value = total_with_tax * residual_value_fraction * (years_active / max(1, horizon.horizon_years - purchase_year_offset))

    return DecisionResultV2(
        label=label, purchase_year_offset=purchase_year_offset, horizon=horizon,
        initial_cost_cad=round(initial_cost, 2), collective_discount_cad=collective_result.total_reduction_cad,
        financing_interest_cad=loan.total_interest, annual_cash_flows=flows,
        total_nominal_cad=round(total_nominal, 2), total_present_value_cad=round(total_pv, 2),
        total_grid_imports_kwh=total_grid_imports_kwh, total_solar_generation_kwh=total_solar_generation_kwh,
        total_incentives_cad=round(total_incentives, 2), total_grid_service_revenue_cad=round(total_grid_service_revenue, 2),
        residual_value_cad=round(residual_value, 2), years_active=years_active,
    )


def find_breakeven_installed_cost_decline(
    *,
    npv_cost_for_decline_rate,
    npv_cost_buy_now: float,
    low: float = 0.0,
    high: float = 0.30,
) -> float | None:
    """Thin re-export of the numeric binary-search pattern from
    ``model/waiting.py`` so ``scenario_v2`` callers do not need a separate
    import path. See ``model.waiting.find_breakeven_decline_rate`` for the
    full docstring and semantics.
    """
    from .waiting import find_breakeven_decline_rate

    return find_breakeven_decline_rate(
        npv_cost_for_decline_rate=npv_cost_for_decline_rate, npv_cost_buy_now=npv_cost_buy_now, low=low, high=high
    )
