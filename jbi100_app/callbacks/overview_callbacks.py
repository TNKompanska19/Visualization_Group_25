"""
Overview Widget Callbacks
JBI100 Visualization - Group 25

Callbacks for the Overview widget (T1):
- Hover interactions → update hovered-week-store
- Tooltip + hover line (bbox-based for direct hover; percentage for cross-widget)
"""

from dash import callback, Output, Input, State, html, ctx, no_update
from dash.exceptions import PreventUpdate
import numpy as np

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS_SHORT
from jbi100_app.data import get_services_data
from jbi100_app.views.overview import build_tooltip_content, get_zoom_level, _hex_to_rgba

_services_df = get_services_data()


def register_overview_callbacks():
    """Register all overview widget callbacks."""
    
    # =========================================================================
    # VIEWPORT TRACKING (for pan/zoom sync)
    # =========================================================================
    @callback(
        Output("visible-week-range", "data"),
        Input("overview-chart", "relayoutData"),
        State("current-week-range", "data"),
        prevent_initial_call=True
    )
    def track_viewport_pan(relayoutData, slider_range):
        """Track viewport changes from chart pan/zoom."""
        if not relayoutData:
            return slider_range or [1, 52]
        
        if 'xaxis.range[0]' in relayoutData and 'xaxis.range[1]' in relayoutData:
            xMin = relayoutData['xaxis.range[0]']
            xMax = relayoutData['xaxis.range[1]']
            return [max(1, round(xMin)), min(52, round(xMax))]
        elif 'xaxis.range' in relayoutData:
            rng = relayoutData['xaxis.range']
            if isinstance(rng, list) and len(rng) == 2:
                return [max(1, round(rng[0])), min(52, round(rng[1]))]
        elif relayoutData.get('xaxis.autorange'):
            return slider_range or [1, 52]
        
        return no_update
    
    # =========================================================================
    # HOVER -> STORE (for cross-widget linking)
    # =========================================================================
    @callback(
        Output("hovered-week-store", "data"),
        Input("overview-chart", "hoverData"),
        prevent_initial_call=True
    )
    def update_hovered_week_store(hoverData):
        """Update hovered-week-store when user hovers over Overview chart."""
        if not hoverData or not hoverData.get("points"):
            return None
        
        point = hoverData["points"][0]
        week = int(round(point.get("x", 0)))
        
        if week < 1 or week > 52:
            return None
        
        hovered_dept = None
        if "customdata" in point and point["customdata"]:
            customdata = point["customdata"]
            if isinstance(customdata, list) and len(customdata) > 0:
                hovered_dept = customdata[0]
        
        return {"week": week, "department": hovered_dept}
    
    # =========================================================================
    # TOOLTIP AND HOVER LINE (working version: overview hover only, bbox-based)
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
    def update_tooltip_and_highlight(hoverData, weekData, selectedDepts, weekRange):
        base_style = {
            "position": "absolute",
            "top": "10px",
            "bottom": "30px",
            "width": "4px",
            "pointerEvents": "none",
            "borderRadius": "2px",
            "transition": "all 0.1s ease"
        }
        default_tooltip = [
            html.Div("Hover over", style={"color": "#999", "textAlign": "center"}),
            html.Div("the chart", style={"color": "#999", "textAlign": "center"})
        ]
        hidden_style = {**base_style, "display": "none", "left": "40px", "backgroundColor": "rgba(52, 152, 219, 0.6)"}
        week_range = weekRange or [1, 52]

        if not hoverData or not hoverData.get("points"):
            return default_tooltip, hidden_style

        point = hoverData["points"][0]
        week = int(round(point["x"]))
        hovered_dept = None
        if "customdata" in point and point["customdata"]:
            cd = point["customdata"]
            if isinstance(cd, list) and len(cd) > 0:
                hovered_dept = cd[0]
        if week < 1 or week > 52:
            return default_tooltip, hidden_style

        bbox = point.get("bbox", {})
        x0 = bbox.get("x0", 40)
        x1 = bbox.get("x1", x0 + 10)
        xCenter = (x0 + x1) / 2

        tooltip_children = build_tooltip_content(
            week, weekData or {}, selectedDepts or [], _services_df, week_range
        )
        line_color = "rgba(52, 152, 219, 0.7)"
        if hovered_dept and DEPT_COLORS.get(hovered_dept):
            line_color = _hex_to_rgba(DEPT_COLORS[hovered_dept], 0.8)

        return tooltip_children, {
            **base_style,
            "display": "block",
            "left": f"{xCenter - 2}px",
            "backgroundColor": line_color
        }
    
    # =========================================================================
    # UPDATE QUALITY MINI KPIs on hover
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
        import plotly.graph_objects as go
        from jbi100_app.views.quality import create_quality_mini_sparkline
        from jbi100_app.data import get_staff_schedule_data
        
        _staff_schedule_df = get_staff_schedule_data()
        
        default_morale_style = {"fontSize": "13px", "fontWeight": "700", "color": "#3498db"}
        hover_morale_style = {"fontSize": "13px", "fontWeight": "700", "color": "#e67e22"}
        
        if not week_range:
            week_range = (1, 52)
        else:
            week_range = tuple(week_range)
        
        empty_fig = go.Figure()
        empty_fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=80)
        
        if not dept_store:
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
                f"{total_staff}",
                " staff",
                staff_breakdown,
                f"{avg_morale:.0f}",
                default_morale_style,
                " avg morale",
                morale_breakdown,
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
            f"{week_staff_total}",
            f" W{week}",
            staff_breakdown,
            f"{avg_week_morale:.0f}",
            hover_morale_style,
            f" W{week} morale",
            morale_breakdown,
            sparkline_fig
        )
