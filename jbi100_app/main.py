"""
Dash application instance for Hospital Operations Dashboard
JBI100 Visualization - Group 25
"""

from dash import Dash

# Create app instance
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Hospital Operations Dashboard"

# Server reference for deployment
server = app.server
