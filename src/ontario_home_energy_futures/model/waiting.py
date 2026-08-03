"""Cost-of-waiting breakeven calculation.

See METHODOLOGY.md section 11. Solves for the minimum annual real
solar-cost decline rate required for waiting N years to produce a lower NPV
than buying now, given a comparison function that evaluates total NPV cost
for a given decline rate.
"""

from __future__ import annotations

from collections.abc import Callable


def find_breakeven_decline_rate(
    *,
    npv_cost_for_decline_rate: Callable[[float], float],
    npv_cost_buy_now: float,
    low: float = 0.0,
    high: float = 0.30,
    tolerance: float = 1e-5,
    max_iterations: int = 100,
) -> float | None:
    """Binary-search for the annual real decline rate ``r`` such that
    ``npv_cost_for_decline_rate(r) == npv_cost_buy_now``.

    Assumes ``npv_cost_for_decline_rate`` is non-increasing in ``r`` (a
    faster decline makes waiting cheaper). Returns ``None`` if waiting never
    beats buying now even at ``high``, or always beats it even at ``low``
    (i.e. no breakeven exists in the search range) — callers should report
    that explicitly rather than showing a misleading number.
    """
    cost_at_low = npv_cost_for_decline_rate(low)
    cost_at_high = npv_cost_for_decline_rate(high)

    if cost_at_low <= npv_cost_buy_now:
        return low  # Waiting already wins even with no decline at all.
    if cost_at_high > npv_cost_buy_now:
        return None  # Waiting never wins, even at the fastest rate searched.

    lo, hi = low, high
    for _ in range(max_iterations):
        mid = (lo + hi) / 2
        cost_at_mid = npv_cost_for_decline_rate(mid)
        if abs(cost_at_mid - npv_cost_buy_now) < tolerance * max(1.0, npv_cost_buy_now):
            return round(mid, 5)
        if cost_at_mid > npv_cost_buy_now:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 5)


def format_breakeven_statement(
    *, breakeven_rate: float | None, wait_years: int, wait_until_year: int, buy_now_year: int
) -> str:
    """Render the required "Under the selected assumptions..." sentence
    format from the project brief.
    """
    if breakeven_rate is None:
        return (
            "Under the selected assumptions, no plausible solar-cost decline "
            f"rate makes waiting until {wait_until_year} cost less than buying "
            f"in {buy_now_year}."
        )
    return (
        f"Under the selected assumptions, installed solar prices would need "
        f"to fall by at least {breakeven_rate * 100:.1f}% per year for "
        f"{wait_years} year{'s' if wait_years != 1 else ''} for waiting until "
        f"{wait_until_year} to cost less than buying in {buy_now_year}."
    )
