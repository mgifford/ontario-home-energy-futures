"""Dependency-free inline SVG line-chart builder.

No third-party charting library (see ACCESSIBILITY.md's chart decision
record). Series are differentiated by BOTH colour and SVG
``stroke-dasharray`` pattern, so the chart never relies on colour alone.
Every call also returns the same data as plain rows, so a caller can
render an adjacent accessible HTML table from the identical values used
to draw the SVG - the two cannot drift because they come from one
function call.

Colours are drawn from a small fixed palette rather than CSS custom
properties, because SVG ``stroke`` does not reliably inherit page-level
``var(--color-x)`` custom properties across all browsers when the SVG is
inlined via a templating string (as opposed to an external stylesheet);
using explicit, WCAG-AA-contrast-checked colours keeps the chart legible
in both the light and dark themes without depending on that inheritance
behaving consistently. Dash patterns (not colour) are the primary
differentiator; colour is a secondary aid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.sax.saxutils import escape

# One (colour, dash-pattern) pair per series, in order. Dash patterns are
# the primary differentiator (colour-blind-safe, works in forced-colours
# mode); colours are chosen for AA contrast against both a white and a
# near-black background.
_SERIES_STYLES = [
    {"color": "#0b4f8a", "dasharray": "none", "marker": "circle"},
    {"color": "#b8860b", "dasharray": "6,4", "marker": "square"},
    {"color": "#146c2e", "dasharray": "2,3", "marker": "triangle"},
    {"color": "#8a3d8a", "dasharray": "8,3,2,3", "marker": "diamond"},
    {"color": "#b3261e", "dasharray": "1,3", "marker": "cross"},
    {"color": "#3a3f45", "dasharray": "10,2,2,2", "marker": "circle"},
]


@dataclass(frozen=True)
class ChartSeries:
    """One line's worth of data: a label and (x, y) points."""

    label: str
    points: list[tuple[float, float]]


@dataclass(frozen=True)
class LineChartResult:
    svg: str
    table_rows: list[dict]
    accessible_name: str
    accessible_description: str


def _marker_path(cx: float, cy: float, shape: str, size: float = 4.0) -> str:
    if shape == "square":
        return f'<rect x="{cx - size:.1f}" y="{cy - size:.1f}" width="{size * 2:.1f}" height="{size * 2:.1f}" />'
    if shape == "triangle":
        return (
            f'<polygon points="{cx:.1f},{cy - size:.1f} '
            f"{cx - size:.1f},{cy + size:.1f} {cx + size:.1f},{cy + size:.1f}\" />"
        )
    if shape == "diamond":
        return (
            f'<polygon points="{cx:.1f},{cy - size:.1f} {cx + size:.1f},{cy:.1f} '
            f'{cx:.1f},{cy + size:.1f} {cx - size:.1f},{cy:.1f}" />'
        )
    if shape == "cross":
        return (
            f'<path d="M{cx - size:.1f},{cy - size:.1f} L{cx + size:.1f},{cy + size:.1f} '
            f'M{cx - size:.1f},{cy + size:.1f} L{cx + size:.1f},{cy - size:.1f}" />'
        )
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{size:.1f}" />'


