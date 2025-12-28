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
    fig.add_annotation(text=title, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=13, color="#999"))
    fig.update_layout(template="plotly_white", margin=dict(l=40, r=40, t=40, b=40), xaxis=dict(visible=False), yaxis=dict(visible=False))
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
    # Get all services data (ignore dept-filter)
    df = _filter_services(None, week_range)  # None = all departments
    if df.empty:
        return _empty_fig("No data")
    
    # Aggregate by department
    agg = df.groupby("service").agg({
        "available_beds": "mean",
    }).reset_index().sort_values("available_beds", ascending=True)
    
    fig = go.Figure()
    
    # Colorblind-friendly colors for each department
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
            text=f"<b>Bed Distribution by Department</b><br><sub style='font-size:11px'>Week(s) {week_range[0]}-{week_range[1]} | Average beds allocated</sub>",
            font=dict(size=14)
        ),
        xaxis=dict(title="<b>Average Beds per Week</b>", gridcolor="#f0f0f0"),
        yaxis=dict(title=""),
        template="plotly_white",
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Arial",
        ),
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
        return {"display": "flex", "flexDirection": "column", "gap": "8px", "height": "100%"}, {"display": "none"}
    else:
        return {"display": "none"}, {"display": "flex", "flexDirection": "column", "gap": "6px", "height": "100%"}


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
    """
    Week-by-week stacked/grouped bars showing:
    - Beds (capacity baseline)
    - Demand (what was requested)
    - Refusals (what couldn't be accommodated)
    """
    if active_tab != "tab-t2":
        raise PreventUpdate
    
    df = _filter_services(selected_depts, week_range)
    if df.empty:
        return _empty_fig("No data")
    
    # Filter out anomaly weeks if toggle is on
    if hide_anomalies and "hide" in hide_anomalies:
        # Mark anomaly weeks: every 3rd week (3, 6, 9, 12, ...)
        anomaly_weeks = [w for w in range(3, 53, 3)]  # [3, 6, 9, ..., 51]
        df = df[~df["week"].isin(anomaly_weeks)]
        if df.empty:
            return _empty_fig("No non-anomaly weeks in selected range")
    
    df = df.sort_values("week")
    
    fig = go.Figure()
    
    # For each department, add traces
    for service in sorted(df["service"].unique()):
        svc_data = df[df["service"] == service]
        color = DEPT_COLORS.get(service, "#3498db")
        label = DEPT_LABELS.get(service, service)
        
        # Colorblind-friendly colors
        bed_color = "#0173B2"  # Blue
        refused_color = "#DE8F05"  # Orange (not red - better for colorblind)
        
        # Beds (baseline)
        fig.add_trace(go.Bar(
            x=svc_data["week"],
            y=svc_data["available_beds"],
            name=f"{label} - Beds",
            marker=dict(color=bed_color, opacity=0.7),
            hovertemplate=(
                f"<b style='font-size:14px'>{label}</b><br>" +
                "<b>Week:</b> %{x}<br>" +
                "<b>Beds:</b> %{y}<br>" +
                "<extra></extra>"
            ),
            legendgroup=label,
        ))
        
        # Refusals (orange for colorblind accessibility)
        fig.add_trace(go.Bar(
            x=svc_data["week"],
            y=svc_data["patients_refused"],
            name=f"{label} - Refused",
            marker=dict(color=refused_color, opacity=0.85),
            customdata=svc_data[["patients_request"]].values,
            hovertemplate=(
                f"<b style='font-size:14px'>{label}</b><br>" +
                "<b>Week:</b> %{x}<br>" +
                "<b>Refused:</b> %{y}<br>" +
                "<b>Demand:</b> %{customdata[0]}<br>" +
                "<extra></extra>"
            ),
            legendgroup=label,
        ))
    
    fig.update_layout(
        title=dict(
            text="<b>Weekly Capacity and Refusals</b><br><sub style='font-size:11px'>Blue=Beds | Orange=Refused | Hover for details</sub>",
            font=dict(size=13)
        ),
        xaxis=dict(title="<b>Week</b>", gridcolor="#f0f0f0"),
        yaxis=dict(title="<b>Patients / Beds</b>", gridcolor="#f0f0f0"),
        template="plotly_white",
        barmode="group",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Arial",
        ),
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
# T2 CHART 2: DEPARTMENT COMPARISON (Refusal efficiency)
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
    """
    Q2 & Q3: Department comparison
    Scatter: X=beds, Y=refusal_rate, size=demand
    Only useful with multiple departments!
    """
    if active_tab != "tab-t2":
        raise PreventUpdate
    
    df = _filter_services(selected_depts, week_range)
    if df.empty:
        return _empty_fig("No data"), "No data"
    
    # Check if single week selected
    week_span = week_range[1] - week_range[0] + 1
    
    # Aggregate by department
    agg = df.groupby("service").agg({
        "available_beds": "mean",
        "patients_request": "sum",
        "patients_refused": "sum",
    }).reset_index()
    
    agg["refusal_rate"] = (agg["patients_refused"] / agg["patients_request"] * 100).fillna(0)
    
    # If single week, show weekly refused instead of total
    if week_span == 1:
        agg["display_refused"] = agg["patients_refused"]
        refused_label = "Refused (this week)"
    else:
        # Scale refused to per-week average for better visualization
        agg["display_refused"] = agg["patients_refused"] / week_span
        refused_label = f"Refused (avg/week over {week_span} weeks)"
    
    # Check if we have multiple departments
    if len(agg) < 2:
        # Show simple bar chart instead
        fig = go.Figure()
        
        service = agg.iloc[0]["service"]
        label = DEPT_LABELS.get(service, service)
        
        # Colorblind-friendly palette
        colors = ["#0173B2", "#029E73", "#DE8F05"]  # Blue, Green, Orange
        
        # Calculate weekly average for beds too
        avg_beds = agg.iloc[0]["available_beds"]  # This is already mean from groupby
        avg_demand = agg.iloc[0]["patients_request"] / week_span
        avg_refused = agg.iloc[0]["display_refused"]
        
        fig.add_trace(go.Bar(
            x=["Beds (avg/week)", "Demand (avg/week)", refused_label],
            y=[avg_beds, avg_demand, avg_refused],
            marker=dict(color=colors, opacity=0.85),
            text=[f"{math.floor(avg_beds)}", f"{math.floor(avg_demand)}", f"{math.floor(avg_refused)}"],
            textposition="inside",
            textfont=dict(color="white", size=11, family="Arial Bold"),
            hovertemplate="<b style='font-size:13px'>%{x}</b><br><b>Count:</b> %{text}<extra></extra>",
            showlegend=False,
        ))
        
        fig.update_layout(
            title=dict(text=f"<b>{label} Summary</b><br><sub style='font-size:11px'>Week(s) {week_range[0]}-{week_range[1]} | Select multiple depts for comparison</sub>", font=dict(size=13)),
            yaxis=dict(title="<b>Count</b>", gridcolor="#f0f0f0"),
            template="plotly_white",
            margin=dict(l=55, r=20, t=50, b=50),
        )
        
        context = f"Select multiple departments to see comparison chart"
        return fig, context
    
    # Multiple departments - show scatter
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
                f"<b>{label}</b><br>" +
                "Beds: %{x:.0f}<br>" +
                "Refusal Rate: %{y:.1f}%<br>" +
                "Refused: %{customdata[0]}<br>" +
                "Demand: %{customdata[1]}<br>" +
                "<extra></extra>"
            ),
            showlegend=False,
        ))
    
    # Trendline
    if len(agg) > 2:
        try:
            slope, intercept, r_value, _, _ = stats.linregress(agg["available_beds"], agg["refusal_rate"])
            x_trend = np.array([agg["available_beds"].min(), agg["available_beds"].max()])
            y_trend = slope * x_trend + intercept
            
            fig.add_trace(go.Scatter(
                x=x_trend,
                y=y_trend,
                mode="lines",
                name="Expected",
                line=dict(color="red", width=2, dash="dash"),
                hovertemplate=f"Expected<br>R²={r_value**2:.2f}<extra></extra>",
            ))
        except:
            pass
    
    # Quadrant lines
    avg_beds = agg["available_beds"].mean()
    avg_refusal = agg["refusal_rate"].mean()
    
    fig.add_vline(x=avg_beds, line_dash="dot", line_color="gray", opacity=0.3)
    fig.add_hline(y=avg_refusal, line_dash="dot", line_color="gray", opacity=0.3)
    
    # Quadrant labels
    max_x, min_x = agg["available_beds"].max(), agg["available_beds"].min()
    max_y, min_y = agg["refusal_rate"].max(), agg["refusal_rate"].min()
    
    fig.add_annotation(x=min_x + (avg_beds - min_x) * 0.3, y=max_y * 0.85, text="<b>UNDER-CAPACITY</b><br>Low beds + High refusals<br>→ Need more beds", showarrow=False, font=dict(size=9, color="red"), bgcolor="rgba(255,0,0,0.08)", bordercolor="red", borderwidth=1, borderpad=4)
    fig.add_annotation(x=avg_beds + (max_x - avg_beds) * 0.7, y=max_y * 0.85, text="<b>INEFFICIENT</b><br>High beds + High refusals<br>→ Process problem", showarrow=False, font=dict(size=9, color="orange"), bgcolor="rgba(255,165,0,0.08)", bordercolor="orange", borderwidth=1, borderpad=4)
    fig.add_annotation(x=min_x + (avg_beds - min_x) * 0.3, y=min_y + (avg_refusal - min_y) * 0.3, text="<b>EFFICIENT</b><br>Low beds + Low refusals<br>→ Well-matched", showarrow=False, font=dict(size=9, color="green"), bgcolor="rgba(0,128,0,0.08)", bordercolor="green", borderwidth=1, borderpad=4)
    fig.add_annotation(x=avg_beds + (max_x - avg_beds) * 0.7, y=min_y + (avg_refusal - min_y) * 0.3, text="<b>OVER-CAPACITY</b><br>High beds + Low refusals<br>→ Reallocation source", showarrow=False, font=dict(size=9, color="blue"), bgcolor="rgba(0,0,255,0.08)", bordercolor="blue", borderwidth=1, borderpad=4)
    
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
    
    # Reallocation recommendation
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
# T3: HEATMAP & STACKED (Same - working well)
# ==================================================================

