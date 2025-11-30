from dash import html, dcc
import plotly.express as px
import pandas as pd


class LOSBoxplot(html.Div):

    def __init__(self, df, mode="service"):
        """
        mode = "service" → LOS grouped by service
        mode = "age" → LOS grouped by age groups
        """
        self.df = df
        self.mode = mode
        self.html_id = f"los-boxplot-{mode}"

        super().__init__(
            className="graph_card",
            children=[
                html.H3(self._title()),
                dcc.Graph(id=self.html_id, figure=self._figure())
            ],
        )

    # ------------------------------------------------------------------
    def _title(self):
        if self.mode == "service":
            return "Distribution of LOS per Service"
        elif self.mode == "age":
            return "Distribution of LOS per Age Group"
        return "LOS Boxplot"

    # ------------------------------------------------------------------
    def _compute_age_group(self):
        bins = [0, 12, 19, 64, 79, 200]
        labels = ["Child (0-12)", "Teen (13-19)", "Adult (20-64)", "Senior (65-79)", "Elderly (80+)"]

        df = self.df.copy()
        df["age_group"] = pd.cut(df["age"], bins=bins, labels=labels, right=True)
        return df

    # ------------------------------------------------------------------
    def _figure(self):
        if self.mode == "service":
            fig = px.box(
                self.df,
                x="service",
                y="LOS",
                title="LOS per Service",
                color="service",
                points="all"
            )

        elif self.mode == "age":
            df_age = self._compute_age_group()
            fig = px.box(
                df_age,
                x="age_group",
                y="LOS",
                title="LOS per Age Group",
                color="age_group",
                points="all"
            )
        else:
            raise ValueError("Invalid LOSBoxplot mode")

        fig.update_layout(height=450, margin=dict(t=60))
        return fig
