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
    WIDGET_INFO,
    DEPT_COLORS,
    DEPT_LABELS,
    DEPT_LABELS_SHORT,
    EVENT_COLORS,
    EVENT_ICONS,
    SEMANTIC_COLORS,
    ZOOM_THRESHOLDS
)


# =============================================================================
# CHART CONFIGURATION
# =============================================================================

CHART_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "scrollZoom": True
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_zoom_level(week_range):
    """Determine zoom level for semantic zoom."""
    span = week_range[1] - week_range[0] + 1

    if span <= ZOOM_THRESHOLDS["detail"]:
        return "detail"
    elif span <= ZOOM_THRESHOLDS["quarter"]:
        return "quarter"
    else:
        return "overview"


def create_overview_charts(df, selected_depts, week_range, show_events=True, hide_anomalies=False, selected_week=None):
    """Create the main overview visualization with threshold lines and event markers.

    Args:
        show_events: If True, display event markers (default: True)
        hide_anomalies: If True, filter out weeks with no staff assigned (default: False)
        selected_week: If provided, highlight this week (Connect from other views, e.g., T2)
    """
    week_min, week_max = week_range
    zoom_level = get_zoom_level(week_range)

    # Filter out anomaly weeks if requested
    # Anomaly = weeks where NO staff members were assigned (present=0 for all staff)
    if hide_anomalies:
        from jbi100_app.data import load_staff_schedule
        staff_df = load_staff_schedule()

        # Find weeks with at least 1 staff member present
        weeks_with_staff = staff_df.groupby("week")["present"].sum()
        valid_weeks = weeks_with_staff[weeks_with_staff > 0].index.tolist()

        # Filter the services dataframe to only valid weeks
        df = df[df["week"].isin(valid_weeks)].copy()

    # Filter data for selected depts and week range
    filtered = df[(df["week"] >= week_min) & (df["week"] <= week_max)]

    if selected_depts:
        filtered = filtered[filtered["service"].isin(selected_depts)]

    # Determine dtick based on zoom
    span = week_max - week_min + 1
    if span <= 8:
        dtick = 1
    elif span <= 13:
        dtick = 2
    elif span <= 26:
        dtick = 4
    else:
        dtick = 6

    # Prepare event aggregation by week
    events_by_week = {}
    if show_events and "event" in filtered.columns:
        for w in range(week_min, week_max + 1):
            week_rows = filtered[filtered["week"] == w]
            week_events = []
            for _, row in week_rows.iterrows():
                if row["event"] != "none":
                    week_events.append(row["event"])
            # Keep unique events
            week_events = list(dict.fromkeys(week_events))
            events_by_week[w] = week_events

    # Build figure with 2 rows: satisfaction and acceptance
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.14,
        subplot_titles=("Patient Satisfaction", "Acceptance Rate")
    )

    # Add traces per department
    for dept in (selected_depts or []):
        dept_data = filtered[filtered["service"] == dept].sort_values("week")
        if dept_data.empty:
            continue

        # Satisfaction line
        fig.add_trace(
            go.Scatter(
                x=dept_data["week"],
                y=dept_data["patient_satisfaction"],
                name=f"{DEPT_LABELS.get(dept, dept)} - Satisfaction",
                mode="lines+markers",
                line=dict(color=DEPT_COLORS.get(dept, "#999"), width=2),
                marker=dict(size=5, color=DEPT_COLORS.get(dept, "#999")),
                customdata=[[dept, i] for i in range(len(dept_data))],
                hovertemplate=f"<b>{DEPT_LABELS.get(dept, dept)}</b><br>" +
                              "Week %{x}<br>Satisfaction: %{y:.1f}<extra></extra>"
            ),
            row=1, col=1
        )

        # Acceptance line
        fig.add_trace(
            go.Scatter(
                x=dept_data["week"],
                y=dept_data["acceptance_rate"],
                name=f"{DEPT_LABELS.get(dept, dept)} - Acceptance",
                mode="lines+markers",
                line=dict(color=DEPT_COLORS.get(dept, "#999"), width=2, dash="dot"),
                marker=dict(size=5, color=DEPT_COLORS.get(dept, "#999")),
                customdata=[[dept, i] for i in range(len(dept_data))],
                hovertemplate=f"<b>{DEPT_LABELS.get(dept, dept)}</b><br>" +
                              "Week %{x}<br>Acceptance: %{y:.1f}%<extra></extra>",
                showlegend=False
            ),
            row=2, col=1
        )

    # Add event markers as vertical lines + icons
    if show_events:
        for week, evts in events_by_week.items():
            if evts:
                # marker line
                fig.add_vline(
                    x=week,
                    line_width=1,
                    line_dash="dash",
                    line_color="rgba(0,0,0,0.15)"
                )
                # icons near top
                icon_text = " ".join([EVENT_ICONS.get(e, "⚡") for e in evts])
                fig.add_annotation(
                    x=week,
                    y=1.06,
                    xref="x",
                    yref="paper",
                    text=icon_text,
                    showarrow=False,
                    font=dict(size=12),
                    align="center"
                )

    # Update layout
    fig.update_layout(
        height=340,
        margin=dict(l=45, r=15, t=35, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        showlegend=False,
        dragmode="pan"
    )

    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0", dtick=dtick,
                     range=[week_min - 0.5, week_max + 0.5], fixedrange=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e0e0e0", zeroline=False,
                     range=[0, 100], dtick=25, fixedrange=True,
                     tickfont=dict(size=9))
    fig.update_xaxes(title_text="Week", row=2, col=1, title_font=dict(size=10))

    # Connect: highlight selected week (e.g., coming from T2 selection)
    if selected_week is not None:
        try:
            w = int(selected_week)
            if week_min <= w <= week_max:
                fig.add_vrect(
                    x0=w - 0.5, x1=w + 0.5,
                    fillcolor="rgba(52,152,219,0.10)",
                    line_width=0,
                    layer="above"
                )
        except Exception:
            pass

    return fig, events_by_week


