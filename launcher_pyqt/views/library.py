import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QGridLayout, QLineEdit, QPushButton)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath
from launcher_pyqt.artworkImage import GameImage
from launcher_pyqt.utils import format_playtime
import colors as c


class PosterWidget(QWidget):
    clicked = pyqtSignal(str)
    right_clicked = pyqtSignal(str)

    def __init__(self, g_id, data, w, h):
        super().__init__()
        self.game_id = g_id
        self.game_image = None
        self._focused = False
        self.is_running = False
        self._zoom = 0.92
        self._zoom_anim = None
        self.setFixedSize(w, h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        art = data.get("art") or data.get("art_land")
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

    def _get_zoom(self):
        return self._zoom

    def _set_zoom(self, v):
        self._zoom = v
        self.update()

    zoom = pyqtProperty(float, _get_zoom, _set_zoom)

    def set_running(self, state):
        self.is_running = bool(state)
        self.update()

    def set_focused(self, state):
        self._focused = state
        self._animate_zoom(1.0 if state else 0.92)
        self.update()

    def _animate_zoom(self, target):
        anim = getattr(self, '_zoom_anim', None)
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:
                pass
        self._zoom_anim = QPropertyAnimation(self, b"zoom")
        self._zoom_anim.setDuration(180)
        self._zoom_anim.setEndValue(target)
        self._zoom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._zoom_anim.start()

    def stop_animations(self):
        anim = getattr(self, '_zoom_anim', None)
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:
                pass
            self._zoom_anim = None
        self._zoom = 0.92
        if self.game_image:
            try:
                self.game_image.stop()
            except RuntimeError:
                pass

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        z = self._zoom
        r = self.rect()
        wz, hz = int(r.width() * z), int(r.height() * z)
        draw_rect = QRectF(r.center().x() - wz / 2.0, r.center().y() - hz / 2.0, wz, hz)
        radius = 12.0 * z
        path = QPainterPath()
        path.addRoundedRect(draw_rect, radius, radius)
        p.setClipPath(path)
        p.fillRect(draw_rect, QColor(c.BG_INPUT))
        if self.bg_pix and not self.bg_pix.isNull():
            scaled = self.bg_pix.scaled(wz, hz,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(draw_rect.toRect(), scaled)
        else:
            p.setPen(QColor(c.TXT_DIM))
            font = p.font()
            font.setPointSize(28)
            p.setFont(font)
            p.drawText(draw_rect, Qt.AlignmentFlag.AlignCenter, "\U0001f3ae")
        if self._focused:
            p.setPen(QPen(QColor(c.ACCENT), max(1, int(3 * z))))
            p.drawRoundedRect(1, 1, r.width() - 2, r.height() - 2, radius, radius)
        if self.is_running:
            badge_h = 18
            badge_w = int(badge_h * 5.0)
            badge_rect = QRectF(draw_rect.right() - badge_w - 6, draw_rect.top() + 6, badge_w, badge_h)
            bpath = QPainterPath()
            bpath.addRoundedRect(badge_rect, badge_h / 2.0, badge_h / 2.0)
            p.fillPath(bpath, QColor(c.SUCCESS))
            p.setPen(QColor("#ffffff"))
            font = p.font()
            font.setPointSize(7)
            font.setBold(True)
            p.setFont(font)
            p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "\u25b6 RUNNING")
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.game_id)
        else:
            self.clicked.emit(self.game_id)


