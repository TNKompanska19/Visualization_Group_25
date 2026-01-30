"""
Main Layout for Hospital Operations Dashboard
JBI100 Visualization - Group 25

This file defines the complete dashboard layout structure.
"""

from dash import html, dcc

from jbi100_app.data import get_services_data, build_week_data_store
from jbi100_app.views.menu import create_sidebar
from jbi100_app.views.unified import create_unified_content

def create_layout():
    """
    Create the main dashboard layout.
    
    Layout structure:
    ┌──────────┬────────────────────────────────────────────┐
    │          │         MAIN WIDGET (70% height)           │
    │ SIDEBAR  │         id="main-widget-area"              │
    │          ├─────────────────────┬──────────────────────┤
    │          │  MINI 1 (30%)       │  MINI 2 (30%)        │
    │          │  id="mini-slot-1"   │  id="mini-slot-2"    │
    └──────────┴─────────────────────┴──────────────────────┘
    
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
            dcc.Store(id="visible-week-range", data=[1, 52]),  # Tracks actual viewport after pan/zoom
            dcc.Store(id="hovered-week-store", data=None),  # For linking hover across widgets
            dcc.Store(id="primary-dept-store", data="emergency"),  # Primary dept for Quality widget
            dcc.Store(id="quality-mini-dept-store", data=None),  # For quality mini on hover (unified)
            dcc.Store(id="impact-metric-store", data="morale"),  # Toggle: morale or satisfaction
            dcc.Store(id="quantity-selected-week", data=None),  # For Quantity widget week selection
            dcc.Store(id="quantity-selected-service", data=None),  # For Quantity widget service selection
            
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
                    "overflow": "hidden",
                    "minWidth": "0"
                },
                children=[
                    # -------------------------------------------------
                    # UNIFIED SINGLE-TAB SCROLLABLE CONTENT
                    # -------------------------------------------------
                    create_unified_content()
                ]
            )
        ]
    )
