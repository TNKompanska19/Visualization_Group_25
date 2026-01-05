"""
Quantity Callbacks - MERGED (Your T3 kept, T2 merged, bed distribution kept)
JBI100 Visualization - Group 25

FIXES:
- Removes Output("quantity-context", ...) because your layout doesn't have it.

KEEP:
- Task 3 exactly as your original (occupancy + LOS + Gantt + stores + toggle)
- Bed distribution modal/chart exactly as your original (horizontal bar, ALL depts)

MERGE (T2):
- grouped vs separate (t2-weekly-layout)
- refused count vs refusal rate (t2-refusal-metric)
- click week -> store selection (quantity-selected-week) + highlight + clear button
- anomalies: hide or shade
- event icons only at detail zoom (<=8 weeks) via show-events-toggle (if EVENT_ICONS exists)
- robust scaling for refused count (visual cap at 95th percentile) (colleague feature)
"""

from dash import callback, Output, Input, State, ctx
from dash.exceptions import PreventUpdate

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import math

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS

# EVENT_ICONS exists in your colleague code; safe import fallback:
try:
    from jbi100_app.config import EVENT_ICONS
except Exception:
    EVENT_ICONS = {}

from jbi100_app.data import get_services_data, get_patients_data

_services = get_services_data()
_patients = get_patients_data()


# ==================================================================
# HELPERS
# ==================================================================

def _filter_services(selected_depts, week_range):
    w0, w1 = int(week_range[0]), int(week_range[1])
    df = _services[(_services["week"] >= w0) & (_services["week"] <= w1)].copy()
    if selected_depts:
        df = df[df["service"].isin(selected_depts)]
    return df


def _filter_patients(selected_depts, week_range):
    w0, w1 = int(week_range[0]), int(week_range[1])
    df = _patients.copy()
    if selected_depts:
        df = df[df["service"].isin(selected_depts)]
    if "arrival_week" in df.columns:
        df = df[(df["arrival_week"] >= w0) & (df["arrival_week"] <= w1)]
    return df


def _empty_fig(title="No data"):
    fig = go.Figure()
    fig.add_annotation(
        text=title, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=13, color="#999")
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def _anomaly_weeks():
    return list(range(3, 53, 3))


def _zoom_level(week_range):
    wmin, wmax = int(week_range[0]), int(week_range[1])
    span = (wmax - wmin) + 1
    if span <= 8:
        return "detail"
    if span <= 13:
        return "quarter"
    return "overview"


# ==================================================================
# T2: SELECTED WEEK STORE (merged in)
# ==================================================================

@callback(
    Output("quantity-selected-week", "data"),
    [Input("t2-spc-chart", "clickData"), Input("t2-clear-selection-btn", "n_clicks")],
    State("quantity-selected-week", "data"),
    prevent_initial_call=True,
)
def store_selected_week(clickData, clear_clicks, current):
    if ctx.triggered_id == "t2-clear-selection-btn":
        return None

    if clickData and "points" in clickData and len(clickData["points"]) > 0:
        x = clickData["points"][0].get("x", None)
        if x is None:
            return current
        try:
            return int(round(float(x)))
        except Exception:
            return current

    return current


# ==================================================================
# T2 MODAL: BED DISTRIBUTION (KEEP YOUR ORIGINAL)
# ==================================================================

@callback(
    Output("distribution-modal", "style"),
    [
        Input("show-distribution-btn", "n_clicks"),
        Input("close-distribution-btn", "n_clicks"),
    ],
    prevent_initial_call=True,
)
def toggle_distribution_modal(show_clicks, close_clicks):
    from dash import callback_context

    if not callback_context.triggered:
        return {"display": "none"}

    button_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    if button_id == "show-distribution-btn":
        return {"display": "flex"}
    return {"display": "none"}


@callback(
    Output("distribution-chart", "figure"),
    [
        Input("week-slider", "value"),
        Input("show-distribution-btn", "n_clicks"),
    ],
)
def update_distribution_chart(week_range, n_clicks):
    """
    KEEP: shows ALL departments regardless of dept-filter, horizontal bar chart.
    """
    df = _filter_services(None, week_range)  # None => all departments
    if df.empty:
        return _empty_fig("No data")

    agg = (
        df.groupby("service")
        .agg({"available_beds": "mean"})
        .reset_index()
        .sort_values("available_beds", ascending=True)
    )

    fig = go.Figure()

    colors = {
        "emergency": "#0173B2",
        "surgery": "#029E73",
        "general_medicine": "#DE8F05",
        "ICU": "#CC78BC",
    }

    for _, row in agg.iterrows():
        service = row["service"]
        label = DEPT_LABELS.get(service, service)
        color = colors.get(service, "#3498db")
        beds = math.floor(row["available_beds"])

        fig.add_trace(go.Bar(
            x=[beds],
            y=[label],
            orientation="h",
            marker=dict(color=color, opacity=0.85),
            text=[f"{beds}"],
            textposition="inside",
            textfont=dict(color="white", size=13, family="Arial Bold"),
            hovertemplate=f"<b style='font-size:14px'>{label}</b><br><b>Avg Beds:</b> {beds}<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(
            text=(
                f"<b>Bed Distribution by Department</b><br>"
                f"<sub style='font-size:11px'>Week(s) {week_range[0]}-{week_range[1]} | Average beds allocated</sub>"
            ),
            font=dict(size=14)
        ),
        xaxis=dict(title="<b>Average Beds per Week</b>", gridcolor="#f0f0f0"),
        yaxis=dict(title=""),
        template="plotly_white",
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Arial"),
        margin=dict(l=120, r=40, t=70, b=60),
    )

    return fig


# ==================================================================
# TAB VISIBILITY (KEEP YOUR ORIGINAL)
# ==================================================================

