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

from dash import callback, Output, Input, State, ctx, ALL, MATCH

from jbi100_app.views.menu import get_sidebar_collapsed_style, get_sidebar_expanded_style
from jbi100_app.views.overview import get_zoom_level
from jbi100_app.config import DEPT_LABELS, DEPT_COLORS


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
    # DEPARTMENT QUICK SELECT - REMOVED (now handled by handle_dept_selection)
    # =========================================================================
    
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
    
    # =========================================================================
    # CUSTOM DEPARTMENT SELECTOR
    # Design: Click toggles selection, click on selected = make primary
    # Theory: Norman's visibility principle - state is always visible
    # =========================================================================
    @callback(
        [Output("dept-filter", "value"),
         Output("primary-dept-store", "data"),
         # Checkmarks for each department
         Output("dept-check-emergency", "children"),
         Output("dept-check-surgery", "children"),
         Output("dept-check-general_medicine", "children"),
         Output("dept-check-ICU", "children"),
         # Stars for each department
         Output("dept-star-emergency", "children"),
         Output("dept-star-surgery", "children"),
         Output("dept-star-general_medicine", "children"),
         Output("dept-star-ICU", "children"),
         # Item styles for each department
         Output("dept-item-emergency", "style"),
         Output("dept-item-surgery", "style"),
         Output("dept-item-general_medicine", "style"),
         Output("dept-item-ICU", "style")],
        [Input("dept-item-emergency", "n_clicks"),
         Input("dept-item-surgery", "n_clicks"),
         Input("dept-item-general_medicine", "n_clicks"),
         Input("dept-item-ICU", "n_clicks"),
         Input("select-all-btn", "n_clicks"),
         Input("reset-btn", "n_clicks")],
        [State("dept-filter", "value"),
         State("primary-dept-store", "data")],
        prevent_initial_call=False
    )
    def handle_dept_selection(e_clicks, s_clicks, g_clicks, i_clicks, all_clicks, reset_clicks,
                               current_selected, current_primary):
        """
        Handle department item clicks.
        
        Behavior:
        - Click unselected dept → Select it (and make primary if first selection)
        - Click selected dept → Make it primary (star indicator)
        - Click primary dept → Deselect it (next selected becomes primary)
        """
        depts = ["emergency", "surgery", "general_medicine", "ICU"]
        triggered = ctx.triggered_id
        
        # Initialize defaults
        if current_selected is None:
            current_selected = ["emergency"]
        if current_primary is None:
            current_primary = "emergency"
        
        new_selected = list(current_selected)
        new_primary = current_primary
        
        # Handle quick select buttons
        if triggered == "select-all-btn":
            new_selected = depts.copy()
            # Keep current primary if it was selected, otherwise use first
            if new_primary not in new_selected:
                new_primary = new_selected[0]
        elif triggered == "reset-btn":
            new_selected = ["emergency"]
            new_primary = "emergency"
        elif triggered and triggered.startswith("dept-item-"):
            # Extract department from trigger id
            clicked_dept = triggered.replace("dept-item-", "")
            
            if clicked_dept in new_selected:
                if clicked_dept == new_primary:
                    # Clicking primary = deselect it
                    new_selected.remove(clicked_dept)
                    # Assign new primary to first remaining selected
                    if new_selected:
                        new_primary = new_selected[0]
                    else:
                        new_primary = None
                else:
                    # Clicking selected (non-primary) = make it primary
                    new_primary = clicked_dept
            else:
                # Clicking unselected = select it
                new_selected.append(clicked_dept)
                # If nothing was selected before, make this primary
                if len(new_selected) == 1:
                    new_primary = clicked_dept
        
        # Ensure primary is in selected (fallback)
        if new_primary and new_primary not in new_selected and new_selected:
            new_primary = new_selected[0]
        
        # Build visual outputs
        checkmarks = []
        stars = []
        styles = []
        
        base_style = {
            "display": "flex",
            "alignItems": "center",
            "padding": "6px 8px",
            "marginBottom": "4px",
            "borderRadius": "6px",
            "cursor": "pointer",
            "transition": "all 0.15s ease"
        }
        
        for dept in depts:
            is_selected = dept in new_selected
            is_primary = dept == new_primary
            
            # Checkmark: ☑ if selected, ☐ if not
            checkmarks.append("☑" if is_selected else "☐")
            
            # Star: ⭐ only for primary
            stars.append("⭐" if is_primary else "")
            
            # Style: highlight based on state
            style = base_style.copy()
            if is_primary:
                # Primary: colored border + light background
                style.update({
                    "backgroundColor": f"{DEPT_COLORS[dept]}15",  # 15 = ~10% opacity
                    "border": f"2px solid {DEPT_COLORS[dept]}",
                    "fontWeight": "600"
                })
            elif is_selected:
                # Selected but not primary: subtle highlight
                style.update({
                    "backgroundColor": "#f0f4f8",
                    "border": "1px solid #bdc3c7"
                })
            else:
                # Not selected
                style.update({
                    "backgroundColor": "#fff",
                    "border": "1px solid #e0e0e0"
                })
            
            styles.append(style)
        
        return (
            new_selected,
            new_primary,
            *checkmarks,
            *stars,
            *styles
        )
