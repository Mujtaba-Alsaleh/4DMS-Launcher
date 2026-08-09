from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve
import colors as c


class ToastManager:
    def __init__(self, parent):
        self.parent = parent
        self.toasts = []

    def show(self, message, duration_ms=2500):
        toast = QLabel(message, self.parent)
        toast.setStyleSheet(f"""
            background-color: {c.BG_PANEL}; color: {c.TXT_MAIN};
            padding: 8px 16px; border-radius: 10px;
            border: 1px solid {c.ACCENT};
            font-size: 13px; font-weight: bold;
        """)
        toast.adjustSize()
        toast.raise_()
        toast.show()
        effect = QGraphicsOpacityEffect(toast)
        effect.setOpacity(0.0)
        toast.setGraphicsEffect(effect)
        fade_in = QPropertyAnimation(effect, b"opacity")
        fade_in.setDuration(150)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        toast._toast_fade_in = fade_in
        fade_in.start()
        self.toasts.append(toast)
        self._reposition()
        QTimer.singleShot(duration_ms, lambda: self._dismiss(toast))

    def _reposition(self):
        parent_w = self.parent.width()
        y_offset = -10
        for toast in reversed(self.toasts):
            x = parent_w - toast.width() - 20
            toast.move(x, self.parent.height() - toast.height() + y_offset)
            y_offset -= 40

    def _dismiss(self, toast):
        try:
            effect = toast.graphicsEffect()
            if isinstance(effect, QGraphicsOpacityEffect):
                fade_out = QPropertyAnimation(effect, b"opacity")
                fade_out.setDuration(200)
                fade_out.setEndValue(0.0)
                fade_out.setEasingCurve(QEasingCurve.Type.InQuad)
                fade_out.finished.connect(lambda: self._finalize(toast))
                toast._toast_fade_out = fade_out
                fade_out.start()
                return
        except RuntimeError:
            pass
        self._finalize(toast)

    def _finalize(self, toast):
        try:
            toast.hide()
            toast.deleteLater()
        except RuntimeError:
            pass
        if toast in self.toasts:
            self.toasts.remove(toast)
        self._reposition()
