from dash import html, dcc
import plotly.express as px
import pandas as pd

class LOSAgeBoxplot(html.Div):

    def __init__(self, df_patients):
        self.df = self._compute_age_group(df_patients)

        self.html_id = "los-boxplot-age"

        super().__init__(
            className="graph_card",
            children=[
                html.H3("Distribution of LOS per Age Group"),
                dcc.Graph(id=self.html_id, figure=self._figure())
            ],
        )

    # ----------------------------------------------
    def _compute_age_group(self, df):
        bins = [0, 12, 19, 64, 79, 200]
        labels = ["Child (0-12)", "Teen (13-19)", "Adult (20-64)", "Senior (65-79)", "Elderly (80+)"]

        df = df.copy()
        df["age_group"] = pd.cut(df["age"], bins=bins, labels=labels, right=True)

        return df.dropna(subset=["age_group"])

    # ----------------------------------------------
    def _figure(self):
        fig = px.box(
            self.df,
            x="age_group",
            y="LOS",
            color="age_group",
            title="LOS per Age Group",
            points="all"
        )

        fig.update_layout(height=450, margin=dict(t=60))
        return fig
