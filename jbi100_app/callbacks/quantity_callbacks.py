"""
Quantity Callbacks - ACTUALLY USEFUL T2 CHARTS
JBI100 Visualization - Group 25

T2:
Chart 1: Week-by-week bars showing demand, beds, refusals
Chart 2: Department comparison scatter (only works with multiple depts)

T3: Heatmap + stacked area (working well)
"""

from dash import callback, Output, Input, State, no_update
from dash.exceptions import PreventUpdate
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats
import math

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS
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
        text=title, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        font=dict(size=13, color="#999")
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
    return fig


# ==================================================================
# T2 MODAL: BED DISTRIBUTION
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
    """
    Show/hide the bed distribution modal.
    """
    from dash import callback_context

    if not callback_context.triggered:
        return {"display": "none"}

    button_id = callback_context.triggered[0]["prop_id"].split(".")[0]

    if button_id == "show-distribution-btn":
        return {"display": "flex"}
    else:
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
    Q1: How are beds distributed across departments?
    Simple horizontal bar chart showing bed allocation by department.
    Always shows ALL departments regardless of filter.
    """
    df = _filter_services(None, week_range)
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

        fig.add_trace(
            go.Bar(
                x=[beds],
                y=[label],
                orientation="h",
                marker=dict(color=color, opacity=0.85),
                text=[f"{beds}"],
                textposition="inside",
                textfont=dict(color="white", size=13, family="Arial Bold"),
                hovertemplate=f"<b style='font-size:14px'>{label}</b><br><b>Avg Beds:</b> {beds}<extra></extra>",
                showlegend=False,
            )
        )

    fig.update_layout(
        title=dict(
            text=(
                f"<b>Bed Distribution by Department</b><br>"
                f"<sub style='font-size:11px'>Week(s) {week_range[0]}-{week_range[1]} | Average beds allocated</sub>"
            ),
            font=dict(size=14),
        ),
        xaxis=dict(title="<b>Average Beds per Week</b>", gridcolor="#f0f0f0"),
        yaxis=dict(title=""),
        template="plotly_white",
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Arial"),
        margin=dict(l=120, r=40, t=70, b=60),
    )

    return fig


# ==================================================================
# TAB VISIBILITY
# ==================================================================

@callback(
    [Output("quantity-t2-content", "style"), Output("quantity-t3-content", "style")],
    Input("quantity-tabs", "value"),
)
def toggle_tab_visibility(active_tab):
    if active_tab == "tab-t2":
        return (
            {"display": "flex", "flexDirection": "column", "gap": "8px", "height": "100%"},
            {"display": "none"},
        )
    else:
        return (
            {"display": "none"},
            {"display": "flex", "flexDirection": "column", "gap": "6px", "height": "100%"},
        )


# ==================================================================
# T2 CHART 1: WEEKLY DEMAND, BEDS, REFUSALS
# ==================================================================

@callback(
    Output("t2-spc-chart", "figure"),
    [
        Input("dept-filter", "value"),
        Input("week-slider", "value"),
        Input("quantity-tabs", "value"),
        Input("hide-anomalies-toggle", "value"),
    ],
)
def update_t2_weekly_bars(selected_depts, week_range, active_tab, hide_anomalies):
    if active_tab != "tab-t2":
        raise PreventUpdate

    df = _filter_services(selected_depts, week_range)
    if df.empty:
        return _empty_fig("No data")

    if hide_anomalies and "hide" in hide_anomalies:
        anomaly_weeks = [w for w in range(3, 53, 3)]
        df = df[~df["week"].isin(anomaly_weeks)]
        if df.empty:
            return _empty_fig("No non-anomaly weeks in selected range")

    df = df.sort_values("week")
    fig = go.Figure()

    for service in sorted(df["service"].unique()):
        svc_data = df[df["service"] == service]
        label = DEPT_LABELS.get(service, service)

        bed_color = "#0173B2"
        refused_color = "#DE8F05"

        fig.add_trace(
            go.Bar(
                x=svc_data["week"],
                y=svc_data["available_beds"],
                name=f"{label} - Beds",
                marker=dict(color=bed_color, opacity=0.7),
                hovertemplate=(
                    f"<b style='font-size:14px'>{label}</b><br>"
                    "<b>Week:</b> %{x}<br>"
                    "<b>Beds:</b> %{y}<br>"
                    "<extra></extra>"
                ),
                legendgroup=label,
            )
        )

        fig.add_trace(
            go.Bar(
                x=svc_data["week"],
                y=svc_data["patients_refused"],
                name=f"{label} - Refused",
                marker=dict(color=refused_color, opacity=0.85),
                customdata=svc_data[["patients_request"]].values,
                hovertemplate=(
                    f"<b style='font-size:14px'>{label}</b><br>"
                    "<b>Week:</b> %{x}<br>"
                    "<b>Refused:</b> %{y}<br>"
                    "<b>Demand:</b> %{customdata[0]}<br>"
                    "<extra></extra>"
                ),
                legendgroup=label,
            )
        )

    fig.update_layout(
        title=dict(
            text=(
                "<b>Weekly Capacity and Refusals</b><br>"
                "<sub style='font-size:11px'>Blue=Beds | Orange=Refused | Hover for details</sub>"
            ),
            font=dict(size=13),
        ),
        xaxis=dict(title="<b>Week</b>", gridcolor="#f0f0f0"),
        yaxis=dict(title="<b>Patients / Beds</b>", gridcolor="#f0f0f0"),
        template="plotly_white",
        barmode="group",
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Arial"),
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
        margin=dict(l=55, r=15, t=50, b=50),
    )

    return fig


# ==================================================================
# T2 CHART 2: DEPARTMENT COMPARISON
# ==================================================================

@callback(
    [Output("t2-detail-chart", "figure"), Output("quantity-context", "children")],
    [
        Input("dept-filter", "value"),
        Input("week-slider", "value"),
        Input("quantity-tabs", "value"),
    ],
)
def update_t2_comparison(selected_depts, week_range, active_tab):
    if active_tab != "tab-t2":
        raise PreventUpdate

    df = _filter_services(selected_depts, week_range)
    if df.empty:
        return _empty_fig("No data"), "No data"

    week_span = week_range[1] - week_range[0] + 1

    agg = (
        df.groupby("service")
        .agg(
            {
                "available_beds": "mean",
                "patients_request": "sum",
                "patients_refused": "sum",
            }
        )
        .reset_index()
    )

    agg["refusal_rate"] = (agg["patients_refused"] / agg["patients_request"] * 100).fillna(0)

    if week_span == 1:
        agg["display_refused"] = agg["patients_refused"]
        refused_label = "Refused (this week)"
    else:
        agg["display_refused"] = agg["patients_refused"] / week_span
        refused_label = f"Refused (avg/week over {week_span} weeks)"

    if len(agg) < 2:
        fig = go.Figure()

        service = agg.iloc[0]["service"]
        label = DEPT_LABELS.get(service, service)

        colors = ["#0173B2", "#029E73", "#DE8F05"]

        avg_beds = agg.iloc[0]["available_beds"]
        avg_demand = agg.iloc[0]["patients_request"] / week_span
        avg_refused = agg.iloc[0]["display_refused"]

        fig.add_trace(
            go.Bar(
                x=["Beds (avg/week)", "Demand (avg/week)", refused_label],
                y=[avg_beds, avg_demand, avg_refused],
                marker=dict(color=colors, opacity=0.85),
                text=[f"{math.floor(avg_beds)}", f"{math.floor(avg_demand)}", f"{math.floor(avg_refused)}"],
                textposition="inside",
                textfont=dict(color="white", size=11, family="Arial Bold"),
                hovertemplate="<b style='font-size:13px'>%{x}</b><br><b>Count:</b> %{text}<extra></extra>",
                showlegend=False,
            )
        )

        fig.update_layout(
            title=dict(
                text=(
                    f"<b>{label} Summary</b><br>"
                    f"<sub style='font-size:11px'>Week(s) {week_range[0]}-{week_range[1]} | "
                    f"Select multiple depts for comparison</sub>"
                ),
                font=dict(size=13),
            ),
            yaxis=dict(title="<b>Count</b>", gridcolor="#f0f0f0"),
            template="plotly_white",
            margin=dict(l=55, r=20, t=50, b=50),
        )

        return fig, "Select multiple departments to see comparison chart"

    fig = go.Figure()

    for _, row in agg.iterrows():
        service = row["service"]
        color = DEPT_COLORS.get(service, "#3498db")
        label = DEPT_LABELS.get(service, service)

        fig.add_trace(
            go.Scatter(
                x=[row["available_beds"]],
                y=[row["refusal_rate"]],
                mode="markers+text",
                name=label,
                marker=dict(
                    size=row["patients_request"] / 50,
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
            )
        )

    if len(agg) > 2:
        try:
            slope, intercept, r_value, _, _ = stats.linregress(agg["available_beds"], agg["refusal_rate"])
            x_trend = np.array([agg["available_beds"].min(), agg["available_beds"].max()])
            y_trend = slope * x_trend + intercept
            fig.add_trace(
                go.Scatter(
                    x=x_trend,
                    y=y_trend,
                    mode="lines",
                    name="Expected",
                    line=dict(color="red", width=2, dash="dash"),
                    hovertemplate=f"Expected<br>R²={r_value ** 2:.2f}<extra></extra>",
                )
            )
        except:
            pass

    avg_beds = agg["available_beds"].mean()
    avg_refusal = agg["refusal_rate"].mean()
    fig.add_vline(x=avg_beds, line_dash="dot", line_color="gray", opacity=0.3)
    fig.add_hline(y=avg_refusal, line_dash="dot", line_color="gray", opacity=0.3)

    max_x, min_x = agg["available_beds"].max(), agg["available_beds"].min()
    max_y, min_y = agg["refusal_rate"].max(), agg["refusal_rate"].min()

    fig.add_annotation(
        x=min_x + (avg_beds - min_x) * 0.3, y=max_y * 0.85,
        text="<b>UNDER-CAPACITY</b><br>Low beds + High refusals<br>→ Need more beds",
        showarrow=False,
        font=dict(size=9, color="red"),
        bgcolor="rgba(255,0,0,0.08)",
        bordercolor="red", borderwidth=1, borderpad=4,
    )
    fig.add_annotation(
        x=avg_beds + (max_x - avg_beds) * 0.7, y=max_y * 0.85,
        text="<b>INEFFICIENT</b><br>High beds + High refusals<br>→ Process problem",
        showarrow=False,
        font=dict(size=9, color="orange"),
        bgcolor="rgba(255,165,0,0.08)",
        bordercolor="orange", borderwidth=1, borderpad=4,
    )
    fig.add_annotation(
        x=min_x + (avg_beds - min_x) * 0.3, y=min_y + (avg_refusal - min_y) * 0.3,
        text="<b>EFFICIENT</b><br>Low beds + Low refusals<br>→ Well-matched",
        showarrow=False,
        font=dict(size=9, color="green"),
        bgcolor="rgba(0,128,0,0.08)",
        bordercolor="green", borderwidth=1, borderpad=4,
    )
    fig.add_annotation(
        x=avg_beds + (max_x - avg_beds) * 0.7, y=min_y + (avg_refusal - min_y) * 0.3,
        text="<b>OVER-CAPACITY</b><br>High beds + Low refusals<br>→ Reallocation source",
        showarrow=False,
        font=dict(size=9, color="blue"),
        bgcolor="rgba(0,0,255,0.08)",
        bordercolor="blue", borderwidth=1, borderpad=4,
    )

    fig.update_layout(
        title=dict(
            text=(
                "<b>Refusal Rate vs Capacity</b><br>"
                "<sub style='font-size:11px'>Size=Demand | Quadrants show reallocation strategy</sub>"
            ),
            font=dict(size=13),
        ),
        xaxis=dict(title="<b>Allocated Beds</b>", gridcolor="#f0f0f0"),
        yaxis=dict(title="<b>Refusal Rate (%)</b>", gridcolor="#f0f0f0"),
        template="plotly_white",
        hovermode="closest",
        margin=dict(l=55, r=55, t=50, b=50),
    )

    high_refusal = agg[agg["refusal_rate"] > avg_refusal].sort_values("refusal_rate", ascending=False)
    low_refusal = agg[agg["refusal_rate"] < avg_refusal].sort_values("available_beds", ascending=False)

    if not high_refusal.empty and not low_refusal.empty:
        worst = DEPT_LABELS.get(high_refusal.iloc[0]["service"], high_refusal.iloc[0]["service"])
        best = DEPT_LABELS.get(low_refusal.iloc[0]["service"], low_refusal.iloc[0]["service"])
        context = f"Week(s) {week_range[0]}-{week_range[1]} | Reallocation: {best} → {worst} | {refused_label}"
    else:
        context = f"Week(s) {week_range[0]}-{week_range[1]} | {len(agg)} depts | {refused_label}"

    return fig, context


# ==================================================================
# T3: HEATMAP + VIOLIN/GANTT SWITCHABLE
# ==================================================================

from dash import dcc


@callback(
    Output("t3-line-chart", "figure"),
    [
        Input("dept-filter", "value"),
        Input("week-slider", "value"),
        Input("quantity-tabs", "value"),
        Input("t3-violin-chart", "relayoutData"),
    ],
)
def update_t3_line(selected_depts, week_range, active_tab, los_relayout):
    if active_tab != "tab-t3":
        raise PreventUpdate

    df = _filter_services(selected_depts, week_range)
    if df.empty:
        return _empty_fig("No data")

    df["occupancy_rate"] = (df["patients_admitted"] / df["available_beds"] * 100).fillna(0)

    zoomed_period = None
    zoom_range = None
    if los_relayout:
        if "xaxis.range[0]" in los_relayout:
            try:
                week_start = int(round(los_relayout["xaxis.range[0]"]))
                week_end = int(round(los_relayout["xaxis.range[1]"]))
                df = df[(df["week"] >= week_start) & (df["week"] <= week_end)]
                zoomed_period = f"Week {week_start}-{week_end}"
                zoom_range = [week_start, week_end]
            except:
                pass
        elif "xaxis.range" in los_relayout:
            try:
                x_range = los_relayout["xaxis.range"]
                week_start = int(round(x_range[0]))
                week_end = int(round(x_range[1]))
                df = df[(df["week"] >= week_start) & (df["week"] <= week_end)]
                zoomed_period = f"Week {week_start}-{week_end}"
                zoom_range = [week_start, week_end]
            except:
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

        fig.add_trace(
            go.Scatter(
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
            )
        )

        peaks = svc_data[svc_data["occupancy_rate"] > 100]
        if not peaks.empty:
            fig.add_trace(
                go.Scatter(
                    x=peaks["week"],
                    y=peaks["occupancy_rate"],
                    mode="markers",
                    name=f"{label} Over",
                    marker=dict(
                        size=10,
                        color=color,
                        symbol="triangle-up",
                        line=dict(width=2, color="#e74c3c")
                    ),
                    showlegend=False,
                    hoverinfo="skip"
                )
            )

    fig.add_hline(y=100, line_dash="dash", line_color="#e74c3c", line_width=2.5, opacity=0.8)
    fig.add_hline(y=85, line_dash="dot", line_color="#2ecc71", line_width=2, opacity=0.7)

    fig.add_annotation(
        x=week_max, y=100, text="<b>100%</b>",
        showarrow=False,
        font=dict(size=11, color="#e74c3c", family="Arial Bold"),
        bgcolor="rgba(255,255,255,0.95)",
        bordercolor="#e74c3c",
        borderwidth=1.5,
        borderpad=4,
        xanchor="left",
        xshift=5
    )
    fig.add_annotation(
        x=week_max, y=85, text="<b>85%</b>",
        showarrow=False,
        font=dict(size=10, color="#2ecc71", family="Arial Bold"),
        bgcolor="rgba(255,255,255,0.95)",
        bordercolor="#2ecc71",
        borderwidth=1.5,
        borderpad=4,
        xanchor="left",
        xshift=5
    )

    fig.update_layout(
        title=dict(
            text=(
                f"<b>Bed Occupancy Rate Over Time{' (' + zoomed_period + ')' if zoomed_period else ''}</b><br>"
                "<sub style='font-size:11px'>Drag to zoom | Zones: Green (85-100% optimal), Red (>100% overcapacity)</sub>"
            ),
            font=dict(size=13),
            x=0.5,
            xanchor="center",
            y=0.92,
            yanchor="top"
        ),
        xaxis=dict(
            title="<b>Week</b>",
            gridcolor="#f0f0f0",
            rangeslider=dict(visible=True, thickness=0.08),
            range=[zoom_range[0] - 0.5, zoom_range[1] + 0.5] if zoom_range else [week_min - 0.5, week_max + 0.5]
        ),
        yaxis=dict(
            title="<b>Occupancy Rate (%)</b>",
            gridcolor="#f0f0f0",
            range=[y_range_min, y_range_max]
        ),
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
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#ddd",
            borderwidth=1
        ),
        margin=dict(l=60, r=30, t=95, b=100),
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
                if "arrival_week" in df.columns:
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
                if "arrival_week" in df.columns:
                    df = df[(df["arrival_week"] >= week_start) & (df["arrival_week"] <= week_end)]
                    zoomed_period = f"Week {week_start}-{week_end}"
                    zoom_range = [week_start, week_end]
            except:
                pass

    if df.empty:
        return _empty_fig("No patients in selected period")

    weekly_los = (
        df.groupby(["arrival_week", "service"])
        .agg({"length_of_stay": ["mean", "count", "max"]})
        .reset_index()
    )
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

    fig.add_shape(
        type="rect",
        x0=week_min - 0.5, x1=week_max + 0.5,
        y0=0, y1=7,
        fillcolor="rgba(46, 204, 113, 0.08)",
        line_width=0,
        layer="below"
    )
    fig.add_shape(
        type="rect",
        x0=week_min - 0.5, x1=week_max + 0.5,
        y0=7, y1=14,
        fillcolor="rgba(241, 196, 15, 0.08)",
        line_width=0,
        layer="below"
    )
    fig.add_shape(
        type="rect",
        x0=week_min - 0.5, x1=week_max + 0.5,
        y0=14, y1=max(max_los + 2, 20),
        fillcolor="rgba(231, 76, 60, 0.12)",
        line_width=0,
        layer="below"
    )

    fig.add_hline(y=7, line_dash="dot", line_color="#27ae60", line_width=1.5, opacity=0.6)
    fig.add_hline(y=14, line_dash="dash", line_color="#e74c3c", line_width=2.5, opacity=0.8)

    for service in services:
        svc_data = weekly_los[weekly_los["service"] == service].sort_values("week")
        color = colors.get(service, "#3498db")
        label = DEPT_LABELS.get(service, service)
        overall_avg = svc_data["avg_los"].mean()

        fig.add_trace(
            go.Scatter(
                x=svc_data["week"],
                y=svc_data["avg_los"],
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=2.5, dash="dot"),
                marker=dict(size=6, color=color, symbol="diamond", line=dict(width=1, color="white")),
                cliponaxis=False,  # valid on Scatter traces
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
            )
        )

    # Right-side panel labels (paper coords; never cover the trend)
    ZONE_TITLE_SIZE = 13
    ZONE_SUB_SIZE = 11
    ZONE_BORDERPAD = 6

    def _zone_tag(y_paper, title, subtitle, color):
        fig.add_annotation(
            xref="paper", yref="paper",
            x=1.02, y=y_paper,
            text=(
                f"<b style='font-size:{ZONE_TITLE_SIZE}px'>{title}</b><br>"
                f"<span style='font-size:{ZONE_SUB_SIZE}px'>{subtitle}</span>"
            ),
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            font=dict(size=ZONE_TITLE_SIZE, color=color, family="Arial Bold"),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor=color,
            borderwidth=1.4,
            borderpad=ZONE_BORDERPAD,
            align="left",
        )

    _zone_tag(0.18, "GOOD", "0–7d", "#27ae60")
    _zone_tag(0.50, "OK", "7–14d", "#f39c12")
    _zone_tag(0.82, "BLOCKER", ">14d", "#e74c3c")

    period_text = f" ({zoomed_period})" if zoomed_period else ""
    high_los_weeks = len(weekly_los[weekly_los["avg_los"] > 14])

    title_text = (
        f"<b>Average Length of Stay Over Time{period_text}</b><br>"
        f"<sub style='font-size:11px'>"
        f"High LOS weeks (>14d): {high_los_weeks} | "
        f"Diamond markers & dotted lines for visual distinction"
        f"</sub>"
    )

    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=13),
            x=0.5,
            xanchor="center",
            y=0.92,
            yanchor="top"
        ),
        xaxis=dict(
            title="<b>Week</b>",
            gridcolor="#e8e8e8",
            gridwidth=1,
            range=[zoom_range[0] - 0.5, zoom_range[1] + 0.5] if zoom_range else [week_min - 0.5, week_max + 0.5]
        ),
        yaxis=dict(
            title="<b>Average Length of Stay (days)</b>",
            gridcolor="#e8e8e8",
            gridwidth=1,
            range=[0, max(max_los + 3, 20)]
        ),
        template="plotly_white",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(255, 255, 255, 0.98)",
            font_size=12,
            font_family="Arial",
            font_color="#000",
            bordercolor="#333"
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#ddd",
            borderwidth=1
        ),
        margin=dict(l=60, r=120, t=95, b=80),
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
        dept_df = df[df["service"] == service].nlargest(max_patients_per_dept, "length_of_stay")
        df_list.append(dept_df)

    df_sorted = pd.concat(df_list).sort_values(["service", "length_of_stay"], ascending=[True, False]) if df_list else df.head(0)
    total_in_period = len(df)

    colors = {
        "emergency": "#0173B2",
        "surgery": "#029E73",
        "general_medicine": "#DE8F05",
        "ICU": "#CC78BC",
    }

    df_sorted["color"] = df_sorted["service"].map(colors)
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
        showing = len(svc_data)
        total = stats_row["count"]
        avg_los = stats_row["avg_los"]
        max_los = stats_row["max_los"]

        y_ticks.append(y_pos)
        y_labels.append(f"{label}\n({showing}/{total} pts)")
        y_pos += 1

        for idx, row in svc_data.iterrows():
            bar_color = "#e74c3c" if row["is_blocker"] else color
            bar_thickness = min(14, max(8, row["length_of_stay"] / 2.5))

            fig.add_trace(
                go.Scatter(
                    x=[row["arrival_date"], row["departure_date"]],
                    y=[y_pos, y_pos],
                    mode="lines",
                    line=dict(color=bar_color, width=bar_thickness),
                    marker=dict(size=6, color=bar_color),
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
                )
            )
            y_pos += 1

        dept_separators.append(y_pos - 0.5)
        y_pos += 0.5

    for sep_y in dept_separators[:-1]:
        fig.add_hline(y=sep_y, line_dash="dot", line_color="#cccccc", line_width=1, opacity=0.5)

    fig.add_annotation(
        text="<b style='color:#e74c3c'>Red</b> = Bed Blocker (>14 days)",
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        font=dict(size=10, color="#333", family="Arial"),
        bgcolor="rgba(255,255,255,0.95)",
        bordercolor="#ddd",
        borderwidth=1,
        borderpad=5,
        xanchor="left",
        yanchor="top"
    )

    shown_patients = len(df_sorted)
    avg_los_all = df["length_of_stay"].mean()
    bed_blockers = (df["length_of_stay"] > 14).sum()

    title_suffix = ""
    if selected_depts and len(selected_depts) == 1:
        title_suffix = f": {DEPT_LABELS.get(selected_depts[0], selected_depts[0])}"
    elif selected_depts:
        title_suffix = f": {len(selected_depts)} Departments"
    else:
        title_suffix = ": All Departments"

    period_text = f" ({zoomed_period})" if zoomed_period else ""
    chart_height = min(500, max(350, y_pos * 10))

    fig.update_layout(
        title=dict(
            text=(
                f"<b>Patient Timeline{title_suffix}{period_text}</b><br>"
                f"<sub style='font-size:11px'>"
                f"Top {shown_patients} of {total_in_period} patients | "
                f"Avg LOS: {avg_los_all:.1f} days | "
                f"Bed Blockers (>14d): {bed_blockers}"
                f"</sub>"
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
            tickfont=dict(size=12),
            showgrid=False
        ),
        template="plotly_white",
        hoverlabel=dict(
            bgcolor="rgba(255, 255, 255, 0.98)",
            font_size=11,
            font_family="Arial",
            font_color="#000",
            bordercolor="#333",
            align="left"
        ),
        height=chart_height,
        margin=dict(l=200, r=20, t=95, b=60),
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
            dcc.Graph(id="t3-violin-chart", config={"displayModeBar": True, "displaylogo": False},
                      style={"height": "100%"}),
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
            dcc.Graph(id="t3-gantt-chart", config={"displayModeBar": True, "displaylogo": False},
                      style={"height": "100%"}),
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
