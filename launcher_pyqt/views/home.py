"""Home tab: recent-games carousel with A-Z quick-jump and empty states."""
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath, QLinearGradient
from launcher_pyqt.artworkImage import GameImage
import colors as c

A_TO_Z = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

_ZOOM_OFF = 0.92
_ZOOM_ON = 1.0


def _zoom_mixin_setup(obj, w, h):
    """Shared zoom-animation state for carousel posters (mirrors library)."""
    obj._zoom = _ZOOM_OFF
    obj._zoom_anim = None
    obj.game_image = None
    obj.setFixedSize(w, h)
    obj.setCursor(Qt.CursorShape.PointingHandCursor)
    obj.setStyleSheet("QPushButton { border: none; background: transparent; }")


def _zoom_prop(obj, value):
    obj._zoom = value
    obj.update()


def _animate_zoom(obj, target):
    anim = getattr(obj, '_zoom_anim', None)
    if anim is not None:
        try:
            anim.stop()
        except RuntimeError:
            pass
    obj._zoom_anim = QPropertyAnimation(obj, b"zoom")
    obj._zoom_anim.setDuration(180)
    obj._zoom_anim.setEndValue(target)
    obj._zoom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    obj._zoom_anim.start()


def _stop_animations(obj):
    anim = getattr(obj, '_zoom_anim', None)
    if anim is not None:
        try:
            anim.stop()
        except RuntimeError:
            pass
        obj._zoom_anim = None
    obj._zoom = _ZOOM_OFF
    gi = getattr(obj, 'game_image', None)
    if gi is not None:
        try:
            gi.stop()
        except RuntimeError:
            pass


class FeaturedPoster(QPushButton):
    """Wide Steam-style banner for the most recently played game (first
    carousel entry). Paints landscape art cover-scaled with the game name in
    a bottom scrim; zooms + runs GameImage on focus like the other posters."""

    def __init__(self, g_id, data, w, h):
        super().__init__()
        self.game_id = g_id
        self._focused = False
        self.is_running = False
        _zoom_mixin_setup(self, w, h)
        self.name = data.get("name", "")
        art = data.get("art_land") or data.get("art")
        self.bg_pix = None
        if art and os.path.exists(art):
            pix = QPixmap(art)
            if not pix.isNull():
                self.bg_pix = pix.scaled(w, h,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
            ext = os.path.splitext(art)[1].lower()
            if ext in ('.webp', '.gif'):
                gi = GameImage(self, art, w, h, quality=75)
                gi.hide()
                self.game_image = gi

    def _get_zoom(self):
        return self._zoom

    def _set_zoom(self, v):
        _zoom_prop(self, v)

    zoom = pyqtProperty(float, _get_zoom, _set_zoom)

    def set_running(self, state):
        self.is_running = bool(state)
        self.update()

    def set_focused(self, state):
        self._focused = bool(state)
        _animate_zoom(self, _ZOOM_ON if state else _ZOOM_OFF)
        self.update()

    def stop_animations(self):
        _stop_animations(self)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        z = self._zoom
        r = self.rect()
        wz, hz = int(r.width() * z), int(r.height() * z)
        draw_rect = QRectF(r.center().x() - wz / 2.0, r.center().y() - hz / 2.0, wz, hz)
        radius = 14.0 * z
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
            grad = QLinearGradient(0, 0, wz, hz)
            grad.setColorAt(0.0, QColor(c.ACCENT).darker(220))
            grad.setColorAt(0.6, QColor(c.BG_PANEL))
            p.fillRect(draw_rect, grad)
            glow = QColor(c.ACCENT)
            glow.setAlpha(50)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawEllipse(int(draw_rect.center().x() - wz * 0.22),
                          int(draw_rect.top() - hz * 0.15),
                          int(wz * 0.44), int(wz * 0.44))
        p.setClipping(False)
        scrim = QLinearGradient(0, draw_rect.bottom() - hz * 0.42, 0, draw_rect.bottom())
        scrim.setColorAt(0.0, QColor(0, 0, 0, 0))
        scrim.setColorAt(1.0, QColor(0, 0, 0, 170))
        p.fillRect(QRectF(draw_rect.left(), draw_rect.bottom() - hz * 0.42,
                          draw_rect.width(), hz * 0.42), scrim)
        if self.name:
            font = p.font()
            font.setPointSize(int(17 * z))
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(draw_rect.left() + 16, draw_rect.bottom() - 40,
                              draw_rect.width() - 32, 28),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.name)
        if self.is_running:
            badge_h = 18
            badge_w = int(badge_h * 5.0)
            badge_rect = QRectF(draw_rect.right() - badge_w - 8, draw_rect.top() + 8, badge_w, badge_h)
            bpath = QPainterPath()
            bpath.addRoundedRect(badge_rect, badge_h / 2.0, badge_h / 2.0)
            p.fillPath(bpath, QColor(c.SUCCESS))
            p.setPen(QColor("#ffffff"))
            font = p.font()
            font.setPointSize(7)
            font.setBold(True)
            p.setFont(font)
            p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "\u25b6 RUNNING")
        if self._focused:
            p.setPen(QPen(QColor(c.ACCENT), max(1, int(3 * z))))
            p.drawRoundedRect(QRectF(draw_rect.adjusted(1, 1, -1, -1)), radius, radius)
        p.end()


