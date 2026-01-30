"""
Unified Chart Callbacks
JBI100 Visualization - Group 25

CRITICAL: Implements all chart updates for the unified single-tab layout:
1. Overview Line Chart with semantic zoom (KDE histograms)
2. PCP (Parallel Coordinates Plot) with proper labels and linking
3. Cross-widget synchronization via current-week-range (line chart zoom ↔ PCP brush)

Interaction Requirements:
- Zoom line chart (select week range) → PCP shows same week range
- Brush PCP (Week axis) → line chart zooms to that week range
- No hover linking between line chart and PCP (zoom/range only)
"""

from dash import callback, Output, Input, State, ctx, no_update, html
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

from jbi100_app.config import (
    DEPT_COLORS, DEPT_LABELS, DEPT_LABELS_SHORT, 
    ZOOM_THRESHOLDS, SEMANTIC_COLORS
)
from jbi100_app.data import get_services_data
from jbi100_app.views.overview import get_zoom_level

_services_df = get_services_data()


def _hex_to_rgba(hex_color, alpha=0.5):
    """Convert hex color to rgba string."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


def create_overview_figure(df, selected_depts, week_range, show_events=True, hide_anomalies=False):
    """
    Create the overview line chart with dual subplots (Satisfaction + Acceptance).
    Hover highlight is drawn by overlay (hover-highlight div), not in figure, to avoid lag.
    """
    week_min, week_max = week_range
    zoom_level = get_zoom_level(week_range)
    
    # Filter anomaly weeks if requested
    if hide_anomalies:
        anomaly_weeks = [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 51]
        df = df[~df["week"].isin(anomaly_weeks)].copy()
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.15,
        subplot_titles=None
    )
    
    marker_sizes = {"overview": 5, "quarter": 8, "detail": 10}
    line_widths = {"overview": 2, "quarter": 2.5, "detail": 2.5}
    marker_size = marker_sizes.get(zoom_level, 5)
    line_width = line_widths.get(zoom_level, 2)
    
    for dept_idx, dept in enumerate(selected_depts):
        dept_data = df[df["service"] == dept].sort_values("week")
        
        # Satisfaction trace
        fig.add_trace(go.Scatter(
            x=dept_data["week"],
            y=dept_data["patient_satisfaction"],
            name=DEPT_LABELS.get(dept, dept),
            line=dict(color=DEPT_COLORS.get(dept, "#999"), width=line_width),
            mode="lines+markers",
            marker=dict(size=marker_size, color=DEPT_COLORS.get(dept, "#999")),
            hovertemplate=f"<b>{DEPT_LABELS_SHORT.get(dept, dept)}</b><br>Week %{{x}}<br>Satisfaction: %{{y}}<extra></extra>",
            legendgroup=dept,
            customdata=[[dept, dept_idx]] * len(dept_data),
        ), row=1, col=1)
        
        # Acceptance trace
        fig.add_trace(go.Scatter(
            x=dept_data["week"],
            y=dept_data["acceptance_rate"],
            name=DEPT_LABELS.get(dept, dept),
            line=dict(color=DEPT_COLORS.get(dept, "#999"), width=line_width),
            mode="lines+markers",
            marker=dict(size=marker_size, color=DEPT_COLORS.get(dept, "#999")),
            hovertemplate=f"<b>{DEPT_LABELS_SHORT.get(dept, dept)}</b><br>Week %{{x}}<br>Acceptance: %{{y:.1f}}%<extra></extra>",
            legendgroup=dept,
            showlegend=False,
            customdata=[[dept, dept_idx]] * len(dept_data),
        ), row=2, col=1)
    
    # Add threshold lines based on selection count
    num_selected = len(selected_depts)
    if num_selected == 1:
        dept = selected_depts[0]
        for row, metric in [(1, "patient_satisfaction"), (2, "acceptance_rate")]:
            metric_data = df[df["service"] == dept][metric]
            mean_val = metric_data.mean()
            std_val = metric_data.std()
            
            fig.add_hline(y=mean_val, line_dash="solid", line_color=DEPT_COLORS.get(dept, "#999"),
                          line_width=1.5, opacity=0.7, row=row, col=1,
                          annotation_text=f"μ={mean_val:.0f}", annotation_position="right",
                          annotation=dict(font_size=8, font_color=DEPT_COLORS.get(dept, "#999")))
            
            upper = min(100, mean_val + 2 * std_val)
            lower = max(0, mean_val - 2 * std_val)
            fig.add_hline(y=upper, line_dash="dash", line_color="#666", line_width=1, opacity=0.4, row=row, col=1,
                          annotation_text=f"+2σ", annotation_position="right", annotation=dict(font_size=7))
            fig.add_hline(y=lower, line_dash="dash", line_color="#666", line_width=1, opacity=0.4, row=row, col=1,
                          annotation_text=f"-2σ", annotation_position="right", annotation=dict(font_size=7))
    
    elif num_selected == 2:
        for row, metric in [(1, "patient_satisfaction"), (2, "acceptance_rate")]:
            for dept in selected_depts:
                metric_data = df[df["service"] == dept][metric]
                mean_val = metric_data.mean()
                fig.add_hline(y=mean_val, line_dash="solid", line_color=DEPT_COLORS.get(dept, "#999"),
                              line_width=1.2, opacity=0.5, row=row, col=1,
                              annotation_text=f"μ={mean_val:.0f}", annotation_position="right",
                              annotation=dict(font_size=8, font_color=DEPT_COLORS.get(dept, "#999")))
    
    dtick = 1 if zoom_level == "detail" else 4
    
    fig.update_layout(
        height=380,
        margin=dict(l=50, r=80, t=20, b=50),
        hovermode="closest",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
        plot_bgcolor="white",
        paper_bgcolor="white",
        dragmode="zoom"
    )
    
    fig.update_yaxes(title_text="Satisfaction", title_font=dict(size=10), row=1, col=1,
                     showgrid=True, gridcolor="#f0f0f0", range=[0, 105], tickfont=dict(size=9))
    fig.update_yaxes(title_text="Acceptance %", title_font=dict(size=10), row=2, col=1,
                     showgrid=True, gridcolor="#f0f0f0", range=[0, 105], tickfont=dict(size=9))
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0", dtick=dtick,
                     range=[week_min - 0.5, week_max + 0.5], row=2, col=1)
    fig.update_xaxes(title_text="Week", row=2, col=1, title_font=dict(size=10))

    return fig


def create_pcp_figure(df, selected_depts, week_range):
    """
    Create Parallel Coordinates Plot showing multivariate hospital data.
    
    Focus + context: always show all 52 weeks. The current week_range is applied
    as constraintrange on the Week axis so Plotly shows selected weeks in color
    (focus) and the rest in gray (context). Double-click / clear brush to reset.
    """
    week_min, week_max = week_range
    full_range = (week_min == 1 and week_max == 52)

    # Use FULL data (all weeks 1-52) so we get focus + context: selected range
    # in color, rest in gray via constraintrange
    filtered = df[
        (df["week"] >= 1) & (df["week"] <= 52) &
        (df["service"].isin(selected_depts))
    ].copy()

    if filtered.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data for selected filters", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False)
        fig.update_layout(height=400, margin=dict(l=60, r=60, t=40, b=40))
        return fig

    # Create department color mapping (numeric for Plotly)
    dept_to_num = {dept: i for i, dept in enumerate(selected_depts)}
    filtered["dept_num"] = filtered["service"].map(dept_to_num)

    # Week dimension always full range [1, 52]; constraintrange = selected range (focus)
    week_dim = dict(label="Week", values=filtered["week"], range=[1, 52])
    if not full_range:
        week_dim["constraintrange"] = [week_min, week_max]

    dimensions = [
        week_dim,
        dict(label="Beds", values=filtered["available_beds"]),
        dict(label="Requests", values=filtered["patients_request"]),
        dict(label="Admitted", values=filtered["patients_admitted"]),
        dict(label="Refused", values=filtered["patients_refused"]),
        dict(label="Accept %", values=filtered["acceptance_rate"], range=[0, 100]),
        dict(label="Satisfaction", values=filtered["patient_satisfaction"], range=[0, 100]),
        dict(label="Morale", values=filtered["staff_morale"], range=[0, 100]),
    ]

    # Create discrete colorscale from department colors
    colorscale = []
    n_depts = len(selected_depts)
    for i, dept in enumerate(selected_depts):
        pos = i / max(n_depts - 1, 1)
        colorscale.append([pos, DEPT_COLORS.get(dept, "#999")])
    if len(colorscale) == 1:
        colorscale = [[0, colorscale[0][1]], [1, colorscale[0][1]]]

    fig = go.Figure(data=go.Parcoords(
        line=dict(
            color=filtered["dept_num"],
            colorscale=colorscale,
            showscale=False,
        ),
        dimensions=dimensions,
        labelangle=0,  # Horizontal labels so they are fully visible
        labelside="top",
        labelfont=dict(size=10, color="#2c3e50"),
        tickfont=dict(size=8),
    ))

    fig.update_layout(
        height=420,
        margin=dict(l=80, r=80, t=70, b=45),  # Extra top/bottom so axis labels are not cut off
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    return fig


def create_kde_figure(df, selected_depts, metric, highlight_value=None, hovered_dept=None):
    """
    Create KDE (Kernel Density Estimate) histogram for semantic zoom.
    
    Munzner Justification:
    - KDE shows distribution shape better than histogram bins
    - Highlight region shows where current value sits in distribution
    """
    from scipy import stats
    
    # Filter by hovered department if provided
    if hovered_dept:
        filtered = df[df["service"] == hovered_dept]
        color = DEPT_COLORS.get(hovered_dept, "#ccc")
    elif selected_depts:
        filtered = df[df["service"].isin(selected_depts)]
        color = "#ccc"
    else:
        filtered = df
        color = "#ccc"
    
    values = filtered[metric].values
    if len(values) < 2:
        fig = go.Figure()
        fig.update_layout(height=170, margin=dict(l=5, r=5, t=25, b=20))
        return fig
    
    # Compute KDE
    kde = stats.gaussian_kde(values)
    x_range = np.linspace(-10, 115, 200)
    y_density = kde(x_range)
    
    fig = go.Figure()
    
    # Main KDE curve
    fig.add_trace(go.Scatter(
        x=x_range, y=y_density,
        mode='lines', fill='tozeroy',
        line=dict(color=color, width=1.5),
        fillcolor=_hex_to_rgba(color, 0.4),
        hoverinfo='skip'
    ))
    
    # Highlight region if value provided
    if highlight_value is not None:
        highlight_width = 3
        mask = (x_range >= highlight_value - highlight_width) & (x_range <= highlight_value + highlight_width)
        fig.add_trace(go.Scatter(
            x=x_range[mask], y=y_density[mask],
            mode='lines', fill='tozeroy',
            line=dict(color=color, width=2),
            fillcolor=_hex_to_rgba(color, 0.8),
            hoverinfo='skip'
        ))
    
    title = "Satisfaction" if "satisfaction" in metric else "Acceptance"
    if hovered_dept:
        title = f"{title} - {DEPT_LABELS_SHORT.get(hovered_dept, hovered_dept)}"
    
    fig.update_layout(
        height=170,
        margin=dict(l=5, r=5, t=25, b=20),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        title=dict(text=title, font=dict(size=9, color="#666"), x=0.5, y=0.95),
        xaxis=dict(range=[-10, 115], tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=7), showgrid=False),
        yaxis=dict(showticklabels=False, showgrid=False),
        showlegend=False
    )
    
    return fig


def register_unified_callbacks():
    """Register all unified chart callbacks."""
    
    # =========================================================================
    # 1. OVERVIEW CHART UPDATE (responds to dept, week range, toggles)
    # =========================================================================
    @callback(
        Output("overview-chart", "figure"),
        [Input("dept-filter", "value"),
         Input("current-week-range", "data"),
         Input("show-events-toggle", "value"),
         Input("hide-anomalies-toggle", "value")],
        prevent_initial_call=False
    )
    def update_overview_chart(selected_depts, week_range, show_events, hide_anomalies):
        """Update the overview line chart. Hover highlight is overlay only (no redraw on hover)."""
        if not selected_depts:
            selected_depts = ["emergency"]
        if not week_range:
            week_range = [1, 52]
        
        show = "show" in (show_events or [])
        hide = "hide" in (hide_anomalies or [])
        
        return create_overview_figure(_services_df, selected_depts, week_range, show, hide)
    
    # =========================================================================
    # 2. PCP UPDATE (responds to dept and week range only; no hover)
    # =========================================================================
    @callback(
        Output("pcp-chart", "figure"),
        [Input("dept-filter", "value"),
         Input("current-week-range", "data")],
        prevent_initial_call=False
    )
    def update_pcp_chart(selected_depts, week_range):
        """Update the Parallel Coordinates Plot. Week range from line chart zoom only."""
        if not selected_depts:
            selected_depts = ["emergency"]
        if not week_range:
            week_range = [1, 52]
        
        return create_pcp_figure(_services_df, selected_depts, week_range)
    
    # =========================================================================
    # 3. KDE SEMANTIC ZOOM (show/hide based on zoom level + update on hover)
    # =========================================================================
    @callback(
        [Output("kde-section", "style"),
         Output("hist-satisfaction", "figure"),
         Output("hist-acceptance", "figure"),
         Output("overview-zoom-indicator", "children")],
        [Input("current-week-range", "data"),
         Input("overview-chart", "hoverData"),
         Input("dept-filter", "value")],
        prevent_initial_call=False
    )
    def update_kde_semantic_zoom(week_range, hover_data, selected_depts):
        """
        SEMANTIC ZOOM: Show KDE histograms when zoomed to detail/quarter level.
        
        Munzner Justification (Semantic Zoom - Ch. 11):
        - At overview level: Focus on trends (line chart only)
        - At detail level: Show distributions (KDE appears)
        - This follows "Overview first, zoom and filter, details on demand"
        """
        if not week_range:
            week_range = [1, 52]
        if not selected_depts:
            selected_depts = ["emergency"]
        
        zoom_level = get_zoom_level(week_range)
        week_span = week_range[1] - week_range[0] + 1
        
        # Determine visibility based on zoom level
        show_kde = zoom_level in ["detail", "quarter"]
        
        kde_style = {
            "width": "200px",
            "display": "flex" if show_kde else "none",
            "flexDirection": "column",
            "gap": "6px",
            "flexShrink": "0",
        }
        
        # Extract hovered department and value
        hovered_dept = None
        hovered_week = None
        highlight_sat = None
        highlight_acc = None
        
        if hover_data and hover_data.get("points"):
            point = hover_data["points"][0]
            hovered_week = round(point.get("x", 0))
            
            # Get department from customdata
            if "customdata" in point and point["customdata"]:
                customdata = point["customdata"]
                if isinstance(customdata, list) and len(customdata) > 0:
                    hovered_dept = customdata[0]
            
            # Get values for hovered week/dept
            if hovered_dept and 1 <= hovered_week <= 52:
                week_data = _services_df[
                    (_services_df["service"] == hovered_dept) &
                    (_services_df["week"] == hovered_week)
                ]
                if not week_data.empty:
                    highlight_sat = week_data["patient_satisfaction"].values[0]
                    highlight_acc = week_data["acceptance_rate"].values[0]
        
        # Create KDE figures
        sat_fig = create_kde_figure(_services_df, selected_depts, "patient_satisfaction", highlight_sat, hovered_dept)
        acc_fig = create_kde_figure(_services_df, selected_depts, "acceptance_rate", highlight_acc, hovered_dept)
        
        # Zoom indicator text
        if zoom_level == "detail":
            indicator = f"🔍 Detail (W{week_range[0]}-{week_range[1]})"
        elif zoom_level == "quarter":
            indicator = f"📊 Quarter (W{week_range[0]}-{week_range[1]})"
        else:
            indicator = f"🌐 Overview (W{week_range[0]}-{week_range[1]})"
        
        return kde_style, sat_fig, acc_fig, indicator
    
    # =========================================================================
    # 4. PCP BRUSH (Week axis) → UPDATE WEEK RANGE (line chart zooms to that range)
    # =========================================================================
    @callback(
        Output("current-week-range", "data", allow_duplicate=True),
        Input("pcp-chart", "restyleData"),
        State("current-week-range", "data"),
        prevent_initial_call=True
    )
    def sync_week_range_from_pcp_brush(restyle_data, current_range):
        """Brush Week axis: zoom line chart to that range. Clear brush / double-click → reset to 52 weeks."""
        if not restyle_data or not isinstance(restyle_data, list) or len(restyle_data) == 0:
            return no_update
        # restyleData format: [edits_dict, trace_indices]; edits has keys like "dimensions[0].constraintrange"
        edits = restyle_data[0] if isinstance(restyle_data[0], dict) else None
        if not edits:
            return no_update
        key = "dimensions[0].constraintrange"
        if key not in edits:
            return no_update
        val = edits[key]
        # Brush cleared (null/empty) → reset to 52 weeks
        if val is None or (isinstance(val, (list, tuple)) and len(val) == 0):
            return [1, 52]
        # Value can be [[min, max]] or [min, max]
        if isinstance(val, (list, tuple)) and len(val) >= 1:
            r = val[0] if isinstance(val[0], (list, tuple)) else val
            if isinstance(r, (list, tuple)) and len(r) >= 2:
                w_min = max(1, int(round(float(r[0]))))
                w_max = min(52, int(round(float(r[1]))))
                span = w_max - w_min + 1
                # Full range or nearly full = reset to 52 weeks (double-click / clear brush)
                if span >= 51 or (w_min <= 2 and w_max >= 51):
                    return [1, 52]
                if w_min < w_max:
                    return [w_min, w_max]
        return no_update

    # =========================================================================
    # 5. OVERVIEW ZOOM → UPDATE WEEK RANGE
    # =========================================================================
    @callback(
        Output("current-week-range", "data", allow_duplicate=True),
        Input("overview-chart", "relayoutData"),
        State("current-week-range", "data"),
        prevent_initial_call=True
    )
    def sync_week_range_from_overview_zoom(relayout_data, current_range):
        """Sync current-week-range when user zooms on the overview chart."""
        if not relayout_data:
            return no_update
        
        # Check for x-axis zoom
        if 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
            x_min = relayout_data['xaxis.range[0]']
            x_max = relayout_data['xaxis.range[1]']
            new_range = [max(1, int(round(x_min))), min(52, int(round(x_max)))]
            if new_range[0] < new_range[1]:
                return new_range
        
        # Also check xaxis2 (shared subplot)
        if 'xaxis2.range[0]' in relayout_data and 'xaxis2.range[1]' in relayout_data:
            x_min = relayout_data['xaxis2.range[0]']
            x_max = relayout_data['xaxis2.range[1]']
            new_range = [max(1, int(round(x_min))), min(52, int(round(x_max)))]
            if new_range[0] < new_range[1]:
                return new_range
        
        # Check for autorange (double-click reset)
        if relayout_data.get('xaxis.autorange') or relayout_data.get('xaxis2.autorange'):
            return [1, 52]
        
        return no_update
    
    # =========================================================================
    # 6. SYNC SLIDER TO MATCH WEEK RANGE STORE
    # =========================================================================
    @callback(
        Output("week-slider", "value", allow_duplicate=True),
        Input("current-week-range", "data"),
        prevent_initial_call=True
    )
    def sync_slider_from_week_range(week_range):
        """Sync slider when week range changes (e.g., from chart zoom)."""
        if not week_range:
            return [1, 52]
        return week_range