@callback(
    [Output("quantity-t2-content", "style"), Output("quantity-t3-content", "style")],
    Input("quantity-tabs", "value"),
)
def toggle_tab_visibility(active_tab):
    if active_tab == "tab-t2":
        return {"display": "flex", "flexDirection": "column", "gap": "8px", "height": "100%"}, {"display": "none"}
    else:
        return {"display": "none"}, {"display": "flex", "flexDirection": "column", "gap": "6px", "height": "100%"}


# ==================================================================
# T2 CHART 1: WEEKLY (MERGED)
# ==================================================================

@callback(
    Output("t2-spc-chart", "figure"),
    [
        Input("dept-filter", "value"),
        Input("week-slider", "value"),
        Input("quantity-tabs", "value"),
        Input("hide-anomalies-toggle", "value"),
        Input("show-events-toggle", "value"),
        Input("t2-weekly-layout", "value"),      # grouped / separate
        Input("t2-refusal-metric", "value"),     # count / rate
        Input("quantity-selected-week", "data"), # highlight
    ],
)
def update_t2_weekly(
    selected_depts,
    week_range,
    active_tab,
    hide_anomalies,
    show_events_list,
    weekly_layout,
    refusal_metric,
    selected_week,
):
    if active_tab != "tab-t2":
        raise PreventUpdate

    df = _filter_services(selected_depts, week_range)
    if df.empty:
        return _empty_fig("No data")

    week_min, week_max = int(week_range[0]), int(week_range[1])
    zoom = _zoom_level(week_range)

    # Hide anomalies
    hide_anom = ("hide" in (hide_anomalies or []))
    anom = _anomaly_weeks()
    if hide_anom:
        df = df[~df["week"].isin(anom)].copy()
        if df.empty:
            return _empty_fig("No non-anomaly weeks in selected range")

    # Refusal metric
    refusal_metric = (refusal_metric or "count").lower()
    if refusal_metric == "rate":
        if "refusal_rate" in df.columns:
            df["refusal_value"] = df["refusal_rate"].astype(float)
        else:
            df["refusal_value"] = (
                (df["patients_refused"] / df["patients_request"]) * 100.0
            ).replace([np.inf, -np.inf], np.nan).fillna(0.0)

        refusal_label = "Refusal rate (%)"
        hover_refusal = "Refusal rate: %{y:.1f}%"
    else:
        df["refusal_value"] = df["patients_refused"]
        refusal_label = "Patients refused"
        hover_refusal = "Refused: %{y}"

    # Robust scaling for count (colleague feature)
    robust_used = False
    q95 = None
    if refusal_metric == "count" and len(df) > 0:
        q95 = float(df["refusal_value"].quantile(0.95))
        if q95 > 0:
            df["refusal_value_robust"] = df["refusal_value"].clip(upper=q95)
            robust_used = (df["refusal_value"].max() > q95 * 1.25)
        else:
            df["refusal_value_robust"] = df["refusal_value"]
    else:
        df["refusal_value_robust"] = df["refusal_value"]

    # Layout mode
    weekly_layout = (weekly_layout or "grouped").lower()
    separate = (weekly_layout == "separate")

    # Figure skeleton
    if separate:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10)
    else:
        fig = go.Figure()

    df = df.sort_values("week")

    # Your original colors/meaning
    bed_color = "#0173B2"
    refused_color = "#DE8F05"

    # Add traces per department like your original
    for service in sorted(df["service"].unique()):
        svc = df[df["service"] == service].sort_values("week")
        label = DEPT_LABELS.get(service, service)

        beds_trace = go.Bar(
            x=svc["week"],
            y=svc["available_beds"],
            name=f"{label} - Beds",
            marker=dict(color=bed_color, opacity=0.7),
            legendgroup=label,
            hovertemplate=(
                f"<b style='font-size:14px'>{label}</b><br>"
                "<b>Week:</b> %{x}<br>"
                "<b>Beds:</b> %{y}<extra></extra>"
            ),
        )

        refused_trace = go.Bar(
            x=svc["week"],
            y=svc["refusal_value_robust"],
            name=f"{label} - {refusal_label}",
            marker=dict(color=refused_color, opacity=0.85),
            legendgroup=label,
            hovertemplate=(
                f"<b style='font-size:14px'>{label}</b><br>"
                "<b>Week:</b> %{x}<br>"
                f"<b>{refusal_label}:</b> " + hover_refusal + "<extra></extra>"
            ),
        )

        if separate:
            fig.add_trace(beds_trace, row=1, col=1)
            fig.add_trace(refused_trace, row=2, col=1)
        else:
            fig.add_trace(beds_trace)
            fig.add_trace(refused_trace)

    # Title note for robust cap
    subtitle = ""
    if refusal_metric == "count" and robust_used:
        subtitle = "<br><span style='font-size:11px;color:#95a5a6'><i>Note: refusal spikes visually capped (95th percentile)</i></span>"

    fig.update_layout(
        title=dict(
            text=f"<b>Weekly Capacity and Refusals</b>{subtitle}",
            font=dict(size=13),
            x=0.02,
            xanchor="left",
        ),
        template="plotly_white",
        clickmode="event+select",
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Arial"),
        margin=dict(l=55, r=15, t=70, b=50),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="right",
            x=0.98,
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#ddd",
            borderwidth=1,
        ),
        barmode="group" if not separate else None,
    )

    # Adaptive dtick (colleague feature)
    span = (week_max - week_min) + 1
    dtick = 1
    if span > 20:
        dtick = 2
    if span > 40:
        dtick = 4

    if separate:
        fig.update_yaxes(title_text="<b>Beds</b>", gridcolor="#f0f0f0", row=1, col=1)
        fig.update_yaxes(title_text=f"<b>{refusal_label}</b>", gridcolor="#f0f0f0", row=2, col=1)
        fig.update_xaxes(title_text="<b>Week</b>", gridcolor="#f0f0f0", dtick=dtick, row=2, col=1)
    else:
        fig.update_xaxes(title_text="<b>Week</b>", gridcolor="#f0f0f0", dtick=dtick)
        fig.update_yaxes(title_text="<b>Patients / Beds</b>", gridcolor="#f0f0f0")

    # Cap line label (only meaningful in separate + count + robust)
    if separate and refusal_metric == "count" and robust_used and q95 is not None and q95 > 0:
        fig.add_hline(
            y=q95,
            line_width=1,
            line_dash="dash",
            line_color="rgba(149,165,166,0.95)",
            row=2, col=1,
        )
        fig.add_annotation(
            x=0.99,
            y=q95,
            xref="paper",
            yref="y2",
            text=f"Cap @95% ≈ {int(round(q95))}",
            showarrow=False,
            xanchor="right",
            yanchor="bottom",
            yshift=8,
            font=dict(size=9, color="rgba(120,130,140,0.95)"),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="rgba(0,0,0,0)",
            borderpad=2,
        )

    # Shade anomaly weeks when not hidden (colleague feature)
    if not hide_anom:
        for w in anom:
            if week_min <= w <= week_max:
                fig.add_vrect(
                    x0=w - 0.5, x1=w + 0.5,
                    fillcolor="rgba(0,0,0,0.04)",
                    line_width=0,
                    layer="below",
                )

    # Highlight selected week (connect)
    if selected_week is not None:
        try:
            w = int(selected_week)
            if week_min <= w <= week_max:
                fig.add_vrect(
                    x0=w - 0.5, x1=w + 0.5,
                    fillcolor="rgba(52,152,219,0.18)",
                    line_width=0,
                    layer="above",
                )
        except Exception:
            pass

    # Event icons only on detail zoom (<=8 weeks)
    show_events = ("show" in (show_events_list or []))
    if show_events and zoom == "detail" and "event" in df.columns and EVENT_ICONS:
        ev = df.groupby("week")["event"].agg(
            lambda x: x[x != "none"].iloc[0] if (x != "none").any() else "none"
        )
        for w, e in ev.items():
            if e != "none":
                fig.add_annotation(
                    x=w,
                    y=1.10,
                    xref="x",
                    yref="paper",
                    text=EVENT_ICONS.get(e, "⚡"),
                    showarrow=False,
                    font=dict(size=12, color="#7f8c8d")
                )

    return fig


