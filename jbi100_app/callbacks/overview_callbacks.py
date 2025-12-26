"""
Overview Widget Callbacks
JBI100 Visualization - Group 25

Callbacks for the Overview widget (T1):
- Hover interactions
- Tooltip updates
- Highlight synchronization
"""

from dash import callback, Output, Input, State, html

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS_SHORT, EVENT_COLORS, EVENT_ICONS
from jbi100_app.data import get_services_data

# Load data for event lookup
_services_df = get_services_data()


def register_overview_callbacks():
    """Register all overview widget callbacks."""
    
    # =========================================================================
    # HOVER INTERACTION
    # =========================================================================
    @callback(
        [Output("tooltip-content", "children"), Output("hover-highlight", "style")],
        [Input("overview-chart", "hoverData")],
        [State("week-data-store", "data"), 
         State("dept-filter", "value"), 
         State("current-week-range", "data")],
        prevent_initial_call=True
    )
    def update_hover(hoverData, weekData, selectedDepts, weekRange):
        """
        Update tooltip content and highlight position on hover.
        
        This callback:
        1. Reads hover position from the chart
        2. Looks up data for that week
        3. Updates the side tooltip panel
        4. Moves the highlight bar to the correct position
        """
        base_style = {
            "position": "absolute",
            "top": "15px",
            "bottom": "25px",
            "width": "14px",
            "backgroundColor": "rgba(52, 152, 219, 0.2)",
            "pointerEvents": "none",
            "borderRadius": "3px"
        }
        default_tooltip = [
            html.Div("Hover over", style={"color": "#999", "textAlign": "center"}),
            html.Div("the chart", style={"color": "#999", "textAlign": "center"})
        ]
        
        if not hoverData or not hoverData.get("points"):
            return default_tooltip, {**base_style, "display": "none", "left": "60px"}
        
        point = hoverData["points"][0]
        week = round(point["x"])
        weekMin, weekMax = weekRange
        
        if week < weekMin or week > weekMax:
            return default_tooltip, {**base_style, "display": "none", "left": "60px"}
        
        # Get position from bbox (pixel coordinates)
        bbox = point.get("bbox", {})
        xPos = bbox.get("x0", 60)
        
        # Build tooltip content
        tooltip_children = _build_tooltip_content(week, weekData, selectedDepts)
        
        highlight_style = {**base_style, "display": "block", "left": f"{xPos - 7}px"}
        return tooltip_children, highlight_style


def _build_tooltip_content(week, week_data, selected_depts):
    """
    Build the tooltip HTML content.
    
    Args:
        week: Current week number
        week_data: Dict from dcc.Store with all week data
        selected_depts: List of selected department IDs
    
    Returns:
        list: List of dash html components
    """
    # Check for events this week
    week_events = _services_df[
        (_services_df["week"] == week) & (_services_df["event"] != "none")
    ]["event"].unique()
    
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
                            html.Span(evt.capitalize(), style={
                                "fontSize": "10px", 
                                "color": evt_color, 
                                "fontWeight": "600"
                            })
                        ]
                    )
                )
    
    # Satisfaction section
    tooltip_children.append(
        html.Div("SATISFACTION", style={
            "fontSize": "9px", 
            "color": "#888", 
            "marginBottom": "4px", 
            "fontWeight": "600"
        })
    )
    
    for dept in (selected_depts or []):
        data = week_data.get(str(week), {}).get(dept)
        if data:
            tooltip_children.append(
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "marginBottom": "2px"},
                    children=[
                        html.Span(DEPT_LABELS_SHORT.get(dept, dept), style={"color": "#555"}),
                        html.Span(str(data["satisfaction"]), style={
                            "fontWeight": "600", 
                            "color": DEPT_COLORS.get(dept, "#999")
                        })
                    ]
                )
            )
    
    # Acceptance section
    tooltip_children.append(
        html.Div("ACCEPTANCE %", style={
            "fontSize": "9px", 
            "color": "#888", 
            "margin": "8px 0 4px 0", 
            "fontWeight": "600"
        })
    )
    
    for dept in (selected_depts or []):
        data = week_data.get(str(week), {}).get(dept)
        if data:
            tooltip_children.append(
                html.Div(
                    style={"display": "flex", "justifyContent": "space-between", "marginBottom": "2px"},
                    children=[
                        html.Span(DEPT_LABELS_SHORT.get(dept, dept), style={"color": "#555"}),
                        html.Span(f"{data['acceptance']}%", style={
                            "fontWeight": "600", 
                            "color": DEPT_COLORS.get(dept, "#999")
                        })
                    ]
                )
            )
    
    return tooltip_children
