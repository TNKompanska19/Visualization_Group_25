from jbi100_app.main import app

from dash import html, dcc
from dash.dependencies import Input, Output, State

# Import visualizations (layout wrappers)
from jbi100_app.views.menu import make_menu_layout
from jbi100_app.views.heatmap import Heatmap
from jbi100_app.views.los_boxplot import LOSBoxplot
from jbi100_app.views.los_age_boxplot import LOSAgeBoxplot
from jbi100_app.views.trend import make_trend_charts
from jbi100_app.views.kpi import make_kpi_row

# Load data
from jbi100_app.data import get_data

import plotly.express as px
import plotly.graph_objects as go


# ============================================================
# LOAD DATA
# ============================================================
df_services, df_patients = get_data()

# Precompute arrival week for filtering LOS by time
df_patients = df_patients.copy()
df_patients["arrival_week"] = df_patients["arrival_date"].dt.isocalendar().week.astype(int)

week_min = int(df_services["week"].min())
week_max = int(df_services["week"].max())

service_list = sorted(df_services["service"].unique())
service_options = [{"label": "All services", "value": "ALL"}] + [
    {"label": s, "value": s} for s in service_list
]

# ============================================================
# INSTANTIATE STATIC LAYOUT COMPONENTS
# ============================================================
heatmap = Heatmap(df_services)

trend_demand, trend_morale = make_trend_charts(df_services)

los_by_service = LOSBoxplot(df_patients, mode="service")
los_by_age = LOSAgeBoxplot(df_patients)

kpi_row = make_kpi_row(df_services, df_patients)


# ============================================================
# APP LAYOUT
# ============================================================
app.layout = html.Div(
    id="app-container",
    children=[
        # LEFT SIDEBAR MENU
        html.Div(
            id="left-column",
            className="three columns",
            children=make_menu_layout(),
        ),

        # RIGHT COLUMN
        html.Div(
            id="right-column",
            className="nine columns",
            children=[

                # FILTER PANEL
                html.Div(
                    className="graph_card",
                    children=[
                        html.H3("Filters"),
                        html.Label("Service"),
                        dcc.Dropdown(
                            id="filter-service",
                            options=service_options,
                            value="ALL",
                            clearable=False,
                        ),
                        html.Br(),
                        html.Label("Week range"),
                        dcc.RangeSlider(
                            id="filter-week",
                            min=week_min,
                            max=week_max,
                            step=1,
                            value=[week_min, week_max],
                            marks={
                                week_min: str(week_min),
                                week_max: str(week_max),
                            },
                            allowCross=False,
                        ),
                        html.Div(
                            id="filter-info",
                            style={"marginTop": "10px", "fontSize": "13px", "color": "#555"},
                        ),
                    ],
                ),

                # HEATMAP
                heatmap.layout(),

                # KPI ROW
                kpi_row,

                # TREND CHARTS
                html.Div(
                    className="row",
                    children=[trend_demand, trend_morale],
                ),

                # LOS CHARTS
                html.Div(
                    className="row",
                    children=[los_by_service, los_by_age],
                ),
            ],
        ),
    ],
)


# ============================================================
# CALLBACK HELPERS
# ============================================================

def filter_services_df(service_value, week_range):
    week_lo, week_hi = week_range
    df = df_services[(df_services["week"] >= week_lo) & (df_services["week"] <= week_hi)]
    if service_value != "ALL":
        df = df[df["service"] == service_value]
    return df


def resolve_active_service(service_dropdown_value, heatmap_click):
    if heatmap_click and "points" in heatmap_click and len(heatmap_click["points"]) > 0:
        return heatmap_click["points"][0].get("y", None)

    if service_dropdown_value != "ALL":
        return service_dropdown_value

    return None


