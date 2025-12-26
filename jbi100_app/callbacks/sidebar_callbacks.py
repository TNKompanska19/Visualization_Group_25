"""
Sidebar Callbacks
JBI100 Visualization - Group 25

Callbacks for sidebar interactions:
- Toggle collapse/expand
- Department quick select
- Time period buttons
- Week range synchronization
- Zoom level indicator
"""

from dash import callback, Output, Input, State, ctx

from jbi100_app.views.menu import get_sidebar_collapsed_style, get_sidebar_expanded_style
from jbi100_app.views.overview import get_zoom_level


def register_sidebar_callbacks():
    """Register all sidebar-related callbacks."""
    
    # =========================================================================
    # SIDEBAR TOGGLE
    # =========================================================================
    @callback(
        [Output("sidebar", "style"),
         Output("sidebar-content", "style"),
         Output("sidebar-title", "style"),
         Output("toggle-sidebar", "style")],
        Input("toggle-sidebar", "n_clicks")
    )
    def toggle_sidebar(n_clicks):
        """Toggle sidebar between collapsed and expanded states."""
        btn_base = {
            "border": "none",
            "color": "white",
            "cursor": "pointer",
            "borderRadius": "8px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center"
        }
        
        if n_clicks and n_clicks % 2 == 1:
            # Collapsed state
            return (
                get_sidebar_collapsed_style(),
                {"display": "none"},
                {"display": "none"},
                {**btn_base, "background": "#3498db", "width": "36px", "height": "36px", "padding": "0", "fontSize": "16px"}
            )
        
        # Expanded state
        return (
            get_sidebar_expanded_style(),
            {"padding": "15px", "overflowY": "auto"},
            {"display": "inline"},
            {**btn_base, "background": "#3498db", "width": "100%", "padding": "10px 12px", "fontSize": "13px", "gap": "6px"}
        )
    
    # =========================================================================
    # DEPARTMENT QUICK SELECT
    # =========================================================================
    @callback(
        Output("dept-filter", "value"),
        [Input("select-all-btn", "n_clicks"), Input("reset-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def quick_select_depts(all_clicks, reset_clicks):
        """Handle department quick select buttons."""
        if ctx.triggered_id == "select-all-btn":
            return ["emergency", "surgery", "general_medicine", "ICU"]
        return ["emergency"]
    
    # =========================================================================
    # TIME PERIOD BUTTONS
    # =========================================================================
    @callback(
        Output("week-slider", "value"),
        [Input("q1-btn", "n_clicks"), Input("q2-btn", "n_clicks"),
         Input("q3-btn", "n_clicks"), Input("q4-btn", "n_clicks"),
         Input("h1-btn", "n_clicks"), Input("h2-btn", "n_clicks"),
         Input("reset-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def set_time_period(q1, q2, q3, q4, h1, h2, reset):
        """Handle time period quick select buttons."""
        periods = {
            "q1-btn": [1, 13],
            "q2-btn": [14, 26],
            "q3-btn": [27, 39],
            "q4-btn": [40, 52],
            "h1-btn": [1, 26],
            "h2-btn": [27, 52],
            "reset-btn": [1, 52]
        }
        return periods.get(ctx.triggered_id, [1, 52])
    
    # =========================================================================
    # WEEK RANGE SYNCHRONIZATION
    # =========================================================================
    @callback(
        Output("current-week-range", "data"),
        Input("week-slider", "value")
    )
    def store_week_range(week_range):
        """Store current week range in dcc.Store."""
        return week_range
    
    @callback(
        [Output("week-start-input", "value"), Output("week-end-input", "value")],
        Input("week-slider", "value")
    )
    def sync_inputs_from_slider(week_range):
        """Sync input fields when slider changes."""
        return week_range[0], week_range[1]
    
    @callback(
        Output("week-slider", "value", allow_duplicate=True),
        [Input("week-start-input", "value"), Input("week-end-input", "value")],
        prevent_initial_call=True
    )
    def sync_slider_from_inputs(start, end):
        """Sync slider when input fields change."""
        start = max(1, min(52, start or 1))
        end = max(1, min(52, end or 52))
        if start > end:
            start, end = end, start
        return [start, end]
    
    # =========================================================================
    # ZOOM LEVEL INDICATOR
    # =========================================================================
    @callback(
        [Output("zoom-level-indicator", "children"), Output("zoom-level-indicator", "style")],
        Input("week-slider", "value")
    )
    def update_zoom_indicator(week_range):
        """Update zoom level indicator based on current range."""
        zoom_level = get_zoom_level(week_range)
        base_style = {
            "fontSize": "10px",
            "textAlign": "center",
            "marginTop": "5px",
            "padding": "4px 8px",
            "borderRadius": "4px",
            "fontWeight": "500"
        }
        
        indicators = {
            "detail": ("🔍 Detail View (labels + events + thresholds)", {"color": "#27ae60", "backgroundColor": "#e8f8f0"}),
            "quarter": ("📊 Quarter View (events visible)", {"color": "#3498db", "backgroundColor": "#ebf5fb"}),
            "overview": ("🌐 Overview (trends only)", {"color": "#7f8c8d", "backgroundColor": "#ecf0f1"})
        }
        
        text, color_style = indicators[zoom_level]
        return text, {**base_style, **color_style}
