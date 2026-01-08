"""
Configuration constants for Hospital Operations Dashboard
JBI100 Visualization - Group 25
"""

# =============================================================================
# DEPARTMENT CONFIGURATION
# =============================================================================

SERVICES = ["emergency", "surgery", "general_medicine", "ICU"]

# Color palette for departments (consistent across all views)
# Justification: Colorblind-safe categorical palette (Okabe-Ito + Wong)
# Avoids red-green confusion (Munzner Ch. 10, theory line 287)
DEPT_COLORS = {
    "emergency": "#E69F00",        # Orange - urgency, high visibility
    "surgery": "#0072B2",          # Blue - clinical/sterile
    "general_medicine": "#009E73", # Teal - health/wellness
    "ICU": "#CC79A7"               # Rose - intensive/critical
}

DEPT_LABELS = {
    "emergency": "Emergency",
    "surgery": "Surgery", 
    "general_medicine": "General Medicine",
    "ICU": "ICU"
}

# Short labels for compact displays
DEPT_LABELS_SHORT = {
    "emergency": "Emerg.",
    "surgery": "Surgery",
    "general_medicine": "Gen.Med",
    "ICU": "ICU"
}

# =============================================================================
# EVENT CONFIGURATION
# =============================================================================

# Colorblind-safe event colors (kept for reference/legend)
EVENT_COLORS = {
    "flu": "#D55E00",      # Vermillion - illness/alert
    "donation": "#009E73", # Teal - positive event
    "strike": "#CC79A7"    # Rose - disruption
}

# Font Awesome 6 SVG icon paths (without color - color applied dynamically per department)
# Source: https://fontawesome.com (CC BY 4.0 License)
EVENT_ICON_PATHS = {
    # fa-virus-covid (viewBox 0 0 512 512)
    "flu": {
        "viewBox": "0 0 512 512",
        "path": "M192 24c0-13.3 10.7-24 24-24h80c13.3 0 24 10.7 24 24s-10.7 24-24 24H280V81.6c30.7 4.2 58.8 16.3 82.3 34.1L386.1 92 374.8 80.6c-9.4-9.4-9.4-24.6 0-33.9s24.6-9.4 33.9 0l56.6 56.6c9.4 9.4 9.4 24.6 0 33.9s-24.6 9.4-33.9 0L420 125.9l-23.8 23.8c17.9 23.5 29.9 51.7 34.1 82.3H464V216c0-13.3 10.7-24 24-24s24 10.7 24 24v80c0 13.3-10.7 24-24 24s-24-10.7-24-24V280H430.4c-4.2 30.7-16.3 58.8-34.1 82.3L420 386.1l11.3-11.3c9.4-9.4 24.6-9.4 33.9 0s9.4 24.6 0 33.9l-56.6 56.6c-9.4 9.4-24.6 9.4-33.9 0s-9.4-24.6 0-33.9L386.1 420l-23.8-23.8c-23.5 17.9-51.7 29.9-82.3 34.1V464h16c13.3 0 24 10.7 24 24s-10.7 24-24 24H216c-13.3 0-24-10.7-24-24s10.7-24 24-24h16V430.4c-30.7-4.2-58.8-16.3-82.3-34.1L125.9 420l11.3 11.3c9.4 9.4 9.4 24.6 0 33.9s-24.6 9.4-33.9 0L46.7 408.7c-9.4-9.4-9.4-24.6 0-33.9s24.6-9.4 33.9 0L92 386.1l23.8-23.8C97.9 338.8 85.8 310.7 81.6 280H48v16c0 13.3-10.7 24-24 24s-24-10.7-24-24V216c0-13.3 10.7-24 24-24s24 10.7 24 24v16H81.6c4.2-30.7 16.3-58.8 34.1-82.3L92 125.9 80.6 137.2c-9.4 9.4-24.6 9.4-33.9 0s-9.4-24.6 0-33.9l56.6-56.6c9.4-9.4 24.6-9.4 33.9 0s9.4 24.6 0 33.9L125.9 92l23.8 23.8c23.5-17.9 51.7-29.9 82.3-34.1V48h-16c-13.3 0-24-10.7-24-24z"
    },
    # fa-hand-holding-droplet (viewBox 0 0 576 512)
    "donation": {
        "viewBox": "0 0 576 512",
        "path": "M275.5 6.6C278.3 2.5 283 0 288 0s9.7 2.5 12.5 6.6L366.8 103C378 119.3 384 138.6 384 158.3V160c0 53-43 96-96 96s-96-43-96-96v-1.7c0-19.8 6-39 17.2-55.3L275.5 6.6zM568.2 336.3c13.1 17.8 9.3 42.8-8.5 55.9L433.1 485.5c-23.4 17.2-51.6 26.5-80.7 26.5H192 32c-17.7 0-32-14.3-32-32V416c0-17.7 14.3-32 32-32H68.8l44.9-36c22.7-18.2 50.9-28 80-28H272h16 64c17.7 0 32 14.3 32 32s-14.3 32-32 32H288 272c-8.8 0-16 7.2-16 16s7.2 16 16 16H392.6l119.7-88.2c17.8-13.1 42.8-9.3 55.9 8.5zM193.6 384l0 0-.9 0c.3 0 .6 0 .9 0z"
    },
    # fa-triangle-exclamation (viewBox 0 0 512 512)
    "strike": {
        "viewBox": "0 0 512 512",
        "path": "M256 32c14.2 0 27.3 7.5 34.5 19.8l216 368c7.3 12.4 7.3 27.7 .2 40.1S486.3 480 472 480H40c-14.3 0-27.6-7.7-34.7-20.1s-7-27.8 .2-40.1l216-368C228.7 39.5 241.8 32 256 32zm0 128c-13.3 0-24 10.7-24 24V296c0 13.3 10.7 24 24 24s24-10.7 24-24V184c0-13.3-10.7-24-24-24zm32 224c0-17.7-14.3-32-32-32s-32 14.3-32 32s14.3 32 32 32s32-14.3 32-32z"
    }
}


