from dash import html

class KPIBox(html.Div):
    def __init__(self, title, value, color="#2c8cff"):
        super().__init__(
            className="kpi_box",
            children=[
                html.Div(title, className="kpi_title"),
                html.Div(value, className="kpi_value", style={"color": color})
            ]
        )

def make_kpi_row(df_services, df_patients):
    avg_los = round(df_patients["LOS"].mean(), 2)
    total_patients = len(df_patients)
    avg_morale = round(df_services["staff_morale"].mean(), 1)
    max_pressure = df_services["pressure_index"].max()

    return html.Div(
        className="kpi_row",
        children=[
            KPIBox("Average LOS", f"{avg_los} days"),
            KPIBox("Total Patients", total_patients),
            KPIBox("Avg Staff Morale", avg_morale),
            KPIBox("Peak Pressure Index", max_pressure),
        ]
    )