# ============================================================
# CALLBACK: Filter Info Text
# ============================================================
@app.callback(
    Output("filter-info", "children"),
    Input("filter-service", "value"),
    Input("filter-week", "value"),
)
def update_filter_info(service_value, week_range):
    week_lo, week_hi = week_range
    if service_value == "ALL":
        return f"Showing all services, weeks {week_lo}–{week_hi}."
    else:
        return f"Showing service '{service_value}', weeks {week_lo}–{week_hi}."


# ============================================================
# CALLBACK: Heatmap (FIXED)
# ============================================================
@app.callback(
    Output("heatmap-graph", "figure"),
    Input("filter-service", "value"),
    Input("filter-week", "value"),
)
def update_heatmap(service_value, week_range):
    df = filter_services_df(service_value, week_range)

    fig = px.density_heatmap(
        df,
        x="week",
        y="service",
        z="pressure_index",
        color_continuous_scale="RdYlGn_r",
        nbinsx=52  # <-- FIX: One bin per week
    )

    # FIX: Force exact 1–52 labels instead of bin ranges like 50–59
    fig.update_layout(
        height=600,
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(type="category")
    )

    return fig


# ============================================================
# CALLBACK: Trend charts
# ============================================================
@app.callback(
    Output("trend-demand", "figure"),
    Output("trend-morale", "figure"),
    Input("filter-service", "value"),
    Input("filter-week", "value"),
)
def update_trends(service_value, week_range):
    df = filter_services_df(service_value, week_range)

    # Demand
    df_demand = (
        df.groupby("week")["patients_request"]
        .sum()
        .reset_index()
        .sort_values("week")
    )

    fig_demand = px.line(
        df_demand,
        x="week",
        y="patients_request",
        title="Total Patients Request per Week",
    )
    fig_demand.update_layout(height=350, xaxis_title="Week", yaxis_title="Total Demand")

    # Morale
    df_morale = (
        df.groupby("week")["staff_morale"]
        .mean()
        .reset_index()
        .sort_values("week")
    )

    fig_morale = px.line(
        df_morale,
        x="week",
        y="staff_morale",
        title="Average Staff Morale per Week",
    )
    fig_morale.update_layout(height=350, xaxis_title="Week", yaxis_title="Average Morale")

    return fig_demand, fig_morale


# ============================================================
# CALLBACK: LOS boxplots
# ============================================================
@app.callback(
    Output("los-boxplot-service", "figure"),
    Output("los-boxplot-age", "figure"),
    Input("filter-service", "value"),
    Input("filter-week", "value"),
    Input("heatmap-graph", "clickData"),
)
def update_los(service_value, week_range, heatmap_click):
    week_lo, week_hi = week_range

    df = df_patients[
        (df_patients["arrival_week"] >= week_lo) &
        (df_patients["arrival_week"] <= week_hi)
    ].copy()

    active_service = resolve_active_service(service_value, heatmap_click)

    if active_service is not None:
        df = df[df["service"] == active_service]

    # LOS by service
    if df.empty:
        fig_service = go.Figure()
        fig_service.update_layout(title="LOS per Service (no data for current filters)")
    else:
        fig_service = px.box(
            df,
            x="service",
            y="LOS",
            color="service",
            title="LOS per Service",
            points="all",
        )
        fig_service.update_layout(height=450, margin=dict(t=60))

    # LOS by age group
    if df.empty:
        fig_age = go.Figure()
        fig_age.update_layout(title="LOS per Age Group (no data for current filters)")
    else:
        import pandas as pd
        bins = [0, 12, 19, 64, 79, 200]
        labels = ["Child (0-12)", "Teen (13-19)", "Adult (20-64)", "Senior (65-79)", "Elderly (80+)"]
        df_age = df.copy()
        df_age["age_group"] = pd.cut(df_age["age"], bins=bins, labels=labels, right=True)

        fig_age = px.box(
            df_age,
            x="age_group",
            y="LOS",
            color="age_group",
            title="LOS per Age Group",
            points="all",
        )
        fig_age.update_layout(height=450, margin=dict(t=60))

    return fig_service, fig_age


# ============================================================
# RUN APP
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
