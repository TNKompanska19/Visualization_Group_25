"""
Quantity View - REDESIGNED T3 WITH VIOLIN + GANTT
JBI100 Visualization - Group 25

T2: Left (weekly bars) + Right (comparison/summary) + Modal (bed distribution)
T3: Heatmap + Switchable (Violin ↔ Gantt with tab button)
"""

from dash import html, dcc
from jbi100_app.config import WIDGET_INFO


def create_quantity_expanded(services_df, patients_df, selected_depts, week_range):
    info = WIDGET_INFO["quantity"]

    header = html.Div(
        style={"paddingBottom": "8px", "marginBottom": "8px", "borderBottom": "2px solid #e8e8e8", "flexShrink": "0"},
        children=[
            html.H4(f"{info['icon']} {info['title']}", style={"margin": "0", "color": "#2c3e50", "fontWeight": "600", "fontSize": "15px"}),
            html.P(info["subtitle"], style={"margin": "0", "fontSize": "11px", "color": "#7f8c8d"})
        ],
    )

    tabs = dcc.Tabs(
        id="quantity-tabs", value="tab-t2", style={"marginBottom": "6px"},
        children=[
            dcc.Tab(label="T2: Bed Allocation", value="tab-t2", style={"padding": "6px 14px", "fontWeight": "500", "fontSize": "12px"}, selected_style={"padding": "6px 14px", "fontWeight": "600", "borderTop": "3px solid #3498db"}),
            dcc.Tab(label="T3: Stay Duration", value="tab-t3", style={"padding": "6px 14px", "fontWeight": "500", "fontSize": "12px"}, selected_style={"padding": "6px 14px", "fontWeight": "600", "borderTop": "3px solid #3498db"}),
        ],
    )

    # T2 graphs
    t2_weekly = dcc.Graph(id="t2-spc-chart", config={"displayModeBar": True, "displaylogo": False}, style={"height": "100%"})
    t2_comparison = dcc.Graph(id="t2-detail-chart", config={"displayModeBar": True, "displaylogo": False}, style={"height": "100%"})
    
    # T3 graphs
    t3_line = dcc.Graph(id="t3-line-chart", config={"displayModeBar": True, "displaylogo": False}, style={"height": "100%"})
    t3_violin = dcc.Graph(id="t3-violin-chart", config={"displayModeBar": True, "displaylogo": False}, style={"height": "100%"})
    t3_gantt = dcc.Graph(id="t3-gantt-chart", config={"displayModeBar": True, "displaylogo": False}, style={"height": "100%"})
    
    # Store for selected service/week from heatmap
    dcc.Store(id="t3-selected-service", data=None),
    dcc.Store(id="t3-selected-week-range", data=None),

    # T2 Content - SIDE BY SIDE + MODAL
    t2_content = html.Div(
        id="quantity-t2-content",
        style={"display": "flex", "flexDirection": "column", "gap": "8px", "height": "100%"},
        children=[
            html.Div(style={"padding": "5px 10px", "backgroundColor": "#f8f9fa", "borderRadius": "4px", "flexShrink": "0"}, children=[
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                    children=[
                        html.Div(id="quantity-context", style={"fontSize": "11px", "color": "#666"}, children="Weekly view | Select multiple departments for comparison"),
                        html.Button(
                            "📊 Bed Distribution",
                            id="show-distribution-btn",
                            n_clicks=0,
                            style={
                                "padding": "5px 12px",
                                "backgroundColor": "#3498db",
                                "color": "white",
                                "border": "none",
                                "borderRadius": "4px",
                                "cursor": "pointer",
                                "fontSize": "11px",
                                "fontWeight": "500",
                            }
                        ),
                    ]
                ),
            ]),
            html.Div(
                style={"flex": "1", "display": "flex", "gap": "10px", "minHeight": "0"},
                children=[
                    html.Div(style={"flex": "0.65", "minWidth": "0"}, children=[t2_weekly]),
                    html.Div(style={"flex": "0.35", "minWidth": "0"}, children=[t2_comparison]),
                ],
            ),
            html.Div(
                id="distribution-modal",
                style={"display": "none"},
                children=[
                    html.Div(
                        style={
                            "position": "fixed",
                            "top": "0",
                            "left": "0",
                            "width": "100%",
                            "height": "100%",
                            "backgroundColor": "rgba(0,0,0,0.5)",
                            "zIndex": "1000",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                        children=[
                            html.Div(
                                style={
                                    "backgroundColor": "white",
                                    "borderRadius": "12px",
                                    "padding": "20px",
                                    "width": "600px",
                                    "maxHeight": "80vh",
                                    "overflow": "auto",
                                    "boxShadow": "0 8px 32px rgba(0,0,0,0.2)",
                                    "position": "relative",
                                },
                                children=[
                                    html.Button(
                                        "✕",
                                        id="close-distribution-btn",
                                        n_clicks=0,
                                        style={
                                            "position": "absolute",
                                            "top": "10px",
                                            "right": "10px",
                                            "background": "none",
                                            "border": "none",
                                            "fontSize": "24px",
                                            "cursor": "pointer",
                                            "color": "#999",
                                        },
                                    ),
                                    dcc.Graph(
                                        id="distribution-chart",
                                        config={"displayModeBar": True, "displaylogo": False},
                                        style={"height": "500px"},
                                    ),
                                ],
                            )
                        ],
                    )
                ],
            ),
        ],
    )

    # T3 Content - HEATMAP + SWITCHABLE (Violin ↔ Gantt)
    t3_content = html.Div(
        id="quantity-t3-content",
        style={"display": "none", "flexDirection": "column", "gap": "6px", "height": "100%"},
        children=[
            html.Div(
                style={"padding": "5px 10px", "backgroundColor": "#f8f9fa", "borderRadius": "4px", "flexShrink": "0"},
                children=[
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                        children=[
                        html.Div(
                        id="t3-context",
                        style={"fontSize": "11px", "color": "#666"},
                        children="Occupancy trends | Brush/zoom to select time period"
                        ),
                            html.Button(
                                "📅 Patient Timeline",
                                id="toggle-gantt-btn",
                                n_clicks=0,
                                style={
                                    "padding": "5px 12px",
                                    "backgroundColor": "#9b59b6",
                                    "color": "white",
                                    "border": "none",
                                    "borderRadius": "4px",
                                    "cursor": "pointer",
                                    "fontSize": "11px",
                                    "fontWeight": "500",
                                }
                            ),
                        ]
                    ),
                ]
            ),
            html.Div(
                style={"flex": "1", "display": "flex", "gap": "10px", "minHeight": "0"},
                children=[
                    html.Div(style={"flex": "0.5", "minWidth": "0"}, children=[t3_line]),
                    html.Div(
                        id="t3-switchable-container",
                        style={"flex": "0.5", "minWidth": "0"},
                        children=[t3_violin]  # Default: violin plot
                    ),
                ],
            ),
        ],
    )

    return html.Div(style={"height": "100%", "display": "flex", "flexDirection": "column", "overflow": "hidden"}, children=[header, tabs, t2_content, t3_content])


