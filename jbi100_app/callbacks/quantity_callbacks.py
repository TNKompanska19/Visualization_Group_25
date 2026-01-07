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
    w0, w1 = int(week_range[0]), int(week_range[1])
    df = _services[(_services["week"] >= w0) & (_services["week"] <= w1)].copy()
    if depts:
        df = df[df["service"].isin(depts)].copy()
    if hide_anomalies:
        df = df[~df["week"].isin(list(range(3, 53, 3)))].copy()
    return df


def _filter_patients(depts, week_range, hide_anomalies=False):
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


@callback(
    Output("t2t3-zoom-store", "data"),
    [Input("t2-refusal-chart", "relayoutData"), Input("t3-occupancy-chart", "relayoutData")],
    State("week-slider", "value"), prevent_initial_call=True
)
def capture_linked_zoom(ref_relayout, occ_relayout, week_range):
    if not ctx.triggered:
        raise PreventUpdate
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    relayout = ref_relayout if triggered_id == "t2-refusal-chart" else occ_relayout
    if not relayout:
        raise PreventUpdate
    if "xaxis.range[0]" in relayout and "xaxis.range[1]" in relayout:
        try:
            ws = max(1, int(round(float(relayout["xaxis.range[0]"]))))
            we = min(52, int(round(float(relayout["xaxis.range[1]"]))))
            if ws < we:
                return {"week_start": ws, "week_end": we, "zoomed": True}
        except (ValueError, TypeError):
            raise PreventUpdate
    if "xaxis.autorange" in relayout:
        return {"week_start": int(week_range[0]), "week_end": int(week_range[1]), "zoomed": False}
    raise PreventUpdate


@callback(Output("global-zoom-store", "data"), Input("t2t3-zoom-store", "data"), prevent_initial_call=True)
def sync_global_zoom(zoom):
    return {"source": "T2T3", **zoom} if zoom and zoom.get("zoomed") else {"zoomed": False}


# Hover updates week, Click clears it
@callback(
    Output("t2t3-selected-week", "data"),
    [Input("t2-refusal-chart", "hoverData"), Input("t3-occupancy-chart", "hoverData"),
     Input("t2-refusal-chart", "clickData"), Input("t3-occupancy-chart", "clickData")],
    prevent_initial_call=True
)
def capture_week_selection(ref_hover, occ_hover, ref_click, occ_click):
    if not ctx.triggered:
        raise PreventUpdate

    triggered_prop = ctx.triggered[0]["prop_id"]

    # Click ALWAYS clears (resets to period view)
    if "clickData" in triggered_prop:
        return None

    # Hover updates the week
    if "hoverData" in triggered_prop:
        hover = ref_hover if "refusal" in triggered_prop else occ_hover
        if hover and "points" in hover and len(hover["points"]) > 0:
            x = hover["points"][0].get("x")
            if x is not None:
                try:
                    week = int(round(float(x)))
                    if 1 <= week <= 52:
                        return {"week": week}
                except (ValueError, TypeError):
                    pass

    raise PreventUpdate


