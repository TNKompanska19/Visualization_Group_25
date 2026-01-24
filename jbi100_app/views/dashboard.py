"""
Unified Efficiency Dashboard View
JBI100 Visualization - Group 25

Single-view layout with linked brushing between:
- Time series (operational pressure over time)
- Multivariate SPLOM (cross-metric relationships)
- Department comparison (slack vs overload)
"""

from dash import html, dcc

from jbi100_app.config import CHART_CONFIG


def create_dashboard_view():
    """Create unified, single-view dashboard layout."""
    header = html.Div(
        style={
            "paddingBottom": "8px",
            "marginBottom": "10px",
            "borderBottom": "2px solid #eee",
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "flex-end",
            "gap": "12px",
            "flexWrap": "wrap",
        },
        children=[
            html.Div(
                children=[
                    html.H3(
                        "Operational Efficiency Dashboard",
                        style={"margin": "0", "color": "#2c3e50", "fontWeight": "600", "fontSize": "18px"},
                    ),
                    html.Div(
                        "Linked brushing across time and multivariate metrics (capacity, utilization, LOS).",
                        style={"fontSize": "11px", "color": "#7f8c8d"},
                    ),
                    html.Div(
                        "Visual encodings: Time series uses diamonds for events (T5); SPLOM marker size = bed capacity (T4).",
                        style={"fontSize": "9px", "color": "#95a5a6", "marginTop": "2px", "fontStyle": "italic"},
                    ),
                    html.Div(
                        style={"fontSize": "10px", "color": "#7f8c8d", "marginTop": "4px", "lineHeight": "1.4"},
                        children=[
                            html.Span("Tasks: "),
                            html.Span("T1 identify high-pressure weeks/services; "),
                            html.Span("T2 analyze relationships among pressure, utilization, acceptance, and LOS; "),
                            html.Span("T3 spot reallocation opportunities from slack vs overload; "),
                            html.Span("T4 evaluate bed capacity efficiency across departments; "),
                            html.Span("T5 assess impact of external events on operational performance."),
                        ],
                    ),
                ]
            ),
            html.Div(
                style={"display": "flex", "flexDirection": "column", "alignItems": "flex-end", "gap": "4px"},
                children=[
                    html.Div(id="brush-summary", style={"fontSize": "11px", "color": "#7f8c8d"}),
                    html.Button(
                        "Clear Selection",
                        id="clear-brush-btn",
                        n_clicks=0,
                        style={
                            "fontSize": "10px",
                            "padding": "4px 8px",
                            "backgroundColor": "#e74c3c",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "4px",
                            "cursor": "pointer",
                            "display": "none",
                        },
                    ),
                ],
            ),
        ],
    )

    charts = html.Div(
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "10px",
            "flex": "1",
            "minHeight": "0",
            "minWidth": "0",
            # Avoid clipping when stacking 3 charts
            "overflowY": "auto",
            "paddingBottom": "12px",
        },
        children=[
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1.2fr 1fr",
                    "gap": "10px",
                    "flex": "1",
                    "minHeight": "560px",
                    "minWidth": "0",
                },
                children=[
                    html.Div(
                        style={
                            "backgroundColor": "white",
                            "borderRadius": "12px",
                            "boxShadow": "0 4px 12px rgba(0,0,0,0.08)",
                            "padding": "12px",
                            "display": "flex",
                            "flexDirection": "column",
                            "minHeight": "560px",
                            "position": "relative",
                        },
                        children=[
                            dcc.Graph(
                                id="efficiency-timeseries",
                                config=CHART_CONFIG,
                                style={"height": "100%", "width": "100%"},
                            ),
                            html.Div(
                                style={
                                    "position": "absolute",
                                    "top": "20px",
                                    "right": "20px",
                                    "backgroundColor": "rgba(255, 255, 255, 0.95)",
                                    "padding": "8px 12px",
                                    "borderRadius": "6px",
                                    "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
                                    "fontSize": "9px",
                                    "zIndex": "10",
                                    "pointerEvents": "none",
                                },
                                children=[
                                    html.Div(
                                        "Events (T5):",
                                        style={"fontWeight": "600", "marginBottom": "4px", "color": "#2c3e50"},
                                    ),
                                    html.Div(
                                        [html.Span("◇ ", style={"color": "#D55E00", "fontSize": "12px"}), html.Span("Flu")],
                                        style={"marginBottom": "2px"},
                                    ),
                                    html.Div(
                                        [html.Span("◇ ", style={"color": "#CC79A7", "fontSize": "12px"}), html.Span("Strike")],
                                        style={"marginBottom": "2px"},
                                    ),
                                    html.Div(
                                        [html.Span("◇ ", style={"color": "#009E73", "fontSize": "12px"}), html.Span("Donation")]
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        style={
                            "backgroundColor": "white",
                            "borderRadius": "12px",
                            "boxShadow": "0 4px 12px rgba(0,0,0,0.08)",
                            "padding": "12px",
                            "display": "flex",
                            "flexDirection": "column",
                            "minHeight": "560px",
                            "position": "relative",
                        },
                        children=[
                            dcc.Graph(
                                id="multivariate-splom",
                                config=CHART_CONFIG,
                                style={"height": "100%", "width": "100%"},
                            ),
                            html.Div(
                                style={
                                    "position": "absolute",
                                    "top": "20px",
                                    "right": "20px",
                                    "backgroundColor": "rgba(255, 255, 255, 0.95)",
                                    "padding": "8px 12px",
                                    "borderRadius": "6px",
                                    "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
                                    "fontSize": "9px",
                                    "zIndex": "10",
                                    "pointerEvents": "none",
                                    "maxWidth": "220px",
                                },
                                children=[
                                    html.Div(
                                        "Bed Capacity (T4):",
                                        style={"fontWeight": "600", "marginBottom": "4px", "color": "#2c3e50"},
                                    ),
                                    html.Div(
                                        [html.Span("●", style={"fontSize": "6px", "marginRight": "4px"}), html.Span("Small (8-20 beds)")],
                                        style={"marginBottom": "2px"},
                                    ),
                                    html.Div(
                                        [html.Span("●", style={"fontSize": "10px", "marginRight": "4px"}), html.Span("Medium (21-40 beds)")],
                                        style={"marginBottom": "2px"},
                                    ),
                                    html.Div(
                                        [html.Span("●", style={"fontSize": "14px", "marginRight": "4px"}), html.Span("Large (41+ beds)")]
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                style={
                    "backgroundColor": "white",
                    "borderRadius": "12px",
                    "boxShadow": "0 4px 12px rgba(0,0,0,0.08)",
                    "padding": "12px",
                    "display": "flex",
                    "flexDirection": "column",
                    "minHeight": "0",
                    # Slightly taller so bars + labels aren't clipped
                    "height": "380px",
                },
                children=[
                    dcc.Graph(
                        id="department-comparison",
                        config=CHART_CONFIG,
                        style={"height": "100%", "width": "100%"},
                    )
                ],
            ),
        ],
    )

    return html.Div(
        # Ensure it fills the parent and allows internal scrolling
        style={"flex": "1", "minHeight": "0", "display": "flex", "flexDirection": "column"},
        children=[header, charts],
    )
