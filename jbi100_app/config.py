"""
Configuration constants for Hospital Dashboard
"""

# Service departments
SERVICES = ['emergency', 'surgery', 'general_medicine', 'ICU']

# Color palette for services (consistent across all views)
COLORS = {
    'emergency': '#e74c3c',        # Red
    'surgery': '#3498db',          # Blue
    'general_medicine': '#27ae60', # Green
    'ICU': '#9b59b6'               # Purple
}

# Semantic colors
SEMANTIC = {
    'good': '#27ae60',
    'warning': '#f39c12',
    'bad': '#e74c3c',
    'neutral': '#95a5a6',
    'primary': '#2c8cff'
}

# Event markers
EVENTS = {
    'flu': {'color': '#e74c3c', 'label': 'Flu Outbreak'},
    'strike': {'color': '#f39c12', 'label': 'Staff Strike'},
    'donation': {'color': '#27ae60', 'label': 'Equipment Donation'},
    'none': {'color': None, 'label': None}
}
