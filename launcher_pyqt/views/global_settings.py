from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QComboBox, QScrollArea)
from PyQt6.QtCore import Qt
import colors as c


class GlobalSettingsView(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setStyleSheet("background: transparent;")
        self.theme_menu = None
        self._hk_labels = {}
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(16)

        # Theme
        theme_card = QFrame()
        theme_card.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_FOCUS};
                      border-radius: 12px; }}
        """)
        theme_inner = QVBoxLayout(theme_card)
        theme_inner.setContentsMargins(20, 16, 20, 16)
        theme_inner.setSpacing(8)

        theme_title = QLabel("LAUNCHER THEME")
        theme_title.setStyleSheet(f"color: {c.ACCENT}; font: bold 14px;")
        theme_inner.addWidget(theme_title)

        self.theme_menu = QComboBox()
        self.theme_menu.addItems(list(c.THEMES.keys()))
        self.theme_menu.setCurrentText(self.app.config_data.get("settings", {}).get("theme", "Deep Blue"))
        self.theme_menu.setStyleSheet(f"""
            QComboBox {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 12px;
                         border-radius: 6px; padding: 8px; }}
            QComboBox::drop-down {{ border: none; }}
        """)
        theme_inner.addWidget(self.theme_menu)

        apply_btn = QPushButton("APPLY THEME")
        apply_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.ACCENT}; font: bold 12px;
                           border: 1px solid {c.ACCENT}; border-radius: 6px; padding: 10px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN}; }}
        """)
        apply_btn.clicked.connect(self._save)
        theme_inner.addWidget(apply_btn)
        layout.addWidget(theme_card)

        # Storage
        storage_card = QFrame()
        storage_card.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_FOCUS};
                      border-radius: 12px; }}
        """)
        storage_inner = QVBoxLayout(storage_card)
        storage_inner.setContentsMargins(20, 16, 20, 16)
        storage_inner.setSpacing(8)

        storage_title = QLabel("STORAGE")
        storage_title.setStyleSheet(f"color: {c.ACCENT}; font: bold 14px;")
        storage_inner.addWidget(storage_title)

        wipe_btn = QPushButton("CLEAN ARTWORK STORAGE")
        wipe_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.DANGER}; font: bold 12px;
                           border: 1px solid {c.DANGER}; border-radius: 6px; padding: 10px; }}
            QPushButton:hover {{ background: {c.DANGER_HOVER}; color: {c.TXT_MAIN}; }}
        """)
        wipe_btn.clicked.connect(self._clear_artwork)
        storage_inner.addWidget(wipe_btn)
        layout.addWidget(storage_card)

        # LiveSplit hotkeys
        import livesplit as ls
        if ls.LiveSplitManager.is_installed():
            self._build_hotkey_section(layout)

        layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

        if self.app.engine:
            self.app.engine.rebuild_nav_map(priority_widget=self.theme_menu)

    def _save(self):
        new_theme = self.theme_menu.currentText()
        if "settings" not in self.app.config_data:
            self.app.config_data["settings"] = {}
        self.app.config_data["settings"]["theme"] = new_theme
        self.app.current_theme = new_theme
        self.app.config_manager.save_data(self.app.config_data)
        c.apply_theme(new_theme)
        self.app.apply_theme_visuals()
        self.app.show_library()

    def _clear_artwork(self):
        self.app.artwork_manager.clear_all(self.app.config_data, self.app.config_manager.save_data)
        self.app.show_library()

    def _build_hotkey_section(self, layout):
        hk_card = QFrame()
        hk_card.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_FOCUS};
                      border-radius: 12px; }}
        """)
        hk_inner = QVBoxLayout(hk_card)
        hk_inner.setContentsMargins(20, 16, 20, 16)
        hk_inner.setSpacing(6)

        hk_title = QLabel("LIVESPLIT HOTKEYS")
        hk_title.setStyleSheet(f"color: {c.ACCENT}; font: bold 14px;")
        hk_inner.addWidget(hk_title)

        actions = [
            ("startorsplit", "Split"),
            ("reset", "Reset"),
            ("undo", "Undo"),
            ("skip", "Skip"),
            ("swap", "Prev Comparison"),
        ]

        import livesplit as ls
        mgr = ls.LiveSplitManager(app=self.app)
        current = mgr.parse_settings()

        for action, label in actions:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: 12px;")
            row.addWidget(lbl)

            key_name = current.get(action, ("None", 0))[0]
            key_lbl = QLabel(key_name)
            key_lbl.setFixedSize(100, 28)
            key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            key_lbl.setStyleSheet(f"""
                QLabel {{ background: {c.ACCENT}; color: {c.BG_MAIN};
                          font: bold 11px Consolas; border-radius: 4px; }}
            """)
            row.addWidget(key_lbl)
            self._hk_labels[action] = key_lbl

            rebind_btn = QPushButton("Rebind")
            rebind_btn.setFixedSize(70, 28)
            rebind_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {c.ACCENT}; font: bold 10px;
                               border: 1px solid {c.ACCENT}; border-radius: 4px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN}; }}
            """)
            rebind_btn.clicked.connect(lambda checked, a=action, k=key_lbl: self._rebind_hotkey(a, k))
            row.addWidget(rebind_btn)
            row.addStretch()
            hk_inner.addLayout(row)

        layout.addWidget(hk_card)

    def _rebind_hotkey(self, action, label_widget):
        label_widget.setText("...")
        label_widget.setStyleSheet(f"""
            QLabel {{ background: {c.DANGER}; color: white;
                      font: bold 11px Consolas; border-radius: 4px; }}
        """)

        import livesplit as ls
        mgr = ls.LiveSplitManager(app=self.app)
        mgr.load_hotkeys()

        def on_key(key_name):
            if key_name:
                mgr.save_hotkey(action, key_name)
                label_widget.setText(key_name)
                label_widget.setStyleSheet(f"""
                    QLabel {{ background: {c.ACCENT}; color: {c.BG_MAIN};
                              font: bold 11px Consolas; border-radius: 4px; }}
                """)
            else:
                old = mgr._hotkeys.get(action, ("None", 0))[0]
                label_widget.setText(old)
                label_widget.setStyleSheet(f"""
                    QLabel {{ background: {c.ACCENT}; color: {c.BG_MAIN};
                              font: bold 11px Consolas; border-radius: 4px; }}
                """)

        mgr.capture_next_key(on_key)