# ==================================================================
# T2 DETAIL CHART (MERGED BEHAVIOR)
# - If multiple depts: your scatter comparison
# - If single dept: colleague summary bars (Beds/Demand/Refused or Rate)
# ==================================================================

@callback(
    Output("t2-detail-chart", "figure"),
    [
        Input("dept-filter", "value"),
        Input("week-slider", "value"),
        Input("t2-refusal-metric", "value"),
        Input("quantity-tabs", "value"),
        Input("quantity-selected-week", "data"),
    ],
)
def update_t2_detail(selected_depts, week_range, refusal_metric, active_tab, selected_week):
    if active_tab != "tab-t2":
        raise PreventUpdate

    df = _filter_services(selected_depts, week_range)
    if df.empty:
        return _empty_fig("No data")

    week_span = int(week_range[1]) - int(week_range[0]) + 1
    refusal_metric = (refusal_metric or "count").lower()

    # Aggregate by department
    agg = df.groupby("service").agg({
        "available_beds": "mean",
        "patients_request": "sum",
        "patients_refused": "sum",
    }).reset_index()

    agg["refusal_rate"] = (
        (agg["patients_refused"] / agg["patients_request"]) * 100
    ).replace([np.inf, -np.inf], np.nan).fillna(0)

    # ===========================
    # MULTI-DEPT => SCATTER + QUADRANTS (RESTORED)
    # ===========================
    if len(agg) >= 2:
        fig = go.Figure()

        for _, row in agg.iterrows():
            service = row["service"]
            color = DEPT_COLORS.get(service, "#3498db")
            label = DEPT_LABELS.get(service, service)

            fig.add_trace(go.Scatter(
                x=[row["available_beds"]],
                y=[row["refusal_rate"]],
                mode="markers+text",
                name=label,
                marker=dict(
                    size=max(10, row["patients_request"] / 50),  # keep readable
                    color=color,
                    opacity=0.7,
                    line=dict(width=2, color="white"),
                ),
                text=[label],
                textposition="top center",
                textfont=dict(size=10),
                customdata=[[row["patients_refused"], row["patients_request"]]],
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "Beds: %{x:.0f}<br>"
                    "Refusal Rate: %{y:.1f}%<br>"
                    "Refused: %{customdata[0]}<br>"
                    "Demand: %{customdata[1]}<br>"
                    "<extra></extra>"
                ),
                showlegend=False,
            ))

        # Trendline (only if > 2 depts, same as your original)
        if len(agg) > 2:
            try:
                slope, intercept, r_value, _, _ = stats.linregress(
                    agg["available_beds"], agg["refusal_rate"]
                )
                x_trend = np.array([agg["available_beds"].min(), agg["available_beds"].max()])
                y_trend = slope * x_trend + intercept

                fig.add_trace(go.Scatter(
                    x=x_trend,
                    y=y_trend,
                    mode="lines",
                    name="Expected",
                    line=dict(color="red", width=2, dash="dash"),
                    hovertemplate=f"Expected<br>R²={r_value ** 2:.2f}<extra></extra>",
                ))
            except:
                pass

        # ---------- RESTORED: quadrant lines + labels ----------
        avg_beds = agg["available_beds"].mean()
        avg_refusal = agg["refusal_rate"].mean()

        fig.add_vline(x=avg_beds, line_dash="dot", line_color="gray", opacity=0.3)
        fig.add_hline(y=avg_refusal, line_dash="dot", line_color="gray", opacity=0.3)

        max_x, min_x = agg["available_beds"].max(), agg["available_beds"].min()
        max_y, min_y = agg["refusal_rate"].max(), agg["refusal_rate"].min()

        # Add some padding so labels don't sit exactly on edge
        pad_x = (max_x - min_x) if (max_x - min_x) != 0 else 1
        pad_y = (max_y - min_y) if (max_y - min_y) != 0 else 1
        plot_max_y = max_y + 0.15 * pad_y
        plot_min_y = max(0, min_y - 0.10 * pad_y)

        fig.update_yaxes(range=[plot_min_y, plot_max_y])

        fig.add_annotation(
            x=min_x + (avg_beds - min_x) * 0.3,
            y=plot_max_y - 0.05 * pad_y,
            text="<b>UNDER-CAPACITY</b><br>Low beds + High refusals<br>→ Need more beds",
            showarrow=False,
            font=dict(size=9, color="red"),
            bgcolor="rgba(255,0,0,0.08)",
            bordercolor="red",
            borderwidth=1,
            borderpad=4,
        )
        fig.add_annotation(
            x=avg_beds + (max_x - avg_beds) * 0.7,
            y=plot_max_y - 0.05 * pad_y,
            text="<b>INEFFICIENT</b><br>High beds + High refusals<br>→ Process problem",
            showarrow=False,
            font=dict(size=9, color="orange"),
            bgcolor="rgba(255,165,0,0.08)",
            bordercolor="orange",
            borderwidth=1,
            borderpad=4,
        )
        fig.add_annotation(
            x=min_x + (avg_beds - min_x) * 0.3,
            y=plot_min_y + 0.25 * pad_y,
            text="<b>EFFICIENT</b><br>Low beds + Low refusals<br>→ Well-matched",
            showarrow=False,
            font=dict(size=9, color="green"),
            bgcolor="rgba(0,128,0,0.08)",
            bordercolor="green",
            borderwidth=1,
            borderpad=4,
        )
        fig.add_annotation(
            x=avg_beds + (max_x - avg_beds) * 0.7,
            y=plot_min_y + 0.25 * pad_y,
            text="<b>OVER-CAPACITY</b><br>High beds + Low refusals<br>→ Reallocation source",
            showarrow=False,
            font=dict(size=9, color="blue"),
            bgcolor="rgba(0,0,255,0.08)",
            bordercolor="blue",
            borderwidth=1,
            borderpad=4,
        )
        # ------------------------------------------------------

        fig.update_layout(
            title=dict(
                text="<b>Refusal Rate vs Capacity</b><br><sub style='font-size:11px'>Size=Demand | Quadrants show reallocation strategy</sub>",
                font=dict(size=13)
            ),
            xaxis=dict(title="<b>Allocated Beds</b>", gridcolor="#f0f0f0"),
            yaxis=dict(title="<b>Refusal Rate (%)</b>", gridcolor="#f0f0f0"),
            template="plotly_white",
            hovermode="closest",
            margin=dict(l=55, r=55, t=50, b=50),
        )
        return fig

    # ===========================
    # SINGLE-DEPT => your merged bar summary (unchanged)
    # ===========================
    beds_avg = float(df.groupby("week")["available_beds"].sum().mean()) if len(df) else 0.0
    demand_avg = float(df.groupby("week")["patients_request"].sum().mean()) if len(df) else 0.0

    if refusal_metric == "rate":
        refused_show = float(df["refusal_rate"].mean()) if "refusal_rate" in df.columns and len(df) else 0.0
        refused_name = "Refusal rate (avg %)"
        refused_disp = round(refused_show, 1)
    else:
        refused_show = float(df.groupby("week")["patients_refused"].sum().mean()) if len(df) else 0.0
        refused_name = "Patients refused (avg/week)"
        refused_disp = int(round(refused_show))

    beds_disp = int(round(beds_avg))
    demand_disp = int(round(demand_avg))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Beds (avg/week)"], y=[beds_avg],
        text=[f"{beds_disp}"], textposition="outside",
        marker=dict(color="#3498db"),
        hovertemplate="Beds (avg/week): %{y:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=["Demand (avg/week)"], y=[demand_avg],
        text=[f"{demand_disp}"], textposition="outside",
        marker=dict(color="#1abc9c"),
        hovertemplate="Demand (avg/week): %{y:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=[refused_name], y=[refused_show],
        text=[f"{refused_disp}"], textposition="outside",
        marker=dict(color="#e67e22"),
        hovertemplate=refused_name + ": %{y:.1f}<extra></extra>" if refusal_metric == "rate" else refused_name + ": %{y}<extra></extra>",
    ))

    # Title context
    dept = df["service"].iloc[0] if len(df) else "Department"
    dept_label = DEPT_LABELS.get(dept, dept)
    if selected_week is not None:
        try:
            context = f"(Selected: Week {int(selected_week)})"
        except Exception:
            context = f"(Weeks {week_range[0]}–{week_range[1]})"
    else:
        context = f"(Weeks {week_range[0]}–{week_range[1]})"

    max_y = max([beds_avg, demand_avg, refused_show, 1.0])
    fig.update_yaxes(range=[0, max_y * 1.18], rangemode="tozero", automargin=True)

    fig.update_layout(
        title=dict(text=f"{dept_label} Summary {context}", x=0.02, xanchor="left", font=dict(size=18)),
        height=440,
        margin=dict(l=55, r=20, t=75, b=95),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        yaxis_title="Value",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    fig.update_xaxes(tickangle=20, automargin=True)
    return fig



# ==================================================================
# =======================  TASK 3 (UNCHANGED)  ======================
# ==================================================================

from dash import dcc

@callback(
    Output("t3-los-interaction-store", "data"),
    [Input("t3-violin-chart", "relayoutData")],
    prevent_initial_call=True
)
def capture_los_interactions(relayout_data):
    if not ctx.triggered:
        raise PreventUpdate

    if relayout_data is None:
        raise PreventUpdate

    if "xaxis.range[0]" in relayout_data and "xaxis.range[1]" in relayout_data:
        try:
            week_start = int(round(relayout_data["xaxis.range[0]"]))
            week_end = int(round(relayout_data["xaxis.range[1]"]))
            if week_start < week_end:
                return {"week_start": week_start, "week_end": week_end}
        except Exception:
            raise PreventUpdate

    raise PreventUpdate


@callback(
    Output("t3-gantt-interaction-store", "data"),
    [Input("t3-gantt-chart", "clickData"), Input("t3-gantt-chart", "relayoutData")],
    prevent_initial_call=True
)
def capture_gantt_interactions(click_data, relayout_data):
    if not ctx.triggered:
        raise PreventUpdate

    trigger = ctx.triggered[0]
    prop_id = trigger["prop_id"]

    if click_data is None and relayout_data is None:
        raise PreventUpdate

    if "clickData" in prop_id and click_data is not None:
        try:
            if "points" in click_data and len(click_data["points"]) > 0:
                point = click_data["points"][0]
                if "customdata" in point and point["customdata"] and len(point["customdata"]) >= 5:
                    arrival_week = point["customdata"][3]
                    length_of_stay = point["customdata"][4]
                    if arrival_week is not None and length_of_stay is not None:
                        return {
                            "type": "patient_click",
                            "arrival_week": int(arrival_week),
                            "length_of_stay": int(length_of_stay),
                        }
        except Exception:
            raise PreventUpdate

    if "relayoutData" in prop_id and relayout_data is not None:
        try:
            if "xaxis.range[0]" in relayout_data and "xaxis.range[1]" in relayout_data:
                date_start = pd.to_datetime(relayout_data["xaxis.range[0]"])
                date_end = pd.to_datetime(relayout_data["xaxis.range[1]"])
                data_start_date = pd.Timestamp(date_start.year, 1, 1)
                week_1 = (date_start - data_start_date).days // 7
                week_2 = (date_end - data_start_date).days // 7
                week_start = max(0, min(week_1, week_2))
                week_end = min(52, max(week_1, week_2))
                if week_start <= week_end and week_end > 0:
                    return {"type": "gantt_zoom", "week_start": int(week_start), "week_end": int(week_end)}
        except Exception:
            raise PreventUpdate

    raise PreventUpdate


@callback(
    Output("t3-line-chart", "figure"),
    [
        Input("dept-filter", "value"),
        Input("week-slider", "value"),
        Input("quantity-tabs", "value"),
        Input("t3-gantt-interaction-store", "data"),
        Input("t3-los-interaction-store", "data"),
    ],
)
def update_t3_line(selected_depts, week_range, active_tab, gantt_interaction, los_interaction):
    # --- YOUR ORIGINAL T3 LINE (unchanged) ---
    if active_tab != "tab-t3":
        raise PreventUpdate

    df = _filter_services(selected_depts, week_range)
    if df.empty:
        return _empty_fig("No data")

    df["occupancy_rate"] = (df["patients_admitted"] / df["available_beds"] * 100).fillna(0)

    zoomed_period = None
    zoom_range = None

    if gantt_interaction:
        interaction_type = gantt_interaction.get("type")

        if interaction_type == "patient_click":
            try:
                arrival_week = gantt_interaction.get("arrival_week")
                length_of_stay = gantt_interaction.get("length_of_stay")
                if arrival_week is not None and length_of_stay is not None:
                    departure_week = arrival_week + (length_of_stay // 7) + 1
                    week_start = max(0, arrival_week - 1)
                    week_end = min(52, departure_week + 1)
                    df = df[(df["week"] >= week_start) & (df["week"] <= week_end)]
                    zoomed_period = f"Week {week_start}-{week_end} (Patient)"
                    zoom_range = [week_start, week_end]
            except Exception:
                pass

        elif interaction_type == "gantt_zoom":
            try:
                week_start = gantt_interaction.get("week_start")
                week_end = gantt_interaction.get("week_end")
                if week_start is not None and week_end is not None:
                    df = df[(df["week"] >= week_start) & (df["week"] <= week_end)]
                    zoomed_period = f"Week {week_start}-{week_end}"
                    zoom_range = [week_start, week_end]
            except Exception:
                pass

    if not zoom_range and los_interaction:
        try:
            week_start = los_interaction.get("week_start")
            week_end = los_interaction.get("week_end")
            if week_start is not None and week_end is not None:
                df = df[(df["week"] >= week_start) & (df["week"] <= week_end)]
                zoomed_period = f"Week {week_start}-{week_end}"
                zoom_range = [week_start, week_end]
        except Exception:
            pass

    if df.empty:
        return _empty_fig("No data in selected period")

    fig = go.Figure()

    colors = {
        "emergency": "#0173B2",
        "surgery": "#029E73",
        "general_medicine": "#DE8F05",
        "ICU": "#CC78BC",
    }

    services = sorted(df["service"].unique())
    week_min, week_max = df["week"].min(), df["week"].max()
    y_max = df["occupancy_rate"].max()
    y_min = df["occupancy_rate"].min()

    if y_min > 80 and y_max < 105:
        y_range_min = 75
        y_range_max = 110
    elif y_min > 70:
        y_range_min = 70
        y_range_max = max(110, y_max + 5)
    else:
        y_range_min = 0
        y_range_max = max(120, y_max + 10)

    if y_range_max > 100:
        fig.add_shape(
            type="rect",
            x0=week_min - 0.5, x1=week_max + 0.5,
            y0=100, y1=y_range_max,
            fillcolor="rgba(231, 76, 60, 0.12)",
            line_width=0,
            layer="below"
        )

    if y_range_min < 100:
        fig.add_shape(
            type="rect",
            x0=week_min - 0.5, x1=week_max + 0.5,
            y0=max(85, y_range_min), y1=100,
            fillcolor="rgba(46, 204, 113, 0.12)",
            line_width=0,
            layer="below"
        )

    if y_range_min < 85:
        fig.add_shape(
            type="rect",
            x0=week_min - 0.5, x1=week_max + 0.5,
            y0=y_range_min, y1=min(85, y_range_max),
            fillcolor="rgba(52, 152, 219, 0.08)",
            line_width=0,
            layer="below"
        )

    for service in services:
        svc_data = df[df["service"] == service].sort_values("week")
        color = colors.get(service, "#3498db")
        label = DEPT_LABELS.get(service, service)
        avg_occ = svc_data["occupancy_rate"].mean()

        fig.add_trace(go.Scatter(
            x=svc_data["week"],
            y=svc_data["occupancy_rate"],
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=3, shape="spline"),
            marker=dict(size=5, color=color, line=dict(width=1, color="white")),
            customdata=svc_data[["patients_admitted", "available_beds"]].values,
            hovertemplate=(
                f"<b style='font-size:14px'>{label}</b><br>"
                "<b>Week:</b> %{x}<br>"
                "<b>Occupancy:</b> %{y:.1f}%<br>"
                "<b>Admitted:</b> %{customdata[0]:.0f}<br>"
                "<b>Beds:</b> %{customdata[1]:.0f}<br>"
                f"<b>Avg:</b> {avg_occ:.1f}%<br>"
                "<extra></extra>"
            ),
        ))

        peaks = svc_data[svc_data["occupancy_rate"] > 100]
        if not peaks.empty:
            fig.add_trace(go.Scatter(
                x=peaks["week"],
                y=peaks["occupancy_rate"],
                mode="markers",
                name=f"{label} Over",
                marker=dict(size=10, color=color, symbol="triangle-up", line=dict(width=2, color="#e74c3c")),
                showlegend=False,
                hoverinfo="skip"
            ))

    fig.add_hline(y=100, line_dash="dash", line_color="#e74c3c", line_width=2.5, opacity=0.8)
    fig.add_hline(y=85, line_dash="dot", line_color="#2ecc71", line_width=2, opacity=0.7)

    fig.add_annotation(
        x=week_max, y=100, text="<b>100%</b>", showarrow=False,
        font=dict(size=11, color="#e74c3c", family="Arial Bold"),
        bgcolor="rgba(255,255,255,0.95)", bordercolor="#e74c3c", borderwidth=1.5, borderpad=4,
        xanchor="left", xshift=5
    )
    fig.add_annotation(
        x=week_max, y=85, text="<b>85%</b>", showarrow=False,
        font=dict(size=10, color="#2ecc71", family="Arial Bold"),
        bgcolor="rgba(255,255,255,0.95)", bordercolor="#2ecc71", borderwidth=1.5, borderpad=4,
        xanchor="left", xshift=5
    )

    period_suffix = f" ({zoomed_period})" if zoomed_period else ""

    fig.update_layout(
        title=dict(
            text=f"<b>Bed Occupancy Rate Over Time{period_suffix}</b><br><sub style='font-size:11px'>Drag to zoom | Zones: Green (85-100% optimal), Red (>100% overcapacity)</sub>",
            font=dict(size=13),
            x=0.5, xanchor="center",
            y=0.98, yanchor="top"
        ),
        xaxis=dict(
            title="<b>Week</b>",
            gridcolor="#f0f0f0",
            rangeslider=dict(visible=True, thickness=0.08),
            range=[zoom_range[0] - 0.5, zoom_range[1] + 0.5] if zoom_range else [week_min - 0.5, week_max + 0.5]
        ),
        yaxis=dict(title="<b>Occupancy Rate (%)</b>", gridcolor="#f0f0f0", range=[y_range_min, y_range_max]),
        template="plotly_white",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(255, 255, 255, 0.95)",
            font_size=12,
            font_family="Arial",
            font_color="#333",
            bordercolor="#333"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#ddd",
            borderwidth=1
        ),
        margin=dict(l=60, r=30, t=80, b=100),
    )

    return fig


