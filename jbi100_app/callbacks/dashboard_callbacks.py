"""
Dashboard Callbacks
JBI100 Visualization - Group 25

Linked brushing between time series and multivariate SPLOM.
"""

from dash import callback, Output, Input, State, ctx
from dash.exceptions import PreventUpdate
import numpy as np
import plotly.graph_objects as go
import json
import time

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS, SERVICES
from jbi100_app.data import get_services_data, get_patients_data

_services_df = get_services_data()
_patients_df = get_patients_data()

ANOMALY_WEEKS = list(range(3, 53, 3))
_LOS_CACHE = None
_DEBUG_LOG_PATH = r"c:\Users\maxib\OneDrive\Documents\Visualization_Group_25\.cursor\debug.log"


def _log_debug(message, data, hypothesis_id):
    # region agent log
    payload = {
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": hypothesis_id,
        "location": "dashboard_callbacks.py",
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # endregion agent log


def _get_los_weekly():
    """Compute (and cache) weekly mean length of stay by service."""
    global _LOS_CACHE
    if _LOS_CACHE is None:
        df = _patients_df.copy()
        if "arrival_week" not in df.columns or "length_of_stay" not in df.columns:
            _LOS_CACHE = None
        else:
            _LOS_CACHE = (
                df.groupby(["service", "arrival_week"])["length_of_stay"]
                .mean()
                .reset_index()
                .rename(columns={"arrival_week": "week", "length_of_stay": "mean_los"})
            )
    return _LOS_CACHE


def _filter_services(depts, week_range, hide_anomalies):
    w0, w1 = int(week_range[0]), int(week_range[1])
    df = _services_df[(_services_df["week"] >= w0) & (_services_df["week"] <= w1)].copy()
    if depts:
        df = df[df["service"].isin(depts)].copy()
    if hide_anomalies:
        df = df[~df["week"].isin(ANOMALY_WEEKS)].copy()
    return df


def _attach_los(df):
    los_df = _get_los_weekly()
    if los_df is None:
        df["mean_los"] = np.nan
        return df
    merged = df.merge(los_df, how="left", on=["service", "week"])
    return merged


def _extract_selection(selected_data):
    if not selected_data or "points" not in selected_data:
        return None
    points = []
    box_bounds = None
    
    # Extract selection box bounds if available
    if "range" in selected_data:
        box_bounds = selected_data["range"]
    
    for point in selected_data["points"]:
        custom = point.get("customdata")
        if isinstance(custom, (list, tuple)) and len(custom) >= 2:
            try:
                week = int(round(float(custom[0])))
                service = custom[1]
                if 1 <= week <= 52 and service:
                    points.append({"week": week, "service": service})
            except (ValueError, TypeError):
                continue
    
    result = {"points": points} if points else None
    if result and box_bounds:
        result["box_bounds"] = box_bounds
    return result


def _selection_set(selection_store):
    if not selection_store or not selection_store.get("points"):
        return set()
    return {(p["week"], p["service"]) for p in selection_store["points"]}


def _calculate_points_in_box(df, box_bounds, x_col="week", y_col="pressure_index"):
    """Calculate which points in df are inside the selection box bounds."""
    if not box_bounds or not isinstance(box_bounds, dict):
        return []
    
    x_range = box_bounds.get("x")
    y_range = box_bounds.get("y")
    
    if not x_range or not y_range or len(x_range) != 2 or len(y_range) != 2:
        return []
    
    x_min, x_max = min(x_range), max(x_range)
    y_min, y_max = min(y_range), max(y_range)
    
    mask = (
        (df[x_col] >= x_min) & (df[x_col] <= x_max) &
        (df[y_col] >= y_min) & (df[y_col] <= y_max)
    )
    
    selected_df = df[mask]
    return [{"week": int(row["week"]), "service": row["service"]} 
            for _, row in selected_df.iterrows()]


def _build_time_series(df, depts, selection_store):
    fig = go.Figure()
    selection_points = _selection_set(selection_store)
    highlight = bool(selection_points)
    _log_debug(
        "_build_time_series selection state",
        {
            "highlight": highlight,
            "selection_points": len(selection_points),
            "selection_source": selection_store.get("source") if selection_store else None,
            "df_rows": len(df),
        },
        "H3"
    )

    is_filtered_by_splom = highlight and selection_store.get("source") == "multivariate-splom"
    if is_filtered_by_splom:
        df = df[df.apply(lambda r: (r["week"], r["service"]) in selection_points, axis=1)].copy()
        _log_debug(
            "_build_time_series filtered by selection",
            {"rows_after_filter": len(df)},
            "H5"
        )
    
    # T5 event encoding (diamonds + color); keep department color for normal weeks
    event_colors = {
        "flu": "#D55E00",
        "strike": "#CC79A7",
        "donation": "#009E73",
    }

    dim_non_selected = 0.15 if highlight and not is_filtered_by_splom else 1.0
    for dept in (depts or []):
        dept_df = df[df["service"] == dept].sort_values("week")
        if dept_df.empty:
            continue
        # Keep (week, service) first so brushing extraction keeps working
        event_series = dept_df["event"] if "event" in dept_df.columns else ["none"] * len(dept_df)
        customdata = list(zip(dept_df["week"], dept_df["service"], dept_df.get("available_beds"), event_series))
        
        if is_filtered_by_splom:
            mode = "markers"
            line = None
        else:
            mode = "lines+markers"
            line = dict(color=DEPT_COLORS.get(dept, "#999"), width=2)
        
        # Diamonds for event weeks, circles otherwise (T5)
        marker_symbols = []
        marker_colors = []
        marker_sizes = []
        for ev in event_series:
            if ev in event_colors:
                marker_symbols.append("diamond")
                marker_colors.append(event_colors[ev])
                marker_sizes.append(7 if not is_filtered_by_splom else 9)
            else:
                marker_symbols.append("circle")
                marker_colors.append(DEPT_COLORS.get(dept, "#999"))
                marker_sizes.append(5 if not is_filtered_by_splom else 8)

        fig.add_trace(go.Scatter(
            x=dept_df["week"],
            y=dept_df["pressure_index"],
            mode=mode,
            name=DEPT_LABELS.get(dept, dept),
            line=line,
            marker=dict(
                size=marker_sizes,
                color=marker_colors,
                symbol=marker_symbols,
                line=dict(width=1, color="#fff") if not is_filtered_by_splom else None,
            ),
            opacity=dim_non_selected,
            customdata=customdata,
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>"
                "Week %{x}<br>"
                "Pressure: %{y:.2f}<br>"
                "Beds: %{customdata[2]}<br>"
                "Event: %{customdata[3]}<extra></extra>"
            )
        ))

        if highlight and not is_filtered_by_splom:
            selected = dept_df[
                dept_df.apply(lambda r: (r["week"], r["service"]) in selection_points, axis=1)
            ]
            _log_debug(
                "_build_time_series selected count",
                {"dept": dept, "selected_rows": len(selected)},
                "H4"
            )
            if not selected.empty:
                selected_event_series = selected["event"] if "event" in selected.columns else ["none"] * len(selected)
                fig.add_trace(go.Scatter(
                    x=selected["week"],
                    y=selected["pressure_index"],
                    mode="markers",
                    name=f"{DEPT_LABELS.get(dept, dept)} selected",
                    marker=dict(size=12, color=DEPT_COLORS.get(dept, "#999"), line=dict(color="#fff", width=1.5)),
                    showlegend=False,
                    customdata=list(zip(selected["week"], selected["service"], selected.get("available_beds"), selected_event_series)),
                    hovertemplate=(
                        "<b>%{customdata[1]}</b><br>"
                        "Week %{x}<br>"
                        "Pressure: %{y:.2f}<br>"
                        "Beds: %{customdata[2]}<br>"
                        "Event: %{customdata[3]}<extra></extra>"
                    )
                ))

    ymax = max(1.5, float(df["pressure_index"].max() * 1.1)) if not df.empty else 1.5
    fig.add_hline(y=1.0, line_dash="dash", line_color="#7f8c8d", line_width=1)

    if is_filtered_by_splom and not df.empty:
        x_min, x_max = df["week"].min(), df["week"].max()
        x_range = [x_min - 1, x_max + 1]
        subtitle = f"Filtered: {len(df)} points from multivariate selection"
    else:
        x_min, x_max = df["week"].min(), df["week"].max()
        x_range = [x_min - 0.5, x_max + 0.5]
        subtitle = "Select points to brush multivariate view. Diamonds = events (T5)"

    fig.update_layout(
        title=dict(
            text=f"<b>Capacity Pressure Over Time</b><br><span style='font-size:9px;color:#7f8c8d'>{subtitle}</span>",
            x=0.5, xanchor="center", y=0.98, font=dict(size=13, color="#2c3e50")
        ),
        template="plotly_white",
        margin=dict(l=50, r=10, t=70, b=70),
        xaxis=dict(title="Week", range=x_range, dtick=4, tickfont=dict(size=9)),
        yaxis=dict(title="Pressure Index (Demand / Beds)", range=[0, ymax], tickfont=dict(size=9)),
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="left", x=0),
        dragmode="select"
    )
    return fig


