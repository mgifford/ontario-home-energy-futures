"""Solar-cost-decline scenarios and electricity-price escalation.

See METHODOLOGY.md sections 7 and 8.

    C_y = C_0 * (1 - r)^y                       (real terms)
    C_y,nominal = C_0 * (1 - r)^y * (1 + i)^y    (nominal terms)
"""

from __future__ import annotations


def installed_cost_after_years(
    *, base_cost: float, annual_real_decline: float, years: int, general_inflation: float = 0.0
) -> tuple[float, float]:
    """Return ``(real_cost, nominal_cost)`` for a solar system purchased
    ``years`` from now, given a real annual decline rate and general
    inflation rate.
    """
    real_cost = base_cost * (1.0 - annual_real_decline) ** years
    nominal_cost = real_cost * (1.0 + general_inflation) ** years
    return round(real_cost, 2), round(nominal_cost, 2)


def bill_component_after_years(
    *, base_value: float, annual_real_change: float, years: int, general_inflation: float = 0.0
) -> tuple[float, float]:
    """Return ``(real_value, nominal_value)`` for one electricity bill
    component after applying its own real annual growth rate plus general
    inflation, kept separate per METHODOLOGY.md section 7 (never a single
    blended "electricity rate" growth number).
    """
    real_value = base_value * (1.0 + annual_real_change) ** years
    nominal_value = real_value * (1.0 + general_inflation) ** years
    return round(real_value, 6), round(nominal_value, 6)


def deflate_to_real(nominal_value: float, *, general_inflation: float, years: int) -> float:
    """Convert a nominal value ``years`` in the future back to today's real
    dollars.
    """
    return round(nominal_value / ((1.0 + general_inflation) ** years), 2)


def discount_to_present_value(cash_flow: float, *, discount_rate: float, years: float) -> float:
    """Discount a future cash flow to present value using the given annual
    discount rate.
    """
    return round(cash_flow / ((1.0 + discount_rate) ** years), 2)