@callback(
    Output("t3-heatmap-chart", "figure"),
    [Input("dept-filter", "value"), Input("week-slider", "value"), Input("quantity-tabs", "value")],
)
def update_t3_heatmap(selected_depts, week_range, active_tab):
    if active_tab != "tab-t3":
        raise PreventUpdate
    df = _filter_services(selected_depts, week_range)
    if df.empty:
        return _empty_fig("No data")
    df["pressure"] = (df["patients_admitted"] / df["available_beds"]).fillna(0).clip(0, 1.5)
    pivot = df.pivot_table(index="service", columns="week", values="pressure", aggfunc="mean").fillna(0)
    pivot["avg"] = pivot.mean(axis=1)
    pivot = pivot.sort_values("avg", ascending=False).drop("avg", axis=1)
    y_labels = [DEPT_LABELS.get(s, s) for s in pivot.index]
    fig = go.Figure(data=go.Heatmap(z=pivot.values, x=pivot.columns.tolist(), y=y_labels, colorscale=[[0, "#d4edda"], [0.5, "#fff3cd"], [0.8, "#f8d7da"], [1, "#721c24"]], colorbar=dict(title="Pressure", tickmode="linear", tick0=0, dtick=0.3, len=0.7), hovertemplate="<b>%{y}</b><br>Week %{x}<br>Pressure: %{z:.2f}<extra></extra>"))
    fig.update_layout(title=dict(text="<b>T3: Bed Pressure Heatmap</b><br><sub>Click to filter stacked area</sub>", font=dict(size=11)), xaxis=dict(title="<b>Week</b>", side="bottom", gridcolor="#f0f0f0"), yaxis=dict(title=""), template="plotly_white", margin=dict(l=100, r=80, t=45, b=40))
    return fig


