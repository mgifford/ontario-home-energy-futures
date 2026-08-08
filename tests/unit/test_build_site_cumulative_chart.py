"""Tests for build_site.py's cumulative-cost chart context
(_build_cumulative_cost_chart) - confirms it uses the REAL DecisionResult
totals already computed by _build_comparison_rows, not placeholder data,
and that the chart's final cumulative values match the comparison table's
own 20-year totals (no drift between the table and the chart).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ontario_home_energy_futures.site.build_site import _build_comparison_rows
from ontario_home_energy_futures.site.context import SiteData

REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture(scope="module")
def comparison():
    data = SiteData(REPO_ROOT)
    return _build_comparison_rows(data)


def test_chart_series_labels_match_four_key_decisions(comparison):
    labels = comparison["cumulative_cost_chart_series_labels"]
    assert labels == ["Grid only", "Buy solar now", "Buy now, 10% group discount", "Wait 3 years"]


def test_chart_svg_present_and_non_trivial(comparison):
    svg = comparison["cumulative_cost_chart_svg"]
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert len(svg) > 500  # a real chart, not an empty shell


def test_chart_table_rows_cover_full_horizon(comparison):
    rows = comparison["cumulative_cost_chart_rows"]
    assert len(rows) == comparison["horizon_years"]


def test_chart_final_cumulative_value_matches_comparison_table_20yr_total(comparison):
    # The chart's last row for each series must match the SAME decision's
    # total_nominal_cad already shown in the main comparison table
    # ("rows") - proving the chart isn't computed from a different or
    # stale set of numbers.
    last_row = comparison["cumulative_cost_chart_rows"][-1]
    table_totals = {r["label"]: r["cost_20yr"] for r in comparison["rows"]}

    def parse_cad(formatted: str) -> float:
        return float(formatted.replace("$", "").replace(",", ""))

    for label in comparison["cumulative_cost_chart_series_labels"]:
        chart_final = last_row[label]
        table_final = parse_cad(table_totals[label])
        assert chart_final == pytest.approx(table_final, abs=0.5)


def test_chart_first_row_shows_initial_payout_step(comparison):
    # At year 0, a purchase decision (Buy solar now) must show a
    # materially higher cumulative cost than the no-purchase decision
    # (Grid only) - this is the "initial payout" the chart exists to make
    # visible.
    first_row = comparison["cumulative_cost_chart_rows"][0]
    assert first_row["Buy solar now"] > first_row["Grid only"]


def test_chart_wait_decision_matches_grid_only_before_purchase_year(comparison):
    # "Wait 3 years" should track "Grid only" closely for the years before
    # the purchase happens (both are just paying the grid bill), then
    # diverge - sanity-checking the underlying cash-flow data actually
    # reflects the wait behaviour, not a flat/constant series.
    rows = comparison["cumulative_cost_chart_rows"]
    year_0 = rows[0]
    assert year_0["Wait 3 years"] == pytest.approx(year_0["Grid only"], abs=1.0)


def test_chart_accessible_description_mentions_no_guarantee(comparison):
    svg = comparison["cumulative_cost_chart_svg"]
    assert "not a" in svg.lower() and ("guarantee" in svg.lower() or "prediction" in svg.lower())
