from jbi100_app.main import app

from dash import html, dcc
from dash.dependencies import Input, Output

from jbi100_app.views.menu import make_menu_layout
from jbi100_app.views.heatmap import Heatmap
from jbi100_app.views.los_boxplot import LOSBoxplot
from jbi100_app.views.los_age_boxplot import LOSAgeBoxplot
from jbi100_app.views.trend import make_trend_charts
from jbi100_app.views.kpi import make_kpi_row
from jbi100_app.data import get_data

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


# ============================================================
# LOAD DATA
# ============================================================
df_services, df_patients = get_data()

df_patients = df_patients.copy()
df_patients["arrival_week"] = df_patients["arrival_date"].dt.isocalendar().week.astype(int)

week_min = int(df_services["week"].min())
week_max = int(df_services["week"].max())

service_list = sorted(df_services["service"].unique())

# Pretty (display) labels
service_display_map = {s: s.replace("_", " ").title() for s in service_list}
display_to_internal = {v: k for k, v in service_display_map.items()}

service_options = [{"label": "All services", "value": "ALL"}] + [
    {"label": service_display_map[s], "value": s} for s in service_list
]


# ============================================================
# STATIC COMPONENTS
# ============================================================
heatmap = Heatmap(df_services)
trend_demand, trend_morale = make_trend_charts(df_services)
los_by_service = LOSBoxplot(df_patients)
los_by_age = LOSAgeBoxplot(df_patients)
kpi_row = make_kpi_row(df_services, df_patients)


# ============================================================
# LAYOUT
# ============================================================
app.layout = html.Div(
    id="app-container",
    children=[
        html.Div(
            id="left-column",
            className="three columns",
            children=make_menu_layout(),
        ),

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
                            marks={week_min: str(week_min), week_max: str(week_max)},
                            allowCross=False,
                        ),

                        html.Br(),
                        html.Label("Week grouping"),
                        dcc.Dropdown(
                            id="week-grouping",
                            options=[
                                {"label": "Weekly (1)", "value": 1},
                                {"label": "Bi-weekly (2)", "value": 2},
                                {"label": "Monthly (4)", "value": 4},
                            ],
                            value=4,   # DEFAULT = MONTHLY (recommended)
                            clearable=False,
                        ),

                        html.Div(
                            id="filter-info",
                            style={"marginTop": "10px", "fontSize": "13px", "color": "#555"},
                        ),
                    ],
                ),

                heatmap.layout(),
                kpi_row,
                html.Div(className="row", children=[trend_demand, trend_morale]),
                html.Div(className="row", children=[los_by_service, los_by_age]),
            ],
        ),
    ],
)


# ============================================================
# HELPERS
# ============================================================
def filter_services_df(service_value, week_range):
    lo, hi = week_range
    df = df_services[(df_services["week"] >= lo) & (df_services["week"] <= hi)]
    if service_value != "ALL":
        df = df[df["service"] == service_value]
    return df


def resolve_active_service(service_dropdown_value, heatmap_click):
    """
    Convert heatmap label → internal name when clicked.
    """
    if heatmap_click and "points" in heatmap_click and len(heatmap_click["points"]) > 0:
        pretty = heatmap_click["points"][0]["y"]
        return display_to_internal.get(pretty, pretty)

    if service_dropdown_value != "ALL":
        return service_dropdown_value

    return None


# ============================================================
# CALLBACKS
# ============================================================

@app.callback(
    Output("filter-info", "children"),
    Input("filter-service", "value"),
    Input("filter-week", "value"),
)
def update_filter_info(service_value, week_range):
    lo, hi = week_range
    if service_value == "ALL":
        return f"Showing all services, weeks {lo}–{hi}."

    pretty = service_display_map.get(service_value, service_value)
    return f"Showing service '{pretty}', weeks {lo}–{hi}."


# ============================================================
# HEATMAP CALLBACK (grouping now ACTUALLY reduces detail)
# ============================================================