@callback(
    Output("t3-violin-chart", "figure"),
    [
        Input("dept-filter", "value"),
        Input("week-slider", "value"),
        Input("quantity-tabs", "value"),
        Input("t3-line-chart", "relayoutData"),
    ],
)
def update_t3_violin(selected_depts, week_range, active_tab, line_relayout):
    # --- YOUR ORIGINAL T3 VIOLIN (unchanged behavior) ---
    if active_tab != "tab-t3":
        raise PreventUpdate

    df = _filter_patients(selected_depts, week_range)
    if df.empty or "length_of_stay" not in df.columns or "arrival_week" not in df.columns:
        return _empty_fig("No patient data")

    zoomed_period = None
    zoom_range = None
    if line_relayout:
        if "xaxis.range[0]" in line_relayout:
            try:
                week_start = int(round(line_relayout["xaxis.range[0]"]))
                week_end = int(round(line_relayout["xaxis.range[1]"]))
                df = df[(df["arrival_week"] >= week_start) & (df["arrival_week"] <= week_end)]
                zoomed_period = f"Week {week_start}-{week_end}"
                zoom_range = [week_start, week_end]
            except:
                pass
        elif "xaxis.range" in line_relayout:
            try:
                x_range = line_relayout["xaxis.range"]
                week_start = int(round(x_range[0]))
                week_end = int(round(x_range[1]))
                df = df[(df["arrival_week"] >= week_start) & (df["arrival_week"] <= week_end)]
                zoomed_period = f"Week {week_start}-{week_end}"
                zoom_range = [week_start, week_end]
            except:
                pass

    if df.empty:
        return _empty_fig("No patients in selected period")

    weekly_los = df.groupby(["arrival_week", "service"]).agg({
        "length_of_stay": ["mean", "count", "max"]
    }).reset_index()
    weekly_los.columns = ["week", "service", "avg_los", "patient_count", "max_los"]

    fig = go.Figure()

    colors = {
        "emergency": "#0173B2",
        "surgery": "#029E73",
        "general_medicine": "#DE8F05",
        "ICU": "#CC78BC",
    }

    services = sorted(weekly_los["service"].unique())
    week_min = weekly_los["week"].min()
    week_max = weekly_los["week"].max()
    max_los = weekly_los["avg_los"].max()

    fig.add_shape(type="rect", x0=week_min - 0.5, x1=week_max + 0.5, y0=0, y1=7,
                  fillcolor="rgba(46, 204, 113, 0.08)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=week_min - 0.5, x1=week_max + 0.5, y0=7, y1=14,
                  fillcolor="rgba(241, 196, 15, 0.08)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=week_min - 0.5, x1=week_max + 0.5, y0=14, y1=max(max_los + 2, 20),
                  fillcolor="rgba(231, 76, 60, 0.12)", line_width=0, layer="below")

    fig.add_hline(y=7, line_dash="dot", line_color="#27ae60", line_width=1.5, opacity=0.6)
    fig.add_hline(y=14, line_dash="dash", line_color="#e74c3c", line_width=2.5, opacity=0.8)

    for service in services:
        svc_data = weekly_los[weekly_los["service"] == service].sort_values("week")
        color = colors.get(service, "#3498db")
        label = DEPT_LABELS.get(service, service)
        overall_avg = svc_data["avg_los"].mean()

        fig.add_trace(go.Scatter(
            x=svc_data["week"],
            y=svc_data["avg_los"],
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=2.5, dash="dot"),
            marker=dict(size=6, color=color, symbol="diamond", line=dict(width=1, color="white")),
            customdata=svc_data[["patient_count", "max_los"]].values,
            hovertemplate=(
                f"<b style='font-size:14px; color:#000'>{label}</b><br>"
                "<b style='color:#000'>Week:</b> <span style='color:#000'>%{x}</span><br>"
                "<b style='color:#000'>Avg LOS:</b> <span style='color:#000; font-weight:bold'>%{y:.1f} days</span><br>"
                "<b style='color:#000'>Patients:</b> <span style='color:#000'>%{customdata[0]}</span><br>"
                "<b style='color:#000'>Longest Stay:</b> <span style='color:#000'>%{customdata[1]:.0f} days</span><br>"
                f"<span style='color:#666; font-size:10px'>Overall Avg: {overall_avg:.1f} days</span>"
                "<extra></extra>"
            ),
        ))

    period_text = f" ({zoomed_period})" if zoomed_period else ""
    high_los_weeks = len(weekly_los[weekly_los["avg_los"] > 14])

    fig.update_layout(
        title=dict(
            text=f"<b>Average Length of Stay Over Time{period_text}</b><br><sub style='font-size:11px'>High LOS weeks (>14d): {high_los_weeks}</sub>",
            font=dict(size=13),
            x=0.5, xanchor="center",
            y=0.98, yanchor="top"
        ),
        xaxis=dict(
            title="<b>Week</b>",
            gridcolor="#e8e8e8",
            range=[zoom_range[0] - 0.5, zoom_range[1] + 0.5] if zoom_range else [week_min - 0.5, week_max + 0.5]
        ),
        yaxis=dict(
            title="<b>Average Length of Stay (days)</b>",
            gridcolor="#e8e8e8",
            range=[0, max(max_los + 3, 20)]
        ),
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=60, r=40, t=70, b=80),
    )

    return fig


