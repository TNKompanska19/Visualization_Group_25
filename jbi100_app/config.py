"""
Configuration constants for Hospital Operations Dashboard
JBI100 Visualization - Group 25
"""

# =============================================================================
# DEPARTMENT CONFIGURATION
# =============================================================================

SERVICES = ["emergency", "surgery", "general_medicine", "ICU"]

# Color palette for departments (consistent across all views)
# Justification: Categorical color scheme with high distinguishability
DEPT_COLORS = {
    "emergency": "#e74c3c",        # Red - urgency association
    "surgery": "#3498db",          # Blue - clinical/sterile
    "general_medicine": "#2ecc71", # Green - general health
    "ICU": "#9b59b6"               # Purple - intensive/critical
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

EVENT_COLORS = {
    "flu": "#e74c3c",
    "donation": "#2ecc71", 
    "holiday": "#9b59b6",
    "training": "#f39c12"
}

EVENT_ICONS = {
    "flu": "🤒",
    "donation": "💝",
    "holiday": "🎄", 
    "training": "📚"
}

# =============================================================================
# SEMANTIC COLORS
# =============================================================================

SEMANTIC_COLORS = {
    "good": "#27ae60",
    "warning": "#f39c12",
    "bad": "#e74c3c",
    "neutral": "#95a5a6",
    "primary": "#3498db"
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
    "detail": 8,    # ≤8 weeks: Show histograms + thresholds
    "quarter": 16   # ≤16 weeks: Show events + larger markers
    # >16 weeks: Overview mode
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
