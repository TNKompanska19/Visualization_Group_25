from dash import html, dcc

class Heatmap:
    def __init__(self, df):
        self.df = df
        self.html_id = "heatmap-graph"

    def layout(self):
        return html.Div(
            className="graph_card",
            children=[
                html.H3("Service × Week Pressure Heatmap"),
                dcc.Graph(id=self.html_id)
            ]
        )
