"""
Overview Widget Callbacks
JBI100 Visualization - Group 25

Callbacks for the Overview widget (T1):
- Hover interactions
- Tooltip updates
- Histogram updates (detail zoom)
"""

from dash import callback, Output, Input, State, html
from dash.exceptions import PreventUpdate
import numpy as np

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS_SHORT
from jbi100_app.data import get_services_data
from jbi100_app.views.overview import build_tooltip_content, get_zoom_level, _hex_to_rgba

_services_df = get_services_data()

# Cache for histogram bin data (computed once per dept selection)
_HIST_CACHE = {}


def _get_cached_histogram_data(selected_depts, metric, hovered_dept=None):
    """Get or compute cached KDE data for a specific department."""
    from scipy import stats
    
    # Cache per department (or merged if no hover)
    dept_key = hovered_dept if hovered_dept else tuple(sorted(selected_depts or []))
    cache_key = (dept_key, metric)
    
    if cache_key not in _HIST_CACHE:
        # Filter by hovered department if provided
        if hovered_dept:
            filtered = _services_df[_services_df["service"] == hovered_dept]
        elif selected_depts:
            filtered = _services_df[_services_df["service"].isin(selected_depts)]
        else:
            filtered = _services_df
        
        values = filtered[metric].values
        
        # Compute KDE (extended range for tails)
        kde = stats.gaussian_kde(values)
        x_range = np.linspace(-10, 115, 250)
        y_density = kde(x_range)
        
        _HIST_CACHE[cache_key] = {
            "x_range": x_range,
            "y_density": y_density
        }
    
    return _HIST_CACHE[cache_key]


def _create_histogram_figure(kde_data, metric, highlight_value=None, hovered_dept=None):
    """Create KDE figure from cached data."""
    import plotly.graph_objects as go
    
    x_range = kde_data["x_range"]
    y_density = kde_data["y_density"]
    
    fig = go.Figure()
    
    # Use department color if hovering a specific department
    fill_color = '#ccc'
    line_color = '#ccc'
    if hovered_dept:
        dept_hex = DEPT_COLORS.get(hovered_dept, '#ccc')
        fill_color = dept_hex
        line_color = dept_hex
    
    # Fill area under curve
    fig.add_trace(go.Scatter(
        x=x_range,
        y=y_density,
        mode='lines',
        fill='tozeroy',
        line=dict(color=line_color, width=1.5),
        fillcolor=_hex_to_rgba(fill_color, 0.5),
        hoverinfo='skip'
    ))
    
    # Add highlighted region if value provided
    if highlight_value is not None:
        highlight_width = 3
        mask = (x_range >= highlight_value - highlight_width) & (x_range <= highlight_value + highlight_width)
        
        # Use darker version of department color for highlight
        if hovered_dept:
            highlight_color = DEPT_COLORS.get(hovered_dept, '#3498db')
        else:
            highlight_color = '#3498db'
        
        fig.add_trace(go.Scatter(
            x=x_range[mask],
            y=y_density[mask],
            mode='lines',
            fill='tozeroy',
            line=dict(color=highlight_color, width=2),
            fillcolor=_hex_to_rgba(highlight_color, 0.8),
            hoverinfo='skip'
        ))
    
    # Title shows metric + department (if hovered)
    base_title = "Satisfaction" if "satisfaction" in metric else "Acceptance"
    if hovered_dept:
        title_text = f"{base_title} - {DEPT_LABELS_SHORT.get(hovered_dept, hovered_dept)}"
    else:
        title_text = base_title
    
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