@callback(
    Output("t3-stacked-chart", "figure"),
    [Input("dept-filter", "value"), Input("week-slider", "value"), Input("t3-bucket-selector", "value"), Input("quantity-tabs", "value"), Input("t3-heatmap-chart", "clickData")],
)
def update_t3_stacked(selected_depts, week_range, bucket_mode, active_tab, heatmap_click):
    if active_tab != "tab-t3":
        raise PreventUpdate
    df = _filter_patients(selected_depts, week_range)
    selected_service = None
    if heatmap_click and "points" in heatmap_click:
        clicked_label = heatmap_click["points"][0]["y"]
        service_map = {v: k for k, v in DEPT_LABELS.items()}
        if clicked_label in service_map:
            selected_service = service_map[clicked_label]
            df = df[df["service"] == selected_service]
    if df.empty or "arrival_week" not in df.columns:
        return _empty_fig("No patient data | Click heatmap")
    buckets = [(0, 3, "0-3"), (4, 7, "4-7"), (8, 999, "8+")] if bucket_mode == "coarse" else [(0, 1, "0-1"), (2, 3, "2-3"), (4, 7, "4-7"), (8, 999, "8+")]
    def assign_bucket(los):
        for min_los, max_los, label in buckets:
            if min_los <= los <= max_los:
                return label
        return buckets[-1][2]
    df["los_bucket"] = df["length_of_stay"].apply(assign_bucket)
    bed_days = df.groupby(["arrival_week", "los_bucket"]).agg({"length_of_stay": "sum"}).reset_index()
    bed_days.columns = ["week", "bucket", "bed_days"]
    pivot = bed_days.pivot_table(index="week", columns="bucket", values="bed_days", fill_value=0)
    for _, _, label in buckets:
        if label not in pivot.columns:
            pivot[label] = 0
    bucket_order = [label for _, _, label in buckets]
    pivot = pivot[[col for col in bucket_order if col in pivot.columns]]
    fig = go.Figure()
    colors = ["#28a745", "#ffc107", "#fd7e14", "#dc3545"]
    for i, bucket_label in enumerate(pivot.columns):
        fig.add_trace(go.Scatter(x=pivot.index, y=pivot[bucket_label], mode="lines", name=f"{bucket_label} days", line=dict(width=0), fillcolor=colors[i % len(colors)], fill="tonexty" if i > 0 else "tozeroy", stackgroup="one", hovertemplate=f"<b>{bucket_label} days</b><br>Week %{{x}}<br>Bed-days: %{{y:.0f}}<extra></extra>"))
    title_text = f"<b>T3: Bed-days by LOS</b><br><sub>{DEPT_LABELS.get(selected_service, 'All')} | Long stays blocking beds</sub>" if selected_service else "<b>T3: Bed-days by LOS</b><br><sub>Click heatmap to filter</sub>"
    fig.update_layout(title=dict(text=title_text, font=dict(size=11)), xaxis=dict(title="<b>Week</b>", gridcolor="#f0f0f0"), yaxis=dict(title="<b>Bed-days</b>", gridcolor="#f0f0f0"), template="plotly_white", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=8)), margin=dict(l=50, r=20, t=45, b=70))
    return fig


# ==================================================================
# REGISTRATION
# ==================================================================

def register_quantity_callbacks():
    pass
