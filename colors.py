# colors.py

THEMES = {
    "Nordic": {
        "ACCENT": "#88c0d0",      # Frost Blue
        "ACCENT_HOVER": "#81a1c1",
        "SUCCESS": "#a3be8c",     # Sage Green
        "DANGER": "#bf616a",      # Muted Red
        "DANGER_HOVER": "#331111" ,
        "BG_MAIN": "#2e3440",     # Dark Polar Night
        "BG_PANEL": "#3b4252",
        "BG_INPUT": "#434c5e",
        "BG_FOCUS": "#4c566a",    # Focused Grey-Blue
        "TXT_MAIN": "#eceff4",
        "TXT_DIM": "#d8dee9"
    },
    "Deep Blue": {
        "ACCENT": "#3d91ff",      # Classic Blue
        "ACCENT_HOVER": "#0065f3",
        "SUCCESS": "#2ecc71",
        "DANGER": "#e74c3c",
        "DANGER_HOVER" : "#331111" ,
        "BG_MAIN": "#0a0f14",     # Midnight
        "BG_PANEL": "#10161d",
        "BG_INPUT": "#1c252f",
        "BG_FOCUS": "#1a3a5f",
        "TXT_MAIN": "#ffffff",
        "TXT_DIM": "#888888"
    },
    "Legion Red": {
        "ACCENT": "#e63946",      # Vivid Red
        "ACCENT_HOVER": "#ff4d5a",
        "SUCCESS": "#2a9d8f",
        "DANGER": "#6b1619",
        "DANGER_HOVER" : "#331111" ,
        "BG_MAIN": "#111111",     # Pure Black
        "BG_PANEL": "#1a1a1a",
        "BG_INPUT": "#252525",
        "BG_FOCUS": "#4a0e0e",    # Dark Blood Focus
        "TXT_MAIN": "#ffffff",
        "TXT_DIM": "#999999"
    }
}

# Default global variables (will be overwritten by the app at runtime)
ACCENT = THEMES["Deep Blue"]["ACCENT"]
ACCENT_HOVER = THEMES["Deep Blue"]["ACCENT_HOVER"]
SUCCESS = THEMES["Deep Blue"]["SUCCESS"]
DANGER = THEMES["Deep Blue"]["DANGER"]
DANGER_HOVER = THEMES["Deep Blue"]["DANGER_HOVER"]
BG_MAIN = THEMES["Deep Blue"]["BG_MAIN"]
BG_PANEL = THEMES["Deep Blue"]["BG_PANEL"]
BG_INPUT = THEMES["Deep Blue"]["BG_INPUT"]
BG_FOCUS = THEMES["Deep Blue"]["BG_FOCUS"]
TXT_MAIN = THEMES["Deep Blue"]["TXT_MAIN"]
TXT_DIM = THEMES["Deep Blue"]["TXT_DIM"]

def apply_theme(theme_name):
    """Updates the global constants to match the chosen theme."""
    global ACCENT, ACCENT_HOVER, SUCCESS, DANGER,DANGER_HOVER, BG_MAIN, BG_PANEL, BG_INPUT, BG_FOCUS, TXT_MAIN, TXT_DIM
    t = THEMES.get(theme_name, THEMES["Deep Blue"])
    ACCENT = t["ACCENT"]
    ACCENT_HOVER = t["ACCENT_HOVER"]
    SUCCESS = t["SUCCESS"]
    DANGER = t["DANGER"]
    DANGER_HOVER = t["DANGER_HOVER"]
    BG_MAIN = t["BG_MAIN"]
    BG_PANEL = t["BG_PANEL"]
    BG_INPUT = t["BG_INPUT"]
    BG_FOCUS = t["BG_FOCUS"]
    TXT_MAIN = t["TXT_MAIN"]
    TXT_DIM = t["TXT_DIM"]

def get_dimmed_accent(hex_color, factor=0.4):
    """Multiplies a hex color by a factor to get a darker version."""
    hex_color = hex_color.lstrip('#')
    # Convert hex to RGB
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    # Multiply each channel
    dimmed_rgb = tuple(max(0, min(255, int(c * factor))) for c in rgb)
    # Convert back to hex
    return '#{:02x}{:02x}{:02x}'.format(*dimmed_rgb)