def _build_department_comparison(df, selection_store):
    """Bottom chart for T3/T4: net capacity (beds - demand) by department."""
    if df.empty:
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text="No data",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=10, color="#999")
        )
        empty_fig.update_layout(template="plotly_white")
        return empty_fig

    selection_points = _selection_set(selection_store)
    if selection_points and selection_store.get("source") in ["efficiency-timeseries", "multivariate-splom"]:
        df = df[df.apply(lambda r: (r["week"], r["service"]) in selection_points, axis=1)].copy()
        if df.empty:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data for selected points",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, font=dict(size=10, color="#999")
            )
            empty_fig.update_layout(template="plotly_white")
            return empty_fig

    dept_stats = df.groupby("service").agg({
        "available_beds": "mean",
        "patients_request": "mean",
        "patients_admitted": "mean",
        "patients_refused": "mean",
        "pressure_index": "mean",
        "acceptance_rate": "mean",
    }).reset_index()

    dept_stats["avg_beds"] = dept_stats["available_beds"]
    dept_stats["avg_demand"] = dept_stats["patients_request"]
    dept_stats["net_capacity"] = dept_stats["avg_beds"] - dept_stats["avg_demand"]
    dept_stats["utilization_rate_calc"] = (
        (dept_stats["patients_admitted"] / dept_stats["available_beds"].replace(0, np.nan)) * 100
    ).fillna(0)

    dept_stats = dept_stats.sort_values("net_capacity", ascending=False)

    selected_depts = set()
    if selection_store and selection_store.get("points"):
        selected_depts = {p.get("service") for p in selection_store["points"] if p.get("service")}

    colors = []
    for _, row in dept_stats.iterrows():
        dept = row["service"]
        net = row["net_capacity"]
        if selection_points and dept in selected_depts:
            colors.append(DEPT_COLORS.get(dept, "#999"))
        else:
            colors.append("#27ae60" if net >= 0 else "#e74c3c")

    customdata = list(zip(
        dept_stats["service"],
        dept_stats["avg_beds"],
        dept_stats["avg_demand"],
        dept_stats["utilization_rate_calc"],
        dept_stats["pressure_index"],
        dept_stats["acceptance_rate"],
    ))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[DEPT_LABELS.get(d, d) for d in dept_stats["service"]],
        y=dept_stats["net_capacity"],
        marker=dict(color=colors, line=dict(width=1.5, color="#fff")),
        customdata=customdata,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Avg Beds: %{customdata[1]:.0f}<br>"
            "Avg Demand: %{customdata[2]:.0f}<br>"
            "Net (Beds - Demand): %{y:.1f}<br>"
            "Utilization: %{customdata[3]:.1f}%<br>"
            "Pressure: %{customdata[4]:.2f}<br>"
            "Acceptance: %{customdata[5]:.1f}%<extra></extra>"
        ),
        showlegend=False,
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="#7f8c8d", line_width=1)

    fig.update_layout(
        title=dict(
            text="<b>Slack vs Overload by Department (T3 & T4)</b>"
                 "<br><span style='font-size:9px;color:#7f8c8d'>Net capacity = Beds − Demand. Green=Slack (≥0), Red=Overload (&lt;0).</span>",
            x=0.5, xanchor="center", y=0.95, font=dict(size=13, color="#2c3e50"),
        ),
        template="plotly_white",
        # More space so axes/labels aren't clipped in shorter cards
        margin=dict(l=90, r=20, t=90, b=80),
        xaxis=dict(title="Department", tickfont=dict(size=9), automargin=True),
        yaxis=dict(title="Net capacity (Beds − Demand)", tickfont=dict(size=9), automargin=True),
    )
    return fig


