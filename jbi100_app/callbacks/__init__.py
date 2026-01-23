"""
Callbacks Module
JBI100 Visualization - Group 25

This module organizes all callbacks into logical groups.
Import and call register_all_callbacks() to register them with the app.
"""
from jbi100_app.callbacks.sidebar_callbacks import register_sidebar_callbacks
from jbi100_app.callbacks.dashboard_callbacks import register_dashboard_callbacks


def register_all_callbacks():
    """
    Register all callbacks with the Dash app.
    
    Call this function AFTER setting app.layout in app.py.
    
    Callback groups:
    - Sidebar: Toggle, quick select, time periods, zoom indicator
    - Dashboard: Linked brushing between charts
    """
    register_sidebar_callbacks()
    register_dashboard_callbacks()


__all__ = [
    "register_all_callbacks",
    "register_sidebar_callbacks",
    "register_dashboard_callbacks"
]
