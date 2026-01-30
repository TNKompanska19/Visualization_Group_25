"""
Overview Widget (T1): Hospital Performance Overview
JBI100 Visualization - Group 25

BIDIRECTIONAL LINKING (Munzner's coordinated multiple views):
- Line chart zoom → PCP shows brush on week axis
- PCP week brush → Line chart x-axis zooms
- Semantic zoom: KDE histograms appear at detail/quarter zoom levels
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from dash import html, dcc

from jbi100_app.config import (
    DEPT_COLORS, DEPT_LABELS, DEPT_LABELS_SHORT,
    get_event_icon_svg, WIDGET_INFO, ZOOM_THRESHOLDS,
    SEMANTIC_COLORS
)


# -----------------------------------------------------------------------------
# Zoom logic
# -----------------------------------------------------------------------------
def get_zoom_level(week_range):
    """Determine zoom level for semantic zoom."""
    if not week_range:
        return "overview"
    span = week_range[1] - week_range[0] + 1
    if span <= ZOOM_THRESHOLDS["detail"]:
        return "detail"
    elif span <= ZOOM_THRESHOLDS["quarter"]:
        return "quarter"
    return "overview"


# -----------------------------------------------------------------------------
# Color helpers
# -----------------------------------------------------------------------------
def _hex_to_rgba(hex_color, alpha=0.5):
    """Convert hex color to rgba string."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


def _build_discrete_colorscale(hex_colors, alpha=0.35):
    """Build discrete colorscale for PCP."""
    n = len(hex_colors)
    if n <= 1:
        c = _hex_to_rgba(hex_colors[0] if n == 1 else "#999", alpha)
        return [(0.0, c), (1.0, c)]
    scale = []
    for i, hx in enumerate(hex_colors):
        c = _hex_to_rgba(hx, alpha)
        lo = i / n
        hi = (i + 1) / n
        scale.append((lo, c))
        scale.append((hi, c))
    scale[0] = (0.0, scale[0][1])
    scale[-1] = (1.0, scale[-1][1])
    return scale


# Chart config that allows zoom
OVERVIEW_CHART_CONFIG = {
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "displaylogo": False,
    "scrollZoom": True
}