def _build_splom(df, selection_store):
    selection_points = _selection_set(selection_store)
    highlight = bool(selection_points)
    _log_debug(
        "_build_splom selection state",
        {
            "highlight": highlight,
            "selection_points": len(selection_points),
            "selection_source": selection_store.get("source") if selection_store else None,
            "df_rows": len(df),
        },
        "H3"
    )

    if highlight and selection_store.get("source") == "efficiency-timeseries":
        df = df[df.apply(lambda r: (r["week"], r["service"]) in selection_points, axis=1)].copy()
        _log_debug(
            "_build_splom filtered by selection",
            {"rows_after_filter": len(df)},
            "H5"
        )

    # Cleaner labels (Splom axes don't support explicit ranges)
    dims = [
        dict(label="Pressure idx", values=df["pressure_index"]),
        dict(label="Util (%)", values=df["utilization_rate"]),
        dict(label="Accept (%)", values=df["acceptance_rate"]),
        dict(label="LOS (days)", values=df["mean_los"]),
    ]

    # Keep (week, service) first so brushing extraction keeps working
    base_custom = list(zip(df["week"], df["service"], df.get("available_beds")))
    # T4: marker size encodes bed capacity
    bed_sizes = [max(4, min(10, int(beds / 10) + 4)) for beds in df.get("available_beds")]
    fig = go.Figure()

    if highlight:
        fig.add_trace(go.Splom(
            dimensions=dims,
            marker=dict(color="#d0d0d0", size=3, opacity=0.12),
            text=df["service"],
            customdata=base_custom,
            hovertemplate="<b>%{text}</b><br>Week %{customdata[0]}<br>Beds: %{customdata[2]}<extra></extra>",
            showupperhalf=True,
            diagonal_visible=False,
            showlegend=False
        ))

        selected_df = df[df.apply(lambda r: (r["week"], r["service"]) in selection_points, axis=1)].copy()
        _log_debug(
            "_build_splom selected count",
            {"selected_rows": len(selected_df)},
            "H4"
        )
        if not selected_df.empty:
            selected_custom = list(zip(selected_df["week"], selected_df["service"], selected_df.get("available_beds")))
            selected_bed_sizes = [max(6, min(12, int(beds / 10) + 5)) for beds in selected_df.get("available_beds")]
            fig.add_trace(go.Splom(
                dimensions=[
                    dict(label="Pressure idx", values=selected_df["pressure_index"]),
                    dict(label="Util (%)", values=selected_df["utilization_rate"]),
                    dict(label="Accept (%)", values=selected_df["acceptance_rate"]),
                    dict(label="LOS (days)", values=selected_df["mean_los"]),
                ],
                marker=dict(
                    color=[DEPT_COLORS.get(s, "#999") for s in selected_df["service"]],
                    size=selected_bed_sizes,
                    opacity=0.95,
                    line=dict(width=0.5, color="#fff")
                ),
                text=selected_df["service"],
                customdata=selected_custom,
                hovertemplate="<b>%{text}</b><br>Week %{customdata[0]}<br>Beds: %{customdata[2]}<extra></extra>",
                showupperhalf=True,
                diagonal_visible=False,
                showlegend=False
            ))
    else:
        fig.add_trace(go.Splom(
            dimensions=dims,
            marker=dict(
                color=[DEPT_COLORS.get(s, "#999") for s in df["service"]],
                size=bed_sizes,
                opacity=0.7
            ),
            text=df["service"],
            customdata=base_custom,
            hovertemplate="<b>%{text}</b><br>Week %{customdata[0]}<br>Beds: %{customdata[2]}<extra></extra>",
            showupperhalf=True,
            diagonal_visible=False,
            showlegend=False
        ))

    fig.update_layout(
        title=dict(
            text="<b>Multivariate Efficiency Relationships</b><br><span style='font-size:9px;color:#7f8c8d'>Brush to filter time series. Marker size = bed capacity (T4)</span>",
            x=0.5, xanchor="center", y=0.96, font=dict(size=13, color="#2c3e50")
        ),
        font=dict(size=10),
        template="plotly_white",
        margin=dict(l=75, r=115, t=70, b=65),
        dragmode="select"
    )
    fig.update_xaxes(tickfont=dict(size=8), title_font=dict(size=9), automargin=True)
    fig.update_yaxes(tickfont=dict(size=8), title_font=dict(size=9), automargin=True)
    return fig


