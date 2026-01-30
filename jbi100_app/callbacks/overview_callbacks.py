"""
Overview Widget Callbacks
JBI100 Visualization - Group 25

BIDIRECTIONAL LINKING:
- Line chart zoom → current-week-range → PCP constraintrange
- PCP week brush → current-week-range → Line chart x-axis
- Semantic zoom: KDE histograms at detail/quarter level
"""

from dash import callback, Output, Input, State, html
from dash import no_update, ctx
from dash.exceptions import PreventUpdate
import numpy as np
import plotly.graph_objects as go

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS_SHORT
from jbi100_app.data import get_services_data
from jbi100_app.views.overview import (
    build_tooltip_content, get_zoom_level, _hex_to_rgba, create_pcp_figure,
    create_overview_charts
)

_services_df = get_services_data()
_HIST_CACHE = {}


def _extract_xrange_from_relayout(relayoutData):
    """
    Extract x-axis range from relayoutData.
    
    FIXED: Handles shared x-axis subplots where Plotly may emit:
    - xaxis.range or xaxis2.range (direct arrays)
    - xaxis.range[0] and xaxis.range[1] (separate keys)
    - xaxis.autorange or xaxis2.autorange (reset on double-click)
    """
    if not relayoutData or not isinstance(relayoutData, dict):
        return None

    # Check for autorange (reset/double-click) on ANY x-axis
    for key in relayoutData.keys():
        if "xaxis" in key and "autorange" in key:
            val = relayoutData[key]
            if val == True:
                return ("autorange", "autorange")

    # Check direct range arrays: xaxis.range or xaxis2.range
    for ax in ("xaxis", "xaxis2"):
        key = f"{ax}.range"
        if key in relayoutData:
            rng = relayoutData[key]
            if isinstance(rng, (list, tuple)) and len(rng) == 2:
                return (rng[0], rng[1])

    # Check separate keys: xaxis.range[0], xaxis.range[1], xaxis2.range[0], xaxis2.range[1]
    for ax in ("xaxis", "xaxis2"):
        k0 = f"{ax}.range[0]"
        k1 = f"{ax}.range[1]"
        if k0 in relayoutData and k1 in relayoutData:
            return (relayoutData[k0], relayoutData[k1])

    return None


def _clamp_week_range(xmin, xmax):
    """Clamp to valid week range."""
    try:
        wmin = int(round(float(xmin)))
        wmax = int(round(float(xmax)))
    except Exception:
        return None
    if wmin > wmax:
        wmin, wmax = wmax, wmin
    wmin = max(1, wmin)
    wmax = min(52, wmax)
    return [wmin, wmax] if wmin <= wmax else None


def _ranges_equal(r1, r2):
    """Check if two week ranges are effectively equal."""
    if r1 is None or r2 is None:
        return r1 is None and r2 is None
    return abs(r1[0] - r2[0]) < 0.5 and abs(r1[1] - r2[1]) < 0.5


def _get_cached_histogram_data(selected_depts, metric, hovered_dept=None):
    """Get or compute cached KDE data."""
    from scipy import stats
    
    dept_key = hovered_dept if hovered_dept else tuple(sorted(selected_depts or []))
    cache_key = (dept_key, metric)
    
    if cache_key not in _HIST_CACHE:
        if hovered_dept:
            filtered = _services_df[_services_df["service"] == hovered_dept]
        elif selected_depts:
            filtered = _services_df[_services_df["service"].isin(selected_depts)]
        else:
            filtered = _services_df
        
        values = filtered[metric].values
        kde = stats.gaussian_kde(values)
        x_range = np.linspace(-10, 115, 250)
        y_density = kde(x_range)
        _HIST_CACHE[cache_key] = {"x_range": x_range, "y_density": y_density}
    
    return _HIST_CACHE[cache_key]