def register_overview_callbacks():
    """Register all overview widget callbacks."""
    
    # =========================================================================
    # HOVER -> STORE (for cross-widget linking)
    # =========================================================================
    @callback(
        Output("hovered-week-store", "data"),
        Input("overview-chart", "hoverData"),
        prevent_initial_call=True
    )
    def update_hovered_week_store(hoverData):
        """
        Update hovered-week-store when user hovers over Overview chart.
        This enables Linking & Brushing (M4_04) with other widgets.
        """
        if not hoverData or not hoverData.get("points"):
            return None
        
        point = hoverData["points"][0]
        week = round(point["x"])
        
        # Clamp week to valid range
        if week < 1 or week > 52:
            return None
        
        # Extract hovered department
        hovered_dept = None
        if "customdata" in point and point["customdata"]:
            customdata = point["customdata"]
            if isinstance(customdata, list) and len(customdata) > 0:
                hovered_dept = customdata[0]
        
        return {"week": week, "department": hovered_dept}
    
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
         State("current-week-range", "data")],
        prevent_initial_call=True
    )
    def update_quality_mini_on_hover(hovered_data, dept_store, week_range):
        """
        Update Quality mini widget on hover from Overview chart.
        
        Justification (M4_04 - Linking & Brushing):
        - Staff count shows assigned staff for hovered week per department
        - Morale shows week-specific value per department
        - Sparkline highlights hovered week with department color
        """
        from jbi100_app.views.quality import create_quality_mini_sparkline
        from jbi100_app.config import DEPT_COLORS, DEPT_LABELS_SHORT
        from jbi100_app.data import get_staff_schedule_data
        from dash import html
        
        _staff_schedule_df = get_staff_schedule_data()
        
        # Styles
        default_morale_style = {"fontSize": "13px", "fontWeight": "700", "color": "#3498db"}
        hover_morale_style = {"fontSize": "13px", "fontWeight": "700", "color": "#e67e22"}
        
        if not week_range:
            week_range = (1, 52)
        else:
            week_range = tuple(week_range)
        
        if not dept_store:
            import plotly.graph_objects as go
            empty_fig = go.Figure()
            empty_fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=80)
            return "--", " staff", [], "--", default_morale_style, " morale", [], empty_fig
        
        # Get settings from store
        selected_depts = dept_store.get("selected_depts", [])
        dept_info = dept_store.get("dept_info", [])
        avg_morale = dept_store.get("avg_morale", 0)
        total_staff = dept_store.get("total_staff", 0)
        hide_anomalies = dept_store.get("hide_anomalies", False)
        
        # Helper to build breakdown spans
        def build_breakdown(values, dept_info_list, key):
            if len(dept_info_list) <= 1:
                return []
            return [
                html.Span([
                    html.Span(f"{values.get(info['dept'], info.get(key, 0)):.0f}" if isinstance(values.get(info['dept'], info.get(key, 0)), float) else f"{values.get(info['dept'], info.get(key, 0))}", 
                              style={"color": info['color'], "fontWeight": "600", "fontSize": "9px"}),
                    html.Span(f" {info['label']} ", style={"fontSize": "7px", "color": "#95a5a6"})
                ]) for info in dept_info_list
            ]
        
        # Default: no hover - show totals with per-dept breakdown
        if not hovered_data or not hovered_data.get("week"):
            sparkline_fig = create_quality_mini_sparkline(
                _services_df, selected_depts, week_range, 
                highlighted_week=None, hide_anomalies=hide_anomalies
            )
            
            # Build default breakdowns from stored dept_info
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
        
        # Hovering: show week-specific data per department
        week = hovered_data["week"]
        hovered_dept = hovered_data.get("department")
        highlight_color = DEPT_COLORS.get(hovered_dept, "#3498db") if hovered_dept else "#3498db"
        
        # Get per-department data for this week
        week_staff_total = 0
        week_staff_per_dept = {}
        week_morale_per_dept = {}
        
        for dept in selected_depts:
            # Staff assigned this week
            staff_count = _staff_schedule_df[
                (_staff_schedule_df['service'] == dept) &
                (_staff_schedule_df['week'] == week) &
                (_staff_schedule_df['present'] == 1)
            ]['staff_id'].nunique()
            week_staff_per_dept[dept] = staff_count
            week_staff_total += staff_count
            
            # Morale this week
            week_row = _services_df[
                (_services_df['service'] == dept) & 
                (_services_df['week'] == week)
            ]
            if not week_row.empty:
                week_morale_per_dept[dept] = week_row['staff_morale'].values[0]
            else:
                week_morale_per_dept[dept] = 0
        
        # Build week-specific breakdowns
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
        
        # Create sparkline with highlighted week
        sparkline_fig = create_quality_mini_sparkline(
            _services_df, selected_depts, week_range, 
            highlighted_week=week, hide_anomalies=hide_anomalies,
            highlight_color=highlight_color
        )
        
        # Get first dept's morale for main display - use AVERAGE across all depts
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
    
    @callback(
        [Output("tooltip-content", "children"),
         Output("hover-highlight", "style")],
        [Input("overview-chart", "hoverData")],
        [State("week-data-store", "data"), 
         State("dept-filter", "value"), 
         State("current-week-range", "data")],
        prevent_initial_call=True
    )
    def update_tooltip_and_highlight(hoverData, weekData, selectedDepts, weekRange):
        """Update tooltip and vertical line indicator on hover."""
        base_style = {
            "position": "absolute",
            "top": "10px", "bottom": "30px",
            "width": "4px",  # Thicker line for visibility
            "pointerEvents": "none",
            "borderRadius": "2px",
            "transition": "all 0.1s ease"  # Smooth transition
        }
        default_tooltip = [
            html.Div("Hover over", style={"color": "#999", "textAlign": "center"}),
            html.Div("the chart", style={"color": "#999", "textAlign": "center"})
        ]
        
        if not hoverData or not hoverData.get("points"):
            return default_tooltip, {**base_style, "display": "none", "left": "40px", "backgroundColor": "rgba(52, 152, 219, 0.6)"}
        
        point = hoverData["points"][0]
        week = round(point["x"])
        
        # Extract hovered department from customdata
        hovered_dept = None
        if "customdata" in point and point["customdata"]:
            customdata = point["customdata"]
            if isinstance(customdata, list) and len(customdata) > 0:
                hovered_dept = customdata[0]
        
        # Clamp week to valid range (1-52)
        if week < 1 or week > 52:
            return default_tooltip, {**base_style, "display": "none", "left": "40px", "backgroundColor": "rgba(52, 152, 219, 0.6)"}
        
        # Get center position from bbox
        bbox = point.get("bbox", {})
        x0 = bbox.get("x0", 40)
        x1 = bbox.get("x1", x0 + 10)
        xCenter = (x0 + x1) / 2  # Center of the point
        
        tooltip_children = build_tooltip_content(
            week, weekData, selectedDepts or [], _services_df, weekRange
        )
        
        # Use department color for highlight line if hovered
        line_color = "rgba(52, 152, 219, 0.7)"
        if hovered_dept:
            dept_hex = DEPT_COLORS.get(hovered_dept)
            if dept_hex:
                # Convert hex to rgba
                line_color = _hex_to_rgba(dept_hex, 0.8)
        
        # Position line at center of hovered point
        highlight_style = {
            **base_style, 
            "display": "block", 
            "left": f"{xCenter - 2}px",  # Center the 4px line
            "backgroundColor": line_color
        }
        return tooltip_children, highlight_style
    
    @callback(
        [Output("hist-satisfaction", "figure"),
         Output("hist-acceptance", "figure")],
        [Input("overview-chart", "hoverData")],
        [State("week-data-store", "data"), 
         State("dept-filter", "value"), 
         State("current-week-range", "data")],
        prevent_initial_call=True
    )
    def update_histograms(hoverData, weekData, selectedDepts, weekRange):
        """Update KDE to show hovered department's distribution (details-on-demand)."""
        zoom_level = get_zoom_level(weekRange)
        if zoom_level not in ["detail", "quarter"]:
            raise PreventUpdate
        
        # Detect which department is being hovered from customdata
        hovered_dept = None
        if hoverData and hoverData.get("points"):
            point = hoverData["points"][0]
            # Extract department from customdata [dept, dept_idx]
            if "customdata" in point and point["customdata"]:
                customdata = point["customdata"]
                if isinstance(customdata, list) and len(customdata) > 0:
                    hovered_dept = customdata[0]  # First element is dept name
        
        # Get KDE data for hovered department (or all if no hover)
        sat_hist_data = _get_cached_histogram_data(selectedDepts, "patient_satisfaction", hovered_dept)
        acc_hist_data = _get_cached_histogram_data(selectedDepts, "acceptance_rate", hovered_dept)
        
        if not hoverData or not hoverData.get("points"):
            return (
                _create_histogram_figure(sat_hist_data, "patient_satisfaction", None, hovered_dept),
                _create_histogram_figure(acc_hist_data, "acceptance_rate", None, hovered_dept)
            )
        
        point = hoverData["points"][0]
        week = round(point["x"])
        
        # Clamp week to valid range (1-52)
        if week < 1 or week > 52:
            return (
                _create_histogram_figure(sat_hist_data, "patient_satisfaction", None, hovered_dept),
                _create_histogram_figure(acc_hist_data, "acceptance_rate", None, hovered_dept)
            )
        
        # Get value for the hovered department only
        week_data_for_hover = weekData.get(str(week), {})
        highlight_sat = None
        highlight_acc = None
        
        if hovered_dept:
            dept_data = week_data_for_hover.get(hovered_dept)
            if dept_data:
                highlight_sat = dept_data.get("satisfaction")
                highlight_acc = dept_data.get("acceptance")
        
        return (
            _create_histogram_figure(sat_hist_data, "patient_satisfaction", highlight_sat, hovered_dept),
            _create_histogram_figure(acc_hist_data, "acceptance_rate", highlight_acc, hovered_dept)
        )
