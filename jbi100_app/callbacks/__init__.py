"""
Callbacks Module
JBI100 Visualization - Group 25

This module organizes all callbacks into logical groups.
Import and call register_all_callbacks() to register them with the app.
"""
from jbi100_app.callbacks.sidebar_callbacks import register_sidebar_callbacks
from jbi100_app.callbacks.overview_callbacks import register_overview_callbacks
from jbi100_app.callbacks.widget_callbacks import register_widget_callbacks
from jbi100_app.callbacks.quantity_callbacks import register_quantity_callbacks  # NEW


def register_all_callbacks():
    register_sidebar_callbacks()
    register_overview_callbacks()
    register_widget_callbacks()
    register_quantity_callbacks()  # NEW



__all__ = [
    "register_all_callbacks",
    "register_sidebar_callbacks",
    "register_overview_callbacks",
    "register_widget_callbacks",
    "register_quantity_callbacks"
]
