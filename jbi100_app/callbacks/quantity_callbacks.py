"""
Quantity Callbacks - T2 & T3 
JBI100 Visualization - Group 25

BEHAVIOR:
- Stacked bar chart shows beds vs demand by department with correct colors
- Violin plot shows length of stay distribution with hover line
- Both respond to hovered-week-store for linking
"""

from dash import callback, Output, Input, State, ctx, html, no_update
from dash.exceptions import PreventUpdate
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from jbi100_app.config import DEPT_COLORS, DEPT_LABELS, DEPT_LABELS_SHORT, SERVICES
from jbi100_app.data import get_services_data, get_patients_data

_services = get_services_data()
_patients = get_patients_data()

LEGEND_ORDER = ["emergency", "surgery", "general_medicine", "ICU"]
AXIS_LABEL_FONT = dict(size=11, color="#2c3e50")
AXIS_TICK_FONT = dict(size=10, color="#34495e")
GRID_COLOR = "#ecf0f1"
TITLE_FONT_SIZE = 13
SUBTITLE_FONT_SIZE = 9


def _filter_services(depts, week_range, hide_anomalies=False):
    week_range = week_range or [1, 52]
    w0, w1 = int(week_range[0]), int(week_range[1])
    df = _services[(_services["week"] >= w0) & (_services["week"] <= w1)].copy()
    if depts:
        df = df[df["service"].isin(depts)].copy()
    if hide_anomalies:
        df = df[~df["week"].isin(list(range(3, 53, 3)))].copy()
    return df


def _filter_patients(depts, week_range, hide_anomalies=False):
    week_range = week_range or [1, 52]
    w0, w1 = int(week_range[0]), int(week_range[1])
    df = _patients.copy()
    if depts:
        df = df[df["service"].isin(depts)].copy()
    if "arrival_week" in df.columns:
        df = df[(df["arrival_week"] >= w0) & (df["arrival_week"] <= w1)].copy()
        if hide_anomalies:
            df = df[~df["arrival_week"].isin(list(range(3, 53, 3)))].copy()
    return df


def _empty_fig(title="No data"):
    fig = go.Figure()
    fig.add_annotation(text=title, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=10, color="#999"))
    fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=20, b=10), xaxis=dict(visible=False),
                      yaxis=dict(visible=False))
    return fig


def _get_ordered_services(depts):
    return [s for s in LEGEND_ORDER if s in depts]


