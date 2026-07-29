import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame)
from PyQt6.QtCore import Qt
from launcher_pyqt.artworkImage import GameImage
from launcher_pyqt.utils import format_playtime
import colors as c


class DashboardView(QWidget):
    def __init__(self, app, game_id):
        super().__init__()
        self.app = app
        self.game_id = game_id
        self.setStyleSheet("background: transparent;")
        self._build()

    def _build(self):
        data = self.app.config_data[self.game_id]
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 20, 30, 20)

        # Artwork display
        art = data.get("art")
        h, w = 280, 210
        if art and os.path.exists(art):
            gi = GameImage(self, art, w, h)
            gi.setFixedSize(w, h)
            gi.setStyleSheet(f"border-radius: 12px; border: 2px solid {c.BG_INPUT};")
            layout.addWidget(gi, alignment=Qt.AlignmentFlag.AlignCenter)
            gi.start()

        name_lbl = QLabel(data.get('name', ''))
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 26px;")
        layout.addWidget(name_lbl)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        play_text = "PLAY"
        play_color = c.SUCCESS
        if self.app.game_process_manager.is_playing:
            play_text = "STOP"
            play_color = c.DANGER

        play_btn = QPushButton(play_text)
        play_btn.setFixedSize(180, 44)
        play_btn.setStyleSheet(f"""
            QPushButton {{ background: {play_color}; color: white; font: bold 18px;
                           border-radius: 10px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        play_btn.clicked.connect(self.app.game_process_manager.try_launch)
        btn_row.addWidget(play_btn)
        self.app.play_btn = play_btn

        edit_btn = QPushButton("SETTINGS")
        edit_btn.setFixedSize(140, 44)
        edit_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: bold 14px;
                           border-radius: 10px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        edit_btn.clicked.connect(self.app.show_editor)
        btn_row.addWidget(edit_btn)
        layout.addLayout(btn_row)

        self.art_btn = QPushButton("SET ARTWORK")
        self.art_btn.setFixedSize(160, 36)
        self.art_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_DIM}; font: bold 11px;
                           border-radius: 8px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; border: 1px solid {c.ACCENT}; }}
        """)
        self.art_btn.clicked.connect(self._browse_artwork)
        layout.addWidget(self.art_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        if art:
            rm_btn = QPushButton("REMOVE ARTWORK")
            rm_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {c.DANGER}; font: bold 11px;
                               border: 1px solid {c.DANGER}; border-radius: 6px; padding: 4px 12px; }}
                QPushButton:hover {{ background: {c.DANGER_HOVER}; }}
            """)
            rm_btn.clicked.connect(self._remove_artwork)
            layout.addWidget(rm_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{ border: 1px solid {c.BG_INPUT}; border-radius: 10px;
                      background: transparent; padding: 4px; }}
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(6)
        info_layout.setContentsMargins(16, 12, 16, 12)

        def add_row(label, value, val_color=c.TXT_MAIN):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: gray; font: bold 11px;")
            row.addWidget(lbl)
            val_lbl = QLabel(value)
            val_lbl.setStyleSheet(f"color: {val_color}; font: 11px;")
            row.addWidget(val_lbl, alignment=Qt.AlignmentFlag.AlignRight)
            info_layout.addLayout(row)

        add_row("PROTON", data.get('proton', ''), c.ACCENT)
        add_row("PREFIX", data.get('prefix', ''), "#bbbbbb")
        gs_active = data.get('gs_on', False) and self.app.has_gamescope
        add_row("GAMESCOPE", "ENABLED" if gs_active else "DISABLED", "#2ecc71" if gs_active else "#e74c3c")
        hud_active = data.get('useMangoHud', False)
        add_row("MANGOHUD", "ACTIVE" if hud_active else "OFF", "#2ecc71" if hud_active else "gray")
        add_row("PLAYTIME", format_playtime(data.get('playtime')), c.ACCENT)
        layout.addWidget(info_frame)

        if self.app.engine:
            self.app.engine.rebuild_nav_map(priority_widget=play_btn)

    def _browse_artwork(self):
        from launcher_pyqt.controller_file_browser import ControllerFileBrowser

        def on_selected(path):
            if path:
                self.app.artwork_manager.select(self.game_id, path, self.app.config_data, self.app.config_manager.save_data)
                self.app.show_dashboard(self.game_id)

        if self.app.engine:
            self.app.engine.sound.play("modal")
        self.app.view_state = "browser"
        browser = ControllerFileBrowser(self.app, is_file=True, is_art=True,
                                        callback=on_selected, engine=self.app.engine)
        browser.exec()

    def _remove_artwork(self):
        self.app.artwork_manager.remove(self.game_id, self.app.config_data, self.app.config_manager.save_data)
        self.app.show_dashboard(self.game_id)
