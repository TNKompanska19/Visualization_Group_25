from dash import html, dcc
import plotly.express as px


class TrendChart(html.Div):
    def __init__(self, title, figure, html_id):
        super().__init__(
            className="graph_card",
            children=[
                html.H3(title),
                dcc.Graph(id=html_id, figure=figure)
            ]
        )


def make_trend_charts(df_services):
    """
    Returns two TrendChart components:
    1. Weekly total demand
    2. Weekly average staff morale
    """

    # -------------------------------------------
    # Weekly demand
    # -------------------------------------------
    df_demand = (
        df_services.groupby("week")["patients_request"]
        .sum()
        .reset_index()
        .sort_values("week")
    )

    fig_demand = px.line(
        df_demand,
        x="week",
        y="patients_request",
        title="Total Patients Request per Week"
    )
    fig_demand.update_layout(height=350, xaxis_title="Week", yaxis_title="Total Demand")

    demand_chart = TrendChart(
        "Weekly Total Demand",
        fig_demand,
        html_id="trend-demand"
    )

    # -------------------------------------------
    # Weekly average staff morale
    # -------------------------------------------
    df_morale = (
        df_services.groupby("week")["staff_morale"]
        .mean()
        .reset_index()
        .sort_values("week")
    )

    fig_morale = px.line(
        df_morale,
        x="week",
        y="staff_morale",
        title="Average Staff Morale per Week"
    )
    fig_morale.update_layout(height=350, xaxis_title="Week", yaxis_title="Average Morale")

    morale_chart = TrendChart(
        "Weekly Staff Morale",
        fig_morale,
        html_id="trend-morale"
    )

    return demand_chart, morale_chart
