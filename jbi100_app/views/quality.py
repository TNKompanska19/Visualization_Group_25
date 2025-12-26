"""
Quality Widget (T4, T5, T6): Quality & Staff Analysis
JBI100 Visualization - Group 25

Tasks:
- T4: Discover correlations between satisfaction factors
- T5: Explore staff configurations → morale dependency
- T6: Locate extreme staff (best/worst performers)

Visual Encoding Justification:
- Parallel Coordinates Plot (PCP): Multivariate analysis (Munzner Ch. 12)
- Correlation matrix: Heatmap for pairwise correlations
- Scatter plot: Bivariate relationship analysis
"""

import plotly.graph_objects as go
import numpy as np
from dash import html, dcc

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS, WIDGET_INFO, CHART_CONFIG


def create_pcp(df, selected_depts):
    """
    Create Parallel Coordinates Plot for multivariate analysis.
    
    Theoretical justification (Munzner M5_01):
    - Shows relationships between multiple quantitative attributes
    - Patterns: parallel lines = positive correlation, crossing = negative
    - Supports brushing on axes for filtering
    
    Args:
        df: Services dataframe
        selected_depts: List of department IDs
    
    Returns:
        plotly.graph_objects.Figure
    """
    if selected_depts:
        pcp_df = df[df["service"].isin(selected_depts)].copy()
    else:
        pcp_df = df.copy()
    
    # Map services to numeric for coloring
    service_map = {s: i for i, s in enumerate(pcp_df["service"].unique())}
    pcp_df["service_num"] = pcp_df["service"].map(service_map)
    
    dimensions = [
        dict(label="Week", values=pcp_df["week"], range=[1, 52]),
        dict(label="Beds", values=pcp_df["available_beds"]),
        dict(label="Admitted", values=pcp_df["patients_admitted"]),
        dict(label="Refused", values=pcp_df["patients_refused"]),
        dict(label="Satisfaction", values=pcp_df["patient_satisfaction"], range=[0, 100]),
        dict(label="Morale", values=pcp_df["staff_morale"], range=[0, 100])
    ]
    
    # Color scale for services
    services = list(pcp_df["service"].unique())
    color_vals = [DEPT_COLORS.get(s, "#999") for s in services]
    
    fig = go.Figure(data=go.Parcoords(
        line=dict(
            color=pcp_df["service_num"],
            colorscale=[[i / max(1, len(services) - 1), color_vals[i]] for i in range(len(services))],
            showscale=False
        ),
        dimensions=dimensions,
        labelangle=-30,
        labelside="top"
    ))
    
    fig.update_layout(
        margin=dict(l=60, r=80, t=30, b=30),
        paper_bgcolor="white"
    )
    
    return fig


def create_correlation_matrix(df):
    """
    Create correlation matrix heatmap.
    
    Args:
        df: Services dataframe
    
    Returns:
        plotly.graph_objects.Figure
    """
    cols = ["available_beds", "patients_admitted", "patients_refused", 
            "patient_satisfaction", "staff_morale"]
    labels = ["Beds", "Admitted", "Refused", "Satisfaction", "Morale"]
    
    corr = df[cols].corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=labels,
        y=labels,
        colorscale="RdBu_r",
        zmid=0, zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr.values],
        texttemplate="%{text}",
        textfont=dict(size=9),
        colorbar=dict(title="r", thickness=10)
    ))
    
    fig.update_layout(
        margin=dict(l=60, r=20, t=10, b=60),
        xaxis=dict(tickangle=-45),
        yaxis=dict(autorange="reversed"),
        paper_bgcolor="white"
    )
    
    return fig


def create_quality_expanded(services_df, selected_depts, week_range):
    """
    Create the expanded quality widget layout.
    
    Args:
        services_df: Services dataframe
        selected_depts: List of department IDs
        week_range: tuple of (start_week, end_week)
    
    Returns:
        dash.html.Div component
    """
    info = WIDGET_INFO["quality"]
    
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
    
    # Placeholder content - to be implemented with PCP
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
        children=["[ QUALITY CHARTS - T4, T5 & T6 - PCP HERE ]"]
    )
    
    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column"},
        children=[header, content]
    )


def create_quality_mini(services_df, selected_depts, week_range):
    """
    Create the mini quality widget card.
    
    Args:
        services_df: Services dataframe
        selected_depts: List of department IDs
        week_range: tuple of (start_week, end_week)
    
    Returns:
        dash.html.Div component
    """
    info = WIDGET_INFO["quality"]
    
    # Calculate summary metrics
    week_min, week_max = week_range
    filtered = services_df[(services_df["week"] >= week_min) & (services_df["week"] <= week_max)]
    
    if selected_depts:
        filtered = filtered[filtered["service"].isin(selected_depts)]
    
    avg_satisfaction = filtered["patient_satisfaction"].mean() if len(filtered) > 0 else 0
    avg_morale = filtered["staff_morale"].mean() if len(filtered) > 0 else 0
    
    # Calculate correlation
    if len(filtered) > 1:
        corr = filtered["patient_satisfaction"].corr(filtered["staff_morale"])
    else:
        corr = 0
    
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
                    html.Div(f"{avg_satisfaction:.0f}", style={"fontSize": "18px", "fontWeight": "600", "color": "#27ae60"}),
                    html.Div("Satisfaction", style={"fontSize": "10px", "color": "#95a5a6"})
                ], style={"textAlign": "center"}),
                html.Div([
                    html.Div(f"{avg_morale:.0f}", style={"fontSize": "18px", "fontWeight": "600", "color": "#9b59b6"}),
                    html.Div("Morale", style={"fontSize": "10px", "color": "#95a5a6"})
                ], style={"textAlign": "center"})
            ]
        ),
        html.Div(
            "↑ Click to expand",
            style={"fontSize": "11px", "color": "#3498db", "fontWeight": "500", "marginTop": "8px", "textAlign": "center"}
        )
    ])
