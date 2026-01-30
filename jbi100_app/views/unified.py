"""
Unified Single-Tab View
JBI100 Visualization - Group 25

REFACTORED: One scrollable column with all visualizations.
- Line chart with SEMANTIC ZOOM (KDE histograms appear at detail level)
- PCP with proper axis labels
- Stacked bar (beds vs demand) + LOS violin side-by-side
- Staff Network linked to hovered week

Interactions:
- Zoom line chart (select week range) → PCP shows same week range
- Brush PCP Week axis → line chart zooms to that week range (no hover linking)
- Network week slider → syncs with hover (other widgets)

SEMANTIC ZOOM LOGIC (Munzner Ch. 11):
- ≤8 weeks (detail): Show KDE panels + detailed markers
- ≤13 weeks (quarter): Show KDE panels
- >13 weeks (overview): Hide KDE panels, focus on trends
"""

from dash import html, dcc
import dash_cytoscape as cyto
import plotly.graph_objects as go

from jbi100_app.config import ZOOM_THRESHOLDS
from jbi100_app.views.quality import create_config_comparison_chart


# Clean card style
SECTION_STYLE = {
    "marginBottom": "20px",
    "backgroundColor": "#ffffff",
    "border": "1px solid #e8ecf0",
    "borderRadius": "8px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.04)",
    "padding": "16px",
    "minHeight": "0",
}


