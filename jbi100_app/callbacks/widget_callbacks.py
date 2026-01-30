"""
Widget Management Callbacks
JBI100 Visualization - Group 25

Callbacks for widget rendering and swapping.
"""

from dash import callback, Output, Input, State, ctx, html
from dash.exceptions import PreventUpdate

from jbi100_app.data import get_services_data, get_patients_data, get_staff_schedule_data
from jbi100_app.views.overview import create_overview_expanded, create_overview_mini
from jbi100_app.views.quantity import create_quantity_expanded, create_quantity_mini
from jbi100_app.views.quality import create_quality_widget, create_quality_mini

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
         Input("primary-dept-store", "data"),
         Input("current-week-range", "data"),
         Input("show-events-toggle", "value"),
         Input("hide-anomalies-toggle", "value")]
    )
    def render_widgets(expanded, selected_depts, primary_dept, week_range, show_events_list, hide_anomalies_list):
        """Render all widgets based on current state."""
        selected_depts = selected_depts or ["emergency"]
        primary_dept = primary_dept or (selected_depts[0] if selected_depts else "emergency")
        week_range = week_range or [1, 52]
        
        show_events = "show" in (show_events_list or [])
        hide_anomalies = "hide" in (hide_anomalies_list or [])
        
        widgets = ["overview", "quantity", "quality"]
        others = [w for w in widgets if w != expanded]
        
        if expanded == "overview":
            main_content = create_overview_expanded(
                _services_df, selected_depts, week_range, show_events, hide_anomalies
            )
        elif expanded == "quantity":
            main_content = create_quantity_expanded(
                _services_df, _patients_df, selected_depts, week_range
            )
        else:
            main_content = create_quality_widget(
                _services_df, _staff_schedule_df, [primary_dept], week_range
            )
        
        mini_creators = {
            "overview": lambda: create_overview_mini(_services_df, selected_depts, week_range),
            "quantity": lambda: create_quantity_mini(_services_df, selected_depts, week_range),
            "quality": lambda: create_quality_mini(_services_df, _staff_schedule_df, selected_depts, week_range, hide_anomalies)
        }
        
        mini1 = mini_creators[others[0]]()
        mini2 = mini_creators[others[1]]()
        
        return main_content, mini1, mini2
