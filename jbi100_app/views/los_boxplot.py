from dash import html, dcc
import plotly.express as px

class LOSBoxplot(html.Div):

    def __init__(self, df):
        df = df.copy()
        df["service_display"] = df["service"].str.replace("_", " ").str.title()

        self.df = df
        self.html_id = "los-boxplot-service"

        super().__init__(
            className="graph_card",
            children=[
                html.H3("LOS per Service (Length of Stay in Days)"),
                dcc.Graph(id=self.html_id, figure=self._figure())
            ],
        )

    def _figure(self):
        fig = px.box(
            self.df,
            x="service_display",
            y="LOS",
            color="service_display",
            points="all",
        )

        fig.update_traces(
            hovertemplate="LOS: %{y}<extra></extra>",
            boxmean=True
        )

        fig.update_layout(
            height=450,
            margin=dict(l=120, r=40, t=40, b=40),
            yaxis=dict(automargin=True)
        )

        return fig