def _lighten_hex(hex_color, factor=0.4):
    """Lighten a hex color by mixing with white. factor=0 is no change, 1 is white."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken_hex(hex_color, factor=0.35):
    """Darken a hex color by reducing luminance. factor=0 is no change, 1 is black."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def register_quantity_callbacks():
    """Register quantity callbacks for T2 and T3."""
    
    # =========================================================================
    # STACKED BAR: Beds vs Demand by DEPARTMENT (proper colors)
    # =========================================================================
    @callback(
        Output("stacked-beds-demand-chart", "figure"),
        [Input("dept-filter", "value"),
         Input("current-week-range", "data"),
         Input("hide-anomalies-toggle", "value"),
         Input("hovered-week-store", "data")],
        prevent_initial_call=False,
    )
    def update_stacked_beds_demand(depts, week_range, hide_anom, hovered_store):
        """
        Stacked bar per department: each department has one bar per week (beds stacked under demand).
        customdata = actual week number so hover callback uses point['customdata'], not x.
        Highlight = vrect in figure (x0=week-0.5, x1=week+0.5) so it stays aligned.
        """
        week_range = week_range or [1, 52]
        w_min, w_max = int(week_range[0]), int(week_range[1])
        depts = depts or ["emergency"]
        hide = "hide" in (hide_anom or [])

        df = _filter_services(depts, week_range, hide)
        if df.empty:
            return _empty_fig("Select departments")

        weeks = sorted(df["week"].unique())
        if not weeks:
            return _empty_fig("No data")

        ordered_depts = _get_ordered_services(depts)
        n_depts = len(ordered_depts)
        # Offset per department so stacked bars sit side by side; use 0.38 so each bar is visibly wide
        bar_gap = 0.38
        offsets = [(i - (n_depts - 1) / 2) * bar_gap for i in range(n_depts)]

        fig = go.Figure()

        # customdata = actual week (int) so hover uses point['customdata'], not x (avoids round/offset mismatch)
        week_list = [int(w) for w in weeks]
        for di, dept in enumerate(ordered_depts):
            off = offsets[di]
            x_vals = [w + off for w in weeks]  # numeric x for linear axis
            dept_df = df[df["service"] == dept]
            by_week = dept_df.set_index("week").reindex(weeks).fillna(0)
            light = _lighten_hex(DEPT_COLORS.get(dept, "#999"), 0.45)
            dark = _darken_hex(DEPT_COLORS.get(dept, "#999"), 0.25)
            lbl = DEPT_LABELS_SHORT.get(dept, dept)
            fig.add_trace(go.Bar(
                x=x_vals,
                y=by_week["available_beds"].values,
                name=f"{lbl} Beds",
                marker_color=light,
                legendgroup=dept,
                customdata=week_list,
                hovertemplate=f"<b>{lbl}</b> Beds<br>Week %{{customdata}}<br>%{{y:.0f}}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                x=x_vals,
                y=by_week["patients_request"].values,
                name=f"{lbl} Demand",
                marker_color=dark,
                legendgroup=dept,
                customdata=week_list,
                hovertemplate=f"<b>{lbl}</b> Demand<br>Week %{{customdata}}<br>%{{y:.0f}}<extra></extra>",
            ))

        # Y range: max total height per bar (beds + demand) per department per week
        y_max = 0
        for dept in ordered_depts:
            dept_df = df[df["service"] == dept]
            by_week = dept_df.set_index("week").reindex(weeks).fillna(0)
            total = by_week["available_beds"] + by_week["patients_request"]
            y_max = max(y_max, total.max() if len(total) else 0)
        y_upper = max(y_max * 1.15, 10)

        fig.update_layout(
            barmode="stack",
            bargap=0.08,
            bargroupgap=0.02,
            height=380,
            template="plotly_white",
            margin=dict(l=60, r=30, t=88, b=50),
            dragmode="zoom",
            uirevision="stacked-beds-demand",
            title=dict(
                text="<b>Beds vs Demand by Week</b><br><span style='font-size:10px;color:#7f8c8d'>Hover or zoom; zoom syncs line chart & PCP</span>",
                font=dict(size=15, color="#2c3e50"),
                x=0.5, xanchor="center", y=0.98,
                automargin=True,
                yref="paper",
            ),
            xaxis=dict(
                type="linear",
                title="Week",
                range=[w_min - 0.6, w_max + 0.6],
                autorange=False,
                gridcolor=GRID_COLOR,
                tickfont=AXIS_TICK_FONT,
                title_font=AXIS_LABEL_FONT,
                fixedrange=False,
                tickvals=list(range(max(0, (w_min // 4) * 4), min(53, w_max + 5), 4)),
            ),
            yaxis=dict(
                title="Count",
                range=[0, y_upper],
                autorange=False,
                gridcolor=GRID_COLOR,
                tickfont=AXIS_TICK_FONT,
                title_font=AXIS_LABEL_FONT,
                fixedrange=False,
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.16,
                xanchor="center",
                x=0.5,
                font=dict(size=9),
            ),
        )

        # Highlight = vrect in data coords (x0=week-0.5, x1=week+0.5) so it stays aligned with bars
        hovered_week = None
        if hovered_store and isinstance(hovered_store, dict):
            hovered_week = hovered_store.get("week")
        if hovered_week is not None and 1 <= hovered_week <= 52:
            fig.add_shape(
                type="rect",
                x0=hovered_week - 0.5,
                x1=hovered_week + 0.5,
                y0=0,
                y1=1,
                yref="paper",
                fillcolor="rgba(52, 152, 219, 0.25)",
                line=dict(width=0),
                layer="below",
            )

        return fig

    # =========================================================================
    # STACKED BAR HIGHLIGHT: overlay hidden; highlight is vrect in figure above
    # Position overlay from stored week so it always matches the week the user hovered.
    # =========================================================================
    @callback(
        Output("stacked-bar-highlight", "style"),
        [Input("hovered-week-store", "data"),
         Input("current-week-range", "data")],
        prevent_initial_call=False,
    )
    def update_stacked_bar_highlight(hovered_store, week_range):
        """Overlay hidden; highlight is vrect in figure (data coords) for exact alignment."""
        return {
            "position": "absolute",
            "top": "72px",
            "bottom": "72px",
            "backgroundColor": "rgba(52, 152, 219, 0.2)",
            "pointerEvents": "none",
            "borderRadius": "4px",
            "display": "none",
            "left": "0%",
            "width": "2%",
        }
    
    # =========================================================================
    # LOS VIOLIN: Length of Stay by Department
    # =========================================================================
    @callback(
        Output("t3-los-chart", "figure"),
        [Input("dept-filter", "value"),
         Input("current-week-range", "data"),
         Input("hide-anomalies-toggle", "value"),
         Input("hovered-week-store", "data")],
        prevent_initial_call=False,
    )
    def update_los_chart(depts, week_range, hide_anom, hovered_store):
        """
        LOS violin plot showing distribution per department.
        When hovering a week, adds horizontal line at that week's median LOS.
        
        Munzner Justification:
        - Violin: Shows full distribution shape (better than box plot for skewed data)
        - Position channel: Department comparison
        - Color hue: Consistent department colors
        """
        week_range = week_range or [1, 52]
        depts = depts or ["emergency"]
        hide = "hide" in (hide_anom or [])
        
        df_full = _filter_patients(depts, week_range, hide)
        
        if df_full.empty or "length_of_stay" not in df_full.columns:
            return _empty_fig("No patient data")
        
        fig = go.Figure()
        services = _get_ordered_services(df_full["service"].unique())
        labels = [DEPT_LABELS_SHORT.get(svc, svc) for svc in services]

        # One violin per department, side by side (explicit x = category label)
        for svc in services:
            svc_df = df_full[df_full["service"] == svc]
            col = DEPT_COLORS.get(svc, "#999")
            lbl = DEPT_LABELS_SHORT.get(svc, svc)
            fig.add_trace(go.Violin(
                x=[lbl] * len(svc_df),
                y=svc_df["length_of_stay"],
                name=lbl,
                box_visible=True,
                meanline_visible=True,
                fillcolor=col,
                line_color=col,
                opacity=0.6,
                points=False,
                hoverinfo="y+name",
            ))

        highlight_txt = ""
        hovered_week = hovered_store.get("week") if isinstance(hovered_store, dict) else None

        # Hovered week: inside EACH violin draw vertical I-beam (min–max) + diamond at median
        if hovered_week and "arrival_week" in df_full.columns:
            highlight_patients = df_full[df_full["arrival_week"] == hovered_week].copy()
            highlight_txt = f" • Week {hovered_week}"

            if not highlight_patients.empty:
                for svc in services:
                    svc_hl = highlight_patients[highlight_patients["service"] == svc]
                    if len(svc_hl) < 1:
                        continue
                    lbl = DEPT_LABELS_SHORT.get(svc, svc)
                    col = DEPT_COLORS.get(svc, "#999")
                    los = svc_hl["length_of_stay"]
                    lo, hi = los.min(), los.max()
                    med = los.median()
                    # Vertical line (I-beam: min to max)
                    fig.add_trace(go.Scatter(
                        x=[lbl, lbl],
                        y=[lo, hi],
                        mode="lines",
                        line=dict(color=col, width=2.5),
                        showlegend=False,
                        hoverinfo="skip",
                    ))
                    # Diamond at median (white fill, dept color border)
                    fig.add_trace(go.Scatter(
                        x=[lbl],
                        y=[med],
                        mode="markers",
                        marker=dict(
                            symbol="diamond",
                            size=14,
                            color="white",
                            line=dict(width=2, color=col),
                        ),
                        showlegend=False,
                        hovertemplate=f"W{hovered_week} {lbl}<br>Median: %{{y:.0f}}d<extra></extra>",
                    ))
        
        # Reference lines
        fig.add_hline(
            y=7, line_dash="dot", line_color="#009E73", line_width=1, opacity=0.5,
            annotation_text="7d target", annotation_position="right",
            annotation_font=dict(size=8, color="#009E73"),
        )
        fig.add_hline(
            y=14, line_dash="dash", line_color="#D55E00", line_width=1.5, opacity=0.6,
            annotation_text="14d blocker", annotation_position="right",
            annotation_font=dict(size=8, color="#D55E00"),
        )
        
        avg_los = df_full["length_of_stay"].mean()
        blockers = (df_full["length_of_stay"] > 14).sum()
        
        fig.update_layout(
            height=380,
            title=dict(
                text=f"<b>Length of Stay</b><br><span style='font-size:{SUBTITLE_FONT_SIZE}px;color:#7f8c8d'>Avg: {avg_los:.1f}d • Blockers: {blockers}{highlight_txt}</span>",
                font=dict(size=TITLE_FONT_SIZE, color="#2c3e50"),
                x=0.5, xanchor="center", y=0.95,
            ),
            template="plotly_white",
            margin=dict(l=60, r=90, t=60, b=50),
            yaxis=dict(
                title=dict(text="Length of Stay (days)", font=AXIS_LABEL_FONT),
                gridcolor=GRID_COLOR,
                range=[0, min(df_full["length_of_stay"].max() + 3, 35)],
                tickfont=AXIS_TICK_FONT,
            ),
            xaxis=dict(
                title="",
                tickfont=AXIS_TICK_FONT,
                type="category",
                categoryorder="array",
                categoryarray=labels,
            ),
            showlegend=False,
            hovermode="closest",
        )

        return fig
    
    # =========================================================================
    # STACKED BAR ZOOM → SYNC WEEK RANGE (line chart, PCP, violin follow)
    # =========================================================================
    @callback(
        Output("current-week-range", "data", allow_duplicate=True),
        Input("stacked-beds-demand-chart", "relayoutData"),
        prevent_initial_call=True,
    )
    def sync_week_range_from_stacked_bar_zoom(relayout_data):
        """When user zooms on stacked bar, sync week range so line chart, PCP, violin update."""
        if not relayout_data:
            return no_update
        if "xaxis.range[0]" in relayout_data and "xaxis.range[1]" in relayout_data:
            x0 = relayout_data["xaxis.range[0]"]
            x1 = relayout_data["xaxis.range[1]"]
            w_min = max(1, int(round(float(x0))))
            w_max = min(52, int(round(float(x1))))
            if w_min < w_max:
                return [w_min, w_max]
        if relayout_data.get("xaxis.autorange"):
            return [1, 52]
        return no_update

    # =========================================================================
    # HOVER ON STACKED BAR → UPDATE HOVERED WEEK STORE
    # =========================================================================
    @callback(
        Output("hovered-week-store", "data", allow_duplicate=True),
        Input("stacked-beds-demand-chart", "hoverData"),
        State("current-week-range", "data"),
        prevent_initial_call=True,
    )
    def update_hovered_week_from_bars(hoverData, week_range):
        """Update hovered-week-store from bar hover. Use point['customdata'] (actual week), not x — avoids round/offset mismatch."""
        if not hoverData or not hoverData.get("points"):
            return None

        point = hoverData["points"][0]
        raw = point.get("customdata")
        if raw is None:
            return None
        # customdata is the actual week (int) we set on the trace
        try:
            week = int(raw) if isinstance(raw, (int, float)) else int(raw[0])
        except (TypeError, ValueError, IndexError):
            return None

        if week < 1 or week > 52:
            return None

        return {"week": week, "department": None}
