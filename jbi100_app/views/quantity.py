"""
Quantity Widget (T2, T3): Capacity & Patient Flow Analysis
JBI100 Visualization - Group 25

Tasks:
- T2: Explore distribution/extremes of bed allocation
- T3: Summarize stay duration distribution

Visual Encoding Justification:
- Scatter plot: Shows relationship between beds and refusal rate
- Box plot: Distribution summary for length of stay
- Bar chart: Categorical comparison of refusals by service
"""

import plotly.graph_objects as go
from dash import html, dcc

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS, WIDGET_INFO, CHART_CONFIG


def create_quantity_expanded(services_df, patients_df, selected_depts, week_range):
    """
    Create the expanded quantity widget layout.
    
    Args:
        services_df: Services dataframe
        patients_df: Patients dataframe
        selected_depts: List of department IDs
        week_range: tuple of (start_week, end_week)
    
    Returns:
        dash.html.Div component
    """
    info = WIDGET_INFO["quantity"]
    
    header = html.Div(
        style={
            "paddingBottom": "8px",
            "marginBottom": "10px",
            "borderBottom": "2px solid #eee",
            "flexShrink": "0"
        },
        children=[
            html.H4(
                f"{info['icon']} {info['title']}",
                style={"margin": "0", "color": "#2c3e50", "fontWeight": "500"}
            ),
            html.Span(info["subtitle"], style={"fontSize": "12px", "color": "#999"})
        ]
    )
    
    # Placeholder content - to be implemented
    content = html.Div(
        style={
            "flex": "1",
            "backgroundColor": "#f8f9fa",
            "borderRadius": "8px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "color": "#bbb",
            "fontSize": "18px"
        },
        children=["[ QUANTITY CHARTS - T2 & T3 ]"]
    )
    
    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column"},
        children=[header, content]
    )


def create_quantity_mini(services_df, selected_depts, week_range):
    """
    Create the mini quantity widget card.
    
    Args:
        services_df: Services dataframe
        selected_depts: List of department IDs
        week_range: tuple of (start_week, end_week)
    
    Returns:
        dash.html.Div component
    """
    info = WIDGET_INFO["quantity"]
    
    # Calculate summary metrics
    week_min, week_max = week_range
    filtered = services_df[(services_df["week"] >= week_min) & (services_df["week"] <= week_max)]
    
    if selected_depts:
        filtered = filtered[filtered["service"].isin(selected_depts)]
    
    total_refused = filtered["patients_refused"].sum() if len(filtered) > 0 else 0
    avg_utilization = filtered["utilization_rate"].mean() if len(filtered) > 0 else 0
    
    return html.Div([
        html.Div(
            f"{info['icon']} {info['title']}",
            style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "5px", "color": "#2c3e50"}
        ),
        html.Div(
            info["subtitle"],
            style={"fontSize": "11px", "color": "#999", "marginBottom": "8px"}
        ),
        html.Div(
            style={
                "flex": "1",
                "backgroundColor": "#f8f9fa",
                "borderRadius": "6px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-around",
                "padding": "10px"
            },
            children=[
                html.Div([
                    html.Div(f"{total_refused:,}", style={"fontSize": "18px", "fontWeight": "600", "color": "#e74c3c"}),
                    html.Div("Refused", style={"fontSize": "10px", "color": "#95a5a6"})
                ], style={"textAlign": "center"}),
                html.Div([
                    html.Div(f"{avg_utilization:.0f}%", style={"fontSize": "18px", "fontWeight": "600", "color": "#3498db"}),
                    html.Div("Utilization", style={"fontSize": "10px", "color": "#95a5a6"})
                ], style={"textAlign": "center"})
            ]
        ),
        html.Div(
            "↑ Click to expand",
            style={"fontSize": "11px", "color": "#3498db", "fontWeight": "500", "marginTop": "8px", "textAlign": "center"}
        )
    ])
