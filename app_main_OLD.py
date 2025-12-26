"""
Hospital Dashboard - CLEAN VERSION
No loading animation, fixed spike positioning using bbox from hoverData
"""

from dash import Dash, html, dcc, callback, Output, Input, State, ctx
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Hospital Dashboard"

# Load data
DATA_PATH = "jbi100_app/data/services_weekly.csv"
df = pd.read_csv(DATA_PATH)
df["acceptance_rate"] = (df["patients_admitted"] / df["patients_request"] * 100).round(1)

DEPT_COLORS = {"emergency": "#e74c3c", "surgery": "#3498db", "general_medicine": "#2ecc71", "ICU": "#9b59b6"}
DEPT_LABELS = {"emergency": "Emergency", "surgery": "Surgery", "general_medicine": "General Medicine", "ICU": "ICU"}

DATA_FOR_CLIENT = {}
for week in range(1, 53):
    week_data = df[df["week"] == week]
    DATA_FOR_CLIENT[week] = {row["service"]: {"satisfaction": int(row["patient_satisfaction"]), "acceptance": round(row["acceptance_rate"], 1)} for _, row in week_data.iterrows()}


def create_overview_charts(selected_depts, week_range):
    week_min, week_max = week_range
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.18, subplot_titles=("Patient Satisfaction by Department", "Acceptance Rate by Department"))
    
    for dept in selected_depts:
        # Load ALL data, not filtered by week_range
        dept_data = df[df["service"] == dept].sort_values("week")
        fig.add_trace(go.Scatter(x=dept_data["week"], y=dept_data["patient_satisfaction"], name=DEPT_LABELS[dept], line=dict(color=DEPT_COLORS[dept], width=2), mode="lines+markers", marker=dict(size=5, color=DEPT_COLORS[dept]), hoverinfo="none", legendgroup=dept), row=1, col=1)
        fig.add_trace(go.Scatter(x=dept_data["week"], y=dept_data["acceptance_rate"], name=DEPT_LABELS[dept], line=dict(color=DEPT_COLORS[dept], width=2), mode="lines+markers", marker=dict(size=5, color=DEPT_COLORS[dept]), hoverinfo="none", legendgroup=dept, showlegend=False), row=2, col=1)
    
    fig.update_layout(
        height=450, 
        margin=dict(l=60, r=20, t=40, b=60), 
        hovermode="x", 
        showlegend=False, 
        plot_bgcolor="white", 
        paper_bgcolor="white",
        dragmode="pan"  # Enable pan/drag
    )
    # Set view window (not data filter)
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0", dtick=4, range=[week_min - 0.5, week_max + 0.5], fixedrange=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e0e0e0", zeroline=False, range=[0, 100], dtick=25, fixedrange=True)  # Y fixed, X can pan
    fig.update_yaxes(title_text="Satisfaction", row=1, col=1)
    fig.update_yaxes(title_text="Acceptance %", row=2, col=1)
    fig.update_xaxes(title_text="Week", row=2, col=1)
    return fig


WIDGET_INFO = {
    "overview": {"icon": "📊", "title": "Hospital Performance Overview", "subtitle": "T1: Browse trends and identify outliers"},
    "quantity": {"icon": "📦", "title": "Capacity & Patient Flow", "subtitle": "T2: Bed allocation | T3: Stay duration"},
    "quality": {"icon": "⭐", "title": "Quality & Satisfaction", "subtitle": "T4: Correlations | T5: Staff impact | T6: Extremes"}
}


