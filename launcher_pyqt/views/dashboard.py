import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath
from launcher_pyqt.artworkImage import GameImage
from launcher_pyqt.utils import format_playtime, relative_time
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
            gi = GameImage(self, art_path, w, h, quality=75)
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

    def stop(self):
        if self._gi:
            try:
                self._gi.stop()
            except RuntimeError:
                pass


class DashboardView(QWidget):
    def __init__(self, app, game_id):
        super().__init__()
        self.app = app
        self.game_id = game_id
        self.setStyleSheet("background: transparent;")
        self._art_widget = None
        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setSpacing(12)
        self._layout.setContentsMargins(30, 20, 30, 20)
        self._build()

    def _build(self):
        data = self.app.config_data[self.game_id]
        layout = self._layout

        art = data.get("art")
        if art and os.path.exists(art):
            aw = ArtworkWidget(art, 300, 400)
            self._art_widget = aw
            layout.addWidget(aw, alignment=Qt.AlignmentFlag.AlignCenter)

        name = data.get("name", "Unknown")
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {c.ACCENT}; font: bold 26px;")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_lbl)

        meta_parts = []
        pt = data.get("playtime")
        if pt:
            meta_parts.append(format_playtime(pt))
        rt = relative_time(data.get("last_played"))
        if rt:
            meta_parts.append(f"Last played {rt}")
        lc = data.get("launch_count", 0)
        if lc:
            meta_parts.append(f"{lc} launch{'s' if lc != 1 else ''}")
        meta_lbl = QLabel("  \u2022  ".join(meta_parts) if meta_parts else "Never played")
        meta_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 13px;")
        meta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(meta_lbl)

        play_btn = QPushButton("PLAY")
        play_btn.setFixedHeight(52)
        play_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.SUCCESS}; color: white; font: bold 18px;
                           border-radius: 10px; }}
            QPushButton:hover {{ background: {c.get_dimmed_accent(c.SUCCESS, 0.8)}; }}
        """)
        play_btn.clicked.connect(lambda: self.app.try_launch_game())
        self.app.play_btn = play_btn
        if self.app.game_process_manager.is_playing and self.app.current_game_id == self.game_id:
            play_btn.setText("STOP")
            play_btn.setStyleSheet(f"""
                QPushButton {{ background: {c.DANGER}; color: white; font: bold 18px;
                               border-radius: 10px; }}
                QPushButton:hover {{ background: {c.get_dimmed_accent(c.DANGER, 0.8)}; }}
            """)
        layout.addWidget(play_btn)

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

        art_actions = QHBoxLayout()
        art_actions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art_actions.setSpacing(12)

        gen_btn = QPushButton("Generate Art")
        gen_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.SUCCESS}; font: bold 11px;
                           border: 1px solid {c.SUCCESS}; border-radius: 6px;
                           padding: 6px 14px; }}
            QPushButton:hover {{ background: {c.get_dimmed_accent(c.SUCCESS, 0.3)}; color: {c.TXT_MAIN}; }}
        """)
        gen_btn.clicked.connect(self._generate_art)
        art_actions.addWidget(gen_btn)

        if art and os.path.exists(art):
            rm_btn = QPushButton("Remove Artwork")
            rm_btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {c.DANGER}; font: bold 11px;
                               border: 1px solid {c.DANGER}; border-radius: 6px;
                               padding: 6px 14px; }}
                QPushButton:hover {{ background: {c.DANGER_HOVER}; color: {c.TXT_MAIN}; }}
            """)
            rm_btn.clicked.connect(self._remove_artwork)
            art_actions.addWidget(rm_btn)

        layout.addLayout(art_actions)

        notes = data.get("notes", "")
        if notes:
            notes_frame = QFrame()
            notes_frame.setStyleSheet(f"""
                QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_INPUT};
                          border-radius: 10px; padding: 12px; }}
            """)
            n_l = QVBoxLayout(notes_frame)
            notes_lbl = QLabel(notes)
            notes_lbl.setWordWrap(True)
            notes_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: 12px;")
            n_l.addWidget(notes_lbl)
            layout.addWidget(notes_frame)

        self._details_visible = False
        self._details_btn = QPushButton("DETAILS  \u25be")
        self._details_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.TXT_DIM}; font: bold 11px;
                           border: 1px solid {c.BG_INPUT}; border-radius: 6px;
                           padding: 6px 18px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN};
                                 border: 1px solid {c.ACCENT}; }}
        """)
        self._details_btn.clicked.connect(self._toggle_details)
        layout.addWidget(self._details_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._details_frame = QFrame()
        self._details_frame.setStyleSheet(f"""
            QFrame {{ border: 1px solid {c.BG_INPUT}; border-radius: 10px;
                       background: {c.BG_PANEL}; padding: 12px; }}
        """)
        details_layout = QVBoxLayout(self._details_frame)
        details_layout.setSpacing(6)

        fields = [
            ("Exe", data.get("exe", "")),
            ("Prefix", data.get("prefix", "")),
            ("Proton", data.get("proton", "Default (UMU Internal)")),
            ("Store", data.get("store", "none")),
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
            details_layout.addLayout(row)

        self._details_frame.hide()
        layout.addWidget(self._details_frame)

        layout.addStretch(1)

    def _toggle_details(self):
        self._details_visible = not self._details_visible
        self._details_frame.setVisible(self._details_visible)
        self._details_btn.setText("DETAILS  \u25b4" if self._details_visible else "DETAILS  \u25be")
        if self.app.engine:
            self.app.engine.rescan()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
                continue
            sub = item.layout()
            if sub is not None:
                self._clear_layout(sub)
                sub.deleteLater()

    def _rebuild(self):
        self._clear_layout(self._layout)
        self._build()

    def refresh(self):
        self._rebuild()

    def hideEvent(self, event):
        super().hideEvent(event)
        if getattr(self, '_art_widget', None):
            try:
                self._art_widget.stop()
            except RuntimeError:
                pass

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
        if self.app.engine:
            self.app.engine.rescan()

    def _remove_artwork(self):
        data = self.app.config_data[self.game_id]
        data["art"] = ""
        self.app.config_manager.save_data(self.app.config_data)
        self.app.show_dashboard(self.game_id)

    def _generate_art(self):
        data = self.app.config_data[self.game_id]
        from launcher_pyqt.utils import generate_placeholder_art
        path = generate_placeholder_art(self.game_id, data.get("name", "New Game"),
                                        c.ACCENT, c.BG_PANEL,
                                        str(self.app.artwork_manager.artwork_dir))
        if path:
            data["art"] = path
            self.app.config_manager.save_data(self.app.config_data)
            self.app.show_dashboard(self.game_id)