# -----------------------------------------------------------------------------
# Line Charts - ALWAYS visible
# -----------------------------------------------------------------------------
def create_overview_charts(df, selected_depts, week_range, show_events=True, hide_anomalies=False):
    """Create the main line chart visualization."""
    week_min, week_max = week_range
    zoom_level = get_zoom_level(week_range)
    
    # Filter anomaly weeks if requested
    if hide_anomalies:
        from jbi100_app.data import load_staff_schedule
        staff_df = load_staff_schedule()
        weeks_with_staff = staff_df[staff_df["present"] == 1]["week"].unique()
        df = df[df["week"].isin(weeks_with_staff)].copy()
    
    # Create subplots with proper spacing
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.15,
        subplot_titles=None,
        row_heights=[0.5, 0.5]
    )
    
    marker_sizes = {"overview": 5, "quarter": 8, "detail": 10}
    line_widths = {"overview": 2, "quarter": 2.5, "detail": 2.5}
    marker_size = marker_sizes[zoom_level]
    line_width = line_widths[zoom_level]
    
    # Add traces for each department
    for dept_idx, dept in enumerate(selected_depts):
        dept_data = df[df["service"] == dept].sort_values("week")
        
        # Satisfaction trace (row 1)
        fig.add_trace(go.Scatter(
            x=dept_data["week"],
            y=dept_data["patient_satisfaction"],
            name=DEPT_LABELS[dept],
            line=dict(color=DEPT_COLORS[dept], width=line_width),
            mode="lines+markers",
            marker=dict(size=marker_size, color=DEPT_COLORS[dept], line=dict(width=0)),
            hoverlabel=dict(bgcolor=DEPT_COLORS[dept], font_size=11, font_color="white"),
            hoverinfo="none",
            legendgroup=dept,
            customdata=[[dept, dept_idx]] * len(dept_data),
            meta={"dept": dept, "dept_idx": dept_idx}
        ), row=1, col=1)
        
        # Acceptance trace (row 2)
        fig.add_trace(go.Scatter(
            x=dept_data["week"],
            y=dept_data["acceptance_rate"],
            name=DEPT_LABELS[dept],
            line=dict(color=DEPT_COLORS[dept], width=line_width),
            mode="lines+markers",
            marker=dict(size=marker_size, color=DEPT_COLORS[dept], line=dict(width=0)),
            hoverinfo="none",
            legendgroup=dept,
            showlegend=False,
            customdata=[[dept, dept_idx]] * len(dept_data),
            meta={"dept": dept, "dept_idx": dept_idx}
        ), row=2, col=1)
    
    # Threshold lines based on selection count
    num_selected = len(selected_depts)
    
    if num_selected == 1:
        dept = selected_depts[0]
        for row, metric in [(1, "patient_satisfaction"), (2, "acceptance_rate")]:
            metric_data = df[df["service"] == dept][metric]
            mean_val = metric_data.mean()
            std_val = metric_data.std()
            
            fig.add_hline(y=mean_val, line_dash="solid", line_color=DEPT_COLORS[dept],
                         line_width=1.8, opacity=0.7, row=row, col=1,
                         annotation_text=f"μ={mean_val:.0f}", annotation_position="right",
                         annotation=dict(font_size=8, font_color=DEPT_COLORS[dept], xshift=10))
            
            upper = min(100, mean_val + 2 * std_val)
            fig.add_hline(y=upper, line_dash="dash", line_color=SEMANTIC_COLORS["threshold_upper"],
                         line_width=1.2, opacity=0.5, row=row, col=1,
                         annotation_text=f"+2σ={upper:.0f}", annotation_position="right",
                         annotation=dict(font_size=7, font_color=SEMANTIC_COLORS["threshold_upper"], xshift=10))
            
            lower = max(0, mean_val - 2 * std_val)
            fig.add_hline(y=lower, line_dash="dash", line_color=SEMANTIC_COLORS["threshold_lower"],
                         line_width=1.2, opacity=0.5, row=row, col=1,
                         annotation_text=f"-2σ={lower:.0f}", annotation_position="right",
                         annotation=dict(font_size=7, font_color=SEMANTIC_COLORS["threshold_lower"], xshift=10))
    
    elif num_selected == 2:
        for row, metric in [(1, "patient_satisfaction"), (2, "acceptance_rate")]:
            for dept in selected_depts:
                metric_data = df[df["service"] == dept][metric]
                mean_val = metric_data.mean()
                fig.add_hline(y=mean_val, line_dash="solid", line_color=DEPT_COLORS[dept],
                             line_width=1.5, opacity=0.6, row=row, col=1,
                             annotation_text=f"μ={mean_val:.0f}", annotation_position="right",
                             annotation=dict(font_size=8, font_color=DEPT_COLORS[dept]))
    
    # Event markers
    events_by_week = {}
    if show_events:
        events_in_range = df[(df["event"] != "none") & (df["service"].isin(selected_depts))]
        
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
            events_by_week[week] = events_by_dept
        
        for week, events_by_dept in events_by_week.items():
            fig.add_vline(x=week, line_dash="dot", line_color="#dddddd", line_width=1, opacity=0.3)
            
            all_events = []
            for dept, dept_events in events_by_dept.items():
                for evt in dept_events:
                    all_events.append((dept, evt))
            
            num_events = len(all_events)
            y_center = 0.50
            y_spacing = 0.035
            y_start = y_center + ((num_events - 1) * y_spacing / 2)
            
            week_span = week_max - week_min + 1
            icon_sizey = 0.04
            icon_sizex = icon_sizey * 0.35 * week_span
            
            for idx, (dept, evt) in enumerate(all_events):
                y_pos = y_start - (idx * y_spacing)
                icon_src = get_event_icon_svg(evt, DEPT_COLORS[dept])
                if icon_src:
                    fig.add_layout_image(
                        source=icon_src, x=week, y=y_pos,
                        xref="x", yref="paper",
                        sizex=icon_sizex, sizey=icon_sizey,
                        xanchor="center", yanchor="middle", layer="above"
                    )
    
    fig.update_layout(
        height=380,
        margin=dict(l=58, r=58, t=18, b=48),
        hovermode="closest",
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        dragmode="zoom",
        uirevision="constant"
    )
    
    fig.update_yaxes(title_text="Satisfaction", title_font=dict(size=10, color="#666"),
                    title_standoff=5, row=1, col=1)
    fig.update_yaxes(title_text="Acceptance %", title_font=dict(size=10, color="#666"),
                    title_standoff=5, row=2, col=1)
    
    dtick = 1 if zoom_level == "detail" else 4
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0", dtick=dtick,
                    range=[week_min - 0.5, week_max + 0.5], fixedrange=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e0e0e0", zeroline=False,
                    range=[0, 100], dtick=25, fixedrange=True, tickfont=dict(size=9))
    fig.update_xaxes(title_text="Week", row=2, col=1, title_font=dict(size=10))
    
    return fig, events_by_week


