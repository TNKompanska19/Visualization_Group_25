"""
Dash application instance for Hospital Operations Dashboard
JBI100 Visualization - Group 25
"""

from dash import Dash

# External stylesheets (Font Awesome for event icons)
external_stylesheets = [
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
]

# Create app instance
app = Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=external_stylesheets)
app.title = "Hospital Operations Dashboard"

# Server reference for deployment
server = app.server
