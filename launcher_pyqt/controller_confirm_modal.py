from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
import colors as c


class ControllerConfirmModal(QDialog):
    def __init__(self, parent, engine=None, on_result=None, msg=None):
        super().__init__(parent)
        self.engine = engine
        self.on_result = on_result
        self.result = None

        if not engine or not on_result:
            self.result = False
            self.reject()
            return

        if self.engine:
            self.finished.connect(lambda: QTimer.singleShot(0, self.engine.rescan))

        self.setWindowTitle("Confirm action")
        self.setFixedSize(480, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QLabel("\u26a0  CONFIRM")
        header.setStyleSheet(f"color: {c.DANGER}; font: bold 18px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        txt = "Do you want to confirm the action?" if not msg else msg
        label = QLabel(txt)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {c.TXT_MAIN}; font: 14px; padding: 4px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: bold 12px;
                           border-radius: 6px; padding: 6px 24px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; border: 1px solid {c.ACCENT}; }}
        """)
        cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton("Confirm")
        confirm_btn.setFixedHeight(36)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.DANGER}; color: white; font: bold 12px;
                           border-radius: 6px; padding: 6px 24px; }}
            QPushButton:hover {{ background: {c.DANGER_HOVER}; }}
        """)
        confirm_btn.clicked.connect(self._finish)
        btn_row.addWidget(confirm_btn)

        layout.addLayout(btn_row)

    def showEvent(self, event):
        super().showEvent(event)
        if self.engine:
            QTimer.singleShot(0, self.engine.rescan)

    def _finish(self):
        self.result = True
        if self.on_result:
            self.on_result(self.result)
        self.accept()

    def _cancel(self):
        self.result = False
        if self.on_result:
            self.on_result(self.result)
        self.reject()
