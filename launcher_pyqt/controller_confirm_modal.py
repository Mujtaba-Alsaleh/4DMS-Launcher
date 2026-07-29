from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
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

        self.setWindowTitle("Confirm action")
        self.setFixedSize(1365, 335)
        self.setWindowFlags(self.windowFlags() | 0x00080000)  # topmost

        txt = "Do you want to confirm the action?" if not msg else msg

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel(txt)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {c.TXT_MAIN}; font: 16px; padding: 10px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        btn_row = QHBoxLayout()
        confirm_btn = QPushButton("Confirm")
        confirm_btn.setFixedHeight(40)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.SUCCESS}; color: white; font: bold 13px;
                           border-radius: 6px; padding: 6px 16px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        confirm_btn.clicked.connect(self._finish)
        btn_row.addWidget(confirm_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.DANGER}; color: white; font: bold 13px;
                           border-radius: 6px; padding: 6px 16px; }}
            QPushButton:hover {{ background: {c.DANGER_HOVER}; }}
        """)
        cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

        if self.engine:
            self.engine.rebuild_nav_map_modal(self)

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
