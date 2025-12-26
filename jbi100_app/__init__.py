"""
JBI100 Visualization - Hospital Operations Dashboard
Group 25

Package structure:
    jbi100_app/
    ├── main.py         - Dash app instance
    ├── config.py       - Configuration constants
    ├── data.py         - Data loading and preprocessing
    ├── layout.py       - Main layout definition
    ├── callbacks/      - All callback functions
    │   ├── sidebar_callbacks.py
    │   ├── overview_callbacks.py
    │   └── widget_callbacks.py
    └── views/          - Widget components
        ├── menu.py
        ├── overview.py
        ├── quantity.py
        └── quality.py
"""

from jbi100_app.main import app

__all__ = ["app"]
