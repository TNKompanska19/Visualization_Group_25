"""
Hospital Operations Dashboard
JBI100 Visualization - Group 25

Entry point for the Dash application.
Run with: python app.py

This file is intentionally minimal - all logic is organized in jbi100_app/
"""

# Import app instance
from jbi100_app.main import app

# Import layout
from jbi100_app.layout import create_layout

# Import callback registration
from jbi100_app.callbacks import register_all_callbacks


# =============================================================================
# SETUP
# =============================================================================

# Set the layout
app.layout = create_layout()

# Register all callbacks
register_all_callbacks()

# Clientside callback: sync highlight rectangle with Overview panning
from dash import ClientsideFunction, Output, Input, State

app.clientside_callback(
    ClientsideFunction(namespace='clientside', function_name='updateHighlightRect'),
    Output("quality-mini-sparkline", "figure", allow_duplicate=True),
    Input("overview-chart", "relayoutData"),
    State("quality-mini-sparkline", "figure"),
    State("week-slider", "value"),
    prevent_initial_call=True
)


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    app.run(debug=True, port=8050)