@callback(
    Output("t2-refusal-chart", "figure"),
    [Input("dept-filter", "value"), Input("week-slider", "value"), Input("hide-anomalies-toggle", "value"),
     Input("t2t3-zoom-store", "data"), Input("t2t3-selected-week", "data")]
)
def update_refusal_chart(depts, week_range, hide_anom, zoom_store, selected_week):
    hide = "hide" in (hide_anom or [])
    df = _filter_services(depts, week_range, hide)
    if df.empty:
        return _empty_fig("Select departments")

    df = df.copy()
    df["ref_per_bed"] = (df["patients_refused"] / df["available_beds"]).replace([np.inf, -np.inf], np.nan).fillna(0)
    fig = go.Figure()
    services = _get_ordered_services(df["service"].unique())
    y_max = df["ref_per_bed"].max() * 1.1
    median_ref = df["ref_per_bed"].median()

    for svc in services:
        svc_df = df[df["service"] == svc].sort_values("week")
        col = DEPT_COLORS.get(svc, "#999")
        lbl = DEPT_LABELS.get(svc, svc)
        fig.add_trace(go.Scatter(x=svc_df["week"], y=svc_df["ref_per_bed"], mode="lines+markers", name=lbl,
                                 line=dict(color=col, width=2), marker=dict(size=4, color=col),
                                 hovertemplate=f"<b>{lbl}</b><br>Week %{{x}}<br>Ref/Bed: %{{y:.2f}}<extra></extra>"))

    wmin, wmax = int(week_range[0]), int(week_range[1])
    x_range = [wmin - 0.5, wmax + 0.5]
    zoom_txt = ""
    if zoom_store and zoom_store.get("zoomed"):
        x_range = [zoom_store["week_start"] - 0.5, zoom_store["week_end"] + 0.5]
        zoom_txt = f" (Wk {zoom_store['week_start']}–{zoom_store['week_end']})"

    # Add highlight for hovered week
    if selected_week and selected_week.get("week"):
        _add_hover_highlight(fig, selected_week["week"], [0, y_max])

    fig.add_hline(y=median_ref, line_dash="dash", line_color="#95a5a6", line_width=1,
                  annotation_text=f"Median: {median_ref:.1f}", annotation_position="right",
                  annotation_font=dict(size=8, color="#7f8c8d"))

    dtick = 4 if wmax - wmin > 26 else 2
    fig.update_layout(
        title=dict(
            text=f"<b>Capacity Pressure</b>{zoom_txt}<br><span style='font-size:{SUBTITLE_FONT_SIZE}px;color:#7f8c8d'>Hover to inspect week • Click to clear</span>",
            font=dict(size=TITLE_FONT_SIZE, color="#2c3e50"), x=0.5, xanchor="center", y=0.96),
        template="plotly_white", margin=dict(l=50, r=10, t=45, b=45),
        xaxis=dict(title=dict(text="Week", font=AXIS_LABEL_FONT), gridcolor=GRID_COLOR, dtick=dtick, range=x_range,
                   tickfont=AXIS_TICK_FONT),
        yaxis=dict(title=dict(text="Refusals per Bed", font=AXIS_LABEL_FONT), gridcolor=GRID_COLOR,
                   tickfont=AXIS_TICK_FONT, range=[0, y_max]),
        showlegend=False, hovermode="x unified",
        clickmode="event",
    )
    return fig


@callback(
    Output("t3-occupancy-chart", "figure"),
    [Input("dept-filter", "value"), Input("week-slider", "value"), Input("hide-anomalies-toggle", "value"),
     Input("t2t3-zoom-store", "data"), Input("t2t3-selected-week", "data")]
)
def update_occupancy_chart(depts, week_range, hide_anom, zoom_store, selected_week):
    hide = "hide" in (hide_anom or [])
    df = _filter_services(depts, week_range, hide)
    if df.empty:
        return _empty_fig("Select departments")

    df = df.copy()
    df["occupancy"] = (df["patients_admitted"] / df["available_beds"] * 100).fillna(0)
    fig = go.Figure()
    wmin, wmax = int(week_range[0]), int(week_range[1])
    ymin, ymax = df["occupancy"].min(), df["occupancy"].max()
    y_range = [max(0, ymin - 10), max(115, ymax + 5)]

    fig.add_shape(type="rect", x0=wmin - 0.5, x1=wmax + 0.5, y0=80, y1=100, fillcolor="rgba(0,158,115,0.06)",
                  line_width=0, layer="below")
    if y_range[1] > 100:
        fig.add_shape(type="rect", x0=wmin - 0.5, x1=wmax + 0.5, y0=100, y1=y_range[1], fillcolor="rgba(213,94,0,0.08)",
                      line_width=0, layer="below")

    for svc in _get_ordered_services(df["service"].unique()):
        svc_df = df[df["service"] == svc].sort_values("week")
        col = DEPT_COLORS.get(svc, "#999")
        lbl = DEPT_LABELS.get(svc, svc)
        fig.add_trace(go.Scatter(x=svc_df["week"], y=svc_df["occupancy"], mode="lines+markers", name=lbl,
                                 line=dict(color=col, width=1.5), marker=dict(size=3, color=col),
                                 hovertemplate=f"<b>{lbl}</b><br>Week %{{x}}<br>Occ: %{{y:.0f}}%<extra></extra>"))

    fig.add_hline(y=100, line_dash="dash", line_color="#D55E00", line_width=1.5, opacity=0.6)
    fig.add_hline(y=80, line_dash="dot", line_color="#009E73", line_width=1, opacity=0.5)

    x_range = [wmin - 0.5, wmax + 0.5]
    zoom_txt = ""
    if zoom_store and zoom_store.get("zoomed"):
        x_range = [zoom_store["week_start"] - 0.5, zoom_store["week_end"] + 0.5]
        zoom_txt = f" (Wk {zoom_store['week_start']}–{zoom_store['week_end']})"

    if selected_week and selected_week.get("week"):
        _add_hover_highlight(fig, selected_week["week"], y_range)

    dtick = 4 if wmax - wmin > 26 else 2
    fig.update_layout(
        title=dict(
            text=f"<b>Occupancy Rate</b>{zoom_txt}<br><span style='font-size:{SUBTITLE_FONT_SIZE}px;color:#7f8c8d'>80–100% optimal • >100% over-capacity</span>",
            font=dict(size=TITLE_FONT_SIZE, color="#2c3e50"), x=0.5, xanchor="center", y=0.95),
        template="plotly_white", margin=dict(l=45, r=10, t=50, b=40),
        xaxis=dict(title=dict(text="Week", font=AXIS_LABEL_FONT), gridcolor=GRID_COLOR, dtick=dtick, range=x_range,
                   tickfont=AXIS_TICK_FONT),
        yaxis=dict(title=dict(text="Occupancy (%)", font=AXIS_LABEL_FONT), gridcolor=GRID_COLOR, range=y_range,
                   tickfont=AXIS_TICK_FONT),
        showlegend=False, hovermode="x unified",
        clickmode="event",
    )
    return fig


