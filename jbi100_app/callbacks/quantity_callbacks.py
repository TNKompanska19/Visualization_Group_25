"""
Quantity Callbacks - T2 & T3 FINAL v11
JBI100 Visualization - Group 25

BEHAVIOR:
- Hover on line charts: Shows week highlight + updates bar/violin/panel (follows mouse)
- Click anywhere on chart: Clears hover, shows zoomed/full period
- Zoom: Shows zoomed period when no hover active
"""

from dash import callback, Output, Input, State, ctx, html, no_update
from dash.exceptions import PreventUpdate
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS, DEPT_LABELS_SHORT, SERVICES
from jbi100_app.data import get_services_data, get_patients_data

_services = get_services_data()
_patients = get_patients_data()

LEGEND_ORDER = ["emergency", "surgery", "general_medicine", "ICU"]
AXIS_LABEL_FONT = dict(size=11, color="#2c3e50")
AXIS_TICK_FONT = dict(size=10, color="#34495e")
GRID_COLOR = "#ecf0f1"
TITLE_FONT_SIZE = 13
SUBTITLE_FONT_SIZE = 9


def _filter_services(depts, week_range, hide_anomalies=False):
    week_range = week_range or [1, 52]
    w0, w1 = int(week_range[0]), int(week_range[1])
    df = _services[(_services["week"] >= w0) & (_services["week"] <= w1)].copy()
    if depts:
        df = df[df["service"].isin(depts)].copy()
    if hide_anomalies:
        df = df[~df["week"].isin(list(range(3, 53, 3)))].copy()
    return df


def _filter_patients(depts, week_range, hide_anomalies=False):
    week_range = week_range or [1, 52]
    w0, w1 = int(week_range[0]), int(week_range[1])
    df = _patients.copy()
    if depts:
        df = df[df["service"].isin(depts)].copy()
    if "arrival_week" in df.columns:
        df = df[(df["arrival_week"] >= w0) & (df["arrival_week"] <= w1)].copy()
        if hide_anomalies:
            df = df[~df["arrival_week"].isin(list(range(3, 53, 3)))].copy()
    return df


def _empty_fig(title="No data"):
    fig = go.Figure()
    fig.add_annotation(text=title, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=10, color="#999"))
    fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=20, b=10), xaxis=dict(visible=False),
                      yaxis=dict(visible=False))
    return fig


def _get_ordered_services(depts):
    return [s for s in LEGEND_ORDER if s in depts]


def _add_hover_highlight(fig, week, y_range):
    if week:
        fig.add_shape(type="rect", x0=week - 0.4, x1=week + 0.4, y0=y_range[0], y1=y_range[1],
                      fillcolor="rgba(52, 152, 219, 0.15)", line=dict(width=0), layer="below")