@callback(
    Output("t3-gantt-chart", "figure"),
    [
        Input("dept-filter", "value"),
        Input("week-slider", "value"),
        Input("quantity-tabs", "value"),
        Input("t3-line-chart", "relayoutData"),
    ],
    State("t3-switchable-container", "children"),
)
def update_t3_gantt(selected_depts, week_range, active_tab, line_relayout, current_children):
    # --- YOUR ORIGINAL T3 GANTT (unchanged) ---
    if active_tab != "tab-t3":
        raise PreventUpdate

    df = _filter_patients(selected_depts, week_range)
    if df.empty or "arrival_date" not in df.columns:
        return _empty_fig("No patient data")

    zoomed_period = None
    if line_relayout:
        if "xaxis.range[0]" in line_relayout:
            try:
                week_start = int(line_relayout["xaxis.range[0]"])
                week_end = int(line_relayout["xaxis.range[1]"])
                if "arrival_week" in df.columns:
                    df = df[(df["arrival_week"] >= week_start) & (df["arrival_week"] <= week_end)]
                    zoomed_period = f"Week {week_start}-{week_end}"
            except:
                pass
        elif "xaxis.range" in line_relayout:
            try:
                x_range = line_relayout["xaxis.range"]
                week_start = int(x_range[0])
                week_end = int(x_range[1])
                if "arrival_week" in df.columns:
                    df = df[(df["arrival_week"] >= week_start) & (df["arrival_week"] <= week_end)]
                    zoomed_period = f"Week {week_start}-{week_end}"
            except:
                pass

    if df.empty:
        return _empty_fig("No patients in selected period")

    max_patients_per_dept = 50 // max(len(df["service"].unique()), 1)
    if max_patients_per_dept < 5:
        max_patients_per_dept = 5

    df_list = []
    for service in df["service"].unique():
        df_list.append(df[df["service"] == service].nlargest(max_patients_per_dept, "length_of_stay"))

    df_sorted = pd.concat(df_list).sort_values(["service", "length_of_stay"], ascending=[True, False]) if df_list else df.head(0)

    colors = {
        "emergency": "#0173B2",
        "surgery": "#029E73",
        "general_medicine": "#DE8F05",
        "ICU": "#CC78BC",
    }

    df_sorted["label"] = df_sorted["service"].map(DEPT_LABELS)
    df_sorted["is_blocker"] = df_sorted["length_of_stay"] > 14

    fig = go.Figure()

    y_pos = 0
    y_ticks = []
    y_labels = []
    dept_separators = []

    dept_stats = df.groupby("service").agg({"length_of_stay": ["mean", "max", "count"]}).reset_index()
    dept_stats.columns = ["service", "avg_los", "max_los", "count"]

    for service in sorted(df_sorted["service"].unique()):
        svc_data = df_sorted[df_sorted["service"] == service]
        color = colors.get(service, "#3498db")
        label = DEPT_LABELS.get(service, service)

        stats_row = dept_stats[dept_stats["service"] == service].iloc[0]
        avg_los = stats_row["avg_los"]
        max_los = stats_row["max_los"]
        showing = len(svc_data)
        total = stats_row["count"]

        y_ticks.append(y_pos)
        y_labels.append(f"<b>{label}</b><br><sub>({showing}/{total} pts)</sub>")
        y_pos += 1

        for idx, row in svc_data.iterrows():
            bar_color = "#e74c3c" if row["is_blocker"] else color
            bar_thickness = min(14, max(8, row["length_of_stay"] / 2.5))

            fig.add_trace(go.Scatter(
                x=[row["arrival_date"], row["departure_date"]],
                y=[y_pos, y_pos],
                mode="lines+markers",
                line=dict(color=bar_color, width=bar_thickness),
                marker=dict(size=0, color=bar_color),
                customdata=[
                    [row["is_blocker"], avg_los, max_los, row.get("arrival_week", 0), row.get("length_of_stay", 0)],
                    [row["is_blocker"], avg_los, max_los, row.get("arrival_week", 0), row.get("length_of_stay", 0)]
                ],
                hovertemplate=(
                    f"<b style='font-size:13px; color:#000'>Patient {row.get('patient_id', idx)}</b><br>"
                    f"<b style='color:#000'>Service:</b> <span style='color:#000'>{row['label']}</span><br>"
                    f"<b style='color:#000'>Arrival:</b> <span style='color:#000'>{row['arrival_date'].strftime('%Y-%m-%d')}</span><br>"
                    f"<b style='color:#000'>Departure:</b> <span style='color:#000'>{row['departure_date'].strftime('%Y-%m-%d')}</span><br>"
                    f"<b style='color:#000'>Length of Stay:</b> <span style='color:#000; font-weight:bold'>{row['length_of_stay']} days</span><br>"
                    + (f"<span style='color:#e74c3c; font-weight:bold'>⚠️ BED BLOCKER (>14 days)</span><br>" if row["is_blocker"] else "")
                    + f"<span style='color:#666; font-size:10px'>Dept Avg: {avg_los:.1f}d | Max: {max_los:.0f}d</span>"
                    "<extra></extra>"
                ),
                showlegend=False,
                opacity=0.9 if row["is_blocker"] else 0.75
            ))
            y_pos += 1

        dept_separators.append(y_pos - 0.5)
        y_pos += 0.5

    for sep_y in dept_separators[:-1]:
        fig.add_hline(y=sep_y, line_dash="dot", line_color="#cccccc", line_width=1, opacity=0.5)

    shown_patients = len(df_sorted)
    avg_los_all = df["length_of_stay"].mean()
    bed_blockers = (df["length_of_stay"] > 14).sum()
    total_in_period = len(df)

    title_suffix = ": All Departments"
    if selected_depts and len(selected_depts) == 1:
        title_suffix = f": {DEPT_LABELS.get(selected_depts[0], selected_depts[0])}"
    elif selected_depts:
        title_suffix = f": {len(selected_depts)} Departments"

    period_text = f" ({zoomed_period})" if zoomed_period else ""
    chart_height = min(500, max(350, y_pos * 10))

    fig.update_layout(
        title=dict(
            text=(
                f"<b>Patient Timeline{title_suffix}{period_text}</b><br>"
                f"<sub style='font-size:11px'>Top {shown_patients} of {total_in_period} patients | "
                f"Avg LOS: {avg_los_all:.1f} days | Bed Blockers (>14d): {bed_blockers}</sub>"
            ),
            font=dict(size=13)
        ),
        xaxis=dict(title="<b>Date</b>", gridcolor="#f0f0f0", showgrid=True),
        yaxis=dict(
            title="",
            showticklabels=True,
            tickmode="array",
            tickvals=y_ticks,
            ticktext=y_labels,
            tickfont=dict(size=10),
            showgrid=False
        ),
        template="plotly_white",
        height=chart_height,
        margin=dict(l=150, r=20, t=70, b=60),
    )

    return fig


