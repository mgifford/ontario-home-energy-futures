"""Cost of inaction: the difference between a delayed/no-action decision and
the best available action under the selected assumptions.

    C_inaction,y = C_decision,y - min_j(C_decision,j)

See the project brief's "Cost of inaction" section and METHODOLOGY.md
section 19. This module does not compute new cash flows - it is a thin
wrapper over ``DecisionResult``s already produced elsewhere (Phase 1's
``model/scenario.py`` or this phase's ``model/scenario_v2.py``), so it
never assumes immediate action is automatically best: it always compares
against whichever decision actually has the lowest cost among the ones
supplied, which could be "buy now," a wait option, or (in principle) even
"no action" if every purchase option were worse under extreme assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InactionBreakdown:
    """Itemized components of one decision's cost-of-inaction figure,
    matching the project brief's required breakdown fields.
    """

    decision_label: str
    additional_nominal_cost_cad: float
    additional_present_value_cad: float
    grid_electricity_purchased_while_waiting_kwh: float
    solar_generation_forgone_kwh: float
    current_incentives_forgone_cad: float
    currently_available_revenue_forgone_cad: float
    residual_value_difference_cad: float
    # Emissions are reported, never monetized by default - see the project
    # brief's "without monetizing it by default" requirement.
    emissions_consequence_note: str


@dataclass(frozen=True)
class DecisionCostInputs:
    """The minimal set of figures ``calculate_cost_of_inaction`` needs from
    a decision result - kept as a separate small dataclass rather than
    depending on ``model.scenario.DecisionResult`` directly, so this module
    stays usable against either the Phase 1 engine or ``scenario_v2``
    without a circular import.
    """

    label: str
    total_nominal_cad: float
    total_present_value_cad: float
    grid_imports_kwh: float
    solar_generation_kwh: float
    incentives_received_cad: float
    grid_service_revenue_cad: float
    residual_value_cad: float


def calculate_cost_of_inaction(
    decisions: list[DecisionCostInputs],
) -> dict[str, InactionBreakdown]:
    """Compute the cost-of-inaction breakdown for every decision in
    ``decisions``, relative to whichever decision in the same list has the
    lowest total present-value cost. Does not assume decisions[0] or any
    "buy now" label is the best option - the minimum is found empirically.
    """
    if not decisions:
        return {}

    best = min(decisions, key=lambda d: d.total_present_value_cad)

    results: dict[str, InactionBreakdown] = {}
    for decision in decisions:
        additional_nominal = decision.total_nominal_cad - best.total_nominal_cad
        additional_pv = decision.total_present_value_cad - best.total_present_value_cad

        grid_purchased_extra = max(0.0, decision.grid_imports_kwh - best.grid_imports_kwh)
        solar_forgone = max(0.0, best.solar_generation_kwh - decision.solar_generation_kwh)
        incentives_forgone = max(0.0, best.incentives_received_cad - decision.incentives_received_cad)
        revenue_forgone = max(0.0, best.grid_service_revenue_cad - decision.grid_service_revenue_cad)
        residual_diff = decision.residual_value_cad - best.residual_value_cad

        results[decision.label] = InactionBreakdown(
            decision_label=decision.label,
            additional_nominal_cost_cad=round(additional_nominal, 2),
            additional_present_value_cad=round(additional_pv, 2),
            grid_electricity_purchased_while_waiting_kwh=round(grid_purchased_extra, 2),
            solar_generation_forgone_kwh=round(solar_forgone, 2),
            current_incentives_forgone_cad=round(incentives_forgone, 2),
            currently_available_revenue_forgone_cad=round(revenue_forgone, 2),
            residual_value_difference_cad=round(residual_diff, 2),
            emissions_consequence_note=(
                "Delayed or foregone solar generation has an emissions consequence; "
                "this tool reports the forgone generation in kWh above but does not "
                "assign it a default dollar value."
            ),
        )
    return results


def cost_of_inaction_excludes_unavailable_future_revenue(
    *, decision_purchase_year_offset: int, revenue_start_year_offset: int | None
) -> bool:
    """Returns True if a value stream's revenue should be EXCLUDED from a
    cost-of-inaction calculation for a decision purchased at
    ``decision_purchase_year_offset``, because the revenue-generating
    programme (``revenue_start_year_offset``) would not actually have been
    available during the relevant comparison years.

    This directly implements: "Do not include hypothetical future VPP
    payments in the cost of inaction unless the selected scenario makes
    that programme available during the relevant years."
    """
    if revenue_start_year_offset is None:
        return True  # no start year recorded => never available => always excluded
    return decision_purchase_year_offset < revenue_start_year_offset
