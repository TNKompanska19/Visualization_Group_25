from dash import html, dcc
import plotly.express as px
import pandas as pd

class LOSAgeBoxplot(html.Div):

    def __init__(self, df_patients):
        df = df_patients.copy()

        bins = [0, 12, 19, 64, 79, 200]
        labels = ["Child", "Teen", "Adult", "Senior", "Elderly"]
        df["age_group"] = pd.cut(df["age"], bins=bins, labels=labels)

        self.df = df.dropna(subset=["age_group"])
        self.html_id = "los-boxplot-age"

        super().__init__(
            className="graph_card",
            children=[
                html.H3("LOS per Age Group (Length of Stay in Days)"),
                dcc.Graph(id=self.html_id, figure=self._figure())
            ],
        )

    def _figure(self):
        fig = px.box(
            self.df,
            x="age_group",
            y="LOS",
            color="age_group",
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