# -----------------------------------------------------------------------------
# KDE Histogram for semantic zoom
# -----------------------------------------------------------------------------
def create_histogram(df, selected_depts, metric, highlight_value=None, hovered_dept=None):
    """Create KDE histogram for semantic zoom detail view."""
    from scipy import stats
    
    if hovered_dept:
        filtered = df[df["service"] == hovered_dept]
    elif selected_depts:
        filtered = df[df["service"].isin(selected_depts)]
    else:
        filtered = df
    
    values = filtered[metric].values
    kde = stats.gaussian_kde(values)
    x_range = np.linspace(-10, 115, 250)
    y_density = kde(x_range)
    
    fig = go.Figure()
    
    fill_color = DEPT_COLORS.get(hovered_dept, '#ccc') if hovered_dept else '#ccc'
    
    fig.add_trace(go.Scatter(
        x=x_range, y=y_density, mode='lines', fill='tozeroy',
        line=dict(color=fill_color, width=1.5),
        fillcolor=_hex_to_rgba(fill_color, 0.5),
        hoverinfo='skip'
    ))
    
    if highlight_value is not None:
        mask = (x_range >= highlight_value - 3) & (x_range <= highlight_value + 3)
        highlight_color = DEPT_COLORS.get(hovered_dept, '#3498db') if hovered_dept else '#3498db'
        fig.add_trace(go.Scatter(
            x=x_range[mask], y=y_density[mask], mode='lines', fill='tozeroy',
            line=dict(color=highlight_color, width=2),
            fillcolor=_hex_to_rgba(highlight_color, 0.8),
            hoverinfo='skip'
        ))
    
    base_title = "Satisfaction" if "satisfaction" in metric else "Acceptance"
    title_text = f"{base_title} - {DEPT_LABELS_SHORT.get(hovered_dept, hovered_dept)}" if hovered_dept else base_title
    
    fig.update_layout(
        height=160,
        margin=dict(l=5, r=5, t=20, b=20),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        title=dict(text=title_text, font=dict(size=9, color="#666"), x=0.5, y=0.95),
        xaxis=dict(range=[-10, 115], tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=7), showgrid=False),
        yaxis=dict(showticklabels=False, showgrid=False),
        showlegend=False
    )
    
    return fig


