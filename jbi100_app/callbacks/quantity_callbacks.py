"""
Quantity Callbacks
JBI100 Visualization - Group 25

T2 improvements (lecture/assignment aligned):
- Select + Connect: click week to persist selection and highlight across T2/T3/Overview
- Reconfigure: grouped vs separate view
- Encode: refused count vs refusal rate
- Compare: if multiple departments selected, show per-dept comparison (overlay)
- Reduce clutter: event icons only in DETAIL zoom (<= 8 weeks)
- Robust scaling: refusal spikes no longer flatten the entire plot (visual cap at 95th percentile)
"""

from dash import callback, Output, Input, State, ctx
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from jbi100_app.data import get_services_data, get_patients_data
from jbi100_app.config import DEPT_COLORS, DEPT_LABELS, EVENT_ICONS


def register_quantity_callbacks():
    # kept for framework consistency
    pass


def _anomaly_weeks():
    return list(range(3, 53, 3))


def _zoom_level(week_range):
    wmin, wmax = week_range
    span = (wmax - wmin) + 1
    if span <= 8:
        return "detail"
    if span <= 13:
        return "quarter"
    return "overview"


@callback(
    [Output("quantity-t2-content", "style"), Output("quantity-t3-content", "style")],
    Input("quantity-tabs", "value"),
)
def switch_quantity_tab(tab_value):
    if tab_value == "tab-t3":
        return {"display": "none"}, {"display": "flex", "flexDirection": "column", "gap": "6px", "height": "100%"}
    return {"display": "flex", "flexDirection": "column", "gap": "8px", "height": "100%"}, {"display": "none"}


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