# ---- Stacked bar: available beds vs demand (unified layout) ----
@callback(
    Output("stacked-beds-demand-chart", "figure"),
    [Input("dept-filter", "value"), Input("week-slider", "value"), Input("hide-anomalies-toggle", "value"),
     Input("hovered-week-store", "data")],
    prevent_initial_call=False,
)
def update_stacked_beds_demand(depts, week_range, hide_anom, hovered_store):
    """Stacked bar: one bar per week in range; stack = beds (bottom), demand (top). Highlight hovered week."""
    week_range = week_range or [1, 52]
    depts = depts or ["emergency"]
    hide = "hide" in (hide_anom or [])
    df = _filter_services(depts, week_range, hide)
    if df.empty:
        return _empty_fig("Select departments")
    w0, w1 = int(week_range[0]), int(week_range[1])
    weeks = sorted(df["week"].unique())
    if not weeks:
        return _empty_fig("No data")
    agg = df.groupby("week").agg(
        available_beds=("available_beds", "sum"),
        demand=("patients_request", "sum"),
    ).reindex(weeks).fillna(0)
    hovered_week = hovered_store.get("week") if isinstance(hovered_store, dict) else None
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=agg.index, y=agg["available_beds"], name="Beds",
        marker_color="#5DADE2", opacity=0.8,
        hovertemplate="Week %{x}<br>Beds: %{y:.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=agg.index, y=agg["demand"], name="Demand",
        marker_color="#E74C3C", opacity=0.8,
        hovertemplate="Week %{x}<br>Demand: %{y:.0f}<extra></extra>",
    ))
    if hovered_week is not None and hovered_week in agg.index:
        y_max = max(agg["available_beds"].max(), agg["demand"].max()) * 1.1
        fig.add_vrect(
            x0=hovered_week - 0.5, x1=hovered_week + 0.5,
            y0=0, y1=y_max, fillcolor="rgba(52, 152, 219, 0.15)", line_width=0, layer="below",
        )
    y_max = max(agg["available_beds"].max(), agg["demand"].max())
    y_upper = max(y_max * 1.15, 10)
    fig.update_layout(
        barmode="stack",
        height=380,
        template="plotly_white", margin=dict(l=58, r=28, t=52, b=52),
        title=dict(
            text="<b>Beds vs Demand by Week</b><br><span style='font-size:9px;color:#7f8c8d'>Hover the line chart (T1) above to highlight a week here</span>",
            font=dict(size=TITLE_FONT_SIZE, color="#2c3e50"), x=0.5, xanchor="center", y=0.96,
        ),
        xaxis=dict(title="Week", gridcolor=GRID_COLOR, tickfont=AXIS_TICK_FONT),
        yaxis=dict(title="Count", range=[0, y_upper], gridcolor=GRID_COLOR, tickfont=AXIS_TICK_FONT),
        showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    return fig


@callback(
    Output("t3-los-chart", "figure"),
    [Input("dept-filter", "value"), Input("week-slider", "value"), Input("hide-anomalies-toggle", "value"),
     Input("hovered-week-store", "data")],
    prevent_initial_call=False,
)
def update_los_chart(depts, week_range, hide_anom, hovered_store):
    """LOS violin: full distribution for week range; when hovered week set, add horizontal line at that week's median LOS."""
    week_range = week_range or [1, 52]
    depts = depts or ["emergency"]
    hide = "hide" in (hide_anom or [])
    df_full = _filter_patients(depts, week_range, hide)

    if df_full.empty or "length_of_stay" not in df_full.columns:
        return _empty_fig("No patient data")

    fig = go.Figure()
    services = _get_ordered_services(df_full["service"].unique())

    for svc in services:
        svc_df = df_full[df_full["service"] == svc]
        col = DEPT_COLORS.get(svc, "#999")
        lbl = DEPT_LABELS_SHORT.get(svc, svc)
        fig.add_trace(go.Violin(y=svc_df["length_of_stay"], name=lbl, box_visible=True, meanline_visible=True,
                                fillcolor=col, line_color=col, opacity=0.5, points=False, hoverinfo="y+name"))

    highlight_txt = ""
    hovered_week = hovered_store.get("week") if isinstance(hovered_store, dict) else None

    if hovered_week and "arrival_week" in df_full.columns:
        highlight_patients = df_full[df_full["arrival_week"] == hovered_week].copy()
        highlight_txt = f" • Week {hovered_week}"
        if not highlight_patients.empty:
            for svc in services:
                svc_hl = highlight_patients[highlight_patients["service"] == svc]
                if len(svc_hl) >= 1:
                    median = svc_hl["length_of_stay"].median()
                    col = DEPT_COLORS.get(svc, "#999")
                    lbl = DEPT_LABELS_SHORT.get(svc, svc)
                    fig.add_hline(
                        y=median, line_dash="solid", line_color=col, line_width=2, opacity=0.8,
                        annotation_text=f"W{hovered_week} {lbl}: {median:.0f}d",
                        annotation_position="right", annotation_font=dict(size=8, color=col),
                    )

    fig.add_hline(y=7, line_dash="dot", line_color="#009E73", line_width=1, opacity=0.4,
                  annotation_text="7d", annotation_position="right", annotation_font=dict(size=8, color="#009E73"))
    fig.add_hline(y=14, line_dash="dash", line_color="#D55E00", line_width=1.5, opacity=0.5,
                  annotation_text="14d blocker", annotation_position="right",
                  annotation_font=dict(size=8, color="#D55E00"))

    avg_los = df_full["length_of_stay"].mean()
    blockers = (df_full["length_of_stay"] > 14).sum()

    fig.update_layout(
        height=420,
        title=dict(
            text=f"<b>Length of Stay</b><br><span style='font-size:{SUBTITLE_FONT_SIZE}px;color:#7f8c8d'>Avg: {avg_los:.1f}d • Blockers: {blockers}{highlight_txt}</span>",
            font=dict(size=TITLE_FONT_SIZE, color="#2c3e50"), x=0.5, xanchor="center", y=0.94),
        template="plotly_white", margin=dict(l=58, r=88, t=58, b=42),
        yaxis=dict(title=dict(text="Length of Stay (days)", font=AXIS_LABEL_FONT), gridcolor=GRID_COLOR,
                   range=[0, min(df_full["length_of_stay"].max() + 3, 35)], tickfont=AXIS_TICK_FONT),
        xaxis=dict(title="", tickfont=AXIS_TICK_FONT),
        showlegend=False, hovermode="closest",
    )
    return fig


def _update_context_panel_placeholder(depts, selected_week, zoom_store, week_range, hide_anom):
    if not depts:
        depts = []
    hide = "hide" in (hide_anom or [])

    legend_items = [html.Div(style={"display": "flex", "alignItems": "center", "gap": "6px", "marginBottom": "3px"},
                             children=[html.Div(style={"width": "12px", "height": "12px",
                                                       "backgroundColor": DEPT_COLORS.get(svc, "#999"),
                                                       "borderRadius": "2px"}),
                                       html.Span(DEPT_LABELS.get(svc, svc),
                                                 style={"fontSize": "9px", "color": "#333"})])
                    for svc in _get_ordered_services(depts)] or [
                       html.Span("Select departments", style={"color": "#999", "fontStyle": "italic"})]

    eff_range = [zoom_store["week_start"], zoom_store["week_end"]] if zoom_store and zoom_store.get(
        "zoomed") else week_range
    df = _filter_services(depts, eff_range, hide)

    week_header = "Hover to inspect"
    week_metrics = [
        html.Span("Hover weeks on charts", style={"color": "#999", "fontStyle": "italic", "fontSize": "8px"})]
    realloc_style = {"display": "none"}
    realloc_text = []

    def build_metrics(week_df):
        week_data, metrics = [], []
        for svc in _get_ordered_services(depts):
            svc_data = week_df[week_df["service"] == svc]
            col = DEPT_COLORS.get(svc, "#999")
            lbl = DEPT_LABELS_SHORT.get(svc, svc)
            if len(svc_data) > 0:
                beds = svc_data["available_beds"].values[0]
                demand = svc_data["patients_admitted"].values[0] + svc_data["patients_refused"].values[0]
                net = beds - demand
                occ = (svc_data["patients_admitted"].values[0] / beds * 100) if beds > 0 else 0
                week_data.append(
                    {"svc": svc, "lbl": lbl, "col": col, "net": net, "beds": beds, "demand": demand, "occ": occ})
                bal_col, bal_icon = ("#27ae60", "✓") if net >= 0 else ("#e74c3c", "⚠")
                metrics.append(html.Div(
                    style={"marginBottom": "4px", "padding": "3px", "backgroundColor": "#fff", "borderRadius": "3px",
                           "borderLeft": f"3px solid {col}"},
                    children=[html.Div([html.Span(lbl, style={"fontWeight": "600", "color": col, "fontSize": "9px"}),
                                        html.Span(f" {bal_icon}", style={"color": bal_col})]),
                              html.Div(f"Beds: {beds:.0f} | Demand: {demand:.0f}",
                                       style={"color": "#555", "fontSize": "8px"}),
                              html.Div([html.Span("Net: ", style={"color": "#888"}),
                                        html.Span(f"{net:+.0f}", style={"fontWeight": "600", "color": bal_col}),
                                        html.Span(f" | Occ: {occ:.0f}%", style={"color": "#888"})],
                                       style={"fontSize": "8px"})]))
        return week_data, metrics

    def build_realloc(week_data):
        if len(week_data) < 2:
            return {"display": "none"}, []
        donors = sorted([d for d in week_data if d["net"] > 0], key=lambda x: x["net"], reverse=True)
        needers = sorted([d for d in week_data if d["net"] < 0], key=lambda x: x["net"])
        if needers and donors:
            hp, dn = needers[0], donors[0]
            return {"display": "block"}, [
                html.Div([html.Span("⚠️ ", style={"fontSize": "10px"}),
                          html.Span(hp["lbl"], style={"color": hp["col"], "fontWeight": "600"}),
                          html.Span(f" ({hp['net']:+.0f})", style={"color": "#e74c3c"})],
                         style={"marginBottom": "2px"}),
                html.Div([html.Span("✅ ", style={"fontSize": "10px"}),
                          html.Span(dn["lbl"], style={"color": dn["col"], "fontWeight": "600"}),
                          html.Span(f" ({dn['net']:+.0f})", style={"color": "#27ae60"})],
                         style={"marginBottom": "4px"}),
                html.Div([html.Span("💡 ", style={"fontSize": "10px"}),
                          html.Span(dn["lbl"], style={"color": dn["col"], "fontWeight": "600"}),
                          html.Span(" → ", style={"color": "#555"}),
                          html.Span(hp["lbl"], style={"color": hp["col"], "fontWeight": "600"})],
                         style={"padding": "3px", "backgroundColor": "#e8f4f8", "borderRadius": "3px"})]
        elif needers:
            hp = needers[0]
            return {"display": "block"}, [html.Div([html.Span("⚠️ ", style={"fontSize": "10px"}), html.Span(hp["lbl"],
                                                                                                            style={
                                                                                                                "color":
                                                                                                                    hp[
                                                                                                                        "col"],
                                                                                                                "fontWeight": "600"}),
                                                    html.Span(f" ({hp['net']:+.0f})", style={"color": "#e74c3c"})]),
                                          html.Div("No donor",
                                                   style={"color": "#888", "fontStyle": "italic", "fontSize": "8px"})]
        return {"display": "block"}, [html.Div("✓ All balanced", style={"color": "#27ae60"})]

    if selected_week and selected_week.get("week") and not df.empty:
        w = selected_week["week"]
        week_header = f"📅 Week {w}"
        week_df = df[df["week"] == w].copy()
        if not week_df.empty:
            week_data, week_metrics = build_metrics(week_df)
            realloc_style, realloc_text = build_realloc(week_data)
        else:
            week_metrics = [html.Span(f"No data for week {w}", style={"color": "#999", "fontSize": "8px"})]
    elif zoom_store and zoom_store.get("zoomed") and not df.empty:
        ws, we = zoom_store["week_start"], zoom_store["week_end"]
        week_header = f"📅 Wk {ws}–{we} (Avg)"
        agg_df = df.groupby("service").agg(
            {"available_beds": "mean", "patients_admitted": "mean", "patients_refused": "mean"}).reset_index()
        week_data, week_metrics = build_metrics(agg_df)
        realloc_style, realloc_text = build_realloc(week_data)
    elif len(depts) >= 2:
        realloc_style = {"display": "block"}
        realloc_text = [
            html.Span("Hover or zoom for insight", style={"color": "#999", "fontStyle": "italic", "fontSize": "8px"})]

    return legend_items, week_header, week_metrics, realloc_style, realloc_text


def register_quantity_callbacks():
    pass