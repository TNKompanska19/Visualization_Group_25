"""
Widget Callbacks
JBI100 Visualization - Group 25

Adds Connect: passes quantity-selected-week into overview rendering.
"""

from dash import callback, Output, Input, State, ctx

from jbi100_app.data import get_services_data, get_patients_data
from jbi100_app.views.overview import create_overview_expanded, create_overview_mini
from jbi100_app.views.quantity import create_quantity_expanded, create_quantity_mini
from jbi100_app.views.quality import create_quality_expanded, create_quality_mini

_services_df = get_services_data()
_patients_df = get_patients_data()


def register_widget_callbacks():

    @callback(
        Output("expanded-widget", "data"),
        [Input("mini-slot-1", "n_clicks"), Input("mini-slot-2", "n_clicks")],
        [State("expanded-widget", "data")],
        prevent_initial_call=True,
    )
    def swap_widget(click1, click2, current):
        widgets = ["overview", "quantity", "quality"]
        others = [w for w in widgets if w != current]
        if ctx.triggered_id == "mini-slot-1":
            return others[0]
        if ctx.triggered_id == "mini-slot-2":
            return others[1]
        return current

    @callback(
        [Output("main-widget-area", "children"),
         Output("mini-slot-1", "children"),
         Output("mini-slot-2", "children")],
        [Input("expanded-widget", "data"),
         Input("dept-filter", "value"),
         Input("week-slider", "value"),
         Input("show-events-toggle", "value"),
         Input("hide-anomalies-toggle", "value"),
         Input("quantity-selected-week", "data")],
    )
    def render_widgets(expanded, selected_depts, week_range, show_events_list, hide_anomalies_list, quantity_selected_week):
        selected_depts = selected_depts or ["emergency"]
        show_events = "show" in (show_events_list or [])
        hide_anomalies = "hide" in (hide_anomalies_list or [])

        widgets = ["overview", "quantity", "quality"]
        others = [w for w in widgets if w != expanded]

        if expanded == "overview":
            main_content = create_overview_expanded(
                _services_df,
                selected_depts,
                week_range,
                show_events,
                hide_anomalies,
                selected_week=quantity_selected_week,
            )
        elif expanded == "quantity":
            main_content = create_quantity_expanded(_services_df, _patients_df, selected_depts, week_range)
        else:
            main_content = create_quality_expanded(_services_df, selected_depts, week_range)

        mini_creators = {
            "overview": lambda: create_overview_mini(_services_df, selected_depts, week_range),
            "quantity": lambda: create_quantity_mini(_services_df, selected_depts, week_range),
            "quality": lambda: create_quality_mini(_services_df, selected_depts, week_range),
        }

        return main_content, mini_creators[others[0]](), mini_creators[others[1]]()