def make_main_widget(name, selected_depts, week_range):
    info = WIDGET_INFO[name]
    header = html.Div(style={"paddingBottom": "8px", "marginBottom": "10px", "borderBottom": "2px solid #eee", "flexShrink": "0"}, children=[
        html.H4(f"{info['icon']} {info['title']}", style={"margin": "0", "color": "#2c3e50", "fontWeight": "500"}),
        html.Span(info["subtitle"], style={"fontSize": "12px", "color": "#999"})
    ])
    
    if name == "overview" and selected_depts:
        content = html.Div(style={"flex": "1", "display": "flex", "gap": "12px", "minHeight": "0"}, children=[
            html.Div(id="chart-container", style={"flex": "1", "position": "relative", "minWidth": "0"}, children=[
                dcc.Graph(id="overview-chart", figure=create_overview_charts(selected_depts, week_range), style={"height": "100%", "width": "100%"}, config={"displayModeBar": False}),
                html.Div(id="hover-highlight", style={"position": "absolute", "top": "15px", "bottom": "25px", "width": "14px", "backgroundColor": "rgba(52, 152, 219, 0.2)", "pointerEvents": "none", "display": "none", "borderRadius": "3px", "left": "60px"})
            ]),
            html.Div(id="side-tooltip", style={"width": "140px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "padding": "10px", "border": "1px solid #e0e0e0", "flexShrink": "0", "fontSize": "11px"}, children=[
                html.Div(id="tooltip-content", children=[html.Div("Hover over", style={"color": "#999", "textAlign": "center"}), html.Div("the chart", style={"color": "#999", "textAlign": "center"})])
            ])
        ])
    elif name == "overview":
        content = html.Div("Please select at least one department", style={"flex": "1", "display": "flex", "alignItems": "center", "justifyContent": "center", "color": "#999"})
    else:
        content = html.Div(style={"flex": "1", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "display": "flex", "alignItems": "center", "justifyContent": "center", "color": "#bbb", "fontSize": "18px"}, children=[f"[ {name.upper()} CHARTS HERE ]"])
    
    return html.Div(style={"height": "100%", "display": "flex", "flexDirection": "column"}, children=[header, content])


def make_mini_widget(name):
    info = WIDGET_INFO[name]
    return html.Div(style={"height": "100%", "display": "flex", "flexDirection": "column"}, children=[
        html.Div(f"{info['icon']} {info['title']}", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "5px", "color": "#2c3e50"}),
        html.Div(info["subtitle"], style={"fontSize": "11px", "color": "#999", "marginBottom": "8px"}),
        html.Div(style={"flex": "1", "backgroundColor": "#f8f9fa", "borderRadius": "6px", "display": "flex", "alignItems": "center", "justifyContent": "center", "color": "#ccc", "fontSize": "12px"}, children=["[ Mini charts here ]"]),
        html.Div("↑ Click to expand", style={"fontSize": "11px", "color": "#3498db", "fontWeight": "500", "marginTop": "8px", "textAlign": "center"})
    ])


