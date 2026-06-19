"""
charts.py (web)
-----------------
Converts the chart_spec dicts produced by app/analytics/* (the same
ones the Tkinter app feeds to app/ui/charts.py) into Plotly figures for
Streamlit. Keeping the chart_spec format shared means every analytics
module's chart support works on both front ends for free.
"""

import plotly.graph_objects as go

from app.web import colors as Palette

AXIS_GRID_COLOR = Palette.BORDER


def render_chart_spec(spec):
    """spec -> a plotly Figure, or None if spec is empty/unsupported."""
    if not spec or not spec.get("items"):
        return None

    chart_type = spec.get("type")
    title = spec.get("title", "")
    value_fmt = spec.get("value_fmt", "{:,.0f}")

    if chart_type == "hbar":
        return _hbar(spec["items"], title, value_fmt)
    if chart_type == "vbar":
        return _vbar(spec["items"], title, value_fmt)
    if chart_type == "line":
        return _line(spec["items"], title, value_fmt)
    if chart_type == "pareto":
        return _pareto(spec["items"], title)
    return None


def _base_layout(title, height):
    return dict(
        title=dict(text=title, font=dict(color=Palette.NAVY, size=16)),
        margin=dict(l=10, r=20, t=46, b=10),
        height=height,
        plot_bgcolor=Palette.PANEL,
        paper_bgcolor=Palette.PANEL,
        font=dict(color=Palette.TEXT),
        xaxis=dict(gridcolor=AXIS_GRID_COLOR),
        yaxis=dict(gridcolor=AXIS_GRID_COLOR),
    )


def _hbar(items, title, value_fmt):
    items = list(items)[::-1]  # reverse so the #1 item ends up on top
    labels = [str(label) for label, _ in items]
    values = [v for _, v in items]
    text = [value_fmt.format(v) for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=Palette.TEAL, text=text, textposition="outside",
    ))
    fig.update_layout(**_base_layout(title, max(280, 30 * len(items) + 60)))
    fig.update_yaxes(automargin=True)
    return fig


def _vbar(items, title, value_fmt):
    labels = [str(label) for label, _ in items]
    values = [v for _, v in items]
    text = [value_fmt.format(v) for v in values]
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=Palette.TEAL, text=text, textposition="outside",
    ))
    fig.update_layout(**_base_layout(title, 380))
    return fig


def _line(items, title, value_fmt):
    labels = [str(label) for label, _ in items]
    values = [v for _, v in items]
    fig = go.Figure(go.Scatter(
        x=labels, y=values, mode="lines+markers", line=dict(color=Palette.TEAL, width=2),
        marker=dict(size=6),
    ))
    fig.update_layout(**_base_layout(title, 380))
    return fig


def _pareto(items, title):
    labels = [str(label) for label, _, _ in items]
    values = [v for _, v, _ in items]
    cum_pct = [c for _, _, c in items]
    fig = go.Figure()
    fig.add_bar(x=labels, y=values, name="Value", marker_color=Palette.TEAL)
    fig.add_trace(go.Scatter(
        x=labels, y=cum_pct, name="Cumulative %", yaxis="y2",
        line=dict(color=Palette.AMBER, width=2), mode="lines+markers",
    ))
    layout = _base_layout(title, 440)
    layout["yaxis2"] = dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105])
    layout["legend"] = dict(orientation="h", y=1.15)
    fig.update_layout(**layout)
    return fig
