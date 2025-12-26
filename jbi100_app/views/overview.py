"""
Overview Widget (T1): Hospital Performance Overview
JBI100 Visualization - Group 25

Task: Browse trends and identify outliers in hospital performance metrics.

Visual Encoding Justification:
- Line chart: Best for showing trends over ordered time (Munzner Ch. 7)
- Position on common scale: Most accurate for quantitative comparison
- Color hue: Categorical distinction between departments

Interaction:
- Semantic Zoom: Different detail levels based on time range (Munzner Ch. 11)
- Brushing: Hover highlights corresponding data across both charts
- Pan: Navigate through time while maintaining context
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import html, dcc

from jbi100_app.config import (
    DEPT_COLORS, DEPT_LABELS, DEPT_LABELS_SHORT,
    EVENT_COLORS, EVENT_ICONS, WIDGET_INFO, ZOOM_THRESHOLDS, CHART_CONFIG
)


def get_zoom_level(week_range):
    """
    Determine zoom level for semantic zoom.
    
    Theoretical basis: Munzner Ch. 11 - Navigate
    - Semantic zoom changes visual encoding based on zoom level
    - Supports Shneiderman's mantra: "Overview first, zoom and filter, details on demand"
    
    Args:
        week_range: tuple of (start_week, end_week)
    
    Returns:
        str: "detail", "quarter", or "overview"
    """
    span = week_range[1] - week_range[0] + 1
    
    if span <= ZOOM_THRESHOLDS["detail"]:
        return "detail"      # Show everything: labels, events, thresholds
    elif span <= ZOOM_THRESHOLDS["quarter"]:
        return "quarter"     # Show events + larger markers
    else:
        return "overview"    # Minimal, clean lines only


def create_overview_charts(df, selected_depts, week_range):
    """
    Create the main overview visualization with semantic zoom.
    
    Visualization idiom: Dual line charts (shared x-axis)
    - Top: Patient satisfaction over time
    - Bottom: Acceptance rate over time
    
    Args:
        df: Services dataframe
        selected_depts: List of department IDs to show
        week_range: tuple of (start_week, end_week)
    
    Returns:
        plotly.graph_objects.Figure
    """
    week_min, week_max = week_range
    zoom_level = get_zoom_level(week_range)
    
    # Create subplots with shared x-axis
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.18,
        subplot_titles=("Patient Satisfaction by Department", "Acceptance Rate by Department")
    )
    
    # Adjust visual parameters based on zoom level (Semantic Zoom)
    marker_sizes = {"overview": 5, "quarter": 8, "detail": 12}
    line_widths = {"overview": 2, "quarter": 2.5, "detail": 3}
    
    marker_size = marker_sizes[zoom_level]
    line_width = line_widths[zoom_level]
    
    # Add traces for each department
    for dept in selected_depts:
        dept_data = df[df["service"] == dept].sort_values("week")
        
        # Satisfaction trace
        fig.add_trace(go.Scatter(
            x=dept_data["week"],
            y=dept_data["patient_satisfaction"],
            name=DEPT_LABELS[dept],
            line=dict(color=DEPT_COLORS[dept], width=line_width),
            mode="lines+markers",
            marker=dict(size=marker_size, color=DEPT_COLORS[dept]),
            hoverinfo="none",
            legendgroup=dept
        ), row=1, col=1)
        
        # Acceptance rate trace
        fig.add_trace(go.Scatter(
            x=dept_data["week"],
            y=dept_data["acceptance_rate"],
            name=DEPT_LABELS[dept],
            line=dict(color=DEPT_COLORS[dept], width=line_width),
            mode="lines+markers",
            marker=dict(size=marker_size, color=DEPT_COLORS[dept]),
            hoverinfo="none",
            legendgroup=dept,
            showlegend=False
        ), row=2, col=1)
        
        # DETAIL ZOOM: Add data labels on points
        # Justification: Details-on-demand at high zoom (Shneiderman)
        if zoom_level == "detail":
            visible_data = dept_data[
                (dept_data["week"] >= week_min) & (dept_data["week"] <= week_max)
            ]
            for _, row in visible_data.iterrows():
                # Satisfaction labels
                fig.add_annotation(
                    x=row["week"],
                    y=row["patient_satisfaction"],
                    text=str(int(row["patient_satisfaction"])),
                    showarrow=False,
                    yshift=15,
                    font=dict(size=10, color=DEPT_COLORS[dept]),
                    row=1, col=1
                )
                # Acceptance labels
                fig.add_annotation(
                    x=row["week"],
                    y=row["acceptance_rate"],
                    text=f"{row['acceptance_rate']:.0f}",
                    showarrow=False,
                    yshift=15,
                    font=dict(size=10, color=DEPT_COLORS[dept]),
                    row=2, col=1
                )
    
    # QUARTER & DETAIL ZOOM: Add event markers
    # Justification: Context layer showing external factors (Focus+Context)
    if zoom_level in ["quarter", "detail"]:
        events_in_range = df[
            (df["week"] >= week_min) & 
            (df["week"] <= week_max) & 
            (df["event"] != "none")
        ]
        events_by_week = events_in_range.groupby("week")["event"].first()
        
        for week, event in events_by_week.items():
            if event in EVENT_COLORS:
                # Vertical line for event
                fig.add_vline(
                    x=week,
                    line_dash="dot",
                    line_color=EVENT_COLORS.get(event, "#95a5a6"),
                    line_width=1,
                    opacity=0.7
                )
                # Event icon at top
                icon = EVENT_ICONS.get(event, "⚡")
                fig.add_annotation(
                    x=week, y=100,
                    text=f"{icon}",
                    showarrow=False,
                    yshift=10,
                    font=dict(size=14),
                    row=1, col=1
                )
    
    # DETAIL ZOOM: Add threshold reference lines
    # Justification: Reference marks for comparison (Cleveland & McGill)
    if zoom_level == "detail":
        fig.add_hline(
            y=75, line_dash="dash", line_color="#27ae60",
            line_width=1, opacity=0.5,
            annotation_text="Target 75%",
            annotation_position="right",
            row=1, col=1
        )
        fig.add_hline(
            y=60, line_dash="dash", line_color="#e74c3c",
            line_width=1, opacity=0.5,
            annotation_text="Critical 60%",
            annotation_position="right",
            row=1, col=1
        )
    
    # Layout configuration
    fig.update_layout(
        height=450,
        margin=dict(l=60, r=20, t=40, b=60),
        hovermode="x",
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        dragmode="pan"  # Enable pan interaction
    )
    
    # X-axis: Time
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#f0f0f0",
        dtick=4,
        range=[week_min - 0.5, week_max + 0.5],
        fixedrange=False  # Allow panning
    )
    
    # Y-axis: Percentage scale
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#e0e0e0",
        zeroline=False,
        range=[0, 100],
        dtick=25,
        fixedrange=True  # Fixed to prevent vertical zoom
    )
    
    fig.update_yaxes(title_text="Satisfaction", row=1, col=1)
    fig.update_yaxes(title_text="Acceptance %", row=2, col=1)
    fig.update_xaxes(title_text="Week", row=2, col=1)
    
    return fig


def create_overview_expanded(df, selected_depts, week_range):
    """
    Create the expanded overview widget layout.
    
    Args:
        df: Services dataframe
        selected_depts: List of department IDs
        week_range: tuple of (start_week, end_week)
    
    Returns:
        dash.html.Div component
    """
    info = WIDGET_INFO["overview"]
    
    # Header
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
    
    if not selected_depts:
        content = html.Div(
            "Please select at least one department",
            style={
                "flex": "1",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "color": "#999"
            }
        )
    else:
        content = html.Div(
            style={"flex": "1", "display": "flex", "gap": "12px", "minHeight": "0"},
            children=[
                # Chart container
                html.Div(
                    id="chart-container",
                    style={"flex": "1", "position": "relative", "minWidth": "0"},
                    children=[
                        dcc.Graph(
                            id="overview-chart",
                            figure=create_overview_charts(df, selected_depts, week_range),
                            style={"height": "100%", "width": "100%"},
                            config=CHART_CONFIG
                        ),
                        # Hover highlight overlay
                        html.Div(
                            id="hover-highlight",
                            style={
                                "position": "absolute",
                                "top": "15px",
                                "bottom": "25px",
                                "width": "14px",
                                "backgroundColor": "rgba(52, 152, 219, 0.2)",
                                "pointerEvents": "none",
                                "display": "none",
                                "borderRadius": "3px",
                                "left": "60px"
                            }
                        )
                    ]
                ),
                # Side tooltip panel
                html.Div(
                    id="side-tooltip",
                    style={
                        "width": "150px",
                        "backgroundColor": "#f8f9fa",
                        "borderRadius": "8px",
                        "padding": "10px",
                        "border": "1px solid #e0e0e0",
                        "flexShrink": "0",
                        "fontSize": "11px"
                    },
                    children=[
                        html.Div(
                            id="tooltip-content",
                            children=[
                                html.Div("Hover over", style={"color": "#999", "textAlign": "center"}),
                                html.Div("the chart", style={"color": "#999", "textAlign": "center"})
                            ]
                        )
                    ]
                )
            ]
        )
    
    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column"},
        children=[header, content]
    )


def create_overview_mini(df, selected_depts, week_range):
    """
    Create the mini overview widget card.
    
    Args:
        df: Services dataframe
        selected_depts: List of department IDs
        week_range: tuple of (start_week, end_week)
    
    Returns:
        dash.html.Div component
    """
    info = WIDGET_INFO["overview"]
    
    # Calculate summary metrics
    week_min, week_max = week_range
    filtered = df[(df["week"] >= week_min) & (df["week"] <= week_max)]
    
    if selected_depts:
        filtered = filtered[filtered["service"].isin(selected_depts)]
    
    avg_satisfaction = filtered["patient_satisfaction"].mean() if len(filtered) > 0 else 0
    avg_acceptance = filtered["acceptance_rate"].mean() if len(filtered) > 0 else 0
    
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
                    html.Div(f"{avg_satisfaction:.0f}", style={"fontSize": "18px", "fontWeight": "600", "color": "#2c3e50"}),
                    html.Div("Satisfaction", style={"fontSize": "10px", "color": "#95a5a6"})
                ], style={"textAlign": "center"}),
                html.Div([
                    html.Div(f"{avg_acceptance:.0f}%", style={"fontSize": "18px", "fontWeight": "600", "color": "#2c3e50"}),
                    html.Div("Acceptance", style={"fontSize": "10px", "color": "#95a5a6"})
                ], style={"textAlign": "center"})
            ]
        ),
        html.Div(
            "↑ Click to expand",
            style={"fontSize": "11px", "color": "#3498db", "fontWeight": "500", "marginTop": "8px", "textAlign": "center"}
        )
    ])


def build_tooltip_content(week, week_data, selected_depts, df, week_range):
    """
    Build tooltip content for hover display.
    
    Args:
        week: Current week number
        week_data: Dict of week data from store
        selected_depts: List of department IDs
        df: Services dataframe (for event lookup)
        week_range: Current week range (for zoom level)
    
    Returns:
        list: List of dash html components
    """
    # Check for events this week
    week_events = df[(df["week"] == week) & (df["event"] != "none")]["event"].unique()
    
    tooltip_children = [
        html.Div(
            f"Week {week}",
            style={
                "fontWeight": "600",
                "fontSize": "13px",
                "color": "#2c3e50",
                "paddingBottom": "6px",
                "marginBottom": "8px",
                "borderBottom": "2px solid #3498db"
            }
        )
    ]
    
    # Add event badges if present
    if len(week_events) > 0:
        for evt in week_events:
            if evt in EVENT_ICONS:
                evt_color = EVENT_COLORS.get(evt, "#95a5a6")
                tooltip_children.append(
                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "4px",
                            "marginBottom": "6px",
                            "padding": "3px 6px",
                            "backgroundColor": evt_color + "20",
                            "borderRadius": "4px",
                            "border": f"1px solid {evt_color}"
                        },
                        children=[
                            html.Span(EVENT_ICONS[evt], style={"fontSize": "12px"}),
                            html.Span(evt.capitalize(), style={"fontSize": "10px", "color": evt_color, "fontWeight": "600"})
                        ]
                    )
                )
    
    # Satisfaction section
    tooltip_children.append(
        html.Div("SATISFACTION", style={"fontSize": "9px", "color": "#888", "marginBottom": "4px", "fontWeight": "600"})
    )
    
    for dept in selected_depts:
        data = week_data.get(str(week), {}).get(dept)
        if data:
            tooltip_children.append(
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "marginBottom": "2px"},
                    children=[
                        html.Span(DEPT_LABELS_SHORT[dept], style={"color": "#555"}),
                        html.Span(str(data["satisfaction"]), style={"fontWeight": "600", "color": DEPT_COLORS[dept]})
                    ]
                )
            )
    
    # Acceptance section
    tooltip_children.append(
        html.Div("ACCEPTANCE %", style={"fontSize": "9px", "color": "#888", "margin": "8px 0 4px 0", "fontWeight": "600"})
    )
    
    for dept in selected_depts:
        data = week_data.get(str(week), {}).get(dept)
        if data:
            tooltip_children.append(
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "marginBottom": "2px"},
                    children=[
                        html.Span(DEPT_LABELS_SHORT[dept], style={"color": "#555"}),
                        html.Span(f"{data['acceptance']}%", style={"fontWeight": "600", "color": DEPT_COLORS[dept]})
                    ]
                )
            )
    
    return tooltip_children
