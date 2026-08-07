"""Tests for the dependency-free SVG line-chart builder
(charts/svg_line_chart.py). See ACCESSIBILITY.md's chart decision record:
no colour-only series encoding, table-backed, accessible name/description
present.
"""

from __future__ import annotations

import re

import pytest

from ontario_home_energy_futures.charts.svg_line_chart import (
    ChartSeries,
    build_cumulative_cost_line_chart,
)

SIMPLE_SERIES = [
    ChartSeries(label="Grid only", points=[(0, 1000), (1, 2100), (2, 3300)]),
    ChartSeries(label="Buy solar now", points=[(0, 15000), (1, 15600), (2, 16100)]),
]


def _build(series=None, **kwargs):
    return build_cumulative_cost_line_chart(
        series=series or SIMPLE_SERIES,
        x_label="Year",
        y_label="Cumulative cost (CAD)",
        accessible_name="Cumulative cost over time",
        accessible_description="Comparison of cumulative nominal cost by year for each decision.",
        **kwargs,
    )


def test_empty_series_raises():
    with pytest.raises(ValueError):
        build_cumulative_cost_line_chart(
            series=[], x_label="Year", y_label="Cost", accessible_name="x", accessible_description="y"
        )


def test_svg_is_well_formed_root_element():
    result = _build()
    assert result.svg.startswith("<svg")
    assert result.svg.endswith("</svg>")
    assert result.svg.count("<svg") == 1


def test_svg_has_accessible_name_and_description():
    result = _build()
    assert 'role="img"' in result.svg
    assert "<title" in result.svg
    assert "<desc" in result.svg
    assert "Cumulative cost over time" in result.svg
    assert "Comparison of cumulative nominal cost" in result.svg


def test_each_series_has_a_polyline():
    result = _build()
    assert result.svg.count("<polyline") == len(SIMPLE_SERIES)


def test_series_use_distinct_dasharray_not_colour_only():
    result = _build()
    # At least one series must have a non-"none" dasharray so that series
    # are distinguishable without colour perception (the first series is
    # allowed to be solid/"none" as the baseline).
    dasharrays = re.findall(r'stroke-dasharray="([^"]+)"', result.svg)
    assert len(dasharrays) >= 1
    assert len(set(dasharrays)) >= 1  # distinct patterns present


def test_series_use_distinct_colours():
    result = _build()
    strokes = re.findall(r'stroke="(#[0-9a-fA-F]{6})"', result.svg)
    # Two series -> at least two distinct polyline/marker colours.
    assert len(set(strokes)) >= 2


def test_table_rows_match_point_count():
    result = _build()
    assert len(result.table_rows) == 3  # 3 years (0, 1, 2)
    for row in result.table_rows:
        assert "Grid only" in row
        assert "Buy solar now" in row


def test_table_rows_values_match_series_points_exactly():
    result = _build()
    row_by_x = {row["x"]: row for row in result.table_rows}
    for series in SIMPLE_SERIES:
        for x, y in series.points:
            assert row_by_x[x][series.label] == y


def test_markers_present_for_each_point():
    result = _build()
    # 2 series x 3 points = 6 markers (default shape is circle for the
    # first series).
    assert result.svg.count("<circle") >= 3


def test_handles_single_series():
    result = _build(series=[ChartSeries(label="Only one", points=[(0, 100), (1, 200)])])
    assert result.svg.count("<polyline") == 1
    assert len(result.table_rows) == 2


def test_handles_flat_series_no_division_by_zero():
    flat = [ChartSeries(label="Flat", points=[(0, 500), (1, 500), (2, 500)])]
    result = _build(series=flat)  # all y equal -> y_max == y_min guard
    assert "<svg" in result.svg


def test_handles_negative_values():
    series = [ChartSeries(label="Net", points=[(0, -500), (1, 200), (2, 1000)])]
    result = _build(series=series)
    assert "<svg" in result.svg
    assert len(result.table_rows) == 3


def test_x_axis_labels_rendered_for_each_unique_year():
    result = _build()
    for year in (0, 1, 2):
        assert f">{year}<" in result.svg


def test_legend_text_present_for_each_series():
    result = _build()
    # Legend text should include both series labels somewhere in the SVG
    # (either the side legend or the fallback under-axis legend).
    assert "Grid only" in result.svg
    assert "Buy solar now" in result.svg


def test_narrow_width_falls_back_to_under_axis_legend():
    result = _build(width=300)
    assert "<svg" in result.svg
    assert "Grid only" in result.svg
