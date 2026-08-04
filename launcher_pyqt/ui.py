"""Design system: role tokens, QSS builders, controller glyphs.

M1 shell — the app-level stylesheet, tab/header/pill builders and the
controller-glyph loader all live here so the rest of the app styles
against role tokens (SURFACE/BORDER/ON_ACCENT/FOCUS_RING/SCRIM).
"""
from pathlib import Path

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QFrame
from PyQt6.QtGui import QFontDatabase

import colors as c
from launcher_pyqt.utils import get_resources_icon

FONT_DIR = Path(__file__).parent.parent / "resources" / "fonts"

GLYPH_PATHS = {
    "A": "button_a",
    "B": "button_b",
    "X": "button_x",
    "Y": "button_y",
    "MENU": "button_menu",
    "VIEW": "button_view",
    "LB": None,
    "RB": None,
    "LB/RB": None,
}
GLYPH_SIZE = (24, 24)

TABS = [
    ("home", "HOME"),
    ("library", "LIBRARY"),
    ("tools", "TOOLS"),
    ("settings", "SETTINGS"),
]


def register_fonts():
    """Load bundled Inter weights; returns the family name or None."""
    families = []
    for f in sorted(FONT_DIR.glob("Inter-*.ttf")):
        fid = QFontDatabase.addApplicationFont(str(f))
        if fid >= 0:
            families.extend(QFontDatabase.applicationFontFamilies(fid))
    if "Inter" in families:
        return "Inter"
    return families[0] if families else None


def glyph_pixmap(key):
    name = GLYPH_PATHS.get(key)
    if not name:
        return None
    return get_resources_icon(name, GLYPH_SIZE)


def app_qss(family="Inter"):
    """Whole-app stylesheet: fonts, focus rings, scrollbars, tooltip."""
    return f"""
        QWidget {{ font-family: "{family}"; font-size: 13px; color: {c.TXT_MAIN}; }}
        QPushButton[focused="true"] {{ border: 3px solid {c.FOCUS_RING} !important; }}
        QLineEdit[focused="true"] {{ border: 2px solid {c.ACCENT} !important; }}
        QCheckBox[focused="true"] {{ background: {c.BG_FOCUS} !important; }}
        QComboBox[focused="true"] {{ background: {c.BG_FOCUS} !important; }}
        QScrollBar:vertical {{ background: {c.BG_INPUT}; width: 8px; border-radius: 4px; }}
        QScrollBar::handle:vertical {{ background: {c.ACCENT}; border-radius: 4px;
                                        min-height: 30px; }}
        QScrollBar::add-line:vertical {{ height: 0; }}
        QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{ background: {c.BG_INPUT}; height: 8px; border-radius: 4px; }}
        QScrollBar::handle:horizontal {{ background: {c.ACCENT}; border-radius: 4px;
                                          min-width: 30px; }}
        QScrollBar::add-line:horizontal {{ width: 0; }}
        QScrollBar::sub-line:horizontal {{ width: 0; }}
        QToolTip {{ background: {c.BG_PANEL}; color: {c.TXT_MAIN};
                    border: 1px solid {c.ACCENT}; border-radius: 4px; padding: 4px; }}
        QComboBox QAbstractItemView {{ background: {c.SURFACE}; color: {c.TXT_MAIN};
                                        selection-background-color: {c.ACCENT};
                                        selection-color: {c.ON_ACCENT}; }}
    """


def header_style():
    return (f"QFrame {{ background: {c.BG_PANEL}; border-bottom: 1px solid {c.BORDER}; }}")


def tab_style(active):
    if active:
        return f"""
            QPushButton {{ background: transparent; color: {c.TXT_MAIN};
                           font-weight: 700; font-size: 13px; letter-spacing: 1px;
                           border-radius: 4px; padding: 6px 16px; border: none;
                           border-bottom: 2px solid {c.ACCENT}; }}
            QPushButton:hover {{ background: transparent; }}
        """
    return f"""
        QPushButton {{ background: transparent; color: {c.TXT_DIM};
                       font-weight: 500; font-size: 13px; letter-spacing: 1px;
                       border-radius: 4px; padding: 6px 16px; border: none;
                       border-bottom: 2px solid transparent; }}
        QPushButton:hover {{ color: {c.TXT_MAIN}; border-bottom: 2px solid {c.BORDER}; }}
    """


def hint_pill(key, action):
    """Glyph + action label pill for the bottom hint bar."""
    pill = QFrame()
    pill.setStyleSheet("QFrame { background: transparent; border: none; }")
    lay = QHBoxLayout(pill)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    pm = glyph_pixmap(key)
    if pm is not None:
        glyph = QLabel()
        glyph.setPixmap(pm)
        glyph.setStyleSheet("background: transparent;")
        lay.addWidget(glyph)
    else:
        key_label = QLabel(key)
        key_label.setStyleSheet(
            f"color: {c.ACCENT}; font-weight: 600; font-size: 12px; background: transparent;")
        lay.addWidget(key_label)
    txt = QLabel(action)
    txt.setStyleSheet(f"color: {c.TXT_DIM}; font-size: 12px; background: transparent;")
    lay.addWidget(txt)
    return pill