# Layout
app.layout = html.Div(style={"display": "flex", "height": "100vh", "backgroundColor": "#f5f6fa", "fontFamily": "Segoe UI, Arial, sans-serif", "overflow": "hidden"}, children=[
    dcc.Store(id="week-data-store", data=DATA_FOR_CLIENT),
    dcc.Store(id="current-week-range", data=[1, 52]),
    dcc.Store(id="expanded-widget", data="overview"),
    
    # Sidebar
    html.Div(id="sidebar", style={"width": "240px", "backgroundColor": "#f8f9fa", "display": "flex", "flexDirection": "column", "transition": "width 0.3s ease", "overflow": "hidden", "flexShrink": "0", "borderRight": "1px solid #e0e0e0", "borderRadius": "0 12px 12px 0"}, children=[
        html.Div(id="toggle-container", style={"padding": "10px", "display": "flex", "justifyContent": "center"}, children=[
            html.Button(id="toggle-sidebar", n_clicks=0, style={"background": "#3eaa77", "border": "none", "color": "white", "cursor": "pointer", "borderRadius": "8px", "padding": "10px 12px", "fontSize": "13px", "width": "100%", "display": "flex", "alignItems": "center", "justifyContent": "center", "gap": "6px"}, children=[html.Span("⚙️", id="sidebar-icon", style={"fontSize": "16px"}), html.Span("Options", id="sidebar-title")])
        ]),
        html.Div(id="sidebar-content", style={"padding": "15px", "overflowY": "auto"}, children=[
            html.Label("Departments", style={"color": "#2c3e50", "fontWeight": "600", "marginBottom": "10px", "display": "block", "fontSize": "13px"}),
            dcc.Checklist(id="dept-filter", options=[{"label": " Emergency", "value": "emergency"}, {"label": " Surgery", "value": "surgery"}, {"label": " General Medicine", "value": "general_medicine"}, {"label": " ICU", "value": "ICU"}], value=["emergency"], style={"color": "#34495e", "fontSize": "12px"}, inputStyle={"marginRight": "8px"}, labelStyle={"display": "block", "marginBottom": "8px", "cursor": "pointer"}),
            html.Hr(style={"borderColor": "#e0e0e0", "margin": "15px 0"}),
            html.Label("Week Range", style={"color": "#2c3e50", "fontWeight": "600", "marginBottom": "10px", "display": "block", "fontSize": "13px"}),
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "8px", "marginBottom": "10px"}, children=[
                dcc.Input(id="week-start-input", type="number", min=1, max=52, value=1, debounce=True, style={"width": "45px", "padding": "4px", "borderRadius": "4px", "border": "1px solid #ccc", "backgroundColor": "white", "color": "#2c3e50", "textAlign": "center", "fontSize": "12px"}),
                html.Span("to", style={"color": "#7f8c8d", "fontSize": "12px"}),
                dcc.Input(id="week-end-input", type="number", min=1, max=52, value=52, debounce=True, style={"width": "45px", "padding": "4px", "borderRadius": "4px", "border": "1px solid #ccc", "backgroundColor": "white", "color": "#2c3e50", "textAlign": "center", "fontSize": "12px"}),
            ]),
            dcc.RangeSlider(id="week-slider", min=1, max=52, step=1, value=[1, 52], marks={1: {"label": "1", "style": {"color": "#7f8c8d", "fontSize": "10px"}}, 26: {"label": "26", "style": {"color": "#7f8c8d", "fontSize": "10px"}}, 52: {"label": "52", "style": {"color": "#7f8c8d", "fontSize": "10px"}}}, tooltip={"placement": "bottom", "always_visible": False}, allowCross=False),
            html.Div("Drag on chart to pan", style={"color": "#95a5a6", "fontSize": "10px", "textAlign": "center", "marginTop": "5px"}),
            html.Hr(style={"borderColor": "#e0e0e0", "margin": "15px 0"}),
            html.Label("Quick Select", style={"color": "#2c3e50", "fontWeight": "600", "marginBottom": "8px", "display": "block", "fontSize": "13px"}),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "6px", "marginBottom": "8px"}, children=[
                html.Button("All Depts", id="select-all-btn", n_clicks=0, style={"padding": "6px", "backgroundColor": "#3498db", "color": "white", "border": "none", "borderRadius": "4px", "cursor": "pointer", "fontSize": "11px"}),
                html.Button("Reset", id="reset-btn", n_clicks=0, style={"padding": "6px", "backgroundColor": "#e74c3c", "color": "white", "border": "none", "borderRadius": "4px", "cursor": "pointer", "fontSize": "11px"}),
            ]),
            html.Hr(style={"borderColor": "#e0e0e0", "margin": "15px 0"}),
            html.Label("Time Periods", style={"color": "#2c3e50", "fontWeight": "600", "marginBottom": "8px", "display": "block", "fontSize": "13px"}),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr 1fr", "gap": "4px"}, children=[
                html.Button("Q1", id="q1-btn", n_clicks=0, style={"padding": "5px", "backgroundColor": "#ecf0f1", "color": "#2c3e50", "border": "1px solid #bdc3c7", "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                html.Button("Q2", id="q2-btn", n_clicks=0, style={"padding": "5px", "backgroundColor": "#ecf0f1", "color": "#2c3e50", "border": "1px solid #bdc3c7", "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                html.Button("Q3", id="q3-btn", n_clicks=0, style={"padding": "5px", "backgroundColor": "#ecf0f1", "color": "#2c3e50", "border": "1px solid #bdc3c7", "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                html.Button("Q4", id="q4-btn", n_clicks=0, style={"padding": "5px", "backgroundColor": "#ecf0f1", "color": "#2c3e50", "border": "1px solid #bdc3c7", "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
            ]),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "4px", "marginTop": "4px"}, children=[
                html.Button("H1", id="h1-btn", n_clicks=0, style={"padding": "5px", "backgroundColor": "#ecf0f1", "color": "#2c3e50", "border": "1px solid #bdc3c7", "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
                html.Button("H2", id="h2-btn", n_clicks=0, style={"padding": "5px", "backgroundColor": "#ecf0f1", "color": "#2c3e50", "border": "1px solid #bdc3c7", "borderRadius": "4px", "cursor": "pointer", "fontSize": "10px"}),
            ])
        ])
    ]),
    
    # Main content - NO loading wrapper
    html.Div(style={"flex": "1", "display": "flex", "flexDirection": "column", "padding": "8px", "gap": "8px", "overflow": "hidden", "minWidth": "0"}, children=[
        html.Div(style={"height": "calc(70vh - 12px)", "backgroundColor": "white", "borderRadius": "12px", "boxShadow": "0 4px 12px rgba(0,0,0,0.08)", "padding": "20px", "display": "flex", "flexDirection": "column", "overflow": "hidden"}, children=[
            html.Div(id="main-widget-area", style={"height": "100%", "display": "flex", "flexDirection": "column"})
        ]),
        html.Div(style={"display": "flex", "gap": "8px", "height": "calc(30vh - 12px)"}, children=[
            html.Div(id="mini-slot-1", n_clicks=0, style={"flex": "1", "backgroundColor": "white", "borderRadius": "10px", "boxShadow": "0 2px 8px rgba(0,0,0,0.08)", "padding": "15px", "cursor": "pointer", "display": "flex", "flexDirection": "column", "overflow": "hidden"}),
            html.Div(id="mini-slot-2", n_clicks=0, style={"flex": "1", "backgroundColor": "white", "borderRadius": "10px", "boxShadow": "0 2px 8px rgba(0,0,0,0.08)", "padding": "15px", "cursor": "pointer", "display": "flex", "flexDirection": "column", "overflow": "hidden"})
        ])
    ])
])


