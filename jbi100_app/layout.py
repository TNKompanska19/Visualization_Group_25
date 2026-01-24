"""
Main Layout for Hospital Operations Dashboard
JBI100 Visualization - Group 25

This file defines the complete dashboard layout structure.
"""

from dash import html, dcc

from jbi100_app.data import get_services_data, build_week_data_store
from jbi100_app.views.menu import create_sidebar
from jbi100_app.views.dashboard import create_dashboard_view

def create_layout():
    """
    Create the main dashboard layout.
    
    Layout structure:
    ┌──────────┬────────────────────────────────────────────┐
    │          │         SINGLE VIEW (linked charts)        │
    │ SIDEBAR  │         time + multivariate                │
    │          │         brushing                            │
    └──────────┴────────────────────────────────────────────┘
    
    Returns:
        dash.html.Div: Complete layout component
    """
    # Pre-load data for client-side store
    services_df = get_services_data()
    week_data_store = build_week_data_store(services_df)
    
    return html.Div(
        style={
            "display": "flex",
            "height": "100vh",
            "backgroundColor": "#f5f6fa",
            "fontFamily": "Segoe UI, Arial, sans-serif",
            "overflow": "hidden"
        },
        children=[
            # =========================================================
            # CLIENT-SIDE DATA STORES
            # These hold state that persists across callbacks
            # =========================================================
            dcc.Store(id="week-data-store", data=week_data_store),
            dcc.Store(id="current-week-range", data=[1, 52]),
            dcc.Store(id="visible-week-range", data=[1, 52]),  # Tracks viewport after pan/zoom
            dcc.Store(id="primary-dept-store", data="emergency"),
            dcc.Store(id="brush-selection-store", data=None),
            
            # =========================================================
            # SIDEBAR (from views/menu.py)
            # =========================================================
            create_sidebar(),
            
            # =========================================================
            # MAIN CONTENT AREA
            # =========================================================
            html.Div(
                style={
                    "flex": "1",
                    "display": "flex",
                    "flexDirection": "column",
                    "padding": "8px",
                    "gap": "8px",
                    # Allow the dashboard to scroll vertically (prevents bottom chart clipping)
                    "overflow": "auto",
                    "minWidth": "0"
                },
                children=[
                    create_dashboard_view()
                ]
            )
        ]
    )
