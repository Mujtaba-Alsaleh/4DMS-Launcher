import time, os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath
from launcher_pyqt.artworkImage import GameImage
from launcher_pyqt.utils import format_playtime, relative_time
import colors as c

SORT_OPTIONS = ["Last Played", "Name", "Play Count", "Date Added"]
FILTER_OPTIONS = ["All", "Favorites", "Recent"]


class PosterWidget(QWidget):
    clicked = pyqtSignal(str)
    right_clicked = pyqtSignal(str)

    def __init__(self, g_id, data, w, h):
        super().__init__()
        self.game_id = g_id
        self.game_image = None
        self._focused = False
        self.setFixedSize(w, h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        art = data.get("art")
        if art and os.path.exists(art):
            self.bg_pix = QPixmap(art)
            if not self.bg_pix.isNull():
                self.bg_pix = self.bg_pix.scaled(w, h,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
            ext = os.path.splitext(art)[1].lower()
            if ext in ('.webp', '.gif'):
                gi = GameImage(self, art, w, h, quality=75)
                gi.hide()
                self.game_image = gi
        else:
            self.bg_pix = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        path = QPainterPath()
        path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), 12, 12)
        p.setClipPath(path)
        p.fillRect(r, QColor(c.BG_INPUT))
        if self.bg_pix and not self.bg_pix.isNull():
            p.drawPixmap(r, self.bg_pix)
        else:
            p.setPen(QColor(c.TXT_DIM))
            font = p.font()
            font.setPointSize(28)
            p.setFont(font)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "\U0001f3ae")
        if self._focused:
            p.setPen(QPen(QColor(c.ACCENT), 3))
            p.drawRoundedRect(1, 1, r.width() - 2, r.height() - 2, 12, 12)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.game_id)
        else:
            self.clicked.emit(self.game_id)

    def set_focused(self, state):
        self._focused = state
        self.update()