# -----------------------------------------------------------------------------
# PCP (Parallel Coordinates) - Shows brush for week range
# -----------------------------------------------------------------------------
def create_pcp_figure(df, selected_depts, week_range, brush_state=None, hovered_week=None):
    """Create PCP with constraintrange for week linking."""
    week_min, week_max = week_range if week_range else (1, 52)

    if selected_depts:
        dff = df[df["service"].isin(selected_depts)].copy()
        dept_order = list(selected_depts)
    else:
        dff = df.copy()
        dept_order = sorted(dff["service"].unique().tolist()) if "service" in dff.columns else []

    dept_to_code = {d: i for i, d in enumerate(dept_order)}
    if "service" in dff.columns and dept_order:
        dept_codes = dff["service"].map(dept_to_code).fillna(0).astype(float).values
        colorscale = _build_discrete_colorscale([DEPT_COLORS.get(d, "#999") for d in dept_order], alpha=0.45)
        cmax = max(1, len(dept_order) - 1)
    else:
        dept_codes = np.zeros(len(dff))
        colorscale = _build_discrete_colorscale(["#999"], alpha=0.45)
        cmax = 1

    # PCP columns (must match DataFrame column names); short labels that fit without truncation
    pcp_columns = [
        ("week", "Week"),
        ("available_beds", "Beds"),
        ("patients_request", "Requests"),
        ("patients_admitted", "Admitted"),
        ("patients_refused", "Refused"),
        ("acceptance_rate", "Accept %"),
        ("patient_satisfaction", "Satisfaction"),
        ("staff_morale", "Morale")
    ]
    
    dimensions = []
    for col, label in pcp_columns:
        if col not in dff.columns:
            continue
        
        vals = dff[col].values
        if col == "week":
            rng = [1, 52]
        else:
            lo, hi = np.nanmin(vals), np.nanmax(vals)
            margin = (hi - lo) * 0.05 if hi > lo else 1
            rng = [lo - margin, hi + margin]
        
        dim = dict(
            label=label,
            values=vals,
            range=rng
        )
        
        # Add constraintrange for week axis if zoomed
        if col == "week" and (week_min > 1 or week_max < 52):
            dim["constraintrange"] = [week_min, week_max]
        
        dimensions.append(dim)

    fig = go.Figure(data=go.Parcoords(
        line=dict(
            color=dept_codes,
            colorscale=colorscale,
            cmin=0,
            cmax=cmax
        ),
        dimensions=dimensions,
        labelangle=-25,
        labelfont=dict(size=10, color="#555"),
        tickfont=dict(size=9, color="#444")
    ))

    # Week range annotation
    if week_min == 1 and week_max == 52:
        range_text = "All weeks (1-52)"
    else:
        range_text = f"Weeks {week_min}-{week_max}"

    fig.update_layout(
        height=400,
        margin=dict(l=68, r=68, t=38, b=38),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(size=9),
        annotations=[
            dict(
                text=range_text,
                x=1.0, y=1.02, xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=9, color="#e67e22"),
                xanchor="right"
            )
        ]
    )

    # Hovered week annotation (top-left so it doesn't overlap Week axis)
    if hovered_week is not None:
        fig.add_annotation(
            text=f"Hovered: W{hovered_week}",
            x=0.02, y=0.98, xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=10, color="#3498db", weight="bold"),
            xanchor="left", yanchor="top"
        )

    return fig