def register_dashboard_callbacks():
    """Register callbacks for unified dashboard view."""

    @callback(
        Output("brush-selection-store", "data"),
        [Input("efficiency-timeseries", "selectedData"),
         Input("multivariate-splom", "selectedData")],
        [State("brush-selection-store", "data")],
        prevent_initial_call=True
    )
    def update_brush_selection(time_selected, splom_selected, prev_selection):
        _log_debug(
            "update_brush_selection entry",
            {
                "triggered": str(ctx.triggered_id),
                "time_selected_points": len(time_selected.get("points", [])) if time_selected else 0,
                "splom_selected_points": len(splom_selected.get("points", [])) if splom_selected else 0,
                "prev_selection_points": len(prev_selection.get("points", [])) if prev_selection else 0,
            },
            "H1"
        )
        if not ctx.triggered:
            raise PreventUpdate
        triggered = ctx.triggered_id
        selected = time_selected if triggered == "efficiency-timeseries" else splom_selected

        selection_data = _extract_selection(selected)
        _log_debug(
            "update_brush_selection parsed points",
            {"point_count": len(selection_data.get("points", [])) if selection_data else 0},
            "H1"
        )
        if selection_data and selection_data.get("points"):
            return {
                "source": triggered, 
                "points": selection_data["points"],
                "box_bounds": selection_data.get("box_bounds")
            }
        # Preserve previous selection on empty (Plotly auto-clears after selection)
        # Use clear button or double-click to explicitly clear
        if not selection_data and prev_selection:
            return prev_selection
        return None

    @callback(
        Output("brush-selection-store", "data", allow_duplicate=True),
        [Input("efficiency-timeseries", "relayoutData"),
         Input("multivariate-splom", "relayoutData"),
         Input("clear-brush-btn", "n_clicks"),
         Input("reset-btn", "n_clicks")],
        [State("brush-selection-store", "data"),
         State("dept-filter", "value"),
         State("week-slider", "value")],
        prevent_initial_call=True
    )
    def handle_selection_updates(time_relayout, splom_relayout, clear_clicks, reset_clicks, 
                                 current_selection, depts, week_range):
        if not ctx.triggered:
            raise PreventUpdate
        
        triggered = ctx.triggered_id
        
        # Clear button clicked
        if triggered == "clear-brush-btn" and clear_clicks:
            return None
        
        # Reset button clicked
        if triggered == "reset-btn" and reset_clicks:
            return None
        
        # Double-click detection (relayout with autorange)
        if triggered in ["efficiency-timeseries", "multivariate-splom"] and current_selection:
            relayout = time_relayout if triggered == "efficiency-timeseries" else splom_relayout
            if relayout and any(k.startswith("xaxis.autorange") or k.startswith("yaxis.autorange") for k in relayout.keys()):
                _log_debug("clear_selection_on_doubleclick", {"triggered": triggered}, "H6")
                return None
            
            # Check for selection box movement (shapes being dragged)
            # This handles persistent, draggable selection boxes
            if relayout and current_selection and current_selection.get("box_bounds"):
                # Look for shape movements in relayoutData
                shape_keys = [k for k in relayout.keys() if k.startswith("shapes[") and ("x0" in k or "x1" in k or "y0" in k or "y1" in k)]
                if shape_keys:
                    # Selection box shape was moved - recalculate points
                    box_bounds = {}
                    for key, value in relayout.items():
                        if key.startswith("shapes[0]."):
                            prop = key.replace("shapes[0].", "")
                            if prop in ["x0", "x1", "y0", "y1"]:
                                box_bounds[prop] = value
                    
                    if box_bounds and len(box_bounds) >= 4:
                        # Recalculate points in new box position
                        df = _filter_services(depts or SERVICES, week_range or [1, 52], False)
                        df = _attach_los(df)
                        
                        x_range = [box_bounds.get("x0"), box_bounds.get("x1")]
                        y_range = [box_bounds.get("y0"), box_bounds.get("y1")]
                        
                        if all(v is not None for v in x_range + y_range):
                            new_box_bounds = {"x": x_range, "y": y_range}
                            new_points = _calculate_points_in_box(df, new_box_bounds)
                            
                            if new_points:
                                return {
                                    "source": current_selection.get("source"),
                                    "points": new_points,
                                    "box_bounds": new_box_bounds
                                }
        
        raise PreventUpdate
    
    @callback(
        Output("clear-brush-btn", "style"),
        Input("brush-selection-store", "data")
    )
    def toggle_clear_button(selection_store):
        if selection_store and selection_store.get("points"):
            return {
                "fontSize": "10px",
                "padding": "4px 8px",
                "backgroundColor": "#e74c3c",
                "color": "white",
                "border": "none",
                "borderRadius": "4px",
                "cursor": "pointer",
                "display": "block"
            }
        return {
            "fontSize": "10px",
            "padding": "4px 8px",
            "backgroundColor": "#e74c3c",
            "color": "white",
            "border": "none",
            "borderRadius": "4px",
            "cursor": "pointer",
            "display": "none"
        }

    @callback(
        [Output("efficiency-timeseries", "figure"),
         Output("multivariate-splom", "figure"),
         Output("department-comparison", "figure"),
         Output("brush-summary", "children")],
        [Input("dept-filter", "value"),
         Input("week-slider", "value"),
         Input("hide-anomalies-toggle", "value"),
         Input("brush-selection-store", "data")]
    )
    def update_dashboard(depts, week_range, hide_anomalies_list, selection_store):
        selected_depts = depts or SERVICES
        hide_anomalies = "hide" in (hide_anomalies_list or [])

        df = _filter_services(selected_depts, week_range, hide_anomalies)
        df = _attach_los(df)
        df = df.dropna(subset=["mean_los"]).copy()
        _log_debug(
            "update_dashboard data snapshot",
            {
                "selected_depts": selected_depts,
                "week_range": week_range,
                "hide_anomalies": hide_anomalies,
                "df_rows": len(df),
                "selection_store_points": len(selection_store.get("points", [])) if selection_store else 0,
                "selection_source": selection_store.get("source") if selection_store else None,
            },
            "H2"
        )

        if df.empty:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data for selection",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, font=dict(size=10, color="#999")
            )
            empty_fig.update_layout(template="plotly_white")
            return empty_fig, empty_fig, empty_fig, "Select departments to begin brushing."

        selection_points = _selection_set(selection_store)
        if selection_points:
            source = selection_store.get("source", "selection")
            source_label = "time series" if source == "efficiency-timeseries" else "multivariate view"
            summary = f"{len(selection_points)} points selected from {source_label}. Click 'Clear Selection' or double-click chart to reset."
        else:
            summary = "Drag to select points in either chart to brush the other."

        time_fig = _build_time_series(df, selected_depts, selection_store or {})
        splom_fig = _build_splom(df, selection_store or {})
        comp_fig = _build_department_comparison(df, selection_store or {})

        return time_fig, splom_fig, comp_fig, summary
