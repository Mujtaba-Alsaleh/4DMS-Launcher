import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath
from launcher_pyqt.artworkImage import GameImage
from launcher_pyqt.utils import format_playtime
import colors as c


class ArtworkWidget(QWidget):
    def __init__(self, art_path, w, h):
        super().__init__()
        self.setFixedSize(w, h)
        self._pix = QPixmap(art_path)
        if not self._pix.isNull():
            self._pix = self._pix.scaled(w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
        ext = os.path.splitext(art_path)[1].lower()
        self._gi = None
        if ext in ('.webp', '.gif'):
            gi = GameImage(self, art_path, 210, 280, quality=75)
            gi.hide()
            self._gi = gi

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        path = QPainterPath()
        path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), 12, 12)
        p.setClipPath(path)
        if self._pix and not self._pix.isNull():
            p.drawPixmap(r, self._pix)
        p.end()

    def showEvent(self, event):
        super().showEvent(event)
        if self._gi:
            self._gi.show()
            self._gi.raise_()
            self._gi.start()


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

        art = data.get("art")
        if art and os.path.exists(art):
            aw = ArtworkWidget(art, 210, 280)
            layout.addWidget(aw, alignment=Qt.AlignmentFlag.AlignCenter)

        name = data.get("name", "Unknown")
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {c.ACCENT}; font: bold 24px;")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_lbl)

        play_btn = QPushButton("PLAY")
        play_btn.setStyleSheet(f"""
            QPushButton {{ background: #2ecc71; color: white; font: bold 16px;
                           border-radius: 8px; padding: 10px; }}
            QPushButton:hover {{ background: #27ae60; }}
        """)
        play_btn.clicked.connect(lambda: self.app.try_launch_game())
        self.app.play_btn = play_btn
        if self.app.game_process_manager.is_playing and self.app.current_game_id == self.game_id:
            play_btn.setText("STOP")
            play_btn.setStyleSheet(f"""
                QPushButton {{ background: #e74c3c; color: white; font: bold 16px;
                               border-radius: 8px; padding: 10px; }}
                QPushButton:hover {{ background: #c0392b; }}
            """)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.setSpacing(12)

        art_btn = QPushButton("Browse Artwork")
        art_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.ACCENT}; font: bold 12px;
                           border: 1px solid {c.ACCENT}; border-radius: 6px; padding: 8px 16px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN}; }}
        """)
        art_btn.clicked.connect(self._browse_artwork)
        btn_row.addWidget(art_btn)

        edit_btn = QPushButton("Game Settings")
        edit_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.ACCENT}; font: bold 12px;
                           border: 1px solid {c.ACCENT}; border-radius: 6px; padding: 8px 16px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN}; }}
        """)
        edit_btn.clicked.connect(lambda: self.app.show_editor())
        btn_row.addWidget(edit_btn)

        fav_char = "\u2605" if data.get("favorite") else "\u2606"
        fav_btn = QPushButton(fav_char)
        fav_btn.setFixedSize(38, 34)
        fav_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.ACCENT}; font: 16px;
                           border: 1px solid {c.ACCENT}; border-radius: 6px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        fav_btn.clicked.connect(self._toggle_favorite)
        btn_row.addWidget(fav_btn)

        layout.addLayout(btn_row)
        layout.addWidget(play_btn)

        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{ border: 1px solid {c.BG_INPUT}; border-radius: 10px;
                       background: {c.BG_PANEL}; padding: 12px; }}
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(6)

        fields = [
            ("Exe", data.get("exe", "")),
            ("Prefix", data.get("prefix", "")),
            ("Proton", data.get("proton", "Default (UMU Internal)")),
            ("Store", data.get("store", "none")),
            ("Play Time", format_playtime(data.get("playtime"))),
            ("Launch Count", str(data.get("launch_count", 0))),
        ]
        for label_text, value in fields:
            row = QHBoxLayout()
            lbl = QLabel(f"{label_text}:")
            lbl.setStyleSheet(f"color: {c.ACCENT}; font: bold 11px;")
            lbl.setFixedWidth(100)
            row.addWidget(lbl)
            val_lbl = QLabel(value if value else "-")
            val_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: 11px;")
            if value:
                val_lbl.setToolTip(value)
            val_lbl.setMinimumWidth(100)
            row.addWidget(val_lbl, 1, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            info_layout.addLayout(row)

        layout.addWidget(info_frame)

        art = data.get("art")
        if art and os.path.exists(art):
            rm_btn = QPushButton("Remove Artwork")
            rm_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {c.DANGER}; font: bold 11px;
                               border: 1px solid {c.DANGER}; border-radius: 6px;
                               padding: 6px; }}
                QPushButton:hover {{ background: {c.DANGER_HOVER}; color: {c.TXT_MAIN}; }}
            """)
            rm_btn.clicked.connect(self._remove_artwork)
            layout.addWidget(rm_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        if self.app.engine:
            self.app.engine.rescan(priority_widget=play_btn)

    def _toggle_favorite(self):
        data = self.app.config_data[self.game_id]
        data["favorite"] = not data.get("favorite", False)
        self.app.config_manager.save_data(self.app.config_data)
        self.app.show_dashboard(self.game_id)

    def _browse_artwork(self):
        prev_state = self.app.view_state
        self.app.view_state = "browser"
        self.app.engine.sound.play("modal")

        def on_selected(path):
            if path:
                data = self.app.config_data[self.game_id]
                data["art"] = path
                self.app.config_manager.save_data(self.app.config_data)
                self.app.show_dashboard(self.game_id)

        from launcher_pyqt.controller_file_browser import ControllerFileBrowser
        browser = ControllerFileBrowser(self, is_file=True, is_art=True, callback=on_selected, engine=self.app.engine)
        browser.exec()
        self.app.view_state = prev_state

    def _remove_artwork(self):
        data = self.app.config_data[self.game_id]
        data["art"] = ""
        self.app.config_manager.save_data(self.app.config_data)
        self.app.show_dashboard(self.game_id)
