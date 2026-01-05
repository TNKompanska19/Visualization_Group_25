"""
Quantity View - MERGED VERSION
JBI100 Visualization - Group 25

MERGED: Colleague's T2 controls + Your T3 interactions
- T2: Bed Allocation with grouped/separate, count/rate, selection, bed distribution modal
- T3: Stay Duration with Occupancy + toggle (LOS ↔ Gantt)
"""

from dash import html, dcc
from jbi100_app.config import WIDGET_INFO


def create_quantity_expanded(services_df, patients_df, selected_depts, week_range):
    info = WIDGET_INFO["quantity"]

    header = html.Div(
        style={"paddingBottom": "8px", "marginBottom": "8px", "borderBottom": "2px solid #e8e8e8", "flexShrink": "0"},
        children=[
            html.H4(
                f"{info['icon']} {info['title']}",
                style={"margin": "0", "color": "#2c3e50", "fontWeight": "600", "fontSize": "15px"},
            ),
            html.P(info["subtitle"], style={"margin": "0", "fontSize": "11px", "color": "#7f8c8d"}),
        ],
    )

    tabs = dcc.Tabs(
        id="quantity-tabs",
        value="tab-t2",
        style={"marginBottom": "6px"},
        children=[
            dcc.Tab(
                label="T2: Bed Allocation",
                value="tab-t2",
                style={"padding": "6px 14px", "fontWeight": "500", "fontSize": "12px"},
                selected_style={"padding": "6px 14px", "fontWeight": "600", "borderTop": "3px solid #3498db"},
            ),
            dcc.Tab(
                label="T3: Stay Duration",
                value="tab-t3",
                style={"padding": "6px 14px", "fontWeight": "500", "fontSize": "12px"},
                selected_style={"padding": "6px 14px", "fontWeight": "600", "borderTop": "3px solid #3498db"},
            ),
        ],
    )

    # Store for selection linking
    selection_store = dcc.Store(id="quantity-selected-week", data=None)

    # ============================================
    # T2: BED ALLOCATION (COLLEAGUE'S CONTROLS)
    # ============================================

    t2_controls = html.Div(
        style={
            "padding": "8px 10px",
            "backgroundColor": "#f8f9fa",
            "borderRadius": "6px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "gap": "10px",
            "flexShrink": "0",
        },
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "14px", "flexWrap": "wrap"},
                children=[
                    html.Div(
                        "T2: Click a week bar to select it (linked to other views).",
                        style={"fontSize": "11px", "color": "#666", "marginRight": "10px"},
                    ),
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                        children=[
                            html.Span("Weekly layout:", style={"fontSize": "11px", "color": "#666"}),
                            dcc.RadioItems(
                                id="t2-weekly-layout",
                                options=[
                                    {"label": "Grouped", "value": "grouped"},
                                    {"label": "Separate", "value": "separate"},
                                ],
                                value="separate",
                                inline=True,
                                style={"fontSize": "11px"},
                            ),
                        ],
                    ),
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                        children=[
                            html.Span("Refusal metric:", style={"fontSize": "11px", "color": "#666"}),
                            dcc.Dropdown(
                                id="t2-refusal-metric",
                                options=[
                                    {"label": "Refused (count)", "value": "count"},
                                    {"label": "Refusal rate (%)", "value": "rate"},
                                ],
                                value="count",
                                clearable=False,
                                style={"width": "190px", "fontSize": "11px"},
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px"},
                children=[
                    html.Button(
                        "🧽 Clear selection",
                        id="t2-clear-selection-btn",
                        n_clicks=0,
                        style={
                            "padding": "6px 12px",
                            "backgroundColor": "#ecf0f1",
                            "border": "1px solid #d0d7de",
                            "borderRadius": "6px",
                            "cursor": "pointer",
                            "fontSize": "11px",
                            "fontWeight": "500",
                        },
                    ),
                    html.Button(
                        "📊 Bed Distribution",
                        id="show-distribution-btn",
                        n_clicks=0,
                        style={
                            "padding": "6px 12px",
                            "backgroundColor": "#3498db",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "6px",
                            "cursor": "pointer",
                            "fontSize": "11px",
                            "fontWeight": "500",
                        },
                    ),
                ],
            ),
        ],
    )

    t2_weekly = dcc.Graph(
        id="t2-spc-chart",
        config={"displayModeBar": True, "displaylogo": False},
        style={"height": "100%"},
    )

    t2_summary = dcc.Graph(
        id="t2-detail-chart",
        config={"displayModeBar": True, "displaylogo": False},
        style={"height": "100%"},
    )

    t2_content = html.Div(
        id="quantity-t2-content",
        style={"display": "flex", "flexDirection": "column", "gap": "10px", "height": "100%", "minHeight": "0"},
        children=[
            t2_controls,
            html.Div(
                style={"flex": "1", "display": "flex", "gap": "10px", "minHeight": "0"},
                children=[
                    html.Div(style={"flex": "0.65", "minWidth": "0"}, children=[t2_weekly]),
                    html.Div(style={"flex": "0.35", "minWidth": "0"}, children=[t2_summary]),
                ],
            ),
            # Bed Distribution Modal (stays as modal, not in toggle)
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

    # ============================================
    # T3: STAY DURATION (YOUR INTERACTIVE CHARTS)
    # ============================================

    # T3 graphs
    t3_line = dcc.Graph(
        id="t3-line-chart",
        config={"displayModeBar": True, "displaylogo": False},
        style={"height": "100%"}
    )
    t3_violin = dcc.Graph(
        id="t3-violin-chart",
        config={"displayModeBar": True, "displaylogo": False},
        style={"height": "100%"}
    )
    t3_gantt = dcc.Graph(
        id="t3-gantt-chart",
        config={"displayModeBar": True, "displaylogo": False},
        style={"height": "100%"}
    )

    t3_content = html.Div(
        id="quantity-t3-content",
        style={"display": "none", "flexDirection": "column", "gap": "6px", "height": "100%"},
        children=[
            # CRITICAL: Store components for chart interactions
            dcc.Store(id="t3-gantt-interaction-store", data=None),  # Gantt → Occupancy
            dcc.Store(id="t3-los-interaction-store", data=None),  # LOS → Occupancy

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
                        children=[t3_violin]  # Default: LOS chart
                    ),
                ],
            ),
        ],
    )

    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column", "overflow": "hidden"},
        children=[selection_store, header, tabs, t2_content, t3_content]
    )


