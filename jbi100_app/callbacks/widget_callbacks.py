"""
Widget Management Callbacks
JBI100 Visualization - Group 25

Callbacks for widget rendering and swapping:
- Main widget rendering
- Mini widget rendering
- Widget swap on click
"""

from dash import callback, Output, Input, State, ctx, html

from jbi100_app.data import get_services_data, get_patients_data, get_staff_schedule_data
from jbi100_app.views.overview import create_overview_expanded, create_overview_mini
from jbi100_app.views.quantity import create_quantity_expanded, create_quantity_mini
from jbi100_app.views.quality import create_quality_widget

# Load data once
_services_df = get_services_data()
_patients_df = get_patients_data()
_staff_schedule_df = get_staff_schedule_data()


def register_widget_callbacks():
    """Register all widget management callbacks."""
    
    # =========================================================================
    # WIDGET SWAP
    # =========================================================================
    @callback(
        Output("expanded-widget", "data"),
        [Input("mini-slot-1", "n_clicks"), Input("mini-slot-2", "n_clicks")],
        [State("expanded-widget", "data")],
        prevent_initial_call=True
    )
    def swap_widget(click1, click2, current):
        """
        Swap expanded widget when mini widget is clicked.
        
        Widget order: overview, quantity, quality
        When one is expanded, the other two are in mini slots.
        """
        widgets = ["overview", "quantity", "quality"]
        others = [w for w in widgets if w != current]
        
        if ctx.triggered_id == "mini-slot-1":
            return others[0]
        elif ctx.triggered_id == "mini-slot-2":
            return others[1]
        return current
    
    # =========================================================================
    # MAIN RENDER CALLBACK
    # =========================================================================
    @callback(
        [Output("main-widget-area", "children"),
         Output("mini-slot-1", "children"),
         Output("mini-slot-2", "children")],
        [Input("expanded-widget", "data"),
         Input("dept-filter", "value"),
         Input("week-slider", "value"),
         Input("show-events-toggle", "value"),
         Input("hide-anomalies-toggle", "value")]
    )
    def render_widgets(expanded, selected_depts, week_range, show_events_list, hide_anomalies_list):
        """
        Render all widgets based on current state.
        
        This is the main render callback that updates:
        - The expanded widget in the main area
        - Both mini widgets in the bottom row
        
        Args:
            expanded: Which widget is currently expanded ("overview", "quantity", "quality")
            selected_depts: List of selected department IDs
            week_range: [start_week, end_week] from slider
        
        Returns:
            tuple: (main_widget_content, mini1_content, mini2_content)
        """
        selected_depts = selected_depts or ["emergency"]
        
        # Convert checkbox lists to booleans
        show_events = "show" in (show_events_list or [])
        hide_anomalies = "hide" in (hide_anomalies_list or [])
        
        widgets = ["overview", "quantity", "quality"]
        others = [w for w in widgets if w != expanded]
        
        # Create expanded widget
        if expanded == "overview":
            main_content = create_overview_expanded(
                _services_df, selected_depts, week_range, show_events, hide_anomalies
            )
        elif expanded == "quantity":
            main_content = create_quantity_expanded(
                _services_df, _patients_df, selected_depts, week_range
            )
        else:  # quality
            main_content = create_quality_widget(
                _services_df, _staff_schedule_df, selected_depts, week_range
            )
        
        # Create mini widgets
        def create_quality_mini(services_df, selected_depts, week_range):
            """Mini placeholder for quality widget"""
            return html.Div([
                html.H4("Quality Analysis", style={'color': '#2c3e50', 'fontSize': '14px'}),
                html.P("Staff impact on morale & satisfaction", 
                       style={'color': '#7f8c8d', 'fontSize': '11px'})
            ])
        
        mini_creators = {
            "overview": lambda: create_overview_mini(_services_df, selected_depts, week_range),
            "quantity": lambda: create_quantity_mini(_services_df, selected_depts, week_range),
            "quality": lambda: create_quality_mini(_services_df, selected_depts, week_range)
        }
        
        mini1 = mini_creators[others[0]]()
        mini2 = mini_creators[others[1]]()
        
        return main_content, mini1, mini2