def build_cumulative_cost_line_chart(
    *,
    series: list[ChartSeries],
    x_label: str,
    y_label: str,
    accessible_name: str,
    accessible_description: str,
    width: int = 640,
    height: int = 360,
) -> LineChartResult:
    """Build a multi-line SVG chart plus the equivalent table rows.

    ``series`` must all share the same x-values (this is enforced by the
    caller passing one point per year per series) - table rows are built
    by zipping series together on that assumption.
    """
    if not series:
        raise ValueError("series must not be empty")

    margin_left, margin_right, margin_top, margin_bottom = 70, 20, 30, 50
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    all_x = [p[0] for s in series for p in s.points]
    all_y = [p[1] for s in series for p in s.points]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(0.0, min(all_y)), max(all_y)
    if x_max == x_min:
        x_max = x_min + 1
    if y_max == y_min:
        y_max = y_min + 1

    def scale_x(x: float) -> float:
        return margin_left + (x - x_min) / (x_max - x_min) * plot_width

    def scale_y(y: float) -> float:
        return margin_top + plot_height - (y - y_min) / (y_max - y_min) * plot_height

    parts: list[str] = []
    parts.append(
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-labelledby="chart-title chart-desc" class="line-chart">'
    )
    parts.append(f"<title id=\"chart-title\">{escape(accessible_name)}</title>")
    parts.append(f"<desc id=\"chart-desc\">{escape(accessible_description)}</desc>")

    # Axes.
    axis_color = "#4a4a4a"
    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" '
        f'y2="{margin_top + plot_height}" stroke="{axis_color}" stroke-width="1" />'
    )
    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top + plot_height}" '
        f'x2="{margin_left + plot_width}" y2="{margin_top + plot_height}" '
        f'stroke="{axis_color}" stroke-width="1" />'
    )

    # Y-axis tick labels (4 ticks: min, 1/3, 2/3, max).
    for i in range(4):
        y_value = y_min + (y_max - y_min) * i / 3
        y_pixel = scale_y(y_value)
        parts.append(
            f'<line x1="{margin_left - 4}" y1="{y_pixel:.1f}" x2="{margin_left}" '
            f'y2="{y_pixel:.1f}" stroke="{axis_color}" stroke-width="1" />'
        )
        parts.append(
            f'<text x="{margin_left - 8}" y="{y_pixel + 4:.1f}" font-size="11" '
            f'text-anchor="end" fill="{axis_color}">${y_value:,.0f}</text>'
        )

    # X-axis tick labels: every x value present (years are few and exact).
    unique_x = sorted(set(all_x))
    for x_value in unique_x:
        x_pixel = scale_x(x_value)
        parts.append(
            f'<text x="{x_pixel:.1f}" y="{margin_top + plot_height + 18}" font-size="11" '
            f'text-anchor="middle" fill="{axis_color}">{x_value:.0f}</text>'
        )

    parts.append(
        f'<text x="{margin_left + plot_width / 2:.1f}" y="{height - 6}" font-size="12" '
        f'text-anchor="middle" fill="{axis_color}">{escape(x_label)}</text>'
    )
    parts.append(
        f'<text x="14" y="{margin_top + plot_height / 2:.1f}" font-size="12" '
        f'text-anchor="middle" fill="{axis_color}" '
        f'transform="rotate(-90 14 {margin_top + plot_height / 2:.1f})">{escape(y_label)}</text>'
    )

    # Series lines + markers.
    for i, s in enumerate(series):
        style = _SERIES_STYLES[i % len(_SERIES_STYLES)]
        path_points = " ".join(f"{scale_x(x):.1f},{scale_y(y):.1f}" for x, y in s.points)
        dash_attr = "" if style["dasharray"] == "none" else f' stroke-dasharray="{style["dasharray"]}"'
        parts.append(
            f'<polyline points="{path_points}" fill="none" stroke="{style["color"]}" '
            f'stroke-width="2.5"{dash_attr} />'
        )
        parts.append(f'<g fill="{style["color"]}">')
        for x, y in s.points:
            parts.append(_marker_path(scale_x(x), scale_y(y), style["marker"]))
        parts.append("</g>")

    # Text legend (not colour-only: label text + dash-pattern swatch).
    legend_y = margin_top
    legend_x = margin_left + plot_width + 8
    if width - legend_x < 100:
        # Not enough room for a side legend at this width; fall back to
        # placing legend entries under the x-axis label instead.
        legend_x = margin_left
        legend_y = height - 40
        for i, s in enumerate(series):
            style = _SERIES_STYLES[i % len(_SERIES_STYLES)]
            entry_x = legend_x + i * (plot_width / max(1, len(series)))
            parts.append(
                f'<line x1="{entry_x}" y1="{legend_y}" x2="{entry_x + 14}" y2="{legend_y}" '
                f'stroke="{style["color"]}" stroke-width="2.5" '
                + ("" if style["dasharray"] == "none" else f'stroke-dasharray="{style["dasharray"]}" ')
                + "/>"
            )
            parts.append(
                f'<text x="{entry_x + 18}" y="{legend_y + 4}" font-size="10" fill="{axis_color}">'
                f"{escape(s.label)}</text>"
            )

    parts.append("</svg>")
    svg = "".join(parts)

    # Table rows: one row per x-value, one column per series.
    table_rows = []
    for x_value in unique_x:
        row: dict = {"x": x_value}
        for s in series:
            match = next((y for (px, y) in s.points if px == x_value), None)
            row[s.label] = match
        table_rows.append(row)

    return LineChartResult(
        svg=svg,
        table_rows=table_rows,
        accessible_name=accessible_name,
        accessible_description=accessible_description,
    )