class HomePoster(QPushButton):
    """A poster that participates in list-mode nav (QPushButton) and paints
    the game art. A/Enter opens the game's dashboard. Zooms + animates on
    focus like library posters."""

    def __init__(self, g_id, data, w, h):
        super().__init__()
        self.game_id = g_id
        self._focused = False
        self.is_running = False
        _zoom_mixin_setup(self, w, h)
        art = data.get("art") or data.get("art_land")
        self.bg_pix = None
        if art and os.path.exists(art):
            pix = QPixmap(art)
            if not pix.isNull():
                self.bg_pix = pix.scaled(w, h,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
            ext = os.path.splitext(art)[1].lower()
            if ext in ('.webp', '.gif'):
                gi = GameImage(self, art, w, h, quality=75)
                gi.hide()
                self.game_image = gi

    def _get_zoom(self):
        return self._zoom

    def _set_zoom(self, v):
        _zoom_prop(self, v)

    zoom = pyqtProperty(float, _get_zoom, _set_zoom)

    def set_running(self, state):
        self.is_running = bool(state)
        self.update()

    def set_focused(self, state):
        self._focused = bool(state)
        _animate_zoom(self, _ZOOM_ON if state else _ZOOM_OFF)
        self.update()

    def stop_animations(self):
        _stop_animations(self)

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
            font.setPointSize(int(26 * z))
            p.setFont(font)
            p.drawText(draw_rect, Qt.AlignmentFlag.AlignCenter, "\U0001f3ae")
        p.setClipping(False)
        if self._focused:
            p.setPen(QPen(QColor(c.ACCENT), max(1, int(3 * z))))
            p.drawRoundedRect(QRectF(draw_rect.adjusted(1, 1, -1, -1)), radius, radius)
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


_browse_pixmap = None

def _load_browse_pixmap():
    global _browse_pixmap
    if _browse_pixmap is not None:
        return _browse_pixmap
    p = os.path.join(os.path.dirname(__file__), "..", "..", "resources", "HOME_ALLGAMES.png")
    p = os.path.normpath(p)
    if os.path.exists(p):
        _browse_pixmap = QPixmap(p)
    return _browse_pixmap


class BrowsePoster(QPushButton):
    """'Browse Library' tile appended last in the carousel, uses a static
    image from resources. A/Enter opens the library."""

    def __init__(self, w, h):
        super().__init__()
        self.game_id = None
        self._focused = False
        self.bg_pix = None
        _zoom_mixin_setup(self, w, h)
        pix = _load_browse_pixmap()
        if pix and not pix.isNull():
            self.bg_pix = pix.scaled(w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)

    def _get_zoom(self):
        return self._zoom

    def _set_zoom(self, v):
        _zoom_prop(self, v)

    zoom = pyqtProperty(float, _get_zoom, _set_zoom)

    def set_focused(self, state):
        self._focused = bool(state)
        _animate_zoom(self, _ZOOM_ON if state else _ZOOM_OFF)
        self.update()

    def stop_animations(self):
        _stop_animations(self)

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
            font.setPointSize(int(10 * z))
            font.setBold(True)
            p.setFont(font)
            p.drawText(draw_rect, Qt.AlignmentFlag.AlignCenter, "ALL GAMES")
        p.setClipping(False)
        if self._focused:
            p.setPen(QPen(QColor(c.ACCENT), max(1, int(3 * z))))
            p.drawRoundedRect(QRectF(draw_rect.adjusted(1, 1, -1, -1)), radius, radius)
        p.end()


class HomeView(QWidget):
    _reflow_on_resize = True

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._sig = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(28, 20, 28, 20)
        self._layout.setSpacing(12)
        self._build()

    def _data_sig(self):
        parts = []
        for gid, d in sorted(self.app.config_data.items()):
            if gid == "settings":
                continue
            parts.append((gid, d.get("name"), d.get("art"), d.get("art_land"),
                          d.get("playtime"), d.get("last_played"),
                          d.get("favorite")))
        return tuple(parts)

    def refresh(self):
        if self._data_sig() != self._sig:
            self._rebuild()

    def _recent_games(self):
        games = [(g_id, d) for g_id, d in self.app.config_data.items()
                 if g_id != "settings" and d.get("last_played")]
        games.sort(key=lambda g: float(g[1].get("last_played", "0")), reverse=True)
        return games[:10]

    def _update_running_badges(self):
        running = self.app.game_process_manager.current_running_game_id
        for w in self.findChildren(HomePoster):
            w.set_running(w.game_id == running)
        for w in self.findChildren(FeaturedPoster):
            w.set_running(w.game_id == running)

    def hideEvent(self, event):
        super().hideEvent(event)
        for w in self.findChildren(HomePoster):
            w.stop_animations()
        for w in self.findChildren(FeaturedPoster):
            w.stop_animations()
        for w in self.findChildren(BrowsePoster):
            w.stop_animations()

    def _clear_layout(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _build(self):
        self._sig = self._data_sig()
        self._clear_layout()

        self.setStyleSheet(f"background: {c.BG_MAIN};")

        title = QLabel("Home")
        title.setStyleSheet(
            f"color: {c.TXT_MAIN}; font-size: 26px; font-weight: 700; background: transparent;")
        self._layout.addWidget(title)

        games = [(g_id, d) for g_id, d in self.app.config_data.items() if g_id != "settings"]
        if not games:
            empty = QLabel("Your library is empty.\nAdd a game to get started.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {c.TXT_DIM}; font-size: 16px; background: transparent;")
            self._layout.addWidget(empty, 1)
            add_btn = QPushButton("+  Add a Game")
            add_btn.setFixedHeight(44)
            add_btn.setStyleSheet(f"""
                QPushButton {{ background: {c.SUCCESS}; color: #ffffff; font: bold 15px;
                               border-radius: 10px; border: none; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
            """)
            add_btn.clicked.connect(self.app.open_add_game)
            self._layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignCenter)
            self._btn_browse = add_btn
            self._carousel_area = None
            if self.app.engine:
                QTimer.singleShot(0, self.app.engine.rescan)
            return

        recents = self._recent_games()
        if recents:
            lbl = QLabel("RECENTLY PLAYED")
            lbl.setStyleSheet(f"color: {c.ACCENT}; font: bold 12px; background: transparent;")
            self._layout.addWidget(lbl)

            self._carousel_area = QScrollArea()
            self._carousel_area.setWidgetResizable(False)
            self._carousel_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._carousel_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._carousel_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            inner = QWidget()
            inner.setStyleSheet("background: transparent;")
            row = QHBoxLayout(inner)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)
            row.addStretch(1)
            cw = min(180, max(130, self.app._content_area.width() // 6))
            ch = int(cw * 1.4)
            total = 0
            for idx, (g_id, data) in enumerate(recents):
                if idx == 0:
                    fw = int(ch * 2.6)
                    poster = FeaturedPoster(g_id, data, fw, ch)
                    total += fw
                else:
                    poster = HomePoster(g_id, data, cw, ch)
                    total += cw
                poster.clicked.connect(lambda checked=False, gid=g_id: self.app.show_dashboard(gid))
                row.addWidget(poster)
                if idx < len(recents) - 1:
                    total += 12
            browse = BrowsePoster(cw, ch)
            browse.clicked.connect(self.app.show_library)
            row.addWidget(browse)
            total += cw + 12
            row.addStretch(1)
            self._carousel_total = total
            self._carousel_inner = inner
            self._carousel_area.setWidget(inner)
            self._layout.addWidget(self._carousel_area, 1)
            QTimer.singleShot(0, self._center_carousel)
        else:
            self._carousel_area = None
            msg = QLabel("No recently played games yet.\nLaunch something from the library!")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet(f"color: {c.TXT_DIM}; font-size: 15px; background: transparent;")
            self._layout.addWidget(msg, 1)
            self._btn_browse = QPushButton("Browse Library")
            self._btn_browse.setFixedHeight(38)
            self._btn_browse.setStyleSheet(f"""
                QPushButton {{ background: {c.SURFACE}; color: {c.TXT_MAIN}; font: 14px;
                               border-radius: 9px; padding: 6px 20px;
                               border: 1px solid {c.BORDER}; }}
                QPushButton:hover {{ background: {c.SURFACE_HOVER}; }}
            """)
            self._btn_browse.clicked.connect(self.app.show_library)
            self._layout.addWidget(self._btn_browse, 0, Qt.AlignmentFlag.AlignCenter)

        a_z_w = QWidget()
        a_z_w.setStyleSheet("background: transparent;")
        a_z_lay = QHBoxLayout(a_z_w)
        a_z_lay.setContentsMargins(0, 6, 0, 0)
        a_z_lay.setSpacing(2)
        for letter in A_TO_Z:
            b = QPushButton(letter)
            b._mouse_only = True
            b.setFixedSize(26, 26)
            b.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {c.TXT_DIM};
                               font: bold 9px; border: none; border-radius: 13px; }}
                QPushButton:hover {{ background: {c.BG_FOCUS}; color: {c.TXT_MAIN}; }}
            """)
            b.clicked.connect(lambda checked=False, ch=letter: self.app.jump_to_letter(ch))
            a_z_lay.addWidget(b)
        a_z_lay.addStretch(1)
        self._layout.addWidget(a_z_w)

        if self.app.engine:
            QTimer.singleShot(0, self.app.engine.rescan)

    def _rebuild(self):
        self._build()

    def _center_carousel(self):
        """Center the carousel row: the inner widget spans at least the
        viewport width (so the row centers when content is narrower) and
        exactly the content width when the row overflows (so it scrolls)."""
        inner = getattr(self, '_carousel_inner', None)
        total = getattr(self, '_carousel_total', 0)
        if inner is None or total <= 0:
            return
        try:
            avail = self.app._content_area.width() - 56
        except RuntimeError:
            avail = self.width()
        if avail <= 0:
            avail = self.width()
        if avail <= 0:
            return
        inner.setFixedWidth(max(total, avail))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._center_carousel()
