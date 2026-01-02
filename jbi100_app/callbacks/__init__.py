"""
Callbacks Module
JBI100 Visualization - Group 25

This module organizes all callbacks into logical groups.
Import and call register_all_callbacks() to register them with the app.
"""

from jbi100_app.callbacks.sidebar_callbacks import register_sidebar_callbacks
from jbi100_app.callbacks.overview_callbacks import register_overview_callbacks
from jbi100_app.callbacks.widget_callbacks import register_widget_callbacks
from jbi100_app.callbacks.quality_callbacks import register_quality_callbacks


def register_all_callbacks():
    """
    Register all callbacks with the Dash app.
    
    Call this function AFTER setting app.layout in app.py.
    
    Callback groups:
    - Sidebar: Toggle, quick select, time periods, zoom indicator
    - Overview: Hover interactions, tooltip updates
    - Widgets: Rendering and swapping
    - Quality: Network metric and layout toggles
    """
    register_sidebar_callbacks()
    register_overview_callbacks()
    register_widget_callbacks()
    register_quality_callbacks()


__all__ = [
    "register_all_callbacks",
    "register_sidebar_callbacks",
    "register_overview_callbacks",
    "register_widget_callbacks",
    "register_quality_callbacks"
]