def get_event_icon_svg(event_type, color):
    """Generate SVG data URI for event icon with specified color.
    
    Args:
        event_type: One of 'flu', 'donation', 'strike'
        color: Hex color string (e.g., '#E69F00')
    
    Returns:
        Data URI string for use in Plotly layout images
    """
    if event_type not in EVENT_ICON_PATHS:
        return None
    
    icon = EVENT_ICON_PATHS[event_type]
    # URL-encode the color (# -> %23)
    encoded_color = color.replace("#", "%23")
    
    svg = f"%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='{icon['viewBox']}'%3E%3Cpath fill='{encoded_color}' d='{icon['path']}'/%3E%3C/svg%3E"
    return f"data:image/svg+xml,{svg}"

# =============================================================================
# SEMANTIC COLORS
# =============================================================================

# Colorblind-safe semantic colors
# Using luminance + shape redundancy (not just hue)
SEMANTIC_COLORS = {
    "good": "#009E73",     # Teal (not pure green)
    "warning": "#F0E442",  # Yellow
    "bad": "#D55E00",      # Vermillion (not pure red)
    "neutral": "#999999",  # Gray
    "primary": "#0072B2",  # Blue
    # Threshold-specific (luminance-based hierarchy)
    "threshold_mean": "#56B4E9",    # Sky blue - central tendency
    "threshold_upper": "#000000",   # Black - limit (dark = constraint)
    "threshold_lower": "#000000"    # Black - limit (redundant with dash)
}

# =============================================================================
# WIDGET CONFIGURATION
# =============================================================================

WIDGET_INFO = {
    "overview": {
        "icon": "📊",
        "title": "Hospital Performance Overview",
        "subtitle": "T1: Browse trends and identify outliers"
    },
    "quantity": {
        "icon": "📦",
        "title": "Capacity & Patient Flow",
        "subtitle": "T2: Bed allocation | T3: Stay duration"
    },
    "quality": {
        "icon": "⭐",
        "title": "Quality & Satisfaction",
        "subtitle": "T4: Correlations | T5: Staff impact | T6: Extremes"
    }
}

# =============================================================================
# ZOOM LEVEL THRESHOLDS (Semantic Zoom - Munzner)
# =============================================================================

ZOOM_THRESHOLDS = {
    "detail": 8,    # ≤8 weeks: Individual data points visible
    "quarter": 13   # ≤13 weeks: True quarter (52/4), shows distributions
    # >13 weeks: Overview mode
}

# =============================================================================
# CHART DEFAULTS
# =============================================================================

CHART_CONFIG = {
    "displayModeBar": False
}

CHART_MARGINS = {
    "overview": dict(l=60, r=20, t=40, b=60),
    "default": dict(l=50, r=20, t=30, b=40)
}