# Hover callback - uses bbox.x0 from Plotly for accurate positioning
@callback(
    [Output("tooltip-content", "children"), Output("hover-highlight", "style")],
    [Input("overview-chart", "hoverData")],
    [State("week-data-store", "data"), State("dept-filter", "value"), State("current-week-range", "data")],
    prevent_initial_call=True
)
def update_hover(hoverData, weekData, selectedDepts, weekRange):
    base_style = {"position": "absolute", "top": "15px", "bottom": "25px", "width": "14px", "backgroundColor": "rgba(52, 152, 219, 0.2)", "pointerEvents": "none", "borderRadius": "3px"}
    default_tooltip = [html.Div("Hover over", style={"color": "#999", "textAlign": "center"}), html.Div("the chart", style={"color": "#999", "textAlign": "center"})]
    
    if not hoverData or not hoverData.get("points"):
        return default_tooltip, {**base_style, "display": "none", "left": "60px"}
    
    point = hoverData["points"][0]
    week = round(point["x"])
    weekMin, weekMax = weekRange
    
    if week < weekMin or week > weekMax:
        return default_tooltip, {**base_style, "display": "none", "left": "60px"}
    
    # Use bbox from Plotly - this is the actual pixel position!
    bbox = point.get("bbox", {})
    xPos = bbox.get("x0", 60)  # x0 is the left edge of the point
    
    colors = {"emergency": "#e74c3c", "surgery": "#3498db", "general_medicine": "#2ecc71", "ICU": "#9b59b6"}
    labels = {"emergency": "Emerg.", "surgery": "Surgery", "general_medicine": "Gen.Med", "ICU": "ICU"}
    
    tooltip_children = [
        html.Div(f"Week {week}", style={"fontWeight": "600", "fontSize": "13px", "color": "#2c3e50", "paddingBottom": "6px", "marginBottom": "8px", "borderBottom": "2px solid #3498db"}),
        html.Div("SATISFACTION", style={"fontSize": "9px", "color": "#888", "marginBottom": "4px", "fontWeight": "600"})
    ]
    
    for dept in selectedDepts:
        data = weekData.get(str(week), {}).get(dept)
        if data:
            tooltip_children.append(html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "2px"}, children=[
                html.Span(labels[dept], style={"color": "#555"}),
                html.Span(str(data["satisfaction"]), style={"fontWeight": "600", "color": colors[dept]})
            ]))
    
    tooltip_children.append(html.Div("ACCEPTANCE %", style={"fontSize": "9px", "color": "#888", "margin": "8px 0 4px 0", "fontWeight": "600"}))
    
    for dept in selectedDepts:
        data = weekData.get(str(week), {}).get(dept)
        if data:
            tooltip_children.append(html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "2px"}, children=[
                html.Span(labels[dept], style={"color": "#555"}),
                html.Span(f"{data['acceptance']}%", style={"fontWeight": "600", "color": colors[dept]})
            ]))
    
    highlight_style = {**base_style, "display": "block", "left": f"{xPos - 7}px"}
    return tooltip_children, highlight_style


