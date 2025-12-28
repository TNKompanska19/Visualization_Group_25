"""
Overview Widget (T1): Hospital Performance Overview
JBI100 Visualization - Group 25

Task: Browse trends and identify outliers in hospital performance metrics.

Visual Encoding Justification:
- Line chart: Best for showing trends over ordered time (Munzner Ch. 7)
- KDE: Shows distribution, highlights where current value sits
- Juxtaposition: Side-by-side comparison of trend vs distribution (Munzner Ch. 12)
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from dash import html, dcc

from jbi100_app.config import (
    DEPT_COLORS, DEPT_LABELS, DEPT_LABELS_SHORT,
    EVENT_COLORS, EVENT_ICONS, WIDGET_INFO, ZOOM_THRESHOLDS, CHART_CONFIG,
    SEMANTIC_COLORS
)


def get_zoom_level(week_range):
    """Determine zoom level for semantic zoom."""
    span = week_range[1] - week_range[0] + 1
    
    if span <= ZOOM_THRESHOLDS["detail"]:
        return "detail"
    elif span <= ZOOM_THRESHOLDS["quarter"]:
        return "quarter"
    else:
        return "overview"


def create_overview_charts(df, selected_depts, week_range, show_events=True, hide_anomalies=False):
    """Create the main overview visualization with threshold lines and event markers.
    
    Args:
        show_events: If True, display event markers (default: True)
        hide_anomalies: If True, filter out weeks with no staff assigned (default: False)
    """
    week_min, week_max = week_range
    zoom_level = get_zoom_level(week_range)
    
    # Filter out anomaly weeks if requested
    # Anomaly = weeks where NO staff members were assigned (present=0 for all staff)
    if hide_anomalies:
        from jbi100_app.data import load_staff_schedule
        staff_df = load_staff_schedule()
        
        # Find weeks with at least 1 staff member present
        weeks_with_staff = staff_df[staff_df["present"] == 1]["week"].unique()
        
        # Filter to only those weeks (removes 17 anomaly weeks: 3,6,9,12,15,18,21,24,27,30,33,36,39,42,45,48,51)
        df = df[df["week"].isin(weeks_with_staff)].copy()
    
    # Create subplots with more vertical spacing for events
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.18,  # Large gap to accommodate many stacked event markers
        subplot_titles=None
    )
    
    marker_sizes = {"overview": 5, "quarter": 8, "detail": 10}
    line_widths = {"overview": 2, "quarter": 2.5, "detail": 2.5}
    marker_size = marker_sizes[zoom_level]
    line_width = line_widths[zoom_level]
    
    # Store original marker size for hover effect
    base_marker_size = marker_size
    
    # Add traces with hover-responsive markers
    for dept_idx, dept in enumerate(selected_depts):
        dept_data = df[df["service"] == dept].sort_values("week")
        
        # Satisfaction trace with hover effect
        fig.add_trace(go.Scatter(
            x=dept_data["week"],
            y=dept_data["patient_satisfaction"],
            name=DEPT_LABELS[dept],
            line=dict(color=DEPT_COLORS[dept], width=line_width),
            mode="lines+markers",
            marker=dict(
                size=base_marker_size, 
                color=DEPT_COLORS[dept],
                line=dict(width=0)  # No border by default
            ),
            # Hover styling - marker gets bigger and white border
            hoverlabel=dict(
                bgcolor=DEPT_COLORS[dept],
                font_size=11,
                font_color="white"
            ),
            hoverinfo="none",
            legendgroup=dept,
            customdata=[[dept, dept_idx]] * len(dept_data),
            meta={"dept": dept, "dept_idx": dept_idx}
        ), row=1, col=1)
        
        # Acceptance trace with hover effect
        fig.add_trace(go.Scatter(
            x=dept_data["week"],
            y=dept_data["acceptance_rate"],
            name=DEPT_LABELS[dept],
            line=dict(color=DEPT_COLORS[dept], width=line_width),
            mode="lines+markers",
            marker=dict(
                size=base_marker_size, 
                color=DEPT_COLORS[dept],
                line=dict(width=0)
            ),
            hoverinfo="none",
            legendgroup=dept,
            showlegend=False,
            customdata=[[dept, dept_idx]] * len(dept_data),
            meta={"dept": dept, "dept_idx": dept_idx}
        ), row=2, col=1)
    
    # SMART THRESHOLD LOGIC based on selection count
    # Justification: Balance detail vs clutter (Tufte's data-ink ratio)
    # - 1 dept: Show μ ± 2σ bands (global baseline for SPC-style monitoring)
    # - 2 depts: Show 2 mean lines (dept-colored, enable comparison)
    # - 3-4 depts: No thresholds (avoid visual clutter)
    num_selected = len(selected_depts)
    
    if num_selected == 1:
        # Single department: Show full statistical control limits (±2σ for 95% CI)
        dept = selected_depts[0]
        for row, metric in [(1, "patient_satisfaction"), (2, "acceptance_rate")]:
            # Global stats: ALL 52 weeks for this department
            metric_data = df[df["service"] == dept][metric]
            mean_val = metric_data.mean()
            std_val = metric_data.std()
            
            # Mean line (department color)
            fig.add_hline(
                y=mean_val, 
                line_dash="solid", 
                line_color=DEPT_COLORS[dept],
                line_width=1.8, 
                opacity=0.7, 
                row=row, col=1,
                annotation_text=f"μ={mean_val:.0f}", 
                annotation_position="right",  # Back to right side
                annotation=dict(font_size=8, font_color=DEPT_COLORS[dept], xshift=10)
            )
            
            # Upper bound (μ + 2σ) - 95% CI upper limit
            upper = min(100, mean_val + 2 * std_val)
            fig.add_hline(
                y=upper, 
                line_dash="dash",  # Same as lower (both are limits)
                line_color=SEMANTIC_COLORS["threshold_upper"],
                line_width=1.2, 
                opacity=0.5, 
                row=row, col=1,
                annotation_text=f"+2σ={upper:.0f}",  # Actual value
                annotation_position="right",  # Back to right side
                annotation=dict(font_size=7, font_color=SEMANTIC_COLORS["threshold_upper"], xshift=10)
            )
            
            # Lower bound (μ - 2σ) - 95% CI lower limit
            lower = max(0, mean_val - 2 * std_val)
            fig.add_hline(
                y=lower, 
                line_dash="dash",  # Same as upper (both are limits)
                line_color=SEMANTIC_COLORS["threshold_lower"],
                line_width=1.2, 
                opacity=0.5, 
                row=row, col=1,
                annotation_text=f"-2σ={lower:.0f}",  # Actual value
                annotation_position="right",  # Back to right side
                annotation=dict(font_size=7, font_color=SEMANTIC_COLORS["threshold_lower"], xshift=10)
            )
    
    elif num_selected == 2:
        # Two departments: Show mean lines only (colored by department)
        # Color already indicates department, so just show "μ=value"
        for row, metric in [(1, "patient_satisfaction"), (2, "acceptance_rate")]:
            for dept in selected_depts:
                # Global mean: ALL 52 weeks for each department
                metric_data = df[df["service"] == dept][metric]
                mean_val = metric_data.mean()
                
                fig.add_hline(
                    y=mean_val, 
                    line_dash="solid", 
                    line_color=DEPT_COLORS[dept],
                    line_width=1.5, 
                    opacity=0.6, 
                    row=row, col=1,
                    annotation_text=f"μ={mean_val:.0f}",  # No dept name - color indicates it
                    annotation_position="right",
                    annotation=dict(font_size=8, font_color=DEPT_COLORS[dept])
                )
    
    # else: 3-4 departments → No threshold lines (avoid clutter)
    
    # Collect and display events with department-colored borders
    # NOTE: Create events for ALL weeks (not just visible range) so they appear when panning
    events_by_week = {}
    week_event_groups = {}  # Initialize empty dict
    
    if show_events:  # Only create event markers if toggle is ON
        events_in_range = df[
            (df["event"] != "none") &  # No week filter - show all events
            (df["service"].isin(selected_depts))
        ]
        
        # Group all events by week and department to prevent overlap
        for week in events_in_range["week"].unique():
            week_events = events_in_range[events_in_range["week"] == week]
            events_by_dept = {}
            for _, row in week_events.iterrows():
                dept = row["service"]
                evt = row["event"]
                if dept not in events_by_dept:
                    events_by_dept[dept] = []
                if evt not in events_by_dept[dept]:
                    events_by_dept[dept].append(evt)
            week_event_groups[week] = events_by_dept
            events_by_week[week] = events_by_dept
        
        # Add event markers - stack vertically, centered on each week's line
        for week, events_by_dept in week_event_groups.items():
            # Add subtle vertical line through both plots
            fig.add_vline(
                x=week, line_dash="dot",
                line_color="#dddddd",
                line_width=1, opacity=0.3
            )
            
            # Flatten all events for this week
            all_events = []
            for dept, dept_events in events_by_dept.items():
                for evt in dept_events:
                    all_events.append((dept, evt))
            
            # Stack events vertically, centered
            num_events = len(all_events)
            y_center = 0.50
            y_spacing = 0.05
            y_start = y_center + ((num_events - 1) * y_spacing / 2)
            
            for idx, (dept, evt) in enumerate(all_events):
                y_pos = y_start - (idx * y_spacing)
                
                fig.add_annotation(
                    x=week,
                    y=y_pos,
                    xref="x",
                    yref="paper",
                    text=EVENT_ICONS.get(evt, "⚡"),
                    showarrow=False,
                    font=dict(size=11),  # Keep your adjusted size
                    bgcolor="white",
                    bordercolor=DEPT_COLORS[dept],
                    borderwidth=1,  # Keep your adjusted thickness
                    borderpad=0,
                    opacity=1.0,
                    align="center",
                    valign="middle",
                )
    
    fig.update_layout(
        height=420,  # Increased to accommodate larger event marker gap
        margin=dict(l=40, r=60, t=15, b=45),
        hovermode="closest",
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        dragmode="pan"
    )
    
    # Y-axis titles (left aligned, above axis)
    fig.update_yaxes(
        title_text="Satisfaction",
        title_font=dict(size=10, color="#666"),
        title_standoff=5,
        row=1, col=1
    )
    fig.update_yaxes(
        title_text="Acceptance %",
        title_font=dict(size=10, color="#666"),
        title_standoff=5,
        row=2, col=1
    )
    
    dtick = 1 if zoom_level == "detail" else 4
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0", dtick=dtick,
                     range=[week_min - 0.5, week_max + 0.5], fixedrange=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e0e0e0", zeroline=False,
                     range=[0, 100], dtick=25, fixedrange=True,
                     tickfont=dict(size=9))
    fig.update_xaxes(title_text="Week", row=2, col=1, title_font=dict(size=10))
    
    return fig, events_by_week


def _hex_to_rgba(hex_color, alpha=0.5):
    """Convert hex color (short or full) to rgba string.
    
    Args:
        hex_color: '#ccc' or '#cccccc' format
        alpha: Opacity value 0-1
    
    Returns:
        String like 'rgba(204,204,204,0.5)'
    """
    hex_color = hex_color.lstrip('#')
    
    # Expand shorthand (e.g., 'ccc' -> 'cccccc')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    return f'rgba({r},{g},{b},{alpha})'


def create_histogram(df, selected_depts, metric, highlight_value=None, hovered_dept=None):
    """
    Create KDE (Kernel Density Estimate) for hovered department.
    
    Args:
        hovered_dept: If provided, show KDE for this specific department only
                     (details-on-demand interaction pattern)
    """
    # Use hovered department if provided, otherwise merge all selected
    if hovered_dept:
        filtered = df[df["service"] == hovered_dept]
    elif selected_depts:
        filtered = df[df["service"].isin(selected_depts)]
    else:
        filtered = df
    
    values = filtered[metric].values
    
    # Create smooth KDE curve (extended range for tails)
    from scipy import stats
    kde = stats.gaussian_kde(values)
    x_range = np.linspace(-10, 115, 250)  # Extended for tails
    y_density = kde(x_range)
    
    fig = go.Figure()
    
    # Fill area under curve (use department color if hovered)
    fill_color = '#ccc'
    line_color = '#ccc'
    if hovered_dept:
        dept_hex = DEPT_COLORS.get(hovered_dept, '#ccc')
        fill_color = dept_hex
        line_color = dept_hex
    
    fig.add_trace(go.Scatter(
        x=x_range,
        y=y_density,
        mode='lines',
        fill='tozeroy',
        line=dict(color=line_color, width=1.5),
        fillcolor=_hex_to_rgba(fill_color, 0.5),
        hoverinfo='skip'
    ))
    
    # Add highlighted region if value provided
    if highlight_value is not None:
        # Highlight a small region around the value
        highlight_width = 3  # +/- 3 points
        mask = (x_range >= highlight_value - highlight_width) & (x_range <= highlight_value + highlight_width)
        
        fig.add_trace(go.Scatter(
            x=x_range[mask],
            y=y_density[mask],
            mode='lines',
            fill='tozeroy',
            line=dict(color='#3498db', width=2),
            fillcolor='rgba(52, 152, 219, 0.6)',
            hoverinfo='skip'
        ))
    
    # Title shows metric + department (if hovered)
    base_title = "Satisfaction" if "satisfaction" in metric else "Acceptance"
    if hovered_dept:
        title_text = f"{base_title} - {DEPT_LABELS_SHORT.get(hovered_dept, hovered_dept)}"
    else:
        title_text = base_title
    
    fig.update_layout(
        height=175,
        margin=dict(l=5, r=5, t=20, b=20),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        title=dict(text=title_text, font=dict(size=9, color="#666"), x=0.5, y=0.95),
        xaxis=dict(range=[-10, 115], tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=7), showgrid=False),
        yaxis=dict(showticklabels=False, showgrid=False),
        showlegend=False
    )
    
    return fig


def create_event_strip(events_by_week, week_range):
    """Create a horizontal strip showing events between the two plots."""
    week_min, week_max = week_range
    
    if not events_by_week:
        return html.Div(style={"height": "20px"})
    
    # Create event markers positioned by week
    total_weeks = week_max - week_min + 1
    
    event_elements = []
    for week, events in events_by_week.items():
        # Calculate position as percentage
        position_pct = ((week - week_min) / total_weeks) * 100
        
        # Combine multiple events into one string
        emoji_str = " ".join([EVENT_ICONS.get(evt, "⚡") for evt in events])
        
        event_elements.append(
            html.Div(
                emoji_str,
                style={
                    "position": "absolute",
                    "left": f"calc({position_pct}% + 40px)",  # Offset for y-axis
                    "transform": "translateX(-50%)",
                    "fontSize": "14px",
                    "cursor": "default"
                },
                title=", ".join([evt.capitalize() for evt in events])  # Tooltip
            )
        )
    
    return html.Div(
        style={
            "position": "relative",
            "height": "22px",
            "backgroundColor": "#fafafa",
            "borderTop": "1px solid #eee",
            "borderBottom": "1px solid #eee",
            "marginLeft": "40px",
            "marginRight": "25px"
        },
        children=event_elements
    )


def create_overview_expanded(df, selected_depts, week_range, show_events=True, hide_anomalies=False):
    """Create the expanded overview widget layout with event strip between plots.
    
    Args:
        show_events: If True, display event markers
        hide_anomalies: If True, filter out anomaly weeks
    """
    info = WIDGET_INFO["overview"]
    zoom_level = get_zoom_level(week_range)
    
    # Create color legend for selected departments
    legend_items = []
    for dept in selected_depts:
        legend_items.append(
            html.Span(
                style={"display": "inline-flex", "alignItems": "center", "marginRight": "12px"},
                children=[
                    html.Span(
                        style={
                            "width": "12px",
                            "height": "12px",
                            "backgroundColor": DEPT_COLORS[dept],
                            "borderRadius": "2px",
                            "marginRight": "4px",
                            "display": "inline-block"
                        }
                    ),
                    html.Span(
                        DEPT_LABELS_SHORT[dept],
                        style={"fontSize": "10px", "color": "#555"}
                    )
                ]
            )
        )
    
    header = html.Div(
        style={
            "paddingBottom": "6px",
            "marginBottom": "8px",
            "borderBottom": "2px solid #eee",
            "flexShrink": "0"
        },
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                children=[
                    html.Div(
                        children=[
                            html.H4(
                                f"{info['icon']} {info['title']}",
                                style={"margin": "0", "color": "#2c3e50", "fontWeight": "500", "fontSize": "16px"}
                            ),
                            html.Span(info["subtitle"], style={"fontSize": "11px", "color": "#999"})
                        ]
                    ),
                    html.Div(
                        style={"display": "flex", "alignItems": "center"},
                        children=legend_items
                    ) if legend_items else None
                ]
            )
        ]
    )
    
    if not selected_depts:
        content = html.Div(
            "Please select at least one department",
            style={
                "flex": "1", "display": "flex",
                "alignItems": "center", "justifyContent": "center",
                "color": "#999"
            }
        )
    else:
        # Get chart and events
        chart_fig, events_by_week = create_overview_charts(
            df, selected_depts, week_range, show_events, hide_anomalies
        )
        
        # Main line charts
        chart_section = html.Div(
            id="chart-container",
            style={
                "flex": "1",
                "position": "relative",
                "minWidth": "0",
                "display": "flex",
                "flexDirection": "column"
            },
            children=[
                dcc.Graph(
                    id="overview-chart",
                    figure=chart_fig,
                    style={"flex": "1", "width": "100%"},
                    config=CHART_CONFIG
                ),
                html.Div(
                    id="hover-highlight",
                    style={
                        "position": "absolute",
                        "top": "10px", "bottom": "30px",
                        "width": "3px",
                        "backgroundColor": "rgba(52, 152, 219, 0.6)",
                        "pointerEvents": "none",
                        "display": "none",
                        "borderRadius": "2px",
                        "left": "40px"
                    }
                )
            ]
        )
        
        if zoom_level in ["detail", "quarter"]:
            # Detail/Quarter view: Add KDE panels (show distributions at ≤13 weeks)
            kde_section = html.Div(
                style={
                    "width": "220px",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "4px",
                    "flexShrink": "0"
                },
                children=[
                    html.Div(
                        style={"flex": "1", "backgroundColor": "#fafafa",
                               "borderRadius": "4px", "border": "1px solid #eee"},
                        children=[
                            dcc.Graph(
                                id="hist-satisfaction",
                                figure=create_histogram(df, selected_depts, "patient_satisfaction"),
                                config={"displayModeBar": False},
                                style={"height": "100%"}
                            )
                        ]
                    ),
                    html.Div(
                        style={"flex": "1", "backgroundColor": "#fafafa",
                               "borderRadius": "4px", "border": "1px solid #eee"},
                        children=[
                            dcc.Graph(
                                id="hist-acceptance",
                                figure=create_histogram(df, selected_depts, "acceptance_rate"),
                                config={"displayModeBar": False},
                                style={"height": "100%"}
                            )
                        ]
                    )
                ]
            )
            
            # Tooltip panel
            tooltip_section = html.Div(
                id="side-tooltip",
                style={
                    "width": "95px",  # Slightly wider now that annotations are moved
                    "backgroundColor": "#f8f9fa",
                    "borderRadius": "6px",
                    "padding": "7px",
                    "border": "1px solid #e0e0e0",
                    "flexShrink": "0",
                    "fontSize": "9px",
                    "overflow": "hidden"
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
            
            content = html.Div(
                style={"flex": "1", "display": "flex", "gap": "8px", "minHeight": "0"},
                children=[chart_section, kde_section, tooltip_section]
            )
        else:
            # Overview/Quarter: Just line charts + tooltip
            tooltip_section = html.Div(
                id="side-tooltip",
                style={
                    "width": "95px",
                    "backgroundColor": "#f8f9fa",
                    "borderRadius": "6px",
                    "padding": "7px",
                    "border": "1px solid #e0e0e0",
                    "flexShrink": "0",
                    "fontSize": "9px"
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
            
            content = html.Div(
                style={"flex": "1", "display": "flex", "gap": "10px", "minHeight": "0"},
                children=[chart_section, tooltip_section]
            )
    
    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column"},
        children=[header, content]
    )


def create_overview_mini_lines(df, selected_depts, week_range):
    """Create mini line chart showing satisfaction per department."""
    week_min, week_max = week_range
    filtered = df[(df["week"] >= week_min) & (df["week"] <= week_max)]
    
    if selected_depts:
        filtered = filtered[filtered["service"].isin(selected_depts)]
    
    fig = go.Figure()
    
    for dept in (selected_depts or []):
        dept_data = filtered[filtered["service"] == dept].sort_values("week")
        fig.add_trace(go.Scatter(
            x=dept_data["week"],
            y=dept_data["patient_satisfaction"],
            name=DEPT_LABELS_SHORT.get(dept, dept),
            mode="lines",
            line=dict(color=DEPT_COLORS.get(dept, "#999"), width=1.5),
            hoverinfo="skip"
        ))
    
    week_span = week_max - week_min + 1
    dtick = 4 if week_span <= 13 else (8 if week_span <= 26 else 13)
    
    fig.update_layout(
        height=100,
        margin=dict(l=25, r=5, t=5, b=18),
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(range=[0, 100], tickvals=[0, 50, 100],
                   tickfont=dict(size=8, color="#999"), showgrid=True, gridcolor="#f0f0f0"),
        xaxis=dict(range=[week_min - 0.5, week_max + 0.5], dtick=dtick,
                   tickfont=dict(size=8, color="#999"), showgrid=False)
    )
    
    return fig


def create_overview_mini(df, selected_depts, week_range):
    """Create the mini overview widget card."""
    info = WIDGET_INFO["overview"]
    week_min, week_max = week_range
    
    dept_count = len(selected_depts) if selected_depts else 0
    filter_text = f"Weeks {week_min}-{week_max} · {dept_count} dept{'s' if dept_count != 1 else ''}"
    
    legend_items = [
        html.Span([
            html.Span("━ ", style={"color": DEPT_COLORS.get(dept, "#999"), "fontWeight": "bold"}),
            html.Span(DEPT_LABELS_SHORT.get(dept, dept), style={"color": "#555", "marginRight": "8px"})
        ]) for dept in (selected_depts or [])
    ]
    
    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column"},
        children=[
            html.Div(f"{info['icon']} {info['title']}",
                     style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "2px", "color": "#2c3e50"}),
            html.Div(filter_text, style={"fontSize": "10px", "color": "#999", "marginBottom": "5px"}),
            html.Div(style={"flex": "1", "minHeight": "0"}, children=[
                dcc.Graph(
                    figure=create_overview_mini_lines(df, selected_depts, week_range),
                    config={"displayModeBar": False, "staticPlot": True},
                    style={"height": "100%", "width": "100%"}
                )
            ]),
            html.Div(style={"display": "flex", "flexWrap": "wrap", "justifyContent": "center",
                           "fontSize": "9px", "marginTop": "3px"},
                     children=legend_items if legend_items else [html.Span("No depts", style={"color": "#999"})]),
            html.Div("Click to expand", style={"fontSize": "10px", "color": "#3498db", "textAlign": "center", "marginTop": "3px"})
        ]
    )


def build_tooltip_content(week, week_data, selected_depts, df, week_range):
    """Build tooltip content for hover display."""
    week_rows = df[df["week"] == week]
    events_this_week = []
    for _, row in week_rows.iterrows():
        if row["event"] != "none" and row["service"] in selected_depts:
            events_this_week.append({
                "event": row["event"],
                "dept": row["service"]
            })
    
    tooltip_children = [
        html.Div(f"Week {week}", style={
            "fontWeight": "600", "fontSize": "12px", "color": "#2c3e50",
            "paddingBottom": "5px", "marginBottom": "6px", "borderBottom": "2px solid #3498db"
        })
    ]
    
    if events_this_week:
        tooltip_children.append(
            html.Div("EVENTS", style={
                "fontSize": "8px", "color": "#888", "marginBottom": "3px", "fontWeight": "600"
            })
        )
        for evt_info in events_this_week:
            evt = evt_info["event"]
            dept = evt_info["dept"]
            dept_color = DEPT_COLORS.get(dept, "#999")  # Use DEPT color, not EVENT color
            
            tooltip_children.append(
                html.Div(
                    style={
                        "display": "flex", "alignItems": "center", "gap": "3px",
                        "marginBottom": "4px", "padding": "2px 4px",
                        "backgroundColor": _hex_to_rgba(dept_color, 0.15),  # Dept color background
                        "borderRadius": "3px", 
                        "borderLeft": f"3px solid {dept_color}"  # Dept color border
                    },
                    children=[
                        html.Span(EVENT_ICONS.get(evt, "⚡"), style={"fontSize": "10px"}),
                        html.Span(evt.capitalize(), style={
                            "fontSize": "9px", "color": "#555", "fontWeight": "500"
                        })
                    ]
                )
            )
        tooltip_children.append(html.Div(style={"height": "4px"}))
    
    tooltip_children.append(html.Div("SATISFACTION", style={
        "fontSize": "8px", "color": "#888", "marginBottom": "3px", "fontWeight": "600"
    }))
    for dept in selected_depts:
        data = week_data.get(str(week), {}).get(dept)
        if data:
            tooltip_children.append(
                html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "2px"}, children=[
                    html.Span(DEPT_LABELS_SHORT[dept], style={"color": "#555", "fontSize": "9px"}),
                    html.Span(str(data["satisfaction"]), style={
                        "fontWeight": "600", "color": DEPT_COLORS[dept], "fontSize": "9px"
                    })
                ])
            )
    
    tooltip_children.append(html.Div("ACCEPTANCE", style={
        "fontSize": "8px", "color": "#888", "margin": "6px 0 3px 0", "fontWeight": "600"
    }))
    for dept in selected_depts:
        data = week_data.get(str(week), {}).get(dept)
        if data:
            tooltip_children.append(
                html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "2px"}, children=[
                    html.Span(DEPT_LABELS_SHORT[dept], style={"color": "#555", "fontSize": "9px"}),
                    html.Span(f"{data['acceptance']}%", style={
                        "fontWeight": "600", "color": DEPT_COLORS[dept], "fontSize": "9px"
                    })
                ])
            )
    
    return tooltip_children