@callback(
    Output("t2-spc-chart", "figure"),
    [
        Input("dept-filter", "value"),
        Input("week-slider", "value"),
        Input("hide-anomalies-toggle", "value"),
        Input("show-events-toggle", "value"),
        Input("t2-weekly-layout", "value"),
        Input("t2-refusal-metric", "value"),
        Input("quantity-selected-week", "data"),
    ],
)
def update_t2_weekly(depts, week_range, hide_anom_list, show_events_list, weekly_layout, refusal_metric, selected_week):
    services = get_services_data()
    depts = depts or ["emergency"]
    week_min, week_max = week_range
    zoom = _zoom_level(week_range)

    df = services[(services["week"] >= week_min) & (services["week"] <= week_max)].copy()
    df = df[df["service"].isin(depts)].copy()

    hide_anom = "hide" in (hide_anom_list or [])
    show_events = "show" in (show_events_list or [])

    anom = _anomaly_weeks()
    if hide_anom:
        df = df[~df["week"].isin(anom)].copy()

    # Encode toggle
    if refusal_metric == "rate":
        df["refusal_value"] = df["refusal_rate"]  # already in %
        refusal_label = "Refusal rate (%)"
        hover_refusal = "Refusal rate: %{y:.1f}%"
    else:
        df["refusal_value"] = df["patients_refused"]
        refusal_label = "Patients refused"
        hover_refusal = "Refused: %{y}"

    # Robust scaling (visual-only) for refused count
    robust_used = False
    q95 = None  # keep for cap-line
    if refusal_metric == "count" and len(df) > 0:
        q95 = float(df["refusal_value"].quantile(0.95))
        if q95 > 0:
            df["refusal_value_robust"] = df["refusal_value"].clip(upper=q95)
            robust_used = (df["refusal_value"].max() > q95 * 1.25)
        else:
            df["refusal_value_robust"] = df["refusal_value"]
    else:
        df["refusal_value_robust"] = df["refusal_value"]

    multi_dept = len(depts) > 1

    # Figure skeleton
    if weekly_layout == "grouped":
        fig = go.Figure()
    else:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.10
        )

    # Build traces
    if multi_dept:
        for dept in depts:
            ddf = (
                df[df["service"] == dept]
                .groupby("week", as_index=False)
                .agg(
                    beds=("available_beds", "sum"),
                    refused=("refusal_value_robust", "sum"),
                    raw_refused=("refusal_value", "sum"),
                    event=("event", lambda x: x[x != "none"].iloc[0] if (x != "none").any() else "none"),
                )
                .sort_values("week")
            )
            weeks = ddf["week"].tolist()

            color = DEPT_COLORS.get(dept, "#666")
            label = DEPT_LABELS.get(dept, dept)

            if weekly_layout == "grouped":
                fig.add_trace(go.Bar(
                    x=weeks, y=ddf["beds"],
                    name=f"{label} - Beds",
                    marker=dict(color=color),
                    opacity=0.55,
                    hovertemplate=f"{label}<br>Week %{x}<br>Beds: %{y}<extra></extra>",
                ))
                fig.add_trace(go.Bar(
                    x=weeks, y=ddf["refused"],
                    name=f"{label} - {refusal_label}",
                    marker=dict(color=color),
                    opacity=0.9,
                    hovertemplate=f"{label}<br>Week %{x}<br>{hover_refusal}<extra></extra>",
                ))
            else:
                fig.add_trace(go.Bar(
                    x=weeks, y=ddf["beds"],
                    name=f"{label} - Beds",
                    marker=dict(color=color),
                    opacity=0.6,
                    hovertemplate=f"{label}<br>Week %{x}<br>Beds: %{y}<extra></extra>",
                ), row=1, col=1)

                fig.add_trace(go.Bar(
                    x=weeks, y=ddf["refused"],
                    name=f"{label} - {refusal_label}",
                    marker=dict(color=color),
                    opacity=0.9,
                    hovertemplate=f"{label}<br>Week %{x}<br>{hover_refusal}<extra></extra>",
                ), row=2, col=1)
    else:
        ddf = (
            df.groupby("week", as_index=False)
            .agg(
                beds=("available_beds", "sum"),
                refused=("refusal_value_robust", "sum"),
                raw_refused=("refusal_value", "sum"),
                event=("event", lambda x: x[x != "none"].iloc[0] if (x != "none").any() else "none"),
            )
            .sort_values("week")
        )
        weeks = ddf["week"].tolist()

        if weekly_layout == "grouped":
            fig.add_trace(go.Bar(
                x=weeks, y=ddf["beds"],
                name="Beds (total)",
                marker=dict(color="#3498db"),
                hovertemplate="Week %{x}<br>Beds: %{y}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                x=weeks, y=ddf["refused"],
                name=refusal_label,
                marker=dict(color="#e67e22"),
                hovertemplate="Week %{x}<br>" + hover_refusal + "<extra></extra>",
            ))
        else:
            fig.add_trace(go.Bar(
                x=weeks, y=ddf["beds"],
                name="Beds (total)",
                marker=dict(color="#3498db"),
                hovertemplate="Week %{x}<br>Beds: %{y}<extra></extra>",
            ), row=1, col=1)

            fig.add_trace(go.Bar(
                x=weeks, y=ddf["refused"],
                name=refusal_label,
                marker=dict(color="#e67e22"),
                hovertemplate="Week %{x}<br>" + hover_refusal + "<extra></extra>",
            ), row=2, col=1)

    # --- Title + subtle subtitle note (prevents overlap with legend) ---
    subtitle = ""
    if refusal_metric == "count" and robust_used:
        subtitle = "<br><span style='font-size:11px;color:#95a5a6'><i>Note: refusal spikes visually capped for readability</i></span>"

    fig.update_layout(
        title=dict(
            text="Weekly Capacity and Refusals" + subtitle,
            x=0.02,
            xanchor="left",
            font=dict(size=20),
        ),
        # Keep visuals consistent and avoid internal scroll pressure
        height=440,
        margin=dict(l=105, r=20, t=115, b=60),
        plot_bgcolor="white",
        paper_bgcolor="white",
        clickmode="event+select",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        barmode="group" if weekly_layout == "grouped" else None,
    )

    # Adaptive tick density to avoid unreadable week labels
    span = (week_max - week_min) + 1
    dtick = 1
    if span > 20:
        dtick = 2
    if span > 40:
        dtick = 4
    fig.update_xaxes(title_text="Week", dtick=dtick, tickangle=0)

    # Axis titles
    if weekly_layout != "grouped":
        fig.update_yaxes(
            title_text="Beds",
            title_standoff=12,
            automargin=True,
            row=1, col=1
        )
        fig.update_yaxes(
            title_text=("Refusal rate (%)" if refusal_metric == "rate" else "Patients refused"),
            title_standoff=16,
            automargin=True,
            row=2, col=1
        )

    # --- Cap threshold line + CLEANER label ---
    if weekly_layout != "grouped" and refusal_metric == "count" and robust_used and q95 is not None and q95 > 0:
        cap_val = int(round(q95))

        fig.add_hline(
            y=q95,
            line_width=1,
            line_dash="dash",
            line_color="rgba(149,165,166,0.95)",
            row=2, col=1
        )

        # Cleaner label: shorter, aligned top-right, with subtle bg
        fig.add_annotation(
            x=0.99,
            y=q95,
            xref="paper",
            yref="y2",
            text=f"Cap @95% ≈ {cap_val}",
            showarrow=False,
            xanchor="right",
            yanchor="bottom",
            yshift=8,
            font=dict(size=9, color="rgba(120,130,140,0.95)"),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="rgba(0,0,0,0)",
            borderpad=2,
        )

    # Transparency: mark anomaly weeks when not hidden
    if not hide_anom:
        for w in anom:
            if week_min <= w <= week_max:
                fig.add_vrect(
                    x0=w - 0.5, x1=w + 0.5,
                    fillcolor="rgba(0,0,0,0.04)",
                    line_width=0,
                    layer="below",
                )

    # Connect: highlight selected week
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

    # Semantic zoom for events -> ONLY at detail zoom (<= 8 weeks)
    if show_events and zoom == "detail":
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