# Other callbacks
@callback(
    [Output("sidebar", "style"), Output("sidebar-content", "style"), Output("sidebar-title", "style"), Output("toggle-sidebar", "style")],
    Input("toggle-sidebar", "n_clicks")
)
def toggle_sidebar(n_clicks):
    base = {"backgroundColor": "#f8f9fa", "display": "flex", "flexDirection": "column", "transition": "width 0.3s ease", "overflow": "hidden", "flexShrink": "0", "borderRight": "1px solid #e0e0e0", "borderRadius": "0 12px 12px 0"}
    btn_base = {"border": "none", "color": "white", "cursor": "pointer", "borderRadius": "8px", "display": "flex", "alignItems": "center", "justifyContent": "center"}
    if n_clicks % 2 == 1:
        # Collapsed: square button, no background
        return (
            {**base, "width": "50px", "backgroundColor": "transparent", "borderRight": "none"},
            {"display": "none"},
            {"display": "none"},
            {**btn_base, "background": "#3498db", "width": "36px", "height": "36px", "padding": "0", "fontSize": "16px"}
        )
    # Expanded: full width button
    return (
        {**base, "width": "240px"},
        {"padding": "15px", "overflowY": "auto"},
        {"display": "inline"},
        {**btn_base, "background": "#3498db", "width": "100%", "padding": "10px 12px", "fontSize": "13px", "gap": "6px"}
    )

@callback(Output("dept-filter", "value"), [Input("select-all-btn", "n_clicks"), Input("reset-btn", "n_clicks")], prevent_initial_call=True)
def quick_select(all_clicks, reset_clicks):
    return ["emergency", "surgery", "general_medicine", "ICU"] if ctx.triggered_id == "select-all-btn" else ["emergency"]

@callback(Output("week-slider", "value"), [Input("q1-btn", "n_clicks"), Input("q2-btn", "n_clicks"), Input("q3-btn", "n_clicks"), Input("q4-btn", "n_clicks"), Input("h1-btn", "n_clicks"), Input("h2-btn", "n_clicks"), Input("reset-btn", "n_clicks")], prevent_initial_call=True)
def set_time_period(q1, q2, q3, q4, h1, h2, reset):
    return {"q1-btn": [1, 13], "q2-btn": [14, 26], "q3-btn": [27, 39], "q4-btn": [40, 52], "h1-btn": [1, 26], "h2-btn": [27, 52], "reset-btn": [1, 52]}.get(ctx.triggered_id, [1, 52])

@callback(Output("current-week-range", "data"), Input("week-slider", "value"))
def store_week_range(week_range):
    return week_range

# Sync inputs with slider
@callback(
    [Output("week-start-input", "value"), Output("week-end-input", "value")],
    Input("week-slider", "value")
)
def sync_inputs_from_slider(week_range):
    return week_range[0], week_range[1]

# Sync slider with inputs
@callback(
    Output("week-slider", "value", allow_duplicate=True),
    [Input("week-start-input", "value"), Input("week-end-input", "value")],
    prevent_initial_call=True
)
def sync_slider_from_inputs(start, end):
    start = max(1, min(52, start or 1))
    end = max(1, min(52, end or 52))
    if start > end:
        start, end = end, start
    return [start, end]

@callback(Output("expanded-widget", "data"), [Input("mini-slot-1", "n_clicks"), Input("mini-slot-2", "n_clicks")], [State("expanded-widget", "data")], prevent_initial_call=True)
def swap_widget(click1, click2, current):
    widgets = ["overview", "quantity", "quality"]
    others = [w for w in widgets if w != current]
    return others[0] if ctx.triggered_id == "mini-slot-1" else others[1] if ctx.triggered_id == "mini-slot-2" else current

@callback([Output("main-widget-area", "children"), Output("mini-slot-1", "children"), Output("mini-slot-2", "children")], [Input("expanded-widget", "data"), Input("dept-filter", "value"), Input("week-slider", "value")])
def render_widgets(expanded, selected_depts, week_range):
    widgets = ["overview", "quantity", "quality"]
    others = [w for w in widgets if w != expanded]
    return make_main_widget(expanded, selected_depts or ["emergency"], week_range), make_mini_widget(others[0]), make_mini_widget(others[1])

if __name__ == "__main__":
    app.run(debug=True, port=8050)