def _create_histogram_figure(kde_data, metric, highlight_value=None, hovered_dept=None):
    """Create KDE figure from cached data."""
    x_range = kde_data["x_range"]
    y_density = kde_data["y_density"]
    
    fig = go.Figure()
    
    fill_color = DEPT_COLORS.get(hovered_dept, '#ccc') if hovered_dept else '#ccc'
    
    fig.add_trace(go.Scatter(
        x=x_range, y=y_density, mode='lines', fill='tozeroy',
        line=dict(color=fill_color, width=1.5),
        fillcolor=_hex_to_rgba(fill_color, 0.5),
        hoverinfo='skip'
    ))
    
    if highlight_value is not None:
        mask = (x_range >= highlight_value - 3) & (x_range <= highlight_value + 3)
        highlight_color = DEPT_COLORS.get(hovered_dept, '#3498db') if hovered_dept else '#3498db'
        fig.add_trace(go.Scatter(
            x=x_range[mask], y=y_density[mask], mode='lines', fill='tozeroy',
            line=dict(color=highlight_color, width=2),
            fillcolor=_hex_to_rgba(highlight_color, 0.8),
            hoverinfo='skip'
        ))
    
    base_title = "Satisfaction" if "satisfaction" in metric else "Acceptance"
    title_text = f"{base_title} - {DEPT_LABELS_SHORT.get(hovered_dept, hovered_dept)}" if hovered_dept else base_title
    
    fig.update_layout(
        height=175,
        margin=dict(l=5, r=5, t=20, b=20),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        title=dict(text=title_text, font=dict(size=9, color="#666"), x=0.5, y=0.95),
        xaxis=dict(range=[-10, 115], tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=7), showgrid=False),
        yaxis=dict(showticklabels=False, showgrid=False),
        showlegend=False
    )
    
    return fig


def _parse_pcp_week_constraint(restyleData):
    """Extract week constraint from PCP restyleData."""
    if not restyleData or not isinstance(restyleData, (list, tuple)) or len(restyleData) == 0:
        return None
    
    payload = restyleData[0]
    if not isinstance(payload, dict):
        return None

    for k, v in payload.items():
        if "dimensions[0]" in k and "constraintrange" in k:
            if v is None:
                return "clear"
            if isinstance(v, list):
                if len(v) == 0:
                    return "clear"
                if len(v) == 2 and not isinstance(v[0], (list, tuple)):
                    try:
                        wmin = max(1, int(round(v[0])))
                        wmax = min(52, int(round(v[1])))
                        if wmin <= wmax:
                            return [wmin, wmax]
                    except:
                        pass
                elif len(v) > 0 and isinstance(v[0], (list, tuple)) and len(v[0]) >= 2:
                    try:
                        wmin = max(1, int(round(v[0][0])))
                        wmax = min(52, int(round(v[0][1])))
                        if wmin <= wmax:
                            return [wmin, wmax]
                    except:
                        pass
    return None


