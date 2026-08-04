from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
import colors as c


class LiveSplitView(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setStyleSheet("background: transparent;")
        self._hk_labels = {}
        self._capturing_action = None
        self._build()

    def _build(self):
        mgr = self.app.livesplit
        mgr.app = self.app

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 12, 30, 12)
        root.setSpacing(10)

        title = QLabel("LIVESPLIT")
        title.setStyleSheet(f"color: {c.ACCENT}; font: bold 18px;")
        root.addWidget(title)

        status_card = QFrame()
        status_card.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_FOCUS};
                       border-radius: 8px; padding: 10px; }}
        """)
        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(4)

        ls_status = "Running" if mgr.process and mgr.process.poll() is None else "Stopped"
        connected = hasattr(mgr, 'client') and mgr.client is not None
        conn_status = "Connected" if connected else "Disconnected"
        ls_color = c.SUCCESS if ls_status == "Running" else c.TXT_DIM
        conn_color = c.SUCCESS if conn_status == "Connected" else c.TXT_DIM

        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        self._status_lbl = QLabel(f"Status: {ls_status}")
        self._status_lbl.setStyleSheet(f"color: {ls_color}; font: bold 13px;")
        status_row.addWidget(self._status_lbl)
        self._conn_lbl = QLabel(f"TCP: {conn_status}")
        self._conn_lbl.setStyleSheet(f"color: {conn_color}; font: 12px;")
        status_row.addWidget(self._conn_lbl)
        status_row.addStretch(1)
        status_layout.addLayout(status_row)

        root.addWidget(status_card)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._launch_btn = QPushButton("Launch")
        self._launch_btn.setFixedHeight(34)
        self._launch_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.ACCENT}; color: white; font: bold 12px;
                           border-radius: 6px; padding: 6px 16px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        self._launch_btn.clicked.connect(self._launch_livesplit)
        btn_row.addWidget(self._launch_btn)

        stop_btn = QPushButton("STOP")
        stop_btn.setFixedHeight(34)
        stop_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.DANGER}; font: bold 12px;
                           border: 1px solid {c.DANGER}; border-radius: 6px;
                           padding: 6px 16px; }}
            QPushButton:hover {{ background: {c.DANGER}; color: white; }}
        """)
        stop_btn.clicked.connect(self._stop_livesplit)
        btn_row.addWidget(stop_btn)
        root.addLayout(btn_row)

        hk_card = QFrame()
        hk_card.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_FOCUS};
                       border-radius: 8px; padding: 10px; }}
        """)
        hk_layout = QVBoxLayout(hk_card)
        hk_layout.setSpacing(4)

        hk_title = QLabel("HOTKEYS")
        hk_title.setStyleSheet(f"color: {c.ACCENT}; font: bold 11px;")
        hk_layout.addWidget(hk_title)

        mgr.load_hotkeys()
        for action, (key_name, _mods) in (mgr._hotkeys or {}).items():
            row = QHBoxLayout()
            row.setSpacing(6)
            act_lbl = QLabel(action)
            act_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: 11px;")
            act_lbl.setFixedWidth(90)
            row.addWidget(act_lbl)
            row.addStretch()
            key_btn = QPushButton(key_name)
            key_btn.setStyleSheet(f"""
                QPushButton {{ background: {c.BG_INPUT}; color: {c.ACCENT}; font: bold 11px;
                               border-radius: 4px; padding: 3px 10px; min-width: 70px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
            """)
            key_btn.clicked.connect(lambda checked=False, a=action: self._begin_rebind(a))
            self._hk_labels[action] = key_btn
            row.addWidget(key_btn)
            hk_layout.addLayout(row)

        root.addWidget(hk_card)
        root.addStretch()

        self.installEventFilter(self)

        self._update_status()

    def _update_status(self):
        mgr = self.app.livesplit
        ls_status = "Running" if mgr.process and mgr.process.poll() is None else "Stopped"
        connected = hasattr(mgr, 'client') and mgr.client is not None
        conn_status = "Connected" if connected else "Disconnected"
        ls_color = c.SUCCESS if ls_status == "Running" else c.TXT_DIM
        conn_color = c.SUCCESS if conn_status == "Connected" else c.TXT_DIM
        self._status_lbl.setText(f"Status: {ls_status}")
        self._status_lbl.setStyleSheet(f"color: {ls_color}; font: bold 14px;")
        self._conn_lbl.setText(f"TCP: {conn_status}")
        self._conn_lbl.setStyleSheet(f"color: {conn_color}; font: 12px;")

    def _launch_livesplit(self):
        self.app.livesplit.launch("", "")
        self._update_status()

    def _stop_livesplit(self):
        self.app.livesplit.stop()
        self._update_status()

    def _begin_rebind(self, action):
        self._capturing_action = action
        lbl = self._hk_labels.get(action)
        if lbl:
            lbl.setStyleSheet(f"""
                QPushButton {{ background: {c.BG_FOCUS}; color: {c.ACCENT}; font: bold 12px;
                              border: 2px solid {c.ACCENT}; border-radius: 4px;
                              padding: 4px 12px; min-width: 80px; }}
            """)
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if not self._capturing_action:
            return super().eventFilter(obj, event)
        if event.type() == QKeyEvent.Type.KeyPress:
            ke: QKeyEvent = event
            text = ke.text()
            mods = ke.modifiers()
            name = self._key_to_ls(text, ke.key(), mods)
            if name:
                action = self._capturing_action
                self._capturing_action = None
                self.app.livesplit.save_hotkey(action, name)
                lbl = self._hk_labels.get(action)
                if lbl:
                    lbl.setText(name)
                    lbl.setStyleSheet(f"""
                        QPushButton {{ background: {c.BG_INPUT}; color: {c.ACCENT}; font: bold 12px;
                                       border-radius: 4px; padding: 4px 12px; min-width: 80px; }}
                        QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
                    """)
            self._capturing_action = None
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().removeEventFilter(self)
            return True
        return super().eventFilter(obj, event)

    def _key_to_ls(self, text, key, modifiers):
        from PyQt6.QtCore import Qt as QtKey
        is_numpad = bool(modifiers & QtKey.KeyboardModifier.KeypadModifier)
        if is_numpad:
            mp = {
                QtKey.Key.Key_0: "NumPad0", QtKey.Key.Key_1: "NumPad1",
                QtKey.Key.Key_2: "NumPad2", QtKey.Key.Key_3: "NumPad3",
                QtKey.Key.Key_4: "NumPad4", QtKey.Key.Key_5: "NumPad5",
                QtKey.Key.Key_6: "NumPad6", QtKey.Key.Key_7: "NumPad7",
                QtKey.Key.Key_8: "NumPad8", QtKey.Key.Key_9: "NumPad9",
                QtKey.Key.Key_Period: "Decimal",
                QtKey.Key.Key_Plus: "Add",
                QtKey.Key.Key_Minus: "Subtract",
                QtKey.Key.Key_Asterisk: "Multiply",
                QtKey.Key.Key_Slash: "Divide",
                QtKey.Key.Key_Delete: "Decimal",
                QtKey.Key.Key_Enter: "NumPadEnter",
            }
            return mp.get(key)
        mp = {
            QtKey.Key.Key_Return: "Enter", QtKey.Key.Key_Space: "Space",
            QtKey.Key.Key_Backspace: "Backspace", QtKey.Key.Key_Tab: "Tab",
            QtKey.Key.Key_Escape: "Escape", QtKey.Key.Key_CapsLock: "CapsLock",
            QtKey.Key.Key_Delete: "Delete", QtKey.Key.Key_Insert: "Insert",
            QtKey.Key.Key_PageUp: "PageUp", QtKey.Key.Key_PageDown: "PageDown",
            QtKey.Key.Key_Home: "Home", QtKey.Key.Key_End: "End",
            QtKey.Key.Key_Left: "LeftArrow", QtKey.Key.Key_Right: "RightArrow",
            QtKey.Key.Key_Up: "UpArrow", QtKey.Key.Key_Down: "DownArrow",
            QtKey.Key.Key_Print: "PrintScreen", QtKey.Key.Key_ScrollLock: "ScrollLock",
            QtKey.Key.Key_Pause: "Pause",
            QtKey.Key.Key_F1: "F1", QtKey.Key.Key_F2: "F2",
            QtKey.Key.Key_F3: "F3", QtKey.Key.Key_F4: "F4",
            QtKey.Key.Key_F5: "F5", QtKey.Key.Key_F6: "F6",
            QtKey.Key.Key_F7: "F7", QtKey.Key.Key_F8: "F8",
            QtKey.Key.Key_F9: "F9", QtKey.Key.Key_F10: "F10",
            QtKey.Key.Key_F11: "F11", QtKey.Key.Key_F12: "F12",
            QtKey.Key.Key_BracketLeft: "OemOpenBrackets",
            QtKey.Key.Key_BracketRight: "OemCloseBrackets",
            QtKey.Key.Key_Backslash: "OemPipe",
            QtKey.Key.Key_Semicolon: "OemSemicolon",
            QtKey.Key.Key_Apostrophe: "OemQuotes",
            QtKey.Key.Key_Comma: "OemComma",
            QtKey.Key.Key_Period: "OemPeriod",
            QtKey.Key.Key_Minus: "OemMinus",
            QtKey.Key.Key_Equal: "OemPlus",
        }
        name = mp.get(key)
        if name:
            return name
        if len(text) == 1:
            return text.upper()
        return None