@app.callback(
    Output("heatmap-graph", "figure"),
    Input("filter-service", "value"),
    Input("filter-week", "value"),
    Input("week-grouping", "value"),
)
def update_heatmap(service_value, week_range, group_size):
    df = filter_services_df(service_value, week_range).copy()

    df["service_display"] = df["service"].map(service_display_map)
    df["week_group"] = ((df["week"] - 1) // group_size) * group_size + 1

    # TRUE aggregation by week group
    df_grouped = (
        df.groupby(["service_display", "week_group"])["pressure_index"]
        .mean()
        .reset_index()
    )

    df_grouped["week_label"] = df_grouped["week_group"].astype(str)

    fig = px.density_heatmap(
        df_grouped,
        x="week_label",
        y="service_display",
        z="pressure_index",
        color_continuous_scale="RdYlGn_r",
    )

    fig.update_layout(
        height=600,
        margin=dict(l=120, r=40, t=60, b=40),
        xaxis_title=f"Week Groups ({group_size} weeks each)",
        yaxis_title="Service",
    )

    fig.update_yaxes(automargin=True)

    return fig


# ============================================================
# TREND CHARTS
# ============================================================

@app.callback(
    Output("trend-demand", "figure"),
    Output("trend-morale", "figure"),
    Input("filter-service", "value"),
    Input("filter-week", "value"),
)
def update_trends(service_value, week_range):
    df = filter_services_df(service_value, week_range)

    df_demand = (
        df.groupby("week")["patients_request"]
        .sum()
        .reset_index()
        .rename(columns={"patients_request": "Patient Demand"})
    )

    df_morale = (
        df.groupby("week")["staff_morale"]
        .mean()
        .reset_index()
        .rename(columns={"staff_morale": "Staff Morale"})
    )

    fig_demand = px.line(
        df_demand, x="week", y="Patient Demand", title="Total Patient Demand per Week"
    )
    fig_demand.update_layout(margin=dict(l=120, r=40, t=40, b=40))
    fig_demand.update_yaxes(automargin=True)

    fig_morale = px.line(
        df_morale, x="week", y="Staff Morale", title="Average Staff Morale per Week"
    )
    fig_morale.update_layout(margin=dict(l=120, r=40, t=40, b=40))
    fig_morale.update_yaxes(automargin=True)

    return fig_demand, fig_morale


# ============================================================
# LOS BOXPLOTS
# ============================================================

@app.callback(
    Output("los-boxplot-service", "figure"),
    Output("los-boxplot-age", "figure"),
    Input("filter-service", "value"),
    Input("filter-week", "value"),
    Input("heatmap-graph", "clickData"),
)
def update_los(service_value, week_range, heatmap_click):
    lo, hi = week_range

    df = df_patients[
        (df_patients["arrival_week"] >= lo) &
        (df_patients["arrival_week"] <= hi)
    ].copy()

    active_service = resolve_active_service(service_value, heatmap_click)
    if active_service:
        df = df[df["service"] == active_service]

    # SERVICE LOS
    if df.empty:
        fig_service = go.Figure()
        fig_service.update_layout(title="LOS per Service (no data)")
    else:
        df["service_display"] = df["service"].map(service_display_map)

        fig_service = px.box(
            df,
            x="service_display",
            y="LOS",
            color="service_display",
            title="LOS per Service (Length of Stay in Days)",
            points="all"
        )
        fig_service.update_traces(
            hovertemplate="LOS: %{y}<extra></extra>",
            boxmean=True
        )
        fig_service.update_layout(
            margin=dict(l=120, r=40, t=60, b=40),
            yaxis_title="Length of Stay (days)"
        )
        fig_service.update_yaxes(automargin=True)

    # AGE LOS
    if df.empty:
        fig_age = go.Figure()
        fig_age.update_layout(title="LOS per Age Group (no data)")
    else:
        bins = [0, 12, 19, 64, 79, 200]
        labels = ["Child", "Teen", "Adult", "Senior", "Elderly"]
        df_age = df.copy()
        df_age["age_group"] = pd.cut(df_age["age"], bins=bins, labels=labels)

        fig_age = px.box(
            df_age,
            x="age_group",
            y="LOS",
            color="age_group",
            title="LOS per Age Group (Length of Stay in Days)",
            points="all"
        )
        fig_age.update_traces(
            hovertemplate="LOS: %{y}<extra></extra>",
            boxmean=True
        )
        fig_age.update_layout(
            margin=dict(l=120, r=40, t=60, b=40),
            yaxis_title="Length of Stay (days)"
        )
        fig_age.update_yaxes(automargin=True)

    return fig_service, fig_age


# ============================================================
# RUN APP
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
