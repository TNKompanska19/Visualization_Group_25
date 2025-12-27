"""
Sidebar Menu Component
JBI100 Visualization - Group 25

Contains the sidebar with filtering controls:
- Department selection
- Week range slider
- Quick select buttons
"""

from dash import html, dcc
from jbi100_app.config import DEPT_LABELS


def create_sidebar():
    """
    Create the sidebar component with all controls.
    
    Interaction justification (Yi et al. taxonomy):
    - Filter: Department checkboxes, week range slider
    - Select: Quick select buttons for time periods
    - Abstract/Elaborate: Zoom level indicator shows semantic zoom state
    """
    return html.Div(
        id="sidebar",
        style={
            "width": "240px",
            "backgroundColor": "#f8f9fa",
            "display": "flex",
            "flexDirection": "column",
            "transition": "width 0.3s ease",
            "overflow": "hidden",
            "flexShrink": "0",
            "borderRight": "1px solid #e0e0e0",
            "borderRadius": "0 12px 12px 0"
        },
        children=[
            # Toggle button container
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
                            "gap": "6px"
                        },
                        children=[
                            html.Span("☰", id="sidebar-icon", style={"fontSize": "16px"}),
                            html.Span("Options", id="sidebar-title")
                        ]
                    )
                ]
            ),
            
            # Sidebar content
            html.Div(
                id="sidebar-content",
                style={"padding": "15px", "overflowY": "auto"},
                children=[
                    # Department filter
                    html.Label(
                        "Departments",
                        style={"color": "#2c3e50", "fontWeight": "600", "marginBottom": "10px", "display": "block", "fontSize": "13px"}
                    ),
                    dcc.Checklist(
                        id="dept-filter",
                        options=[{"label": f" {DEPT_LABELS[dept]}", "value": dept} for dept in DEPT_LABELS],
                        value=["emergency"],
                        style={"color": "#34495e", "fontSize": "12px"},
                        inputStyle={"marginRight": "8px"},
                        labelStyle={"display": "block", "marginBottom": "8px", "cursor": "pointer"}
                    ),
                    
                    html.Hr(style={"borderColor": "#e0e0e0", "margin": "15px 0"}),
                    
                    # Week range controls
                    html.Label(
                        "Week Range",
                        style={"color": "#2c3e50", "fontWeight": "600", "marginBottom": "10px", "display": "block", "fontSize": "13px"}
                    ),
                    
                    # Manual input fields
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px", "marginBottom": "10px"},
                        children=[
                            dcc.Input(
                                id="week-start-input",
                                type="number",
                                min=1, max=52, value=1,
                                debounce=True,
                                style={
                                    "width": "45px", "padding": "4px", "borderRadius": "4px",
                                    "border": "1px solid #ccc", "backgroundColor": "white",
                                    "color": "#2c3e50", "textAlign": "center", "fontSize": "12px"
                                }
                            ),
                            html.Span("to", style={"color": "#7f8c8d", "fontSize": "12px"}),
                            dcc.Input(
                                id="week-end-input",
                                type="number",
                                min=1, max=52, value=52,
                                debounce=True,
                                style={
                                    "width": "45px", "padding": "4px", "borderRadius": "4px",
                                    "border": "1px solid #ccc", "backgroundColor": "white",
                                    "color": "#2c3e50", "textAlign": "center", "fontSize": "12px"
                                }
                            ),
                        ]
                    ),
                    
                    # Range slider
                    dcc.RangeSlider(
                        id="week-slider",
                        min=1, max=52, step=1,
                        value=[1, 52],
                        marks={
                            1: {"label": "1", "style": {"color": "#7f8c8d", "fontSize": "10px"}},
                            26: {"label": "26", "style": {"color": "#7f8c8d", "fontSize": "10px"}},
                            52: {"label": "52", "style": {"color": "#7f8c8d", "fontSize": "10px"}}
                        },
                        tooltip={"placement": "bottom", "always_visible": False},
                        allowCross=False
                    ),
                    
                    # Zoom level indicator (Semantic Zoom feedback)
                    html.Div(
                        id="zoom-level-indicator",
                        children="🌐 Overview",
                        style={
                            "color": "#95a5a6",
                            "fontSize": "10px",
                            "textAlign": "center",
                            "marginTop": "5px",
                            "padding": "4px",
                            "backgroundColor": "#ecf0f1",
                            "borderRadius": "4px"
                        }
                    ),
                    
                    html.Hr(style={"borderColor": "#e0e0e0", "margin": "15px 0"}),
                    
                    # Quick select buttons
                    html.Label(
                        "Quick Select",
                        style={"color": "#2c3e50", "fontWeight": "600", "marginBottom": "8px", "display": "block", "fontSize": "13px"}
                    ),
                    html.Div(
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "8px"},
                        children=[
                            html.Button("All Depts", id="select-all-btn", n_clicks=0,
                                style={"padding": "6px", "backgroundColor": "#3498db", "color": "white", "border": "none", "borderRadius": "4px", "cursor": "pointer", "fontSize": "11px"}),
                            html.Button("Reset", id="reset-btn", n_clicks=0,
                                style={"padding": "6px", "backgroundColor": "#e74c3c", "color": "white", "border": "none", "borderRadius": "4px", "cursor": "pointer", "fontSize": "11px"}),
                        ]
                    ),
                    
                    html.Hr(style={"borderColor": "#e0e0e0", "margin": "15px 0"}),
                    
                    # Time period buttons
                    html.Label(
                        "Time Periods",
                        style={"color": "#2c3e50", "fontWeight": "600", "marginBottom": "8px", "display": "block", "fontSize": "13px"}
                    ),
                    html.Div(
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr 1fr", "gap": "4px"},
                        children=[
                            html.Button(f"Q{i}", id=f"q{i}-btn", n_clicks=0,
                                style={"padding": "5px", "backgroundColor": "#ecf0f1", "color": "#2c3e50", "border": "1px solid #bdc3c7", "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"})
                            for i in range(1, 5)
                        ]
                    ),
                    html.Div(
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "4px", "marginTop": "4px"},
                        children=[
                            html.Button("H1", id="h1-btn", n_clicks=0,
                                style={"padding": "5px", "backgroundColor": "#ecf0f1", "color": "#2c3e50", "border": "1px solid #bdc3c7", "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                            html.Button("H2", id="h2-btn", n_clicks=0,
                                style={"padding": "5px", "backgroundColor": "#ecf0f1", "color": "#2c3e50", "border": "1px solid #bdc3c7", "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                        ]
                    ),
                    
                    html.Hr(style={"borderColor": "#e0e0e0", "margin": "15px 0"}),
                    
                    # Display options
                    html.Label(
                        "Display Options",
                        style={"color": "#2c3e50", "fontWeight": "600", "marginBottom": "10px", "display": "block", "fontSize": "13px"}
                    ),
                    
                    # Show event markers toggle
                    dcc.Checklist(
                        id="show-events-toggle",
                        options=[{"label": " Show event markers", "value": "show"}],
                        value=["show"],  # Default: checked (events visible)
                        style={"color": "#34495e", "fontSize": "12px"},
                        inputStyle={"marginRight": "8px"},
                        labelStyle={"display": "block", "marginBottom": "8px", "cursor": "pointer"}
                    ),
                    
                    # Hide anomaly weeks toggle
                    dcc.Checklist(
                        id="hide-anomalies-toggle",
                        options=[{"label": " Hide anomaly weeks", "value": "hide"}],
                        value=[],  # Default: unchecked (show all data)
                        style={"color": "#34495e", "fontSize": "12px"},
                        inputStyle={"marginRight": "8px"},
                        labelStyle={"display": "block", "marginBottom": "8px", "cursor": "pointer"}
                    )
                ]
            )
        ]
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
        "borderRadius": "0 12px 12px 0"
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
        "borderRadius": "0 12px 12px 0"
    }
