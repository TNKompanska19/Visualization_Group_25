"""
Unified Single-Tab View
JBI100 Visualization - Group 25

One scrollable column: Line chart, PCP, Stacked bar (beds vs demand), LOS violin, Node graph.
Each section in its own div with spacing. No widget swap.
"""

from dash import html, dcc
import dash_cytoscape as cyto



# Clean card style: no overlap, clear separation, minimal shadow
# Avoid overflow:hidden so chart labels/axes are not clipped
SECTION_STYLE = {
    "marginBottom": "20px",
    "backgroundColor": "#ffffff",
    "border": "1px solid #e8ecf0",
    "borderRadius": "8px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.04)",
    "padding": "20px",
    "minHeight": "0",
}


def create_unified_content():
    """
    Create the single-tab scrollable layout with all sections.
    Figures are filled by callbacks (no initial figures here to avoid loading data in layout).
    """
    # ---- 1. Line chart only (own card; fixed height so it never overlaps PCP) ----
    chart_section = html.Div(
        id="chart-container",
        style={
            **SECTION_STYLE,
            "position": "relative",
            "minHeight": "420px",
            "display": "flex",
            "flexDirection": "column",
        },
        children=[
            html.Div(
                [
                    html.Span("Hospital Performance Overview (T1)", style={"fontSize": "13px", "fontWeight": "600", "color": "#2c3e50"}),
                    html.Span(" — Hover to link all charts to that week; double-click to clear.", style={"fontSize": "11px", "color": "#7f8c8d", "marginLeft": "8px"}),
                ],
                style={"marginBottom": "10px", "flexShrink": "0"},
            ),
            html.Div(
                style={"display": "flex", "gap": "10px", "flex": "1", "minHeight": "380px"},
                children=[
                    html.Div(
                        style={"flex": "1", "position": "relative", "minWidth": "0", "minHeight": "380px"},
                        children=[
                            dcc.Graph(
                                id="overview-chart",
                                config={"displayModeBar": True, "scrollZoom": True, "displaylogo": False},
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
                    html.Div(
                        id="side-tooltip",
                        style={
                            "width": "90px", "backgroundColor": "#f8f9fa", "borderRadius": "6px",
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
            html.Div(style={"display": "none"}, children=[
                dcc.Graph(id="hist-satisfaction"),
                dcc.Graph(id="hist-acceptance"),
                html.Div(id="quality-mini-staff-total"),
                html.Div(id="quality-mini-staff-label"),
                html.Div(id="quality-mini-staff-breakdown"),
                html.Div(id="quality-mini-morale-value"),
                html.Div(id="quality-mini-morale-label"),
                html.Div(id="quality-mini-morale-breakdown"),
                dcc.Graph(id="quality-mini-sparkline"),
            ]),
        ],
    )

    # ---- 2. PCP (separate card; no overlap with line chart) ----
    pcp_section = html.Div(
        style={**SECTION_STYLE, "minHeight": "460px", "display": "flex", "flexDirection": "column"},
        children=[
            html.Div(
                "Hospital Performance PCP: Capacity → Flow → Quality",
                style={"fontSize": "13px", "fontWeight": "600", "color": "#2c3e50", "marginBottom": "10px", "flexShrink": "0"},
            ),
            html.Div(
                style={"flex": "1", "minHeight": "400px"},
                children=[
                    dcc.Graph(
                        id="pcp-chart",
                        config={"displayModeBar": False},
                        style={"height": "400px", "width": "100%"},
                    ),
                ],
            ),
        ],
    )

    # ---- 3. Stacked bar (available beds vs demand) ----
    stacked_bar_section = html.Div(
        style={**SECTION_STYLE, "minHeight": "420px", "display": "flex", "flexDirection": "column"},
        children=[
            html.Div(
                "Capacity: Available Beds vs Demand (T2+T3)",
                style={"fontSize": "14px", "fontWeight": "600", "color": "#2c3e50", "marginBottom": "8px"},
            ),
            dcc.Graph(
                id="stacked-beds-demand-chart",
                config={"displayModeBar": False},
                style={"height": "380px", "width": "100%"},
            ),
        ],
    )

    # ---- 4. LOS violin ----
    los_section = html.Div(
        style={**SECTION_STYLE, "minHeight": "480px", "display": "flex", "flexDirection": "column"},
        children=[
            html.Div(
                "Length of Stay by Department (T3)",
                style={"fontSize": "14px", "fontWeight": "600", "color": "#2c3e50", "marginBottom": "8px"},
            ),
            dcc.Graph(
                id="t3-los-chart",
                config={"displayModeBar": False},
                style={"height": "420px", "width": "100%"},
            ),
        ],
    )

    # ---- 5. Node graph (staff for selected week) ----
    # Hidden quality outputs so the existing quality callback can run (it outputs to these IDs)
    hidden_quality = html.Div(
        id="hidden-quality-outputs",
        style={"display": "none"},
        children=[
            html.Div(id="working-count-display"),
            html.Span(id="selected-week-display", children="1"),
            dcc.Graph(id="week-context-chart"),
            dcc.Graph(id="morale-comparison-chart"),
            html.Div(id="prediction-status"),
            dcc.Graph(id="satisfaction-comparison-chart"),
            dcc.Store(id="custom-team-store", data={"active": False, "working_ids": []}),
            dcc.Store(id="working-ids-store", data=[]),
            dcc.Store(id="dept-averages-store", data={"morale": 0, "satisfaction": 0}),
            dcc.Store(id="current-department-store", data="emergency"),
            dcc.Store(id="role-colors-store", data={}),
            dcc.Store(id="saved-configs-store", data=[]),
        ],
    )

    node_section = html.Div(
        style={**SECTION_STYLE, "minHeight": "520px", "display": "flex", "flexDirection": "column"},
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "marginBottom": "10px", "flexWrap": "wrap", "gap": "8px"},
                children=[
                    html.Span(
                        "Staff Network (T5)",
                        style={"fontSize": "13px", "fontWeight": "600", "color": "#2c3e50"},
                    ),
                    html.Div(
                        className="network-week-control",
                        style={"display": "flex", "alignItems": "center", "gap": "10px", "minWidth": "220px"},
                        children=[
                            html.Label("Week:", style={"fontSize": "11px", "color": "#5a6c7d", "flexShrink": "0"}),
                            dcc.Slider(
                                id="quality-week-slider",
                                min=1,
                                max=52,
                                value=1,
                                step=1,
                                marks={1: "1", 26: "26", 52: "52"},
                                tooltip={"placement": "bottom"},
                            ),
                            html.Span(id="network-week-display", children="Week 1", style={"fontSize": "12px", "fontWeight": "600", "color": "#2c3e50", "minWidth": "44px"}),
                        ],
                    ),
                ],
            ),
            html.Div(
                id="network-container",
                style={"flex": "1", "minHeight": "400px", "width": "100%", "border": "1px solid #e8ecf0", "borderRadius": "6px"},
                children=[
                    cyto.Cytoscape(
                        id="staff-network-weekly",
                        elements=[],
                        style={"width": "100%", "height": "100%"},
                        layout={"name": "preset"},
                        stylesheet=[],
                    ),
                ],
            ),
            html.Div(style={"display": "none"}, id="hidden-quality-outputs", children=[
                html.Div(id="working-count-display"),
                html.Span(id="selected-week-display", children="1"),
                dcc.Graph(id="week-context-chart"),
                dcc.Graph(id="morale-comparison-chart"),
                html.Div(id="prediction-status"),
                dcc.Graph(id="satisfaction-comparison-chart"),
                dcc.Store(id="custom-team-store", data={"active": False, "working_ids": []}),
                dcc.Store(id="working-ids-store", data=[]),
                dcc.Store(id="dept-averages-store", data={"morale": 0, "satisfaction": 0}),
                dcc.Store(id="current-department-store", data="emergency"),
                dcc.Store(id="role-colors-store", data={}),
                dcc.Store(id="saved-configs-store", data=[]),
            ]),
        ],
    )

    # Scrollable column
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
            stacked_bar_section,
            los_section,
            node_section,
        ],
    )
