"""
warehouse_map.py (web)
-------------------------
The Warehouse Map / Heat Map of Picking Activity page. Unlike the
Tkinter version's custom click-to-drill HeatGrid, this uses a Plotly
icicle chart: the full Zone -> Aisle -> Rack -> Shelf -> Bin hierarchy
renders at once, color-coded by picking activity, and clicking any
segment zooms in - that's native Plotly.js behavior, no custom
click-handling code needed.
"""

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from app.theme import Palette
from app.analytics.common import parse_date
from app.analytics.warehouse_map import build_activity_tree, skus_at_location, LEVELS
from app.web.analysis import _build_presets, _load_orders_and_master

HEAT_SCALE = [Palette.BORDER, Palette.TEAL, Palette.AMBER, Palette.RED]


def _build_icicle_dataframe(counts, master_rows, metric):
    rows = []
    grand_total_lines = sum(v["order_lines"] for k, v in counts.items() if len(k) == 1)
    grand_total_units = sum(v["units"] for k, v in counts.items() if len(k) == 1)
    rows.append({
        "id": "", "parent": "", "label": "Warehouse",
        "order_lines": grand_total_lines, "units": grand_total_units, "info": "",
    })

    for path, vals in counts.items():
        node_id = "/".join(path)
        parent_id = "/".join(path[:-1])
        info = ""
        if len(path) == len(LEVELS):
            skus = skus_at_location(master_rows, path)
            if skus:
                info = ", ".join(f"{s['sku']} ({s['product_name']})" for s in skus[:3])
        rows.append({
            "id": node_id, "parent": parent_id, "label": path[-1],
            "order_lines": vals["order_lines"], "units": vals["units"], "info": info,
        })

    return pd.DataFrame(rows)


def render_warehouse_map_page(analysis_config):
    st.title(f"{analysis_config.icon} {analysis_config.label}")
    if analysis_config.description:
        st.caption(analysis_config.description)
    st.caption(
        "Click any segment to zoom in; click the center label to zoom back out. "
        "Color = picking activity in the date range below."
    )

    order_rows, master_rows = _load_orders_and_master()

    dates = [d for d in (parse_date(r.get("order_date", "")) for r in order_rows) if d is not None]
    data_min = min(dates) if dates else date.today() - timedelta(days=365)
    data_max = max(dates) if dates else date.today()
    presets = _build_presets(data_max, data_min, data_max)
    preset_names = [p[0] for p in presets]

    preset_key = "warehouse_map_preset"
    start_key = "warehouse_map_start"
    end_key = "warehouse_map_end"

    def _apply_preset():
        chosen = st.session_state[preset_key]
        for name, s, e in presets:
            if name == chosen:
                st.session_state[start_key] = s
                st.session_state[end_key] = e
                return

    if preset_key not in st.session_state:
        st.session_state[preset_key] = "All Time"
        _apply_preset()

    st.subheader("Date Range")
    st.selectbox("Quick range", preset_names, key=preset_key, on_change=_apply_preset)
    col1, col2, col3 = st.columns(3)
    start = col1.date_input("Start", key=start_key)
    end = col2.date_input("End", key=end_key)
    metric = col3.selectbox("Color by", ["order_lines", "units"], key="warehouse_map_metric")

    if start > end:
        st.error("Start date must be on or before the end date.")
        return

    counts = build_activity_tree(order_rows, start, end)
    if not counts:
        st.info("No picking activity recorded in this date range.")
        return

    df = _build_icicle_dataframe(counts, master_rows, metric)

    fig = px.icicle(
        df, ids="id", parents="parent", names="label", values=metric,
        color=metric, color_continuous_scale=HEAT_SCALE, branchvalues="total",
        hover_data={"order_lines": True, "units": True, "info": True},
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=650)
    st.plotly_chart(fig, width='stretch')

    metric_label = "Order Lines" if metric == "order_lines" else "Units"
    st.caption(f"Coloring by {metric_label}. Leaf-level (Bin) segments show which SKU is homed there on hover.")

    with st.expander("\U0001F4BE Export full activity breakdown to CSV"):
        export_df = df[df["id"] != ""].rename(columns={
            "id": "location_path", "label": "code", "order_lines": "order_lines", "units": "units",
        })
        st.dataframe(export_df[["location_path", "code", "order_lines", "units"]],
                    width='stretch', hide_index=True, height=300)
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV", data=csv_bytes,
            file_name=f"warehouse_map_{start}_{end}.csv", mime="text/csv",
            key="warehouse_map_download",
        )