# -----------------------------------------------------------------------------
# Expanded Layout - Line charts + PCP + semantic zoom KDE
# -----------------------------------------------------------------------------
def create_overview_expanded(df, selected_depts, week_range, show_events=True, hide_anomalies=False):
    """Create the expanded overview widget with semantic zoom."""
    info = WIDGET_INFO["overview"]
    zoom_level = get_zoom_level(week_range)
    
    # Legend items
    legend_items = []
    for dept in selected_depts:
        legend_items.append(
            html.Span(
                style={"display": "inline-flex", "alignItems": "center", "marginRight": "12px"},
                children=[
                    html.Span(style={
                        "width": "12px", "height": "12px",
                        "backgroundColor": DEPT_COLORS[dept],
                        "borderRadius": "2px", "marginRight": "4px", "display": "inline-block"
                    }),
                    html.Span(DEPT_LABELS_SHORT[dept], style={"fontSize": "10px", "color": "#555"})
                ]
            )
        )
    
    header = html.Div(
        style={"paddingBottom": "4px", "marginBottom": "6px", "borderBottom": "2px solid #eee", "flexShrink": "0"},
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"},
                children=[
                    html.Div(children=[
                        html.H4(f"{info['icon']} {info['title']}",
                               style={"margin": "0", "color": "#2c3e50", "fontWeight": "500", "fontSize": "15px"}),
                        html.Span(info["subtitle"], style={"fontSize": "10px", "color": "#999"})
                    ]),
                    html.Div(style={"display": "flex", "alignItems": "center"}, children=legend_items) if legend_items else None
                ]
            )
        ]
    )
    
    if not selected_depts:
        content = html.Div(
            "Please select at least one department",
            style={"flex": "1", "display": "flex", "alignItems": "center", "justifyContent": "center", "color": "#999"}
        )
        pcp_section = html.Div()
    else:
        # Create line chart
        chart_fig, events_by_week = create_overview_charts(df, selected_depts, week_range, show_events, hide_anomalies)
        
        # Line chart container
        chart_section = html.Div(
            id="chart-container",
            style={"flex": "1", "position": "relative", "minWidth": "0", "minHeight": "350px"},
            children=[
                dcc.Graph(
                    id="overview-chart",
                    figure=chart_fig,
                    style={"height": "350px", "width": "100%"},
                    config=OVERVIEW_CHART_CONFIG
                ),
                html.Div(
                    id="hover-highlight",
                    style={
                        "position": "absolute", "top": "10px", "bottom": "30px",
                        "width": "3px", "backgroundColor": "rgba(52, 152, 219, 0.6)",
                        "pointerEvents": "none", "display": "none", "borderRadius": "2px", "left": "40px"
                    }
                )
            ]
        )
        
        # Tooltip section - only for line charts
        tooltip_section = html.Div(
            id="side-tooltip",
            style={
                "width": "90px", "backgroundColor": "#f8f9fa", "borderRadius": "6px",
                "padding": "6px", "border": "1px solid #e0e0e0", "flexShrink": "0",
                "fontSize": "9px", "overflow": "hidden", "height": "350px"
            },
            children=[
                html.Div(
                    id="tooltip-content",
                    style={"height": "100%"},
                    children=[
                        html.Div(
                            style={"height": "100%", "display": "flex", "flexDirection": "column",
                                  "justifyContent": "center", "alignItems": "center"},
                            children=[
                                html.Div("Hover over", style={"color": "#999", "textAlign": "center"}),
                                html.Div("the chart", style={"color": "#999", "textAlign": "center"})
                            ]
                        )
                    ]
                )
            ]
        )
        
        # Semantic zoom: KDE panels at detail/quarter level
        if zoom_level in ["detail", "quarter"]:
            kde_section = html.Div(
                style={"width": "180px", "display": "flex", "flexDirection": "column", "gap": "4px", "flexShrink": "0"},
                children=[
                    html.Div(
                        style={"flex": "1", "backgroundColor": "#fafafa", "borderRadius": "4px", "border": "1px solid #eee"},
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
                        style={"flex": "1", "backgroundColor": "#fafafa", "borderRadius": "4px", "border": "1px solid #eee"},
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
            
            # Line charts + KDE + tooltip in a row
            line_charts_row = html.Div(
                style={"display": "flex", "gap": "8px", "height": "350px"},
                children=[chart_section, kde_section, tooltip_section]
            )
        else:
            # Overview level: just line charts + tooltip (no KDE)
            line_charts_row = html.Div(
                style={"display": "flex", "gap": "8px", "height": "350px"},
                children=[chart_section, tooltip_section]
            )
        
        # PCP section - separate below line charts
        pcp_section = html.Div(
            style={"flexShrink": "0", "marginTop": "6px"},
            children=[
                dcc.Graph(
                    id="pcp-chart",
                    figure=create_pcp_figure(df, selected_depts, week_range),
                    config={"displayModeBar": False},
                    style={"width": "100%"}
                )
            ]
        )
        
        content = line_charts_row
    
    return html.Div(
        style={"height": "100%", "display": "flex", "flexDirection": "column", "overflow": "hidden"},
        children=[header, content, pcp_section]
    )


# -----------------------------------------------------------------------------
# Mini Widget
# -----------------------------------------------------------------------------
def create_overview_mini_lines(df, selected_depts, week_range):
    """Create mini line chart."""
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
        yaxis=dict(range=[0, 100], tickvals=[0, 50, 100], tickfont=dict(size=8, color="#999"),
                  showgrid=True, gridcolor="#f0f0f0"),
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


# -----------------------------------------------------------------------------
# Tooltip Builder
# -----------------------------------------------------------------------------
def build_tooltip_content(week, week_data, selected_depts, df, week_range):
    """Build tooltip content with spatial alignment."""
    week_rows = df[df["week"] == week]
    events_this_week = []
    for _, row in week_rows.iterrows():
        if row["event"] != "none" and row["service"] in selected_depts:
            events_this_week.append({"event": row["event"], "dept": row["service"]})
    
    top_section_children = [
        html.Div(f"Week {week}", style={
            "fontWeight": "600", "fontSize": "11px", "color": "#2c3e50",
            "paddingBottom": "3px", "marginBottom": "4px", "borderBottom": "2px solid #3498db"
        })
    ]
    
    if events_this_week:
        top_section_children.append(
            html.Div("EVENTS", style={"fontSize": "7px", "color": "#888", "marginBottom": "2px", "fontWeight": "600"})
        )
        for evt_info in events_this_week:
            evt = evt_info["event"]
            dept = evt_info["dept"]
            dept_color = DEPT_COLORS.get(dept, "#999")
            icon_src = get_event_icon_svg(evt, dept_color)
            
            top_section_children.append(
                html.Div(
                    style={
                        "display": "flex", "alignItems": "center", "gap": "3px",
                        "marginBottom": "2px", "padding": "2px 3px",
                        "backgroundColor": _hex_to_rgba(dept_color, 0.15),
                        "borderRadius": "3px", "borderLeft": f"2px solid {dept_color}"
                    },
                    children=[
                        html.Img(src=icon_src, style={"width": "10px", "height": "10px"}),
                        html.Span(evt.capitalize(), style={"fontSize": "8px", "color": "#555", "fontWeight": "500"})
                    ]
                )
            )
        top_section_children.append(html.Div(style={"height": "2px"}))
    
    top_section_children.append(html.Div("SATISFACTION", style={
        "fontSize": "7px", "color": "#888", "marginBottom": "2px", "fontWeight": "600"
    }))
    for dept in selected_depts:
        data = week_data.get(str(week), {}).get(dept)
        if data:
            top_section_children.append(
                html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "1px"}, children=[
                    html.Span(DEPT_LABELS_SHORT[dept], style={"color": "#555", "fontSize": "8px"}),
                    html.Span(str(data["satisfaction"]), style={
                        "fontWeight": "600", "color": DEPT_COLORS[dept], "fontSize": "8px"
                    })
                ])
            )
    
    bottom_section_children = [
        html.Div("ACCEPTANCE", style={"fontSize": "7px", "color": "#888", "marginBottom": "2px", "fontWeight": "600"})
    ]
    for dept in selected_depts:
        data = week_data.get(str(week), {}).get(dept)
        if data:
            bottom_section_children.append(
                html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "1px"}, children=[
                    html.Span(DEPT_LABELS_SHORT[dept], style={"color": "#555", "fontSize": "8px"}),
                    html.Span(f"{data['acceptance']}%", style={
                        "fontWeight": "600", "color": DEPT_COLORS[dept], "fontSize": "8px"
                    })
                ])
            )
    
    return [
        html.Div(
            style={
                "display": "flex", "flexDirection": "column", "justifyContent": "space-between",
                "height": "100%", "minHeight": "320px"
            },
            children=[
                html.Div(children=top_section_children),
                html.Div(children=bottom_section_children)
            ]
        )
    ]