def create_unified_content():
    """
    Create the single-tab scrollable layout with all sections.
    RESTORED: Semantic zoom with KDE histograms.
    """
    
    # ---- 1. Overview Line Chart Section (with semantic zoom KDE panels) ----
    # KDE panels are shown/hidden based on zoom level via callback
    chart_section = html.Div(
        id="overview-section",
        style={
            **SECTION_STYLE,
            "position": "relative",
            "minHeight": "440px",
            "display": "flex",
            "flexDirection": "column",
        },
        children=[
            # Header with instructions
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "10px", "flexShrink": "0"},
                children=[
                    html.Div([
                        html.Span("Hospital Performance Overview (T1)", style={"fontSize": "14px", "fontWeight": "600", "color": "#2c3e50"}),
                        html.Span(" — Zoom to select week range; range syncs with PCP below.", style={"fontSize": "10px", "color": "#7f8c8d", "marginLeft": "8px"}),
                    ]),
                    # Zoom level indicator (updated by callback)
                    html.Span(id="overview-zoom-indicator", children="🌐 Overview (W1-52)", style={"fontSize": "10px", "color": "#3498db", "fontWeight": "500"}),
                ]
            ),
            # Main content: Line chart + KDE (semantic zoom) + Tooltip
            html.Div(
                id="overview-content-row",
                style={"display": "flex", "gap": "10px", "flex": "1", "minHeight": "380px"},
                children=[
                    # Line chart (always visible)
                    html.Div(
                        style={"flex": "1", "position": "relative", "minWidth": "0", "minHeight": "380px"},
                        children=[
                            dcc.Graph(
                                id="overview-chart",
                                config={"displayModeBar": True, "scrollZoom": True, "displaylogo": False,
                                        "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]},
                                style={"height": "380px", "width": "100%"},
                            ),
                            html.Div(
                                id="hover-highlight",
                                style={
                                    "position": "absolute", "top": "10px", "bottom": "30px",
                                    "width": "4px", "backgroundColor": "rgba(52, 152, 219, 0.6)",
                                    "pointerEvents": "none", "display": "none", "borderRadius": "2px", "left": "40px",
                                },
                            ),
                        ],
                    ),
                    # KDE section (semantic zoom: visible when zoomed in)
                    # CRITICAL: Style is controlled by callback based on zoom level
                    # Initially hidden (display: none) - callback sets display: flex when zoomed
                    html.Div(
                        id="kde-section",
                        style={
                            "width": "200px",
                            "display": "none",  # Initially hidden - callback shows when zoom_level in ["detail", "quarter"]
                            "flexDirection": "column",
                            "gap": "6px",
                            "flexShrink": "0",
                        },
                        children=[
                            html.Div(
                                style={"flex": "1", "backgroundColor": "#fafafa", "borderRadius": "4px", "border": "1px solid #eee", "minHeight": "170px"},
                                children=[
                                    dcc.Graph(
                                        id="hist-satisfaction",
                                        config={"displayModeBar": False},
                                        style={"height": "170px", "width": "100%"}
                                    )
                                ]
                            ),
                            html.Div(
                                style={"flex": "1", "backgroundColor": "#fafafa", "borderRadius": "4px", "border": "1px solid #eee", "minHeight": "170px"},
                                children=[
                                    dcc.Graph(
                                        id="hist-acceptance",
                                        config={"displayModeBar": False},
                                        style={"height": "170px", "width": "100%"}
                                    )
                                ]
                            ),
                        ],
                    ),
                    # Tooltip section
                    html.Div(
                        id="side-tooltip",
                        style={
                            "width": "95px", "backgroundColor": "#f8f9fa", "borderRadius": "6px",
                            "padding": "8px", "border": "1px solid #e8ecf0", "flexShrink": "0",
                            "fontSize": "9px", "overflow": "auto", "minHeight": "380px",
                        },
                        children=[
                            html.Div(
                                id="tooltip-content",
                                children=[
                                    html.Div("Hover over", style={"color": "#999", "textAlign": "center"}),
                                    html.Div("the chart", style={"color": "#999", "textAlign": "center"}),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )

    # ---- 2. PCP Section (separate card with proper margins) ----
    # Title is in HTML (not Plotly title) to prevent overlap with axes
    pcp_section = html.Div(
        style={**SECTION_STYLE, "minHeight": "480px", "display": "flex", "flexDirection": "column"},
        children=[
            # Title in HTML (not Plotly title) to prevent overlap
            html.Div(
                style={"marginBottom": "8px", "flexShrink": "0"},
                children=[
                    html.Span("Hospital Performance PCP: Capacity → Flow → Quality", 
                              style={"fontSize": "14px", "fontWeight": "600", "color": "#2c3e50"}),
                    html.Span(" — Brush Week axis: focus (color) + context (gray). Double-click brush to reset to 52 weeks.", 
                              style={"fontSize": "10px", "color": "#7f8c8d", "marginLeft": "8px"}),
                ]
            ),
            # PCP graph with increased height for proper axis labels
            html.Div(
                style={"flex": "1", "minHeight": "420px"},
                children=[
                    dcc.Graph(
                        id="pcp-chart",
                        config={"displayModeBar": False},
                        style={"height": "420px", "width": "100%"},
                    ),
                ],
            ),
        ],
    )

    # ---- 3. Capacity Section: Stacked Bar + LOS Violin SIDE BY SIDE ----
    # CRITICAL: Use flexbox with flex-direction: row for horizontal layout
    capacity_section = html.Div(
        style={**SECTION_STYLE, "minHeight": "450px", "display": "flex", "flexDirection": "column"},
        children=[
            html.Div(
                "Capacity: Available Beds vs Demand (T2+T3)",
                style={
                    "fontSize": "14px", "fontWeight": "600", "color": "#2c3e50",
                    "marginBottom": "8px", "flexShrink": "0",
                    "overflow": "visible", "whiteSpace": "normal", "wordWrap": "break-word",
                    "minHeight": "2.2em", "lineHeight": "1.3",
                },
            ),
            # Side-by-side layout: Stacked bar (left) + LOS violin (right)
            # HORIZONTAL flexbox layout as required
            html.Div(
                style={
                    "display": "flex",           # Flexbox
                    "flexDirection": "row",       # Horizontal
                    "gap": "16px",                # Gap between charts
                    "flex": "1",
                    "minHeight": "400px"
                },
                children=[
                    # Stacked bar chart (55% width) + overlay for hover highlight (no redraw on hover)
                    html.Div(
                        id="stacked-bar-chart-container",
                        style={"flex": "0.55", "minHeight": "380px", "minWidth": "0", "position": "relative"},
                        children=[
                            dcc.Graph(
                                id="stacked-beds-demand-chart",
                                config={"displayModeBar": True, "scrollZoom": True, "displaylogo": False,
                                        "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]},
                                style={"height": "380px", "width": "100%"},
                            ),
                            html.Div(
                                id="stacked-bar-highlight",
                                style={
                                    "position": "absolute", "top": "50px", "bottom": "50px",
                                    "width": "12px", "marginLeft": "-6px",
                                    "backgroundColor": "rgba(52, 152, 219, 0.2)",
                                    "pointerEvents": "none", "display": "none", "borderRadius": "4px",
                                },
                            ),
                        ]
                    ),
                    # LOS violin chart (45% width)
                    html.Div(
                        style={"flex": "0.45", "minHeight": "380px", "minWidth": "0"},
                        children=[
                            dcc.Graph(
                                id="t3-los-chart",
                                config={"displayModeBar": False},
                                style={"height": "380px", "width": "100%"},
                            ),
                        ]
                    ),
                ]
            ),
        ],
    )

    # ---- 4. Staff Network Section (T5) – same layout as quality.py ----
    _empty_context = go.Figure()
    _empty_context.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=45,
                                 plot_bgcolor="white", paper_bgcolor="white")
    _empty_bar = go.Figure()
    _empty_bar.update_layout(margin=dict(l=25, r=5, t=20, b=18), height=120,
                            plot_bgcolor="white", paper_bgcolor="white")
    _config_fig = create_config_comparison_chart([], 0, 0)

    # Stores for quality callbacks (impact-metric-store is in layout.py)
    quality_stores = html.Div([
        dcc.Store(id="custom-team-store", data={"active": False, "working_ids": []}),
        dcc.Store(id="working-ids-store", data=[]),
        dcc.Store(id="dept-averages-store", data={"morale": 0, "satisfaction": 0}),
        dcc.Store(id="current-department-store", data="emergency"),
        dcc.Store(id="role-colors-store", data={}),
        dcc.Store(id="saved-configs-store", data=[]),
    ])

    quality_header = html.Div(
        style={"flexShrink": "0", "marginBottom": "4px", "display": "flex",
               "justifyContent": "space-between", "alignItems": "center"},
        children=[
            html.Div([
                html.H4("Staff Configuration: Emergency", style={"color": "#2c3e50", "margin": "0", "fontSize": "14px"}),
                html.Span("— | Lasso / Lasso", style={"fontSize": "9px", "color": "#7f8c8d"}),
            ]),
            html.Div(id="working-count-display", children=[
                html.Span("# assigned: ", style={"fontSize": "10px", "color": "#7f8c8d"}),
                html.Span("0", style={"fontSize": "13px", "color": "#27ae60", "fontWeight": "bold"}),
            ]),
        ],
    )

    quality_main = html.Div(
        style={"flex": "1", "display": "flex", "gap": "8px", "minHeight": "0"},
        children=[
            # LEFT: Week context + network (60%) – same as quality.py
            html.Div(
                style={"flex": "0.6", "display": "flex", "flexDirection": "column", "minWidth": "0"},
                children=[
                    html.Div(style={"flexShrink": "0", "marginBottom": "5px"}, children=[
                        html.Div(style={"display": "flex", "alignItems": "center", "gap": "5px", "marginBottom": "2px"}, children=[
                            html.Label("Week:", style={"fontSize": "9px", "color": "#7f8c8d"}),
                            html.Span(id="selected-week-display", children="1", style={"fontSize": "11px", "fontWeight": "bold", "color": "#2c3e50"}),
                        ]),
                        dcc.Graph(id="week-context-chart", figure=_empty_context,
                                  config={"displayModeBar": False}, style={"height": "40px", "marginBottom": "-5px"}),
                        dcc.Slider(id="quality-week-slider", min=1, max=52, value=1, step=1,
                                  marks={1: "1", 13: "13", 26: "26", 39: "39", 52: "52"},
                                  tooltip={"placement": "bottom", "always_visible": False}),
                    ]),
                    html.Div(style={"flex": "1", "display": "flex", "flexDirection": "column", "minHeight": "0"}, children=[
                        html.Div(style={"fontSize": "8px", "color": "#7f8c8d", "textAlign": "center", "marginBottom": "3px"},
                                 children="💡 Click staff nodes to toggle assignment"),
                        html.Div(style={"flex": "1", "border": "1px solid #dee2e6", "borderRadius": "6px",
                                        "backgroundColor": "white", "minHeight": "0"}, children=[
                            cyto.Cytoscape(
                                id="staff-network-weekly",
                                elements=[],
                                style={"width": "100%", "height": "100%"},
                                layout={"name": "preset"},
                                stylesheet=[],
                                minZoom=0.4, maxZoom=2.5,
                                autoRefreshLayout=False,
                            ),
                        ]),
                    ]),
                    html.Div(style={"flexShrink": "0", "marginTop": "4px", "fontSize": "8px", "textAlign": "center",
                                    "display": "flex", "justifyContent": "center", "alignItems": "center", "gap": "8px", "flexWrap": "wrap"}, children=[
                        html.Div(style={"display": "flex", "alignItems": "center", "gap": "6px"}, children=[
                            html.Span("●", style={"color": "#5DADE2"}), html.Span("Doc", style={"marginRight": "4px"}),
                            html.Span("●", style={"color": "#AF7AC5"}), html.Span("Nurse", style={"marginRight": "4px"}),
                            html.Span("●", style={"color": "#58D68D"}), html.Span("Asst"),
                        ]),
                        html.Span("|", style={"color": "#ccc"}),
                        html.Div(style={"display": "flex", "alignItems": "center", "gap": "4px"}, children=[
                            html.Span("Impact:", style={"color": "#7f8c8d"}),
                            html.Button("Morale", id="impact-morale-btn", n_clicks=0,
                                        style={"padding": "2px 6px", "fontSize": "8px", "fontWeight": "600",
                                               "backgroundColor": "#3498db", "color": "white", "border": "none",
                                               "borderRadius": "3px 0 0 3px", "cursor": "pointer"}),
                            html.Button("Satisf.", id="impact-satisfaction-btn", n_clicks=0,
                                        style={"padding": "2px 6px", "fontSize": "8px", "fontWeight": "500",
                                               "backgroundColor": "#ecf0f1", "color": "#7f8c8d", "border": "none",
                                               "borderRadius": "0 3px 3px 0", "cursor": "pointer"}),
                        ]),
                        html.Span("|", style={"color": "#ccc"}),
                        html.Div(style={"display": "flex", "alignItems": "center", "gap": "4px"}, children=[
                            html.Span("●", style={"color": "#27ae60", "fontSize": "10px"}), html.Span("+", style={"marginRight": "2px"}),
                            html.Span("●", style={"color": "#e74c3c", "fontSize": "10px"}), html.Span("−", style={"marginRight": "4px"}),
                            html.Span("| border = strength", style={"color": "#7f8c8d"}),
                        ]),
                        html.Span("|", style={"color": "#ccc"}),
                        html.Span("● Bright + line = Assigned", style={"color": "#7f8c8d"}),
                    ]),
                ],
            ),
            # RIGHT: Morale/Satisfaction comparison (Avg + W1 bars) + save config (40%)
            html.Div(
                style={"flex": "0.4", "display": "flex", "flexDirection": "column", "gap": "5px", "minWidth": "0"},
                children=[
                    html.Div(style={"display": "flex", "gap": "5px", "flexShrink": "0"}, children=[
                        html.Div(style={"flex": "1", "display": "flex", "flexDirection": "column"}, children=[
                            html.Div(style={"textAlign": "center", "fontSize": "8px", "color": "#7f8c8d"}, children="vs Avg Morale"),
                            dcc.Graph(id="morale-comparison-chart", figure=_empty_bar,
                                      config={"displayModeBar": False}, style={"height": "120px"}),
                        ]),
                        html.Div(style={"flex": "1", "display": "flex", "flexDirection": "column"}, children=[
                            html.Div(id="prediction-status", style={"textAlign": "center", "fontSize": "8px", "minHeight": "14px"}),
                            html.Div(style={"textAlign": "center", "fontSize": "8px", "color": "#7f8c8d"}, children="W1 actual Satisfaction"),
                            dcc.Graph(id="satisfaction-comparison-chart", figure=_empty_bar,
                                      config={"displayModeBar": False}, style={"height": "120px"}),
                        ]),
                    ]),
                    html.Div(style={"flex": "1", "border": "1px solid #dee2e6", "borderRadius": "6px", "padding": "8px",
                                    "minHeight": "60px", "backgroundColor": "white", "display": "flex",
                                    "flexDirection": "column", "gap": "5px"}, children=[
                        html.Div(style={"display": "flex", "gap": "5px", "alignItems": "center"}, children=[
                            dcc.Input(id="config-name-input", type="text", placeholder="Config name...",
                                      style={"flex": "1", "padding": "4px 8px", "fontSize": "9px",
                                             "border": "1px solid #dee2e6", "borderRadius": "4px"}),
                            html.Button("💾 Save", id="save-config-btn",
                                        style={"padding": "4px 8px", "fontSize": "9px", "backgroundColor": "#3498db",
                                               "color": "white", "border": "none", "borderRadius": "4px", "cursor": "pointer"}),
                        ]),
                        html.Div(id="saved-configs-list", style={"flex": "1", "overflowY": "auto", "fontSize": "8px", "color": "#7f8c8d"}),
                    ]),
                    html.Div(style={"flex": "1", "border": "1px solid #dee2e6", "borderRadius": "6px",
                                    "minHeight": "60px", "backgroundColor": "white"}, children=[
                        dcc.Graph(id="config-comparison-chart", figure=_config_fig,
                                  config={"displayModeBar": False}, style={"height": "100%"}),
                    ]),
                ],
            ),
        ],
    )

    hidden_quality_mini = html.Div(
        id="hidden-quality-outputs",
        style={"display": "none"},
        children=[
            html.Span(id="network-week-display", children="Week 1"),
            html.Div(id="quality-mini-staff-total"),
            html.Div(id="quality-mini-staff-label"),
            html.Div(id="quality-mini-staff-breakdown"),
            html.Div(id="quality-mini-morale-value"),
            html.Div(id="quality-mini-morale-label"),
            html.Div(id="quality-mini-morale-breakdown"),
            dcc.Graph(id="quality-mini-sparkline"),
        ],
    )

    node_section = html.Div(
        style={**SECTION_STYLE, "minHeight": "520px", "display": "flex", "flexDirection": "column", "padding": "6px"},
        children=[quality_stores, quality_header, quality_main, hidden_quality_mini],
    )

    # Scrollable column with all sections
    return html.Div(
        style={
            "flex": "1",
            "overflowY": "auto",
            "overflowX": "hidden",
            "display": "flex",
            "flexDirection": "column",
            "minHeight": "0",
            "padding": "8px",
        },
        children=[
            chart_section,
            pcp_section,
            capacity_section,
            node_section,
        ],
    )