class LibraryView(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setStyleSheet("background: transparent;")
        self.grid = None
        self._scroll_area = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._first_show = False
        self._sig = None
        self.search_text = ""
        self._cards = []
        self._reflow_pending = False
        self._reflow_on_resize = True
        self._build()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._first_show:
            self._first_show = True
            QTimer.singleShot(30, self._rebuild)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_animations()

    def _stop_animations(self):
        if not self.grid:
            return
        for w in self.grid.findChildren(QWidget):
            if isinstance(w, PosterWidget):
                w.stop_animations()
            elif hasattr(w, 'game_image') and w.game_image:
                try:
                    w.game_image.stop()
                except RuntimeError:
                    pass

    def _update_running_badges(self):
        running = self.app.game_process_manager.current_running_game_id
        for w in self.findChildren(PosterWidget):
            w.set_running(w.game_id == running)

    def _data_sig(self):
        parts = []
        for gid, d in sorted(self.app.config_data.items()):
            if gid == "settings":
                continue
            parts.append((gid, d.get("name"), d.get("art"), d.get("art_land"),
                          d.get("playtime"), d.get("last_played"),
                          d.get("favorite"), d.get("launch_count")))
        return tuple(parts)

    def refresh(self):
        if self._data_sig() != self._sig:
            self._rebuild()

    def _get_sorted_games(self):
        games = [(g_id, data) for g_id, data in self.app.config_data.items() if g_id != "settings"]
        q = self.search_text.strip().lower()
        if q:
            games = [(g_id, d) for g_id, d in games if q in d.get("name", "").lower()]
        games.sort(key=lambda g: g[1].get("name", "").lower())
        return games

    def _build(self):
        self._sig = self._data_sig()
        self.grid = None
        self._scroll_area = None
        self._cards = []
        header = QHBoxLayout()
        header.setContentsMargins(20, 8, 20, 8)
        header.setSpacing(10)

        self._search = QLineEdit()
        self._search.setText(self.search_text)
        self._search.setPlaceholderText("Search games...")
        self._search.setClearButtonEnabled(True)
        self._search.setFixedHeight(34)
        self._search.setStyleSheet(f"""
            QLineEdit {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 13px;
                         border-radius: 8px; padding: 6px 12px;
                         border: 1px solid {c.BG_INPUT}; }}
            QLineEdit:focus {{ border: 1px solid {c.ACCENT}; }}
        """)
        self._search.textChanged.connect(self._on_search_changed)
        header.addWidget(self._search, 1)

        add_btn = QPushButton("+")
        add_btn.setToolTip("Add a game")
        add_btn.setFixedSize(34, 34)
        add_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.SUCCESS}; color: #ffffff; font: bold 20px;
                           border-radius: 17px; border: none; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        add_btn.clicked.connect(self.app.open_add_game)
        header.addWidget(add_btn)

        self._header_nav = [self._search, add_btn]

        self._stats_lbl = QLabel()
        self._stats_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 11px; background: transparent;")
        header.addWidget(self._stats_lbl)

        header_w = QWidget()
        header_w.setLayout(header)
        header_w.setFixedHeight(50)
        self._layout.addWidget(header_w)

        games = self._get_sorted_games()
        if games:
            n = len(games)
            self._stats_lbl.setText(f"{n} {'game' if n == 1 else 'games'}")
        if not games:
            empty = QLabel("No games found.\nPress + to add a game or adjust your filter/search.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {c.TXT_DIM}; font: 16px;")
            self._layout.addWidget(empty)
            if self.app.engine:
                QTimer.singleShot(0, self.app.engine.rescan)
            return

        if not self.app.current_game_id and games:
            self.app.current_game_id = games[0][0]

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_inner = QWidget()
        scroll_inner.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_inner)
        scroll_layout.setContentsMargins(20, 10, 20, 20)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.grid = QWidget()
        self.grid.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(self.grid)
        grid_layout.setSpacing(12)
        sidebar_w = 0
        avail = max(400, self.app._content_area.width() - sidebar_w - 40)
        spacing = 12
        poster_w = min(170, max(130, (avail - spacing * 3) // 5))
        self.num_cols = max(2, (avail + spacing) // (poster_w + spacing))
        num_cols = self.num_cols
        poster_h = int(poster_w * 1.4)

        for i, (g_id, data) in enumerate(games):
            card = QWidget()
            card.setStyleSheet("background: transparent;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(4)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            poster = PosterWidget(g_id, data, poster_w, poster_h)
            poster.set_running(g_id == self.app.game_process_manager.current_running_game_id)
            poster.clicked.connect(self.app.show_dashboard)
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
            self._cards.append(card)

        scroll_layout.addWidget(self.grid)
        self._scroll_area.setWidget(scroll_inner)
        self._layout.addWidget(self._scroll_area)

        if self.app.engine:
            QTimer.singleShot(0, self.app.engine.rescan)

    def _animate_scroll(self, target_value):
        if not self._scroll_area:
            return
        sb = self._scroll_area.verticalScrollBar()
        cur = sb.value()
        if abs(target_value - cur) < 2:
            return
        if not hasattr(self, '_scroll_anim') or self._scroll_anim is None:
            self._scroll_anim = QPropertyAnimation(sb, b"value")
            self._scroll_anim.setDuration(180)
            self._scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_anim.stop()
        self._scroll_anim.setStartValue(cur)
        self._scroll_anim.setEndValue(target_value)
        self._scroll_anim.start()

    def scroll_to_item(self, index):
        if self._scroll_area and self.app.engine and 0 <= index < len(self.app.engine.nav_list):
            target = self.app.engine.nav_list[index]
            if hasattr(target, 'game_id'):
                sb = self._scroll_area.verticalScrollBar()
                origin = target.mapTo(self._scroll_area.widget(), target.rect().topLeft())
                top_y = origin.y()
                bottom_y = origin.y() + target.height()
                view_h = self._scroll_area.viewport().height()
                margin = 60
                val = sb.value()
                if top_y < val + margin:
                    target_val = max(0, top_y - margin)
                elif bottom_y > val + view_h - margin:
                    target_val = min(sb.maximum(), bottom_y - view_h + margin)
                else:
                    return
                self._animate_scroll(target_val)

    def scroll_to_letter(self, letter):
        letter = letter.lower()
        for i, card in enumerate(self._cards):
            poster = card.findChild(PosterWidget)
            if not poster or not poster.game_id:
                continue
            name = self.app.config_data.get(poster.game_id, {}).get("name", "").lower()
            if name.startswith(letter):
                if self._scroll_area:
                    sb = self._scroll_area.verticalScrollBar()
                    origin = card.mapTo(self._scroll_area.widget(), card.rect().topLeft())
                    top_y = origin.y()
                    bottom_y = origin.y() + card.height()
                    view_h = self._scroll_area.viewport().height()
                    val = sb.value()
                    margin = 60
                    if top_y < val + margin:
                        target_val = max(0, top_y - margin)
                    elif bottom_y > val + view_h - margin:
                        target_val = min(sb.maximum(), bottom_y - view_h + margin)
                    else:
                        target_val = None
                    if target_val is not None:
                        self._animate_scroll(target_val)
                if self.app.engine:
                    tabs = getattr(self.app.engine, '_tabs_btn_count', 0)
                    header = getattr(self, '_header_nav', None) or []
                    base = tabs + len(header)
                    self.app.engine.nav_index = min(base + i, max(0, len(self.app.engine.nav_list) - 1))
                    self.app.engine.sync_visuals()
                break

    def _on_search_changed(self, text):
        had_focus = hasattr(self, '_search') and self._search.hasFocus()
        cursor = self._search.cursorPosition() if had_focus else 0
        scroll = self._scroll_area.verticalScrollBar().value() if self._scroll_area else 0
        osk = getattr(self.app, 'on_screen_keyboard', None)
        osk_targeting = (osk is not None and osk.isVisible()
                         and getattr(osk, '_last_target', None) is self._search)
        self.search_text = text
        self._rebuild()
        if (had_focus or osk_targeting) and hasattr(self, '_search'):
            search = self._search
            if osk_targeting and not had_focus:
                cursor = len(search.text())
            QTimer.singleShot(0, lambda: (search.setFocus(), search.setCursorPosition(cursor)))
        if self._scroll_area:
            QTimer.singleShot(0, lambda: self._restore_scroll(scroll))

    def _restore_scroll(self, scroll):
        if self._scroll_area:
            sb = self._scroll_area.verticalScrollBar()
            if sb.maximum() >= scroll:
                sb.setValue(scroll)

    def toggle_favorite(self):
        gid = self.app._focused_game_id()
        if not gid:
            return
        self.app.toggle_favorite_for(gid)

    def _rebuild(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._build()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._reflow_pending:
            return
        self._reflow_pending = True
        QTimer.singleShot(0, self._do_reflow)

    def _do_reflow(self):
        self._reflow_pending = False
        self._reflow_grid()

    def _reflow_grid(self):
        if not self._cards or not self.grid:
            return
        sa = self._scroll_area
        avail = sa.viewport().width() if sa else self.width()
        if avail < 100:
            return
        first = self._cards[0].findChild(PosterWidget)
        pw = first.width() if first else 170
        spacing = 12
        new_cols = max(2, (avail + spacing) // (pw + spacing))
        if new_cols == self.num_cols:
            return
        self.num_cols = new_cols
        gl = self.grid.layout()
        for i, card in enumerate(self._cards):
            gl.addWidget(card, i // new_cols, i % new_cols)
