"""
Views module for Hospital Operations Dashboard
Contains widget components for each task group.
"""

from jbi100_app.views.overview import (
    create_overview_expanded,
    create_overview_mini,
    create_overview_charts,
    get_zoom_level,
    build_tooltip_content
)

from jbi100_app.views.quantity import (
    create_quantity_expanded,
    create_quantity_mini
)


from jbi100_app.views.menu import (
    create_sidebar,
    get_sidebar_collapsed_style,
    get_sidebar_expanded_style
)

__all__ = [
    "create_overview_expanded",
    "create_overview_mini", 
    "create_overview_charts",
    "get_zoom_level",
    "build_tooltip_content",
    "create_quantity_expanded",
    "create_quantity_mini",
    "create_sidebar",
    "get_sidebar_collapsed_style",
    "get_sidebar_expanded_style"
]
