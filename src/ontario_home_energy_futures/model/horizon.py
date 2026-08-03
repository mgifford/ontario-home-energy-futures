"""Fixed-calendar comparison horizon.

Every purchase-timing decision in a comparison (buy now, wait N years, no
action) must be evaluated over the exact same set of calendar years - never
each decision getting its own fresh N-year window starting at its own
purchase date. See the project brief's "Fixed-calendar 20-year comparison"
requirement and METHODOLOGY.md section 10.

Example: base_year=2026, horizon_years=20 -> every decision is evaluated
over calendar years 2026..2045 inclusive-exclusive [2026, 2046). A household
that waits until 2029 to buy still only gets solar-active years 2029..2045
(17 years of production), not a fresh 2029..2048 window. This is what makes
"wait 3 years" a genuinely fair comparison against "buy now" rather than a
comparison that quietly gives the waiting option extra years.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FixedHorizon:
    """A shared calendar comparison window."""

    base_year: int
    horizon_years: int

    @property
    def end_year(self) -> int:
        """Exclusive end year: the horizon covers [base_year, end_year)."""
        return self.base_year + self.horizon_years

    @property
    def calendar_years(self) -> list[int]:
        return list(range(self.base_year, self.end_year))

    def years_active_for_purchase(self, purchase_year_offset: int) -> int:
        """How many years within this fixed horizon a system purchased at
        ``purchase_year_offset`` (0 = base year, 3 = wait 3 years, etc.)
        would actually be in service.

        A purchase at or after the horizon's end contributes 0 active
        years. This is what naturally produces a smaller residual/solar
        benefit for later purchases within the SAME window, rather than
        artificially extending the window to give them a full share.
        """
        if purchase_year_offset < 0:
            raise ValueError("purchase_year_offset must be >= 0")
        if purchase_year_offset >= self.horizon_years:
            return 0
        return self.horizon_years - purchase_year_offset

    def year_offsets(self) -> list[int]:
        """0-indexed offsets into the fixed horizon, e.g. [0, 1, ..., 19]
        for a 20-year horizon - the index used by every decision's yearly
        cash-flow loop.
        """
        return list(range(self.horizon_years))

    def is_purchase_within_horizon(self, purchase_year_offset: int) -> bool:
        return 0 <= purchase_year_offset < self.horizon_years

    def calendar_year_for_offset(self, year_offset: int) -> int:
        return self.base_year + year_offset


def assert_same_horizon(*horizons: FixedHorizon) -> None:
    """Raise ``ValueError`` unless every given horizon shares the same
    base_year and end_year - a defensive check callers can use before
    comparing multiple ``DecisionResult``s to guarantee the "fixed-horizon
    fairness" invariant actually held for a given comparison.
    """
    if not horizons:
        return
    first = horizons[0]
    for h in horizons[1:]:
        if h.base_year != first.base_year or h.end_year != first.end_year:
            raise ValueError(
                f"horizons are not aligned: {first.base_year}-{first.end_year} "
                f"vs {h.base_year}-{h.end_year}. Every decision in a comparison "
                "must share the same calendar horizon."
            )