def _hex_to_rgba(hex_color, alpha=1.0):
    """Convert hex color to rgba string."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


# =============================================================================
# KDE / DISTRIBUTION PANELS
# =============================================================================

def create_histogram(df, selected_depts, metric):
    """Create KDE-based histogram panel for details-on-demand."""
    # Filter for selected departments
    if selected_depts:
        data = df[df["service"].isin(selected_depts)][metric].dropna().values
    else:
        data = df[metric].dropna().values

    if len(data) < 3:
        # not enough data to make KDE meaningful
        fig = go.Figure()
        fig.update_layout(
            height=175,
            margin=dict(l=5, r=5, t=20, b=20),
            plot_bgcolor="white",
            paper_bgcolor="rgba(0,0,0,0)",
            title=dict(text=f"{metric}", font=dict(size=9, color="#666"), x=0.5, y=0.95),
            xaxis=dict(range=[-10, 115], tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=7), showgrid=False),
            yaxis=dict(showticklabels=False, showgrid=False),
            showlegend=False
        )
        return fig

    # KDE via numpy approximation
    # (Real KDE is computed in callbacks using scipy; this keeps view self-contained)
    # Use histogram density as fallback
    counts, bin_edges = np.histogram(data, bins=20, range=(-10, 110), density=True)
    centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=centers,
        y=counts,
        mode="lines",
        fill="tozeroy",
        line=dict(color="#ccc", width=1.5),
        fillcolor=_hex_to_rgba("#cccccc", 0.5),
        hoverinfo="skip"
    ))

    fig.update_layout(
        height=175,
        margin=dict(l=5, r=5, t=20, b=20),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        title=dict(text=f"{metric}", font=dict(size=9, color="#666"), x=0.5, y=0.95),
        xaxis=dict(range=[-10, 115], tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=7), showgrid=False),
        yaxis=dict(showticklabels=False, showgrid=False),
        showlegend=False
    )

    return fig


# =============================================================================
# VIEW CONSTRUCTION
# =============================================================================

def create_overview_expanded(df, selected_depts, week_range, show_events=True, hide_anomalies=False, selected_week=None):
    """Create expanded overview widget."""
    info = WIDGET_INFO["overview"]
    zoom_level = get_zoom_level(week_range)

    header = html.Div(
        style={"paddingBottom": "6px", "marginBottom": "6px", "borderBottom": "2px solid #eee", "flexShrink": "0"},
        children=[
            html.H4(f"{info['icon']} {info['title']}",
                    style={"margin": "0", "color": "#2c3e50", "fontWeight": "600", "fontSize": "15px"}),
            html.Span(f"{info['subtitle']} • Zoom: {zoom_level}",
                      style={"fontSize": "11px", "color": "#999"})
        ],
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
            df, selected_depts, week_range, show_events, hide_anomalies, selected_week=selected_week
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
                    "width": "95px",
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
            # Overview: Just line charts + tooltip
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

    filter_text = f"Weeks {week_min}-{week_max} • {len(selected_depts or [])} dept"

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
            dept_color = DEPT_COLORS.get(dept, "#999")  # Use DEPT color

            tooltip_children.append(
                html.Div(
                    style={
                        "display": "flex", "alignItems": "center", "gap": "3px",
                        "marginBottom": "4px", "padding": "2px 4px",
                        "backgroundColor": _hex_to_rgba(dept_color, 0.15),
                        "borderRadius": "3px",
                        "borderLeft": f"3px solid {dept_color}"
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