def create_quantity_mini(services_df, selected_depts, week_range):
    info = WIDGET_INFO["quantity"]
    week_min, week_max = week_range
    df = services_df[(services_df["week"] >= week_min) & (services_df["week"] <= week_max)].copy()
    if selected_depts:
        df = df[df["service"].isin(selected_depts)].copy()

    total_refused = int(df["patients_refused"].sum()) if len(df) > 0 else 0
    avg_util = float(df["utilization_rate"].mean()) if len(df) > 0 else 0.0

    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column"},
        children=[
            html.Div(
                f"{info['icon']} {info['title']}",
                style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "5px", "color": "#2c3e50"},
            ),
            html.Div(info["subtitle"], style={"fontSize": "10px", "color": "#999", "marginBottom": "8px"}),
            html.Div(
                style={
                    "flex": "1",
                    "backgroundColor": "#f8f9fa",
                    "borderRadius": "8px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-around",
                    "padding": "10px",
                },
                children=[
                    html.Div(
                        style={"textAlign": "center"},
                        children=[
                            html.Div(f"{total_refused:,}",
                                     style={"fontSize": "20px", "fontWeight": "700", "color": "#e74c3c"}),
                            html.Div("Refused", style={"fontSize": "10px", "color": "#95a5a6", "marginTop": "2px"}),
                        ],
                    ),
                    html.Div(
                        style={"textAlign": "center"},
                        children=[
                            html.Div(f"{avg_util:.0f}%",
                                     style={"fontSize": "20px", "fontWeight": "700", "color": "#3498db"}),
                            html.Div("Utilization", style={"fontSize": "10px", "color": "#95a5a6", "marginTop": "2px"}),
                        ],
                    ),
                ],
            ),
            html.Div(
                "↑ Click to expand",
                style={"fontSize": "10px", "color": "#3498db", "fontWeight": "500", "marginTop": "8px",
                       "textAlign": "center"},
            ),
        ],
    )
