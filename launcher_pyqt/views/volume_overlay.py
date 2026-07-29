import subprocess
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer
import colors as c


class VolumeOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.visible = False
        self.dismiss_timer = None

        self.setStyleSheet(f"""
            background: #1a1a1a;
            border: 2px solid {c.BG_FOCUS};
            border-radius: 16px;
        """)
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)

        self.icon = QLabel()
        self.icon.setStyleSheet(f"color: {c.TXT_MAIN}; font: 20px;")
        layout.addWidget(self.icon)

        self.bar = QProgressBar()
        self.bar.setFixedSize(200, 14)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet(f"""
            QProgressBar {{ background: {c.BG_INPUT}; border-radius: 7px; }}
            QProgressBar::chunk {{ background: {c.ACCENT}; border-radius: 7px; }}
        """)
        layout.addWidget(self.bar)

        self.pct = QLabel("50%")
        self.pct.setFixedWidth(40)
        self.pct.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 12px;")
        layout.addWidget(self.pct)

        self._has_pactl = self._check_pactl()

    def _check_pactl(self):
        try:
            result = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                                    capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False

    def get_volume(self):
        if not self._has_pactl:
            return 50
        try:
            result = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                                    capture_output=True, text=True, timeout=2)
            for part in result.stdout.split("/"):
                part = part.strip()
                if part.endswith("%"):
                    return int(part.replace("%", ""))
        except Exception:
            pass
        return 50

    def set_volume(self, percent):
        percent = max(0, min(150, percent))
        if not self._has_pactl:
            return
        try:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"], timeout=2)
        except Exception:
            pass

    def show(self):
        if not self._has_pactl:
            return
        vol = self.get_volume()
        self.bar.setValue(vol)
        self.pct.setText(f"{vol}%")
        if vol == 0:
            self.icon.setText("\U0001f507")
        elif vol < 33:
            self.icon.setText("\U0001f508")
        elif vol < 66:
            self.icon.setText("\U0001f509")
        else:
            self.icon.setText("\U0001f50a")
        parent = self.parent()
        if parent:
            pw = parent.width() if hasattr(parent, 'width') else 1920
            self.move(int(pw / 2 - 150), parent.height() - 80)
        self.raise_()
        super().show()
        self.visible = True
        self._schedule_dismiss()

    def hide(self):
        self.visible = False
        super().hide()
        if self.dismiss_timer:
            self.dismiss_timer.stop()
            self.dismiss_timer = None

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()

    def _schedule_dismiss(self):
        if self.dismiss_timer:
            self.dismiss_timer.stop()
        self.dismiss_timer = QTimer()
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.hide)
        self.dismiss_timer.start(2000)

    def adjust(self, delta):
        vol = self.get_volume()
        new_vol = max(0, min(150, vol + delta))
        self.set_volume(new_vol)
        self.show()
