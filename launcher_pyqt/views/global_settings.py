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

        layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

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
