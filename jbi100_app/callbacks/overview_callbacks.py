"""
Overview Widget Callbacks
JBI100 Visualization - Group 25

Callbacks for the Overview widget (T1):
- Hover interactions
- Tooltip updates
- Histogram updates (detail zoom)
"""

from dash import callback, Output, Input, State, html
from dash.exceptions import PreventUpdate
import numpy as np

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS_SHORT
from jbi100_app.data import get_services_data
from jbi100_app.views.overview import build_tooltip_content, get_zoom_level

_services_df = get_services_data()

# Cache for histogram bin data (computed once per dept selection)
_HIST_CACHE = {}


def _get_cached_histogram_data(selected_depts, metric):
    """Get or compute cached KDE data."""
    from scipy import stats
    
    cache_key = (tuple(sorted(selected_depts or [])), metric)
    
    if cache_key not in _HIST_CACHE:
        if selected_depts:
            filtered = _services_df[_services_df["service"].isin(selected_depts)]
        else:
            filtered = _services_df
        
        values = filtered[metric].values
        
        # Compute KDE
        kde = stats.gaussian_kde(values)
        x_range = np.linspace(0, 100, 200)
        y_density = kde(x_range)
        
        _HIST_CACHE[cache_key] = {
            "x_range": x_range,
            "y_density": y_density
        }
    
    return _HIST_CACHE[cache_key]


def _create_histogram_figure(kde_data, metric, highlight_value=None):
    """Create KDE figure from cached data."""
    import plotly.graph_objects as go
    
    x_range = kde_data["x_range"]
    y_density = kde_data["y_density"]
    
    fig = go.Figure()
    
    # Fill area under curve (gray background)
    fig.add_trace(go.Scatter(
        x=x_range,
        y=y_density,
        mode='lines',
        fill='tozeroy',
        line=dict(color='#ccc', width=1),
        fillcolor='rgba(200,200,200,0.5)',
        hoverinfo='skip'
    ))
    
    # Add highlighted region if value provided
    if highlight_value is not None:
        highlight_width = 3
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
    
    title_text = "Satisfaction" if "satisfaction" in metric else "Acceptance"
    
    fig.update_layout(
        height=175,
        margin=dict(l=5, r=5, t=20, b=20),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        title=dict(text=title_text, font=dict(size=9, color="#666"), x=0.5, y=0.95),
        xaxis=dict(range=[0, 100], tickvals=[0, 25, 50, 75, 100], tickfont=dict(size=7), showgrid=False),
        yaxis=dict(showticklabels=False, showgrid=False),
        showlegend=False
    )
    
    return fig


def register_overview_callbacks():
    """Register all overview widget callbacks."""
    
    @callback(
        [Output("tooltip-content", "children"),
         Output("hover-highlight", "style")],
        [Input("overview-chart", "hoverData")],
        [State("week-data-store", "data"), 
         State("dept-filter", "value"), 
         State("current-week-range", "data")],
        prevent_initial_call=True
    )
    def update_tooltip_and_highlight(hoverData, weekData, selectedDepts, weekRange):
        """Update tooltip and vertical line indicator on hover."""
        base_style = {
            "position": "absolute",
            "top": "10px", "bottom": "30px",
            "width": "3px",
            "backgroundColor": "rgba(52, 152, 219, 0.6)",
            "pointerEvents": "none",
            "borderRadius": "2px"
        }
        default_tooltip = [
            html.Div("Hover over", style={"color": "#999", "textAlign": "center"}),
            html.Div("the chart", style={"color": "#999", "textAlign": "center"})
        ]
        
        if not hoverData or not hoverData.get("points"):
            return default_tooltip, {**base_style, "display": "none", "left": "40px"}
        
        point = hoverData["points"][0]
        week = round(point["x"])
        weekMin, weekMax = weekRange
        
        if week < weekMin or week > weekMax:
            return default_tooltip, {**base_style, "display": "none", "left": "40px"}
        
        # Get center position from bbox
        bbox = point.get("bbox", {})
        x0 = bbox.get("x0", 40)
        x1 = bbox.get("x1", x0 + 10)
        xCenter = (x0 + x1) / 2  # Center of the point
        
        tooltip_children = build_tooltip_content(
            week, weekData, selectedDepts or [], _services_df, weekRange
        )
        
        # Position line at center of hovered point
        highlight_style = {**base_style, "display": "block", "left": f"{xCenter - 1.5}px"}
        return tooltip_children, highlight_style
    
    @callback(
        [Output("hist-satisfaction", "figure"),
         Output("hist-acceptance", "figure")],
        [Input("overview-chart", "hoverData")],
        [State("week-data-store", "data"), 
         State("dept-filter", "value"), 
         State("current-week-range", "data")],
        prevent_initial_call=True
    )
    def update_histograms(hoverData, weekData, selectedDepts, weekRange):
        """Update histogram highlighting on hover."""
        zoom_level = get_zoom_level(weekRange)
        if zoom_level != "detail":
            raise PreventUpdate
        
        sat_hist_data = _get_cached_histogram_data(selectedDepts, "patient_satisfaction")
        acc_hist_data = _get_cached_histogram_data(selectedDepts, "acceptance_rate")
        
        if not hoverData or not hoverData.get("points"):
            return (
                _create_histogram_figure(sat_hist_data, "patient_satisfaction", None),
                _create_histogram_figure(acc_hist_data, "acceptance_rate", None)
            )
        
        point = hoverData["points"][0]
        week = round(point["x"])
        weekMin, weekMax = weekRange
        
        if week < weekMin or week > weekMax:
            return (
                _create_histogram_figure(sat_hist_data, "patient_satisfaction", None),
                _create_histogram_figure(acc_hist_data, "acceptance_rate", None)
            )
        
        week_data_for_hover = weekData.get(str(week), {})
        
        sat_values = []
        acc_values = []
        for dept in (selectedDepts or []):
            dept_data = week_data_for_hover.get(dept)
            if dept_data:
                sat_values.append(dept_data.get("satisfaction", 0))
                acc_values.append(dept_data.get("acceptance", 0))
        
        avg_sat = sum(sat_values) / len(sat_values) if sat_values else None
        avg_acc = sum(acc_values) / len(acc_values) if acc_values else None
        
        return (
            _create_histogram_figure(sat_hist_data, "patient_satisfaction", avg_sat),
            _create_histogram_figure(acc_hist_data, "acceptance_rate", avg_acc)
        )