@callback(
    Output("t2-detail-chart", "figure"),
    [
        Input("dept-filter", "value"),
        Input("week-slider", "value"),
        Input("t2-refusal-metric", "value"),
        Input("quantity-selected-week", "data"),
    ],
)
def update_t2_detail(depts, week_range, refusal_metric, selected_week):
    services = get_services_data()
    depts = depts or ["emergency"]
    week_min, week_max = week_range

    df = services[(services["week"] >= week_min) & (services["week"] <= week_max)].copy()
    df = df[df["service"].isin(depts)].copy()

    beds_avg = float(df.groupby("week")["available_beds"].sum().mean()) if len(df) else 0.0
    demand_avg = float(df.groupby("week")["patients_request"].sum().mean()) if len(df) else 0.0

    if refusal_metric == "rate":
        refused_show = float(df["refusal_rate"].mean()) if len(df) else 0.0
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

    base_title = " / ".join([DEPT_LABELS.get(d, d) for d in depts]) + " Summary"
    if selected_week is not None:
        try:
            w = int(selected_week)
            context = f"(Selected: Week {w})"
        except Exception:
            context = f"(Weeks {week_min}–{week_max})"
    else:
        context = f"(Weeks {week_min}–{week_max})"
    title_text = f"{base_title} {context}"

    max_y = max([beds_avg, demand_avg, refused_show, 1.0])
    fig.update_yaxes(range=[0, max_y * 1.18], rangemode="tozero", automargin=True)

    fig.update_layout(
        title=dict(text=title_text, x=0.02, xanchor="left", font=dict(size=18)),
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


@callback(
    Output("distribution-modal", "style"),
    [Input("show-distribution-btn", "n_clicks"), Input("close-distribution-btn", "n_clicks")],
    prevent_initial_call=True,
)
def toggle_distribution_modal(open_clicks, close_clicks):
    if ctx.triggered_id == "show-distribution-btn":
        return {"display": "block"}
    return {"display": "none"}


@callback(
    Output("distribution-chart", "figure"),
    Input("show-distribution-btn", "n_clicks"),
    [State("dept-filter", "value"), State("week-slider", "value")],
    prevent_initial_call=True,
)
def update_distribution_chart(n_clicks, depts, week_range):
    services = get_services_data()
    depts = depts or ["emergency"]
    week_min, week_max = week_range

    df = services[(services["week"] >= week_min) & (services["week"] <= week_max)].copy()
    df = df[df["service"].isin(depts)].copy()

    fig = go.Figure()
    for dept in depts:
        ddf = df[df["service"] == dept]
        fig.add_trace(go.Box(
            y=ddf["available_beds"],
            name=DEPT_LABELS.get(dept, dept),
            marker=dict(color=DEPT_COLORS.get(dept, "#666")),
            boxmean=True,
        ))

    fig.update_layout(
        title="Bed Distribution (selected time range)",
        height=500,
        margin=dict(l=50, r=20, t=50, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        yaxis_title="Available beds",
    )
    return fig


@callback(
    Output("t3-heatmap-chart", "figure"),
    [Input("dept-filter", "value"), Input("week-slider", "value"), Input("quantity-selected-week", "data")],
)
def update_t3_heatmap(depts, week_range, selected_week):
    services = get_services_data()
    depts = depts or ["emergency"]
    week_min, week_max = week_range

    df = services[(services["week"] >= week_min) & (services["week"] <= week_max)].copy()
    df = df[df["service"].isin(depts)].copy()

    pivot = df.pivot_table(index="service", columns="week", values="utilization_rate", aggfunc="mean").reindex(depts)

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=[DEPT_LABELS.get(s, s) for s in pivot.index.tolist()],
            colorbar=dict(title="Utilization %"),
            hovertemplate="Week %{x}<br>%{y}<br>Utilization: %{z:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title="T3: Utilization Heatmap (proxy for occupancy pressure)",
        height=420,
        margin=dict(l=90, r=20, t=60, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

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

    return fig


@callback(
    Output("t3-stacked-chart", "figure"),
    [Input("dept-filter", "value"), Input("week-slider", "value"), Input("t3-bucket-selector", "value")],
)
def update_t3_stacked(depts, week_range, bucket_mode):
    patients = get_patients_data()
    depts = depts or ["emergency"]
    week_min, week_max = week_range

    df = patients[patients["service"].isin(depts)].copy()
    df = df[(df["arrival_week"] >= week_min) & (df["arrival_week"] <= week_max)].copy()

    if bucket_mode == "fine":
        bins = [-1, 1, 3, 7, 999]
        labels = ["0-1", "2-3", "4-7", "8+"]
    else:
        bins = [-1, 3, 7, 999]
        labels = ["0-3", "4-7", "8+"]

    df["bucket"] = pd.cut(df["length_of_stay"], bins=bins, labels=labels)

    # silence pandas FutureWarning (categorical groupby default change)
    grouped = (
        df.groupby(["arrival_week", "bucket"], observed=True)
        .size()
        .reset_index(name="count")
    )

    weeks = list(range(week_min, week_max + 1))
    fig = go.Figure()

    for label in labels:
        tmp = grouped[grouped["bucket"] == label]
        y = [int(tmp[tmp["arrival_week"] == w]["count"].sum()) for w in weeks]
        fig.add_trace(go.Scatter(
            x=weeks, y=y, mode="lines", stackgroup="one",
            name=f"LOS {label}",
            hovertemplate="Week %{x}<br>" + f"{label}" + ": %{y}<extra></extra>",
        ))

    fig.update_layout(
        title="T3: Stay Duration Distribution (stacked)",
        height=420,
        margin=dict(l=50, r=20, t=60, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_title="Week",
        yaxis_title="Patients",
    )
    return fig
