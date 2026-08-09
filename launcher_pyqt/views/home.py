"""Home tab: recent-games carousel with A-Z quick-jump and empty states."""
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty, QEvent
from PyQt6.QtGui import (QPixmap, QPainter, QColor, QPen, QPainterPath,
                         QLinearGradient, QImage)
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
        p.setClipping(False)
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
        self.name = data.get("name", "")
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
            grad = QLinearGradient(0, 0, wz, hz)
            grad.setColorAt(0.0, QColor(c.ACCENT).darker(220))
            grad.setColorAt(0.6, QColor(c.BG_PANEL))
            p.fillRect(draw_rect, grad)
            glow = QColor(c.ACCENT)
            glow.setAlpha(50)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawEllipse(int(draw_rect.center().x() - wz * 0.3),
                          int(draw_rect.top() - hz * 0.12),
                          int(wz * 0.6), int(wz * 0.6))
        if self.name:
            scrim = QLinearGradient(0, draw_rect.bottom() - hz * 0.32, 0, draw_rect.bottom())
            scrim.setColorAt(0.0, QColor(0, 0, 0, 0))
            scrim.setColorAt(1.0, QColor(0, 0, 0, 160))
            p.fillRect(QRectF(draw_rect.left(), draw_rect.bottom() - hz * 0.32,
                              draw_rect.width(), hz * 0.32), scrim)
            font = p.font()
            font.setPointSize(int(11 * z))
            font.setBold(True)
            p.setFont(font)
            elided = p.fontMetrics().elidedText(self.name, Qt.TextElideMode.ElideRight,
                                                int(draw_rect.width() - 16))
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(draw_rect.left() + 8, draw_rect.bottom() - 22,
                              draw_rect.width() - 16, 16),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)
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


