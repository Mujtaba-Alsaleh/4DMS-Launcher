# colors.py
#
# Theme tokens. Legacy keys (ACCENT/BG_MAIN/BG_PANEL/...) remain for
# backward-compat with per-widget stylesheets; role tokens
# (SURFACE/SURFACE_HOVER/BORDER/ON_ACCENT/FOCUS_RING/SCRIM) are the
# design-system roles used by launcher_pyqt/ui.py builders.

THEMES = {
    "Deep Blue": {
        "ACCENT": "#3d91ff",
        "ACCENT_HOVER": "#0065f3",
        "SUCCESS": "#2ecc71",
        "DANGER": "#e74c3c",
        "DANGER_HOVER": "#331111",
        "BG_MAIN": "#0a0f14",
        "BG_PANEL": "#10161d",
        "BG_INPUT": "#1c252f",
        "BG_FOCUS": "#1a3a5f",
        "TXT_MAIN": "#ffffff",
        "TXT_DIM": "#888888",
        "SURFACE": "#10161d",
        "SURFACE_HOVER": "#1a2330",
        "BORDER": "#1c252f",
        "ON_ACCENT": "#ffffff",
        "FOCUS_RING": "#ffffff",
        "SCRIM": "rgba(0, 0, 0, 160)"
    },
    "Amber Glow": {
        "ACCENT": "#ffa726",
        "ACCENT_HOVER": "#ef6c00",
        "SUCCESS": "#2ecc71",
        "DANGER": "#e74c3c",
        "DANGER_HOVER": "#331111",
        "BG_MAIN": "#16120d",
        "BG_PANEL": "#1e1912",
        "BG_INPUT": "#282115",
        "BG_FOCUS": "#3d2f1a",
        "TXT_MAIN": "#ffffff",
        "TXT_DIM": "#aaaaaa",
        "SURFACE": "#1e1912",
        "SURFACE_HOVER": "#2a2318",
        "BORDER": "#282115",
        "ON_ACCENT": "#1a1208",
        "FOCUS_RING": "#ffffff",
        "SCRIM": "rgba(0, 0, 0, 170)"
    },
    "Synthwave": {
        "ACCENT": "#ff2d95",
        "ACCENT_HOVER": "#cc0066",
        "SUCCESS": "#2ecc71",
        "DANGER": "#e74c3c",
        "DANGER_HOVER": "#331111",
        "BG_MAIN": "#0d0b1a",
        "BG_PANEL": "#151130",
        "BG_INPUT": "#1d1540",
        "BG_FOCUS": "#301860",
        "TXT_MAIN": "#ffffff",
        "TXT_DIM": "#aaaaaa",
        "SURFACE": "#151130",
        "SURFACE_HOVER": "#241c55",
        "BORDER": "#1d1540",
        "ON_ACCENT": "#ffffff",
        "FOCUS_RING": "#ffffff",
        "SCRIM": "rgba(0, 0, 0, 165)"
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
SURFACE = THEMES["Deep Blue"]["SURFACE"]
SURFACE_HOVER = THEMES["Deep Blue"]["SURFACE_HOVER"]
BORDER = THEMES["Deep Blue"]["BORDER"]
ON_ACCENT = THEMES["Deep Blue"]["ON_ACCENT"]
FOCUS_RING = THEMES["Deep Blue"]["FOCUS_RING"]
SCRIM = THEMES["Deep Blue"]["SCRIM"]


def apply_theme(theme_name):
    """Updates the global constants to match the chosen theme."""
    global ACCENT, ACCENT_HOVER, SUCCESS, DANGER, DANGER_HOVER, BG_MAIN
    global BG_PANEL, BG_INPUT, BG_FOCUS, TXT_MAIN, TXT_DIM
    global SURFACE, SURFACE_HOVER, BORDER, ON_ACCENT, FOCUS_RING, SCRIM
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
    SURFACE = t["SURFACE"]
    SURFACE_HOVER = t["SURFACE_HOVER"]
    BORDER = t["BORDER"]
    ON_ACCENT = t["ON_ACCENT"]
    FOCUS_RING = t["FOCUS_RING"]
    SCRIM = t["SCRIM"]


def get_dimmed_accent(hex_color, factor=0.4):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    dimmed_rgb = tuple(max(0, min(255, int(c * factor))) for c in rgb)
    return '#{:02x}{:02x}{:02x}'.format(*dimmed_rgb)