def create_quantity_mini(services_df, selected_depts, week_range):
    info = WIDGET_INFO["quantity"]
    week_min, week_max = week_range
    df = services_df[(services_df["week"] >= week_min) & (services_df["week"] <= week_max)].copy()
    if selected_depts:
        df = df[df["service"].isin(selected_depts)].copy()
    total_refused = int(df["patients_refused"].sum()) if len(df) > 0 else 0
    avg_util = float(df["utilization_rate"].mean()) if len(df) > 0 else 0.0
    return html.Div(style={"height": "100%", "display": "flex", "flexDirection": "column"}, children=[
        html.Div(f"{info['icon']} {info['title']}", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "5px", "color": "#2c3e50"}),
        html.Div(info["subtitle"], style={"fontSize": "10px", "color": "#999", "marginBottom": "8px"}),
        html.Div(style={"flex": "1", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "display": "flex", "alignItems": "center", "justifyContent": "space-around", "padding": "10px"}, children=[
            html.Div(style={"textAlign": "center"}, children=[html.Div(f"{total_refused:,}", style={"fontSize": "20px", "fontWeight": "700", "color": "#e74c3c"}), html.Div("Refused", style={"fontSize": "10px", "color": "#95a5a6", "marginTop": "2px"})]),
            html.Div(style={"textAlign": "center"}, children=[html.Div(f"{avg_util:.0f}%", style={"fontSize": "20px", "fontWeight": "700", "color": "#3498db"}), html.Div("Utilization", style={"fontSize": "10px", "color": "#95a5a6", "marginTop": "2px"})]),
        ]),
        html.Div("↑ Click to expand", style={"fontSize": "10px", "color": "#3498db", "fontWeight": "500", "marginTop": "8px", "textAlign": "center"}),
    ])
