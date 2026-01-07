"""
Quantity View - T2 & T3 v9
JBI100 Visualization - Group 25

Changes:
- Added t2t3-selected-week store for click-based week selection
- Updated instruction text
"""

from dash import html, dcc
from jbi100_app.config import WIDGET_INFO, DEPT_COLORS, DEPT_LABELS


def create_quantity_expanded(services_df, patients_df, selected_depts, week_range):
    """Create the T2-T3 view."""
    info = WIDGET_INFO["quantity"]

    header = html.Div(
        style={"paddingBottom": "2px", "marginBottom": "2px", "borderBottom": "1px solid #e8e8e8", "flexShrink": "0"},
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                children=[
                    html.H4(f"{info['icon']} Capacity & Patient Flow",
                            style={"margin": "0", "color": "#2c3e50", "fontWeight": "600", "fontSize": "13px"}),
                    html.Span("Click chart to select week • Drag to zoom • Double-click to reset",
                              style={"fontSize": "9px", "color": "#7f8c8d"}),
                ],
            ),
        ],
    )

    stores = html.Div([
        dcc.Store(id="t2t3-zoom-store", data=None),
        dcc.Store(id="t2t3-selected-week", data=None),  # Click-based selection
        dcc.Store(id="global-zoom-store", data=None),
    ])

    # TOP-LEFT: Capacity Pressure (line chart)
    refusal_chart = dcc.Graph(id="t2-refusal-chart", config={"displayModeBar": False}, style={"height": "100%"})

    # BOTTOM-LEFT: Capacity vs Demand (grouped bars)
    bed_chart = dcc.Graph(id="t2-bed-chart", config={"displayModeBar": False}, style={"height": "100%"})

    # TOP-RIGHT: Occupancy Rate
    occupancy_chart = dcc.Graph(id="t3-occupancy-chart", config={"displayModeBar": False}, style={"height": "100%"})

    # BOTTOM-RIGHT: LOS Violin
    los_chart = dcc.Graph(id="t3-los-chart", config={"displayModeBar": False}, style={"height": "100%"})

    chart_grid = html.Div(
        style={
            "flex": "1",
            "display": "grid",
            "gridTemplateColumns": "1.2fr 0.8fr",
            "gridTemplateRows": "1fr 1fr",
            "gap": "3px",
            "minHeight": "0",
            "minWidth": "0",
        },
        children=[
            html.Div(refusal_chart, style={"minHeight": "0", "minWidth": "0", "overflow": "hidden"}),
            html.Div(occupancy_chart, style={"minHeight": "0", "minWidth": "0", "overflow": "hidden"}),
            html.Div(bed_chart, style={"minHeight": "0", "minWidth": "0", "overflow": "hidden"}),
            html.Div(los_chart, style={"minHeight": "0", "minWidth": "0", "overflow": "hidden"}),
        ]
    )

    context_panel = html.Div(
        id="context-panel",
        style={
            "width": "175px",
            "flexShrink": "0",
            "backgroundColor": "#f9fafb",
            "borderLeft": "1px solid #e1e4e8",
            "padding": "8px",
            "display": "flex",
            "flexDirection": "column",
            "gap": "8px",
            "overflowY": "auto",
            "fontSize": "9px",
        },
        children=[
            html.Div(
                style={"borderBottom": "1px solid #e1e4e8", "paddingBottom": "6px"},
                children=[
                    html.Div("Departments", style={"fontWeight": "600", "fontSize": "10px", "color": "#2c3e50",
                                                   "marginBottom": "4px"}),
                    html.Div(id="legend-items"),
                ]
            ),
            html.Div(
                style={"borderBottom": "1px solid #e1e4e8", "paddingBottom": "6px"},
                children=[
                    html.Div(id="week-header", style={"fontWeight": "600", "fontSize": "10px", "color": "#2c3e50",
                                                      "marginBottom": "4px"}),
                    html.Div(id="week-metrics"),
                ]
            ),
            html.Div(
                id="reallocation-section",
                children=[
                    html.Div("🔄 Reallocation Insight",
                             style={"fontWeight": "600", "fontSize": "10px", "color": "#2c3e50",
                                    "marginBottom": "4px"}),
                    html.Div(id="reallocation-text"),
                ]
            ),
        ]
    )

    content = html.Div(
        style={"flex": "1", "display": "flex", "gap": "3px", "minHeight": "0", "overflow": "hidden"},
        children=[chart_grid, context_panel]
    )

    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column", "overflow": "hidden"},
        children=[stores, header, content]
    )


def create_quantity_mini(services_df, selected_depts, week_range):
    """Mini view for collapsed state."""
    info = WIDGET_INFO["quantity"]
    week_min, week_max = week_range
    df = services_df[(services_df["week"] >= week_min) & (services_df["week"] <= week_max)].copy()
    if selected_depts:
        df = df[df["service"].isin(selected_depts)].copy()

    total_refused = int(df["patients_refused"].sum()) if len(df) > 0 else 0
    avg_occ = float((df["patients_admitted"] / df["available_beds"] * 100).mean()) if len(df) > 0 else 0.0

    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column"},
        children=[
            html.Div(f"{info['icon']} Capacity & Flow",
                     style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "5px", "color": "#2c3e50"}),
            html.Div("T2+T3", style={"fontSize": "10px", "color": "#999", "marginBottom": "8px"}),
            html.Div(
                style={"flex": "1", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "display": "flex",
                       "alignItems": "center", "justifyContent": "space-around", "padding": "10px"},
                children=[
                    html.Div(style={"textAlign": "center"}, children=[
                        html.Div(f"{total_refused:,}",
                                 style={"fontSize": "18px", "fontWeight": "700", "color": "#D55E00"}),
                        html.Div("Refused", style={"fontSize": "9px", "color": "#95a5a6"}),
                    ]),
                    html.Div(style={"textAlign": "center"}, children=[
                        html.Div(f"{avg_occ:.0f}%",
                                 style={"fontSize": "18px", "fontWeight": "700", "color": "#0072B2"}),
                        html.Div("Occupancy", style={"fontSize": "9px", "color": "#95a5a6"}),
                    ]),
                ],
            ),
            html.Div("↑ Click to expand",
                     style={"fontSize": "10px", "color": "#0072B2", "fontWeight": "500", "marginTop": "8px",
                            "textAlign": "center"}),
        ],
    )