@callback(
    Output("t3-switchable-container", "children"),
    Output("toggle-gantt-btn", "children"),
    Output("toggle-gantt-btn", "style"),
    Input("toggle-gantt-btn", "n_clicks"),
    prevent_initial_call=False,
)
def toggle_violin_gantt(n_clicks):
    if n_clicks is None:
        n_clicks = 0

    if n_clicks % 2 == 0:
        return (
            dcc.Graph(id="t3-violin-chart", config={"displayModeBar": True, "displaylogo": False}, style={"height": "100%"}),
            "📅 Patient Timeline",
            {
                "padding": "5px 12px",
                "backgroundColor": "#9b59b6",
                "color": "white",
                "border": "none",
                "borderRadius": "4px",
                "cursor": "pointer",
                "fontSize": "11px",
                "fontWeight": "500",
            }
        )
    else:
        return (
            dcc.Graph(id="t3-gantt-chart", config={"displayModeBar": True, "displaylogo": False}, style={"height": "100%"}),
            "📈 Average LOS Trends",
            {
                "padding": "5px 12px",
                "backgroundColor": "#e67e22",
                "color": "white",
                "border": "none",
                "borderRadius": "4px",
                "cursor": "pointer",
                "fontSize": "11px",
                "fontWeight": "500",
            }
        )


# ==================================================================
# REGISTRATION
# ==================================================================

def register_quantity_callbacks():
    pass