def register_overview_callbacks():
    """Register all overview callbacks."""

    # =========================================================================
    # 0) Overview line chart figure (unified layout: no expanded widget)
    # =========================================================================
    @callback(
        Output("overview-chart", "figure"),
        [Input("dept-filter", "value"),
         Input("week-slider", "value"),
         Input("current-week-range", "data"),
         Input("show-events-toggle", "value"),
         Input("hide-anomalies-toggle", "value"),
         Input("hovered-week-store", "data")],
        prevent_initial_call=False,
    )
    def update_overview_chart(depts, week_slider, week_range_data, show_events_list, hide_anomalies_list, hovered_store):
        """Build line chart figure; filter by week range; highlight hovered week."""
        week_range = week_range_data or week_slider or [1, 52]
        week_range = list(week_range) if week_range else [1, 52]
        selected_depts = depts or ["emergency"]
        show_events = "show" in (show_events_list or [])
        hide_anomalies = "hide" in (hide_anomalies_list or [])
        w0, w1 = int(week_range[0]), int(week_range[1])
        df = _services_df[(_services_df["week"] >= w0) & (_services_df["week"] <= w1)].copy()
        if selected_depts:
            df = df[df["service"].isin(selected_depts)].copy()
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
            fig.update_layout(template="plotly_white")
            return fig
        fig, _ = create_overview_charts(df, selected_depts, (w0, w1), show_events, hide_anomalies)
        hovered_week = hovered_store.get("week") if isinstance(hovered_store, dict) else None
        if hovered_week is not None and w0 <= hovered_week <= w1:
            fig.add_vline(x=hovered_week, line_dash="solid", line_color="rgba(52, 152, 219, 0.8)",
                          line_width=2, row=1, col=1)
            fig.add_vline(x=hovered_week, line_dash="solid", line_color="rgba(52, 152, 219, 0.8)",
                          line_width=2, row=2, col=1)
        return fig

    # =========================================================================
    # 1) Slider change → current-week-range
    # =========================================================================
    @callback(
        Output("current-week-range", "data", allow_duplicate=True),
        Input("week-slider", "value"),
        prevent_initial_call=True
    )
    def slider_to_range(slider_value):
        return list(slider_value) if slider_value else [1, 52]

    # =========================================================================
    # 2) Line chart zoom/reset → current-week-range (FIXED)
    # =========================================================================
    @callback(
        Output("current-week-range", "data", allow_duplicate=True),
        Input("overview-chart", "relayoutData"),
        [State("current-week-range", "data"),
         State("week-slider", "value")],
        prevent_initial_call=True
    )
    def linechart_zoom_to_range(relayoutData, current_range, slider_value):
        """FIXED: Now properly extracts range from shared x-axis subplots."""
        xr = _extract_xrange_from_relayout(relayoutData)
        if xr is None:
            raise PreventUpdate

        if xr[0] == "autorange":
            new_range = list(slider_value) if slider_value else [1, 52]
        else:
            new_range = _clamp_week_range(xr[0], xr[1])
            if not new_range:
                raise PreventUpdate
        
        if _ranges_equal(new_range, current_range):
            raise PreventUpdate
            
        return new_range

    # =========================================================================
    # 3) PCP week brush → current-week-range
    # =========================================================================
    @callback(
        Output("current-week-range", "data", allow_duplicate=True),
        Input("pcp-chart", "restyleData"),
        [State("current-week-range", "data"),
         State("week-slider", "value")],
        prevent_initial_call=True
    )
    def pcp_brush_to_range(restyleData, current_range, slider_value):
        result = _parse_pcp_week_constraint(restyleData)
        
        if result is None:
            raise PreventUpdate
        
        if result == "clear":
            new_range = list(slider_value) if slider_value else [1, 52]
        else:
            new_range = result
        
        if _ranges_equal(new_range, current_range):
            raise PreventUpdate
            
        return new_range

    # =========================================================================
    # 4) current-week-range → Update PCP only (line chart has its own update)
    # =========================================================================
    @callback(
        Output("pcp-chart", "figure"),
        [Input("current-week-range", "data"),
         Input("dept-filter", "value")],
        State("hovered-week-store", "data"),
        prevent_initial_call=False,
    )
    def update_pcp_on_range(week_range, selected_depts, hovered_store):
        """PCP always visible in unified layout; filter data by week range so it renders clearly."""
        week_range = week_range or [1, 52]
        selected_depts = selected_depts or ["emergency"]
        hovered_week = hovered_store.get("week") if isinstance(hovered_store, dict) else None
        w0, w1 = int(week_range[0]), int(week_range[1])
        df = _services_df[(_services_df["week"] >= w0) & (_services_df["week"] <= w1)].copy()
        if selected_depts:
            df = df[df["service"].isin(selected_depts)].copy()
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
            fig.update_layout(template="plotly_white", height=400)
            return fig
        return create_pcp_figure(df, selected_depts, (w0, w1), hovered_week=hovered_week)

    # =========================================================================
    # 4b) Double-click overview chart → clear hovered week
    # =========================================================================
    @callback(
        Output("hovered-week-store", "data", allow_duplicate=True),
        Input("overview-chart", "relayoutData"),
        State("hovered-week-store", "data"),
        prevent_initial_call=True
    )
    def clear_hovered_week_on_doubleclick(relayoutData, current_hovered):
        if not relayoutData or not isinstance(relayoutData, dict):
            raise PreventUpdate
        if any(k for k in relayoutData if "autorange" in k and relayoutData.get(k) is True):
            return None
        raise PreventUpdate

    # =========================================================================
    # 4c) Network week slider → hovered-week-store (so network updates without scrolling to line chart)
    # =========================================================================
    @callback(
        Output("hovered-week-store", "data", allow_duplicate=True),
        Input("quality-week-slider", "value"),
        prevent_initial_call=True
    )
    def sync_hovered_from_slider(slider_week):
        if slider_week is None:
            return None
        return {"week": int(slider_week)}

    # =========================================================================
    # 5) Hover → hovered-week-store
    # =========================================================================
    @callback(
        Output("hovered-week-store", "data"),
        Input("overview-chart", "hoverData"),
        prevent_initial_call=True
    )
    def update_hovered_week(hoverData):
        if not hoverData or not hoverData.get("points"):
            return None
        point = hoverData["points"][0]
        week = round(point.get("x", 0))
        if week < 1 or week > 52:
            return None
        hovered_dept = None
        if "customdata" in point and point["customdata"]:
            cd = point["customdata"]
            if isinstance(cd, list) and len(cd) > 0:
                hovered_dept = cd[0]
        return {"week": week, "department": hovered_dept}

    # =========================================================================
    # 6) Tooltip + highlight line
    # =========================================================================
    @callback(
        [Output("tooltip-content", "children"),
         Output("hover-highlight", "style")],
        Input("overview-chart", "hoverData"),
        [State("week-data-store", "data"),
         State("dept-filter", "value"),
         State("current-week-range", "data")],
        prevent_initial_call=True
    )
    def update_tooltip(hoverData, weekData, selectedDepts, weekRange):
        base_style = {
            "position": "absolute", "top": "10px", "bottom": "30px",
            "width": "4px", "pointerEvents": "none", "borderRadius": "2px",
            "transition": "all 0.1s ease"
        }
        default_tooltip = [
            html.Div("Hover over", style={"color": "#999", "textAlign": "center"}),
            html.Div("the chart", style={"color": "#999", "textAlign": "center"})
        ]

        if not hoverData or not hoverData.get("points"):
            return default_tooltip, {**base_style, "display": "none", "left": "40px", "backgroundColor": "rgba(52, 152, 219, 0.6)"}

        point = hoverData["points"][0]
        week = round(point.get("x", 0))
        hovered_dept = None
        if "customdata" in point and point["customdata"]:
            cd = point["customdata"]
            if isinstance(cd, list) and len(cd) > 0:
                hovered_dept = cd[0]

        if week < 1 or week > 52:
            return default_tooltip, {**base_style, "display": "none", "left": "40px", "backgroundColor": "rgba(52, 152, 219, 0.6)"}

        bbox = point.get("bbox", {})
        xCenter = (bbox.get("x0", 40) + bbox.get("x1", 50)) / 2

        tooltip_children = build_tooltip_content(week, weekData, selectedDepts or [], _services_df, weekRange)

        line_color = _hex_to_rgba(DEPT_COLORS.get(hovered_dept, "#3498db"), 0.8) if hovered_dept else "rgba(52, 152, 219, 0.7)"

        return tooltip_children, {**base_style, "display": "block", "left": f"{xCenter - 2}px", "backgroundColor": line_color}

    # =========================================================================
    # 7) KDE histograms (semantic zoom - detail/quarter only)
    # =========================================================================
    @callback(
        [Output("hist-satisfaction", "figure"),
         Output("hist-acceptance", "figure")],
        Input("overview-chart", "hoverData"),
        [State("week-data-store", "data"),
         State("dept-filter", "value"),
         State("current-week-range", "data")],
        prevent_initial_call=True
    )
    def update_histograms(hoverData, weekData, selectedDepts, weekRange):
        zoom_level = get_zoom_level(weekRange)
        if zoom_level not in ["detail", "quarter"]:
            raise PreventUpdate

        hovered_dept = None
        if hoverData and hoverData.get("points"):
            point = hoverData["points"][0]
            if "customdata" in point and point["customdata"]:
                cd = point["customdata"]
                if isinstance(cd, list) and len(cd) > 0:
                    hovered_dept = cd[0]

        sat_data = _get_cached_histogram_data(selectedDepts, "patient_satisfaction", hovered_dept)
        acc_data = _get_cached_histogram_data(selectedDepts, "acceptance_rate", hovered_dept)

        highlight_sat, highlight_acc = None, None
        if hoverData and hoverData.get("points"):
            week = round(hoverData["points"][0].get("x", 0))
            if 1 <= week <= 52 and hovered_dept:
                week_info = weekData.get(str(week), {}).get(hovered_dept, {})
                highlight_sat = week_info.get("satisfaction")
                highlight_acc = week_info.get("acceptance")

        return (
            _create_histogram_figure(sat_data, "patient_satisfaction", highlight_sat, hovered_dept),
            _create_histogram_figure(acc_data, "acceptance_rate", highlight_acc, hovered_dept)
        )
    
    # =========================================================================
    # 8) Quality mini widget hover updates (from original callbacks)
    # =========================================================================
    @callback(
        [Output("quality-mini-staff-total", "children"),
         Output("quality-mini-staff-label", "children"),
         Output("quality-mini-staff-breakdown", "children"),
         Output("quality-mini-morale-value", "children"),
         Output("quality-mini-morale-value", "style"),
         Output("quality-mini-morale-label", "children"),
         Output("quality-mini-morale-breakdown", "children"),
         Output("quality-mini-sparkline", "figure")],
        [Input("hovered-week-store", "data")],
        [State("quality-mini-dept-store", "data"),
         State("visible-week-range", "data")],
        prevent_initial_call=True
    )
    def update_quality_mini_on_hover(hovered_data, dept_store, week_range):
        """Update Quality mini widget on hover from Overview chart."""
        from jbi100_app.views.quality import create_quality_mini_sparkline
        from jbi100_app.data import get_staff_schedule_data
        
        _staff_schedule_df = get_staff_schedule_data()
        
        default_morale_style = {"fontSize": "13px", "fontWeight": "700", "color": "#3498db"}
        hover_morale_style = {"fontSize": "13px", "fontWeight": "700", "color": "#e67e22"}
        
        if not week_range:
            week_range = (1, 52)
        else:
            week_range = tuple(week_range)
        
        if not dept_store:
            empty_fig = go.Figure()
            empty_fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=80)
            return "--", " staff", [], "--", default_morale_style, " morale", [], empty_fig
        
        selected_depts = dept_store.get("selected_depts", [])
        dept_info = dept_store.get("dept_info", [])
        avg_morale = dept_store.get("avg_morale", 0)
        total_staff = dept_store.get("total_staff", 0)
        hide_anomalies = dept_store.get("hide_anomalies", False)
        
        if not hovered_data or not hovered_data.get("week"):
            sparkline_fig = create_quality_mini_sparkline(
                _services_df, selected_depts, week_range, 
                highlighted_week=None, hide_anomalies=hide_anomalies
            )
            
            staff_breakdown = [
                html.Span([
                    html.Span(f"{info['staff']}", style={"color": info['color'], "fontWeight": "600", "fontSize": "9px"}),
                    html.Span(f" {info['label']} ", style={"fontSize": "7px", "color": "#95a5a6"})
                ]) for info in dept_info
            ] if len(dept_info) > 1 else []
            
            morale_breakdown = [
                html.Span([
                    html.Span(f"{info['morale']:.0f}", style={"color": info['color'], "fontWeight": "600", "fontSize": "9px"}),
                    html.Span(f" {info['label']} ", style={"fontSize": "7px", "color": "#95a5a6"})
                ]) for info in dept_info
            ] if len(dept_info) > 1 else []
            
            return (
                f"{total_staff}", " staff", staff_breakdown,
                f"{avg_morale:.0f}", default_morale_style, " avg morale", morale_breakdown,
                sparkline_fig
            )
        
        week = hovered_data["week"]
        hovered_dept = hovered_data.get("department")
        highlight_color = DEPT_COLORS.get(hovered_dept, "#3498db") if hovered_dept else "#3498db"
        
        week_staff_total = 0
        week_staff_per_dept = {}
        week_morale_per_dept = {}
        
        for dept in selected_depts:
            staff_count = _staff_schedule_df[
                (_staff_schedule_df['service'] == dept) &
                (_staff_schedule_df['week'] == week) &
                (_staff_schedule_df['present'] == 1)
            ]['staff_id'].nunique()
            week_staff_per_dept[dept] = staff_count
            week_staff_total += staff_count
            
            week_row = _services_df[
                (_services_df['service'] == dept) & 
                (_services_df['week'] == week)
            ]
            if not week_row.empty:
                week_morale_per_dept[dept] = week_row['staff_morale'].values[0]
            else:
                week_morale_per_dept[dept] = 0
        
        staff_breakdown = [
            html.Span([
                html.Span(f"{week_staff_per_dept.get(info['dept'], 0)}", 
                          style={"color": info['color'], "fontWeight": "600", "fontSize": "9px"}),
                html.Span(f" {info['label']} ", style={"fontSize": "7px", "color": "#95a5a6"})
            ]) for info in dept_info
        ] if len(dept_info) > 1 else []
        
        morale_breakdown = [
            html.Span([
                html.Span(f"{week_morale_per_dept.get(info['dept'], 0):.0f}", 
                          style={"color": info['color'], "fontWeight": "600", "fontSize": "9px"}),
                html.Span(f" {info['label']} ", style={"fontSize": "7px", "color": "#95a5a6"})
            ]) for info in dept_info
        ] if len(dept_info) > 1 else []
        
        sparkline_fig = create_quality_mini_sparkline(
            _services_df, selected_depts, week_range, 
            highlighted_week=week, hide_anomalies=hide_anomalies,
            highlight_color=highlight_color
        )
        
        avg_week_morale = sum(week_morale_per_dept.values()) / len(week_morale_per_dept) if week_morale_per_dept else avg_morale
        
        return (
            f"{week_staff_total}", f" W{week}", staff_breakdown,
            f"{avg_week_morale:.0f}", hover_morale_style, f" W{week} morale", morale_breakdown,
            sparkline_fig
        )
