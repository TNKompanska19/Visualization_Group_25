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

# Colorblind-safe event colors (distinct from dept colors)
EVENT_COLORS = {
    "flu": "#D55E00",      # Vermillion - alert
    "donation": "#009E73", # Teal - positive
    "holiday": "#CC79A7",  # Rose - special occasion
    "training": "#F0E442"  # Yellow - learning
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
