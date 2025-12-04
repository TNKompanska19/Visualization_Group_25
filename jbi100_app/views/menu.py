from dash import dcc, html
from ..config import color_list1, color_list2


def generate_description_card():
    return html.Div(
        id="description-card",
        children=[
            html.H5("Example dashboard"),
            html.Div(
                id="intro",
                children="You can use this as a basic template for your JBI100 visualization project.",
            ),
            html.Div(
                "LOS = Length of Stay (number of days a patient remains in the hospital).",
                style={"fontSize": "13px", "color": "#666", "marginTop": "10px"},
            ),
        ],
    )


def generate_control_card():
    return html.Div(
        id="control-card",
        children=[
            html.Label("Color scatterplot 1"),
            dcc.Dropdown(
                id="select-color-scatter-1",
                options=[{"label": i, "value": i} for i in color_list1],
                value=color_list1[0],
            ),
            html.Br(),
            html.Label("Color scatterplot 2"),
            dcc.Dropdown(
                id="select-color-scatter-2",
                options=[{"label": i, "value": i} for i in color_list2],
                value=color_list2[0],
            ),
        ],
        style={"textAlign": "float-left"},
    )


def make_menu_layout():
    return [generate_description_card(), generate_control_card()]