@callback(
    Output("t2-bed-chart", "figure"),
    [Input("dept-filter", "value"), Input("week-slider", "value"), Input("hide-anomalies-toggle", "value"),
     Input("t2t3-zoom-store", "data"), Input("t2t3-selected-week", "data")]
)
def update_capacity_chart(depts, week_range, hide_anom, zoom_store, selected_week):
    hide = "hide" in (hide_anom or [])
    df = _filter_services(depts, week_range, hide)
    if df.empty:
        return _empty_fig("Select departments")

    # If hovering a specific week, show that week
    if selected_week and selected_week.get("week"):
        w = selected_week["week"]
        week_df = df[df["week"] == w].copy()
        week_label = f"Week {w}"
        if week_df.empty:
            selected_week = None  # Fall back to period

    # Otherwise show zoomed period or full range
    if not (selected_week and selected_week.get("week")):
        if zoom_store and zoom_store.get("zoomed"):
            ws, we = zoom_store["week_start"], zoom_store["week_end"]
            week_df = df[(df["week"] >= ws) & (df["week"] <= we)].copy()
            week_df = week_df.groupby("service").agg(
                {"available_beds": "mean", "patients_admitted": "mean", "patients_refused": "mean"}).reset_index()
            week_label = f"Avg Wk {ws}–{we}"
        else:
            week_df = df.groupby("service").agg(
                {"available_beds": "mean", "patients_admitted": "mean", "patients_refused": "mean"}).reset_index()
            week_label = f"Avg Wk {int(week_range[0])}–{int(week_range[1])}"

    if week_df.empty:
        return _empty_fig("No data")

    week_df = week_df.copy()
    week_df["demand"] = week_df["patients_admitted"] + week_df["patients_refused"]
    fig = go.Figure()
    services = _get_ordered_services(week_df["service"].unique())

    dept_labels = [DEPT_LABELS.get(s, s) for s in services]
    beds_values, demand_values, colors = [], [], []

    for svc in services:
        row = week_df[week_df["service"] == svc]
        if len(row) > 0:
            beds_values.append(row["available_beds"].values[0])
            demand_values.append(row["demand"].values[0])
            colors.append(DEPT_COLORS.get(svc, "#999"))

    fig.add_trace(go.Bar(x=dept_labels, y=beds_values, showlegend=False,
                         marker=dict(color=colors, opacity=0.4, line=dict(color=colors, width=2)),
                         hovertemplate="<b>%{x}</b><br>Beds: %{y:.0f}<extra></extra>"))
    fig.add_trace(go.Bar(x=dept_labels, y=demand_values, showlegend=False,
                         marker=dict(color=colors, opacity=0.9),
                         hovertemplate="<b>%{x}</b><br>Demand: %{y:.0f}<extra></extra>"))

    for i, svc in enumerate(services):
        row = week_df[week_df["service"] == svc]
        if len(row) > 0:
            beds, demand = row["available_beds"].values[0], row["demand"].values[0]
            net = beds - demand
            y_pos = max(beds, demand) + 2
            color = "#27ae60" if net >= 0 else "#e74c3c"
            fig.add_annotation(x=dept_labels[i], y=y_pos, text=f"{net:+.0f}", showarrow=False,
                               font=dict(size=11, color=color, weight="bold"))

    y_max = max(max(beds_values) if beds_values else 0, max(demand_values) if demand_values else 0) * 1.15

    fig.update_layout(
        title=dict(
            text=f"<b>Capacity vs Demand</b> — {week_label}<br><span style='font-size:{SUBTITLE_FONT_SIZE}px;color:#7f8c8d'>Light=Beds • Dark=Demand • Number=Net</span>",
            font=dict(size=TITLE_FONT_SIZE, color="#2c3e50"), x=0.5, xanchor="center", y=0.93),
        template="plotly_white", margin=dict(l=50, r=20, t=65, b=40), barmode="group",
        xaxis=dict(title="", tickfont=dict(size=10, color="#2c3e50")),
        yaxis=dict(title=dict(text="Count", font=AXIS_LABEL_FONT), gridcolor=GRID_COLOR, tickfont=AXIS_TICK_FONT,
                   range=[0, y_max]),
        showlegend=False, bargap=0.15, bargroupgap=0.05,
    )
    return fig