class HomeBackdrop(QWidget):
    """Steam-style ambient backdrop: blurred art of the focused game, dimmed,
    behind the whole Home view. Blur = cheap downscale-upscale (no
    QGraphicsBlurEffect); crossfades via a paint-driven `fade` property."""

    _FADE_MS = 180

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._art = None
        self._scaled = None
        self._scaled_vw = None
        self._fade = 0.0
        self._fade_anim = None
        self._cache = {}

    def _get_fade(self):
        return self._fade

    def _set_fade(self, v):
        self._fade = v
        self.update()

    fade = pyqtProperty(float, _get_fade, _set_fade)

    def _blur_pixmap(self, path):
        img = QImage(path)
        if img.isNull():
            return None
        small = img.scaled(220, max(1, int(220 * img.height() / max(1, img.width()))),
                           Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                           Qt.TransformationMode.SmoothTransformation)
        return QPixmap.fromImage(small)

    def set_game(self, gid, data):
        target = None
        if gid and data:
            art = data.get("art_land") or data.get("art")
            if art and os.path.exists(art):
                pix = self._cache.get(gid)
                if pix is None:
                    pix = self._blur_pixmap(art)
                    self._cache[gid] = pix
                target = pix
        if target is self._art:
            return
        self._art = target
        self._scaled = None
        self._scaled_vw = None
        self._animate_fade(1.0 if target is not None else 0.0)

    def invalidate_cache(self):
        self._scaled = None
        self._scaled_vw = None

    def _scaled_for(self, w, h):
        art = self._art
        if art is None or art.isNull() or w <= 0 or h <= 0:
            return None
        s = self._scaled
        if s is not None and self._scaled_vw == (w, h):
            return s
        s = art.scaled(w, h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation)
        self._scaled = s
        self._scaled_vw = (w, h)
        return s

    def _animate_fade(self, value):
        anim = getattr(self, '_fade_anim', None)
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:
                pass
        self._fade_anim = QPropertyAnimation(self, b"fade")
        self._fade_anim.setDuration(self._FADE_MS)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.setStartValue(self._fade)
        self._fade_anim.setEndValue(value)
        self._fade_anim.start()

    def stop_animations(self):
        anim = getattr(self, '_fade_anim', None)
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:
                pass
        self._fade_anim = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(c.BG_MAIN))
        if self._art is not None and not self._art.isNull() and self._fade > 0.01:
            r = self.rect()
            scaled = self._scaled_for(r.width(), r.height())
            if scaled is not None:
                p.setOpacity(self._fade * 0.5)
                p.drawPixmap((r.width() - scaled.width()) // 2,
                             (r.height() - scaled.height()) // 2, scaled)
                p.setOpacity(1.0)
        scrim = QColor(c.BG_MAIN)
        scrim.setAlpha(175)
        p.fillRect(self.rect(), scrim)
        p.end()


class HomeView(QWidget):
    _reflow_on_resize = True

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._sig = None
        self._backdrop = HomeBackdrop(self)
        self._backdrop.lower()
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
        try:
            self._backdrop.stop_animations()
        except RuntimeError:
            pass
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

    _FIXED_OVERHEAD = 155

    def _avail_carousel_h(self):
        ca = getattr(self, '_carousel_area', None)
        if ca is not None:
            try:
                if ca.height() > 0:
                    return ca.height()
            except RuntimeError:
                pass
        view_h = self.height()
        if view_h <= 0:
            try:
                view_h = self.app._content_area.height() - 36
            except RuntimeError:
                view_h = 600
        return max(200, view_h - self._FIXED_OVERHEAD)

    def _carousel_sizes(self):
        avail = self._avail_carousel_h()
        ch = min(430, max(220, int(avail * 0.55)))
        try:
            content_w = self.app._content_area.width()
        except RuntimeError:
            content_w = self.width()
        cw = min(int(ch / 1.4), max(130, content_w // 5))
        if cw < int(ch / 1.4):
            ch = int(cw * 1.4)
        return cw, ch

    def _build(self):
        self._sig = self._data_sig()
        self._clear_layout()
        self._carousel_area = None
        self._carousel_inner = None
        self._ch_used = 0

        self.setStyleSheet(f"background: {c.BG_MAIN};")

        if getattr(self, '_backdrop', None) is not None:
            try:
                self._backdrop.lower()
                self._backdrop.setGeometry(self.rect())
            except RuntimeError:
                pass

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

            cw, ch = self._carousel_sizes()
            self._build_carousel(cw, ch)
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

    def _build_carousel(self, cw, ch):
        recents = self._recent_games()
        if not recents:
            return
        ca = getattr(self, '_carousel_area', None)
        if ca is None:
            ca = QScrollArea()
            ca.setWidgetResizable(False)
            ca.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            ca.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            ca.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            self._carousel_area = ca
            self._layout.addWidget(ca, 1)
        old_inner = ca.widget()
        if old_inner is not None:
            old_inner.deleteLater()
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        row = QHBoxLayout(inner)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.addStretch(1)
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
            row.addWidget(poster, 0, Qt.AlignmentFlag.AlignVCenter)
            if idx < len(recents) - 1:
                total += 12
        browse = BrowsePoster(cw, ch)
        browse.clicked.connect(self.app.show_library)
        row.addWidget(browse, 0, Qt.AlignmentFlag.AlignVCenter)
        total += cw + 12
        row.addStretch(1)
        self._carousel_total = total
        self._carousel_inner = inner
        self._ch_used = ch
        self._cw_used = cw
        ca.setWidget(inner)
        try:
            ca.removeEventFilter(self)
        except RuntimeError:
            pass
        ca.installEventFilter(self)
        self._update_running_badges()

    def eventFilter(self, obj, event):
        if obj is getattr(self, '_carousel_area', None) and event.type() == QEvent.Type.Resize:
            inner = getattr(self, '_carousel_inner', None)
            if inner is not None:
                try:
                    vh = obj.viewport().height()
                    if vh > 0 and inner.height() != vh:
                        inner.setFixedHeight(vh)
                except RuntimeError:
                    pass
        return False

    def _reflow_carousel(self):
        ca = getattr(self, '_carousel_area', None)
        if ca is None or getattr(self, '_sig', None) is None:
            return
        cw, ch = self._carousel_sizes()
        if abs(ch - getattr(self, '_ch_used', 0)) <= 8:
            return
        focus_gid = None
        try:
            focus_gid = self.app._focused_game_id()
        except RuntimeError:
            pass
        self._build_carousel(cw, ch)
        self._center_carousel()
        if self.app.engine:
            priority = None
            if focus_gid:
                for w in ca.findChildren((HomePoster, FeaturedPoster)):
                    if getattr(w, 'game_id', None) == focus_gid:
                        priority = w
                        break
            QTimer.singleShot(0, lambda: self.app.engine.rescan(priority_widget=priority))

    def _on_nav_focus(self, widget):
        try:
            if self.app.view_state != "home":
                return
            gid = None
            if widget is not None:
                try:
                    if hasattr(widget, 'game_id'):
                        gid = widget.game_id
                except RuntimeError:
                    gid = None
            data = self.app.config_data.get(gid) if gid else None
            self._backdrop.set_game(gid, data)
            self._scroll_to_poster(widget)
        except RuntimeError:
            pass

    def _is_carousel_member(self, widget):
        try:
            p = widget.parentWidget()
            ca = getattr(self, '_carousel_area', None)
            if ca is None:
                return False
            while p is not None:
                if p is ca:
                    return True
                p = p.parentWidget()
        except RuntimeError:
            return False
        return False

    def _animate_h_scroll(self, target):
        sb = self._carousel_area.horizontalScrollBar()
        cur = sb.value()
        if abs(target - cur) < 2:
            return
        anim = getattr(self, '_h_scroll_anim', None)
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:
                pass
        self._h_scroll_anim = QPropertyAnimation(sb, b"value")
        self._h_scroll_anim.setDuration(180)
        self._h_scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._h_scroll_anim.setStartValue(cur)
        self._h_scroll_anim.setEndValue(target)
        self._h_scroll_anim.start()

    def _scroll_to_poster(self, widget):
        ca = getattr(self, '_carousel_area', None)
        inner = getattr(self, '_carousel_inner', None)
        if ca is None or inner is None or widget is None:
            return
        if not self._is_carousel_member(widget):
            return
        sb = ca.horizontalScrollBar()
        origin = widget.mapTo(inner, widget.rect().topLeft())
        left = origin.x()
        right = origin.x() + widget.width()
        view_w = ca.viewport().width()
        val = sb.value()
        margin = 28
        if left < val + margin:
            target = max(0, left - margin)
        elif right > val + view_w - margin:
            target = min(sb.maximum(), right - view_w + margin)
        else:
            return
        self._animate_h_scroll(target)

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
        inner.setFixedHeight(self._avail_carousel_h())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        bd = getattr(self, '_backdrop', None)
        if bd is not None:
            try:
                bd.setGeometry(self.rect())
                bd.invalidate_cache()
            except RuntimeError:
                pass
        self._center_carousel()
        if getattr(self, '_carousel_area', None) is not None:
            QTimer.singleShot(0, self._reflow_carousel)
