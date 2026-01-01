"""
Sidebar Menu Component
JBI100 Visualization - Group 25

Contains the sidebar with filtering controls:
- Department selection
- Week range slider
- Quick select buttons
- Display options (events/anomaly weeks)
"""

from dash import html, dcc
from jbi100_app.config import DEPT_LABELS


def create_sidebar():
    """
    Create the sidebar component with all controls.

    Interaction justification (Yi et al. taxonomy):
    - Filter: Department checkboxes, week range slider, anomaly toggle
    - Select: Quick select buttons for time periods
    - Abstract/Elaborate: Sidebar collapse/expand and zoom feedback in other views
    """
    return html.Div(
        id="sidebar",
        style=get_sidebar_expanded_style(),
        children=[
            # ---------------------------------------------------------
            # Toggle button container
            # ---------------------------------------------------------
            html.Div(
                id="toggle-container",
                style={"padding": "10px", "display": "flex", "justifyContent": "center"},
                children=[
                    html.Button(
                        id="toggle-sidebar",
                        n_clicks=0,
                        style={
                            "background": "#3498db",
                            "border": "none",
                            "color": "white",
                            "cursor": "pointer",
                            "borderRadius": "8px",
                            "padding": "10px 12px",
                            "fontSize": "13px",
                            "width": "100%",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "gap": "6px",
                        },
                        children=[
                            html.Span("☰", id="sidebar-icon", style={"fontSize": "16px"}),
                            html.Span("Options", id="sidebar-title"),
                        ],
                    )
                ],
            ),

            # ---------------------------------------------------------
            # Sidebar content (collapsible)
            # ---------------------------------------------------------
            html.Div(
                id="sidebar-content",
                style={"padding": "15px", "overflowY": "auto"},
                children=[
                    # =====================================================
                    # Department filter
                    # =====================================================
                    html.Label(
                        "Departments",
                        style={
                            "color": "#2c3e50",
                            "fontWeight": "600",
                            "marginBottom": "10px",
                            "display": "block",
                            "fontSize": "13px",
                        },
                    ),
                    dcc.Checklist(
                        id="dept-filter",
                        options=[{"label": f" {DEPT_LABELS[d]}", "value": d} for d in DEPT_LABELS],
                        value=["emergency"],
                        style={"color": "#34495e", "fontSize": "12px"},
                        inputStyle={"marginRight": "8px"},
                        labelStyle={"display": "block", "marginBottom": "8px", "cursor": "pointer"},
                    ),

                    html.Div(
                        style={"display": "flex", "gap": "8px", "marginTop": "6px"},
                        children=[
                            html.Button(
                                "Select all",
                                id="select-all-btn",
                                n_clicks=0,
                                style={
                                    "flex": "1",
                                    "padding": "6px 8px",
                                    "backgroundColor": "#ecf0f1",
                                    "color": "#2c3e50",
                                    "border": "1px solid #bdc3c7",
                                    "borderRadius": "4px",
                                    "cursor": "pointer",
                                    "fontSize": "11px",
                                },
                            ),
                            html.Button(
                                "Reset",
                                id="reset-btn",
                                n_clicks=0,
                                style={
                                    "flex": "1",
                                    "padding": "6px 8px",
                                    "backgroundColor": "#ecf0f1",
                                    "color": "#2c3e50",
                                    "border": "1px solid #bdc3c7",
                                    "borderRadius": "4px",
                                    "cursor": "pointer",
                                    "fontSize": "11px",
                                },
                            ),
                        ],
                    ),

                    html.Hr(style={"borderColor": "#e0e0e0", "margin": "15px 0"}),

                    # =====================================================
                    # Week range controls
                    # =====================================================
                    html.Label(
                        "Week Range",
                        style={
                            "color": "#2c3e50",
                            "fontWeight": "600",
                            "marginBottom": "10px",
                            "display": "block",
                            "fontSize": "13px",
                        },
                    ),

                    # Manual input fields
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "6px", "marginBottom": "8px"},
                        children=[
                            dcc.Input(
                                id="week-start-input",
                                type="number",
                                min=1,
                                max=52,
                                value=1,
                                style={
                                    "width": "70px",
                                    "padding": "6px",
                                    "border": "1px solid #d0d0d0",
                                    "borderRadius": "4px",
                                    "fontSize": "12px",
                                },
                            ),
                            html.Span("to", style={"fontSize": "12px", "color": "#7f8c8d"}),
                            dcc.Input(
                                id="week-end-input",
                                type="number",
                                min=1,
                                max=52,
                                value=52,
                                style={
                                    "width": "70px",
                                    "padding": "6px",
                                    "border": "1px solid #d0d0d0",
                                    "borderRadius": "4px",
                                    "fontSize": "12px",
                                },
                            ),
                        ],
                    ),

                    dcc.RangeSlider(
                        id="week-slider",
                        min=1,
                        max=52,
                        step=1,
                        value=[1, 52],
                        marks={1: "1", 13: "13", 26: "26", 39: "39", 52: "52"},
                        tooltip={"placement": "bottom", "always_visible": False},
                        allowCross=False,
                    ),

                    html.Div(style={"height": "10px"}),

                    # Quick time period buttons
                    html.Label(
                        "Quick Select",
                        style={
                            "color": "#2c3e50",
                            "fontWeight": "600",
                            "marginBottom": "8px",
                            "display": "block",
                            "fontSize": "13px",
                        },
                    ),

                    html.Div(
                        style={"display": "flex", "gap": "6px", "marginBottom": "8px"},
                        children=[
                            html.Button("Q1", id="q1-btn", n_clicks=0,
                                style={"flex": "1", "padding": "5px", "backgroundColor": "#ecf0f1",
                                       "color": "#2c3e50", "border": "1px solid #bdc3c7",
                                       "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                            html.Button("Q2", id="q2-btn", n_clicks=0,
                                style={"flex": "1", "padding": "5px", "backgroundColor": "#ecf0f1",
                                       "color": "#2c3e50", "border": "1px solid #bdc3c7",
                                       "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                            html.Button("Q3", id="q3-btn", n_clicks=0,
                                style={"flex": "1", "padding": "5px", "backgroundColor": "#ecf0f1",
                                       "color": "#2c3e50", "border": "1px solid #bdc3c7",
                                       "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                            html.Button("Q4", id="q4-btn", n_clicks=0,
                                style={"flex": "1", "padding": "5px", "backgroundColor": "#ecf0f1",
                                       "color": "#2c3e50", "border": "1px solid #bdc3c7",
                                       "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                        ],
                    ),

                    html.Div(
                        style={"display": "flex", "gap": "6px"},
                        children=[
                            html.Button("H1", id="h1-btn", n_clicks=0,
                                style={"flex": "1", "padding": "5px", "backgroundColor": "#ecf0f1",
                                       "color": "#2c3e50", "border": "1px solid #bdc3c7",
                                       "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                            html.Button("H2", id="h2-btn", n_clicks=0,
                                style={"flex": "1", "padding": "5px", "backgroundColor": "#ecf0f1",
                                       "color": "#2c3e50", "border": "1px solid #bdc3c7",
                                       "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                        ],
                    ),

                    html.Hr(style={"borderColor": "#e0e0e0", "margin": "15px 0"}),

                    # =====================================================
                    # Display options
                    # =====================================================
                    html.Label(
                        "Display Options",
                        style={
                            "color": "#2c3e50",
                            "fontWeight": "600",
                            "marginBottom": "10px",
                            "display": "block",
                            "fontSize": "13px",
                        },
                    ),

                    # Show event markers toggle
                    dcc.Checklist(
                        id="show-events-toggle",
                        options=[{"label": " Show event markers", "value": "show"}],
                        value=["show"],  # Default: checked (events visible)
                        style={"color": "#34495e", "fontSize": "12px"},
                        inputStyle={"marginRight": "8px"},
                        labelStyle={"display": "block", "marginBottom": "8px", "cursor": "pointer"},
                    ),

                    # Hide anomaly weeks toggle
                    dcc.Checklist(
                        id="hide-anomalies-toggle",
                        options=[{"label": " Hide anomaly weeks", "value": "hide"}],
                        value=[],  # Default: unchecked (show all data)
                        style={"color": "#34495e", "fontSize": "12px"},
                        inputStyle={"marginRight": "8px"},
                        labelStyle={"display": "block", "marginBottom": "8px", "cursor": "pointer"},
                    ),
                ],
            ),
        ],
    )


def get_sidebar_collapsed_style():
    """Return style for collapsed sidebar."""
    return {
        "width": "50px",
        "backgroundColor": "transparent",
        "borderRight": "none",
        "display": "flex",
        "flexDirection": "column",
        "transition": "width 0.3s ease",
        "overflow": "hidden",
        "flexShrink": "0",
        "borderRadius": "0 12px 12px 0",
    }


def get_sidebar_expanded_style():
    """Return style for expanded sidebar."""
    return {
        "width": "240px",
        "backgroundColor": "#f8f9fa",
        "display": "flex",
        "flexDirection": "column",
        "transition": "width 0.3s ease",
        "overflow": "hidden",
        "flexShrink": "0",
        "borderRight": "1px solid #e0e0e0",
        "borderRadius": "0 12px 12px 0",
    }