@callback(
    Output("t3-los-chart", "figure"),
    [Input("dept-filter", "value"), Input("week-slider", "value"), Input("hide-anomalies-toggle", "value"),
     Input("t2t3-zoom-store", "data"), Input("t2t3-selected-week", "data")]
)
def update_los_chart(depts, week_range, hide_anom, zoom_store, selected_week):
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
    highlight_patients = None

    if selected_week and selected_week.get("week") and "arrival_week" in df_full.columns:
        w = selected_week["week"]
        highlight_patients = df_full[df_full["arrival_week"] == w].copy()
        highlight_txt = f" • Week {w}"
    elif zoom_store and zoom_store.get("zoomed") and "arrival_week" in df_full.columns:
        ws, we = zoom_store["week_start"], zoom_store["week_end"]
        highlight_patients = df_full[(df_full["arrival_week"] >= ws) & (df_full["arrival_week"] <= we)].copy()
        highlight_txt = f" • Wk {ws}–{we}"

    if highlight_patients is not None and not highlight_patients.empty and len(highlight_patients) >= 2:
        for svc in services:
            svc_hl = highlight_patients[highlight_patients["service"] == svc]
            if len(svc_hl) >= 2:
                col = DEPT_COLORS.get(svc, "#999")
                lbl = DEPT_LABELS_SHORT.get(svc, svc)
                q1, q3, median = svc_hl["length_of_stay"].quantile(0.25), svc_hl["length_of_stay"].quantile(0.75), \
                svc_hl["length_of_stay"].median()
                fig.add_trace(go.Scatter(
                    x=[lbl], y=[median], mode="markers",
                    marker=dict(color=col, size=12, symbol="diamond", line=dict(color="#fff", width=2)),
                    error_y=dict(type="data", symmetric=False, array=[q3 - median], arrayminus=[median - q1], color=col,
                                 thickness=4, width=15),
                    hovertemplate=f"<b>{lbl}</b>{highlight_txt}<br>Median: {median:.1f}d<br>IQR: {q1:.1f}–{q3:.1f}d<br>n={len(svc_hl)}<extra></extra>",
                    showlegend=False,
                ))

    fig.add_hline(y=7, line_dash="dot", line_color="#009E73", line_width=1, opacity=0.4,
                  annotation_text="7d", annotation_position="right", annotation_font=dict(size=8, color="#009E73"))
    fig.add_hline(y=14, line_dash="dash", line_color="#D55E00", line_width=1.5, opacity=0.5,
                  annotation_text="14d blocker", annotation_position="right",
                  annotation_font=dict(size=8, color="#D55E00"))

    avg_los = df_full["length_of_stay"].mean()
    blockers = (df_full["length_of_stay"] > 14).sum()

    fig.update_layout(
        title=dict(
            text=f"<b>Length of Stay</b><br><span style='font-size:{SUBTITLE_FONT_SIZE}px;color:#7f8c8d'>Avg: {avg_los:.1f}d • Blockers: {blockers}{highlight_txt}</span>",
            font=dict(size=TITLE_FONT_SIZE, color="#2c3e50"), x=0.5, xanchor="center", y=0.94),
        template="plotly_white", margin=dict(l=45, r=10, t=55, b=35),
        yaxis=dict(title=dict(text="Length of Stay (days)", font=AXIS_LABEL_FONT), gridcolor=GRID_COLOR,
                   range=[0, min(df_full["length_of_stay"].max() + 3, 35)], tickfont=AXIS_TICK_FONT),
        xaxis=dict(title="", tickfont=AXIS_TICK_FONT),
        showlegend=False, hovermode="closest",
    )
    return fig


@callback(
    [Output("legend-items", "children"), Output("week-header", "children"), Output("week-metrics", "children"),
     Output("reallocation-section", "style"), Output("reallocation-text", "children")],
    [Input("dept-filter", "value"), Input("t2t3-selected-week", "data"), Input("t2t3-zoom-store", "data"),
     Input("week-slider", "value"), Input("hide-anomalies-toggle", "value")]
)
def update_context_panel(depts, selected_week, zoom_store, week_range, hide_anom):
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