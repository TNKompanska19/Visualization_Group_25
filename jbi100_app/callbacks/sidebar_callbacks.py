"""
Sidebar Callbacks
JBI100 Visualization - Group 25

Handles:
- Sidebar collapse/expand
- Quick select departments
- Week range control sync (slider <-> inputs)
- Time period buttons (quarters/halves)
- Zoom-level indicator text
"""

from dash import callback, Output, Input, State, ctx
from jbi100_app.config import ZOOM_THRESHOLDS


def register_sidebar_callbacks():
    # Present for architecture consistency
    pass


@callback(
    [Output("sidebar", "style"),
     Output("sidebar-content", "style"),
     Output("sidebar-title", "style"),
     Output("toggle-sidebar", "style")],
    Input("toggle-sidebar", "n_clicks")
)
def toggle_sidebar(n_clicks):
    base = {"backgroundColor": "#f8f9fa", "display": "flex", "flexDirection": "column", "transition": "width 0.3s ease", "overflow": "hidden", "flexShrink": "0", "borderRight": "1px solid #e0e0e0", "borderRadius": "0 12px 12px 0"}
    btn_base = {"border": "none", "color": "white", "cursor": "pointer", "borderRadius": "8px", "display": "flex", "alignItems": "center", "justifyContent": "center"}

    if n_clicks % 2 == 1:
        return (
            {**base, "width": "50px", "backgroundColor": "transparent", "borderRight": "none"},
            {"display": "none"},
            {"display": "none"},
            {**btn_base, "background": "#3498db", "width": "36px", "height": "36px", "padding": "0", "fontSize": "16px"}
        )

    return (
        {**base, "width": "240px"},
        {"padding": "15px", "overflowY": "auto"},
        {"display": "inline"},
        {**btn_base, "background": "#3498db", "width": "100%", "padding": "10px 12px", "fontSize": "13px", "gap": "6px"}
    )


@callback(
    Output("dept-filter", "value"),
    [Input("select-all-btn", "n_clicks"), Input("reset-btn", "n_clicks")],
    prevent_initial_call=True
)
def quick_select_departments(all_clicks, reset_clicks):
    if ctx.triggered_id == "select-all-btn":
        return ["emergency", "surgery", "general_medicine", "ICU"]
    return ["emergency"]


@callback(
    Output("week-slider", "value"),
    [Input("q1-btn", "n_clicks"),
     Input("q2-btn", "n_clicks"),
     Input("q3-btn", "n_clicks"),
     Input("q4-btn", "n_clicks"),
     Input("h1-btn", "n_clicks"),
     Input("h2-btn", "n_clicks"),
     Input("reset-btn", "n_clicks")],
    prevent_initial_call=True
)
def set_time_period(q1, q2, q3, q4, h1, h2, reset):
    return {
        "q1-btn": [1, 13],
        "q2-btn": [14, 26],
        "q3-btn": [27, 39],
        "q4-btn": [40, 52],
        "h1-btn": [1, 26],
        "h2-btn": [27, 52],
        "reset-btn": [1, 52]
    }.get(ctx.triggered_id, [1, 52])


@callback(
    Output("current-week-range", "data"),
    Input("week-slider", "value")
)
def store_week_range(week_range):
    return week_range


@callback(
    [Output("week-start-input", "value"), Output("week-end-input", "value")],
    Input("week-slider", "value")
)
def sync_inputs_from_slider(week_range):
    return week_range[0], week_range[1]


@callback(
    Output("week-slider", "value", allow_duplicate=True),
    [Input("week-start-input", "value"), Input("week-end-input", "value")],
    prevent_initial_call=True
)
def sync_slider_from_inputs(start, end):
    start = max(1, min(52, start or 1))
    end = max(1, min(52, end or 52))
    if start > end:
        start, end = end, start
    return [start, end]


@callback(
    Output("zoom-level-indicator", "children"),
    Input("week-slider", "value")
)
def update_zoom_indicator(week_range):
    wmin, wmax = week_range
    span = (wmax - wmin) + 1

    if span <= ZOOM_THRESHOLDS["detail"]:
        return "🔍 Detail view (≤8 weeks)"
    if span <= ZOOM_THRESHOLDS["quarter"]:
        return "📅 Quarter view (≤13 weeks)"
    return "🌍 Overview (full range)"
