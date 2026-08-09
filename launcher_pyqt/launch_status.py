import colors as c
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QProgressBar)
from PyQt6.QtCore import Qt


class LaunchStatusOverlay(QFrame):
    """Dimmed overlay shown while a game is launching: indeterminate spinner
    + game name + status message. Decorative only (WA_TransparentForMouseEvents)
    so it never steals mouse/hover; the launch can be cancelled by pressing
    the play button (LAUNCHING... state) or START/R again."""

    def __init__(self, app):
        super().__init__(app._content_area)
        self.app = app
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: rgba(0, 0, 0, 140);")
        self._build()
        self.hide()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 48, 48, 48)

        panel = QFrame(self)
        panel.setMaximumWidth(440)
        panel.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_INPUT};
                      border-radius: 12px; }}
        """)
        lay.addWidget(panel, 0, Qt.AlignmentFlag.AlignCenter)

        p_l = QVBoxLayout(panel)
        p_l.setContentsMargins(30, 26, 30, 26)
        p_l.setSpacing(12)

        self._name_lbl = QLabel("")
        self._name_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 16px;")
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_l.addWidget(self._name_lbl)

        self._spinner = QProgressBar()
        self._spinner.setRange(0, 0)
        self._spinner.setFixedWidth(220)
        self._spinner.setTextVisible(False)
        self._spinner.setFixedHeight(8)
        self._spinner.setStyleSheet(f"""
            QProgressBar {{ background: {c.BG_INPUT}; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {c.ACCENT}; border-radius: 4px; }}
        """)
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self._spinner)
        p_l.addLayout(row)

        self._msg_lbl = QLabel("Launching\u2026")
        self._msg_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 12px;")
        self._msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg_lbl.setWordWrap(True)
        p_l.addWidget(self._msg_lbl)

        self._hint_lbl = QLabel("Press again to cancel")
        self._hint_lbl.setStyleSheet(f"color: {c.ACCENT}; font: bold 10px;")
        self._hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_l.addWidget(self._hint_lbl)

    def show_status(self, gid, data, first_run=False):
        self._name_lbl.setText(data.get("name", ""))
        if first_run:
            self._msg_lbl.setText(
                "First run detected \u2014 creating prefix. This can take a few minutes\u2026")
        else:
            self._msg_lbl.setText("Launching\u2026")
        try:
            self.setGeometry(self.app._content_area.rect())
        except RuntimeError:
            pass
        self.show()
        self.raise_()

    def hide_status(self):
        self.hide()