class LibraryView(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setStyleSheet("background: transparent;")
        self.sort_mode = "Last Played"
        self.filter_mode = "All"
        self.grid = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._build()

    def _get_sorted_games(self):
        games = [(g_id, data) for g_id, data in self.app.config_data.items() if g_id != "settings"]
        if self.filter_mode == "Favorites":
            games = [(g_id, d) for g_id, d in games if d.get("favorite")]
        elif self.filter_mode == "Recent":
            cutoff = time.time() - (7 * 86400)
            games = [(g_id, d) for g_id, d in games
                     if d.get("last_played") and float(d.get("last_played", "0")) > cutoff]
        if self.sort_mode == "Name":
            games.sort(key=lambda g: g[1].get("name", "").lower())
        elif self.sort_mode == "Play Count":
            games.sort(key=lambda g: g[1].get("launch_count", 0), reverse=True)
        elif self.sort_mode == "Date Added":
            games.sort(key=lambda g: g[1].get("added_at", "0"), reverse=True)
        else:
            games.sort(key=lambda g: g[1].get("last_played", "0"), reverse=True)
        return games

    def _build(self):
        header = QHBoxLayout()
        self.sort_label = QLabel(f"Sort: {self.sort_mode}  |  Filter: {self.filter_mode}")
        self.sort_label.setStyleSheet(f"color: {c.ACCENT}; font: bold 12px;")
        header.addWidget(self.sort_label)
        header.addStretch()
        header_w = QWidget()
        header_w.setLayout(header)
        header_w.setFixedHeight(40)
        self._layout.addWidget(header_w)

        games = self._get_sorted_games()
        if not games:
            empty = QLabel("No games found.\nPress + to add a game or adjust your filter.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {c.TXT_DIM}; font: 16px;")
            self._layout.addWidget(empty)
            if self.app.engine:
                self.app.engine.rebuild_nav_map()
            return

        if not self.app.current_game_id and games:
            self.app.current_game_id = games[0][0]

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_inner = QWidget()
        scroll_inner.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_inner)
        scroll_layout.setContentsMargins(20, 10, 20, 20)

        recent_games = []
        if self.sort_mode == "Last Played" and self.filter_mode == "All":
            recent_games = [(g_id, d) for g_id, d in games if d.get("last_played")][:5]

        if recent_games:
            recent_lbl = QLabel("RECENTLY PLAYED")
            recent_lbl.setStyleSheet(f"color: {c.ACCENT}; font: bold 12px;")
            scroll_layout.addWidget(recent_lbl)

            recent_row = QHBoxLayout()
            recent_row.setSpacing(8)
            rp_w = 110
            rp_h = int(rp_w * 1.43)
            for g_id, data in recent_games:
                card = QWidget()
                card.setStyleSheet("background: transparent;")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(0, 0, 0, 0)
                card_layout.setSpacing(4)
                card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

                poster = PosterWidget(g_id, data, rp_w, rp_h)
                poster.clicked.connect(self._quick_launch)
                poster.right_clicked.connect(self.app.show_dashboard)
                card_layout.addWidget(poster)

                name_lbl = QLabel(data.get('name', '').upper())
                name_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 10px;")
                name_lbl.setWordWrap(True)
                name_lbl.setFixedWidth(rp_w)
                card_layout.addWidget(name_lbl)

                rt = relative_time(data.get('last_played'))
                if rt:
                    time_lbl = QLabel(rt)
                    time_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 9px;")
                    card_layout.addWidget(time_lbl)

                recent_row.addWidget(card)
            recent_row_w = QWidget()
            recent_row_w.setLayout(recent_row)
            scroll_layout.addWidget(recent_row_w)
            scroll_layout.addSpacing(16)

        self.grid = QWidget()
        self.grid.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(self.grid)
        grid_layout.setSpacing(20)
        num_cols = 5
        poster_w = 170
        poster_h = 238

        for i, (g_id, data) in enumerate(games):
            card = QWidget()
            card.setStyleSheet("background: transparent;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(4)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            poster = PosterWidget(g_id, data, poster_w, poster_h)
            poster.clicked.connect(self._quick_launch)
            poster.right_clicked.connect(self.app.show_dashboard)
            card_layout.addWidget(poster)

            name_text = data.get('name', '').upper()
            name_lbl = QLabel(name_text)
            name_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 11px;")
            name_lbl.setWordWrap(True)
            name_lbl.setFixedWidth(poster_w)
            card_layout.addWidget(name_lbl)

            pt = data.get('playtime')
            if pt:
                pt_lbl = QLabel(format_playtime(pt))
                pt_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 9px;")
                card_layout.addWidget(pt_lbl)

            grid_layout.addWidget(card, i // num_cols, i % num_cols)

        scroll_layout.addWidget(self.grid)
        scroll.setWidget(scroll_inner)
        self._layout.addWidget(scroll)

    def _quick_launch(self, game_id):
        self.app.current_game_id = game_id
        self.app.game_process_manager.try_launch()

    def scroll_to_item(self, index):
        pass

    def cycle_sort(self):
        idx = SORT_OPTIONS.index(self.sort_mode) if self.sort_mode in SORT_OPTIONS else 0
        self.sort_mode = SORT_OPTIONS[(idx + 1) % len(SORT_OPTIONS)]
        self.app.toast.show(f"Sort: {self.sort_mode}")
        self._rebuild()

    def cycle_filter(self):
        idx = FILTER_OPTIONS.index(self.filter_mode) if self.filter_mode in FILTER_OPTIONS else 0
        self.filter_mode = FILTER_OPTIONS[(idx + 1) % len(FILTER_OPTIONS)]
        self.app.toast.show(f"Filter: {self.filter_mode}")
        self._rebuild()

    def toggle_favorite(self):
        if not self.app.current_game_id:
            return
        game_id = self.app.current_game_id
        current = self.app.config_data[game_id].get("favorite", False)
        self.app.config_data[game_id]["favorite"] = not current
        self.app.config_manager.save_data(self.app.config_data)
        state = "added to" if not current else "removed from"
        self.app.toast.show(f"Favorites: {state}")
        self._rebuild()

    def _rebuild(self):
        for i in reversed(range(self._layout.count())):
            w = self._layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._build()
