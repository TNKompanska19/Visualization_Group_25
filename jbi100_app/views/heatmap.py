from dash import html, dcc
import plotly.express as px

class Heatmap:
    def __init__(self, df):
        self.df = df
        self.html_id = "heatmap-graph"

    def layout(self):
        return html.Div(
            className="graph_card",
            children=[
                html.H3("Service × Week Pressure Heatmap"),
                dcc.Graph(id=self.html_id, figure=self.figure())
            ]
        )

    def figure(self):
        fig = px.density_heatmap(
            self.df,
            x="week",
            y="service",
            z="pressure_index",
            color_continuous_scale="RdYlGn_r",
            nbinsx=52  # <-- FIX: one bin per week
        )

        # FIX: make weeks appear as 1,2,3,... instead of bins
        fig.update_layout(
            height=600,
            xaxis=dict(type="category")
        )

        return fig
