import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QGraphicsOpacityEffect,
                             QGridLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QEvent, QObject, QPropertyAnimation, QEasingCurve, QTimer, QRectF
from PyQt6.QtGui import QPixmap, QMovie, QPainter, QColor, QPen, QPainterPath, QLinearGradient
from launcher_pyqt.utils import format_playtime, relative_time
import colors as c


class HeroBackdrop(QWidget):
    """Full-bleed landscape backdrop. Paints art_land (falling back to the
    portrait art) cover-scaled, or a themed gradient, with a bottom scrim so
    the floating card stays readable. Animated webp/gif art plays via QMovie
    (start() only when the dashboard is the visible view)."""

    def __init__(self, art_path, accent, bg):
        super().__init__()
        self._accent = QColor(accent)
        self._bg = QColor(bg)
        self._pix = None
        self._movie = None
        if art_path and os.path.exists(art_path):
            ext = os.path.splitext(art_path)[1].lower()
            if ext in ('.webp', '.gif'):
                movie = QMovie(art_path, parent=self)
                movie.setCacheMode(QMovie.CacheMode.CacheNone)
                movie.frameChanged.connect(self._on_movie_frame)
                self._movie = movie
            else:
                pix = QPixmap(art_path)
                if not pix.isNull():
                    self._pix = pix
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _on_movie_frame(self, _frame=0):
        """Guarded frame handler: the movie is parented to this widget so it
        dies with it, but during teardown a frame can still land on a deleted
        wrapper (re-present / rebuild) — never let that escape."""
        try:
            self.update()
        except RuntimeError:
            pass

    def _current(self):
        if self._movie is not None:
            try:
                return self._movie.currentPixmap()
            except RuntimeError:
                return QPixmap()
        return self._pix

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        w, h = r.width(), r.height()
        if w <= 0 or h <= 0:
            p.end()
            return
        pix = self._current()
        if pix is not None and not pix.isNull():
            scaled = pix.scaled(w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            sx = (scaled.width() - w) // 2
            sy = (scaled.height() - h) // 2
            p.drawPixmap(0, 0, w, h, scaled, sx, sy, w, h)
        else:
            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, self._accent.darker(200))
            grad.setColorAt(0.55, self._bg)
            grad.setColorAt(1.0, self._bg.darker(115))
            p.fillRect(r, grad)
            glow = QColor(self._accent)
            glow.setAlpha(40)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawEllipse(int(w * 0.5 - w * 0.35), int(h * 0.15), int(w * 0.7), int(w * 0.7))
            p.setPen(QPen(self._accent, 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(w * 0.5 - 70, h * 0.08, 140, 140), 0, 180 * 16)
            p.drawArc(QRectF(w * 0.5 - 45, h * 0.10, 90, 90), 180 * 16, 180 * 16)
        scrim = QLinearGradient(0, h - int(h * 0.55), 0, h)
        scrim.setColorAt(0.0, QColor(0, 0, 0, 0))
        scrim.setColorAt(1.0, QColor(0, 0, 0, 160))
        p.fillRect(r, scrim)
        p.end()

    def start(self):
        if self._movie is not None:
            try:
                self._movie.start()
            except RuntimeError:
                pass

    def stop(self):
        if self._movie is not None:
            try:
                self._movie.stop()
                self._movie.jumpToFrame(0)
            except RuntimeError:
                pass


class _AbsorbFilter(QObject):
    """Consumes mouse/touch events so clicks inside the panel don't reach the
    backdrop (which would dismiss the overlay)."""

    def eventFilter(self, obj, event):
        t = event.type()
        if t in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
                 QEvent.Type.MouseButtonDblClick, QEvent.Type.MouseMove,
                 QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate,
                 QEvent.Type.TouchEnd):
            return True
        return False


class DetailsOverlay(QFrame):
    """Centered DETAILS panel over a dimmed backdrop. Discarded by pressing
    back (B/Esc via handle_back) or clicking/tapping outside the panel."""

    def __init__(self, view, app, game_id):
        super().__init__(view)
        self.view = view
        self.app = app
        self.game_id = game_id
        self._ov_anim = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0, 0, 0, 160);")
        self._build()
        self.hide()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)

        panel = QFrame(self)
        panel.setMaximumWidth(620)
        panel.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_INPUT};
                      border-radius: 12px; }}
        """)
        p_l = QVBoxLayout(panel)
        p_l.setContentsMargins(28, 22, 28, 24)
        p_l.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("DETAILS")
        title.setStyleSheet(f"color: {c.ACCENT}; font: bold 16px;")
        header.addWidget(title)
        header.addStretch(1)
        self.close_btn = QPushButton("\u2715")
        self.close_btn.setFixedSize(34, 30)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.TXT_DIM}; font: bold 13px;
                           border: 1px solid {c.BG_INPUT}; border-radius: 6px; }}
            QPushButton:hover {{ background: {c.DANGER}; color: white; }}
        """)
        self.close_btn.clicked.connect(lambda: self.view._close_details())
        header.addWidget(self.close_btn)
        p_l.addLayout(header)

        data = self.app.config_data[self.game_id]
        proton_val = data.get("proton", "") or ""
        if proton_val:
            proton_display = proton_val
        else:
            gdef = self.app.config_data.get("settings", {}).get("default_proton", "") or ""
            proton_display = f"Use Default ({gdef or 'UMU Internal'})"
        fields = [
            ("Exe", data.get("exe", "")),
            ("Prefix", data.get("prefix", "")),
            ("Proton", proton_display),
            ("Store", data.get("store", "none")),
            ("Launch Count", str(data.get("launch_count", 0))),
            ("Portrait", "set" if data.get("art") else "none"),
            ("Landscape", "set" if data.get("art_land") else "none"),
        ]
        for label_text, value in fields:
            row = QHBoxLayout()
            lbl = QLabel(f"{label_text}:")
            lbl.setStyleSheet(f"color: {c.ACCENT}; font: bold 11px;")
            lbl.setFixedWidth(110)
            row.addWidget(lbl)
            val_lbl = QLabel(value if value else "-")
            val_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: 11px;")
            if value:
                val_lbl.setToolTip(value)
            val_lbl.setMinimumWidth(200)
            row.addWidget(val_lbl, 1, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            p_l.addLayout(row)

        layout.addWidget(panel, 0, Qt.AlignmentFlag.AlignCenter)
        panel.installEventFilter(_AbsorbFilter(panel))

    def showEvent(self, event):
        super().showEvent(event)
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(150)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._ov_anim = anim
        anim.start()

    def mousePressEvent(self, event):
        self.view._close_details()
        event.accept()


class ArtOverlay(QFrame):
    """Centered ARTWORK panel over a dimmed backdrop. Opens from the card's
    Artwork button; holds Browse Portrait / Browse Landscape / Generate /
    Remove. Same dismissal contract as DetailsOverlay (back, backdrop click,
    close button)."""

    def __init__(self, view, app, game_id):
        super().__init__(view)
        self.view = view
        self.app = app
        self.game_id = game_id
        self._ov_anim = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0, 0, 0, 160);")
        self._build()
        self.hide()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)

        panel = QFrame(self)
        panel.setMaximumWidth(460)
        panel.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_INPUT};
                      border-radius: 12px; }}
        """)
        p_l = QVBoxLayout(panel)
        p_l.setContentsMargins(28, 22, 28, 24)
        p_l.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("ARTWORK")
        title.setStyleSheet(f"color: {c.ACCENT}; font: bold 16px;")
        header.addWidget(title)
        header.addStretch(1)
        self.close_btn = QPushButton("\u2715")
        self.close_btn.setFixedSize(34, 30)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.TXT_DIM}; font: bold 13px;
                           border: 1px solid {c.BG_INPUT}; border-radius: 6px; }}
            QPushButton:hover {{ background: {c.DANGER}; color: white; }}
        """)
        self.close_btn.clicked.connect(lambda: self.view._close_art())
        header.addWidget(self.close_btn)
        p_l.addLayout(header)

        def row_btn(text, color, fn, enabled=True):
            b = QPushButton(text)
            b.setEnabled(enabled)
            b.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {color}; font: bold 12px;
                               border: 1px solid {color}; border-radius: 7px;
                               padding: 9px 14px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN}; }}
                QPushButton:disabled {{ color: {c.TXT_DIM}; border-color: {c.BG_INPUT};
                                        background: transparent; }}
            """)
            b.clicked.connect(lambda checked=False, f=fn: self.view._act_art(f))
            return b

        data = self.app.config_data[self.game_id]
        has_art = bool(data.get("art") or data.get("art_land"))
        p_l.addWidget(row_btn("Browse Portrait", c.ACCENT,
                              lambda: self.view._browse_artwork("art")))
        p_l.addWidget(row_btn("Browse Landscape", c.ACCENT,
                              lambda: self.view._browse_artwork("art_land")))
        p_l.addWidget(row_btn("Generate Art", c.SUCCESS, self.view._generate_art))
        p_l.addWidget(row_btn("Remove Artwork", c.DANGER, self.view._remove_artwork,
                              enabled=has_art))

        layout.addWidget(panel, 0, Qt.AlignmentFlag.AlignCenter)
        panel.installEventFilter(_AbsorbFilter(panel))

    def showEvent(self, event):
        super().showEvent(event)
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(150)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._ov_anim = anim
        anim.start()

    def mousePressEvent(self, event):
        self.view._close_art()
        event.accept()


class SettingsOverlay(QFrame):
    """Centered GAME SETTINGS chooser over a dimmed backdrop. Opens from the
    card's Settings button and prompts between Quick Settings (sheet) and
    Advanced Settings (editor). Same dismissal contract as the other
    overlays (back, backdrop click, close button)."""

    def __init__(self, view, app, game_id):
        super().__init__(view)
        self.view = view
        self.app = app
        self.game_id = game_id
        self._ov_anim = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0, 0, 0, 160);")
        self._build()
        self.hide()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)

        panel = QFrame(self)
        panel.setMaximumWidth(440)
        panel.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_INPUT};
                      border-radius: 12px; }}
        """)
        p_l = QVBoxLayout(panel)
        p_l.setContentsMargins(28, 22, 28, 26)
        p_l.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("GAME SETTINGS")
        title.setStyleSheet(f"color: {c.ACCENT}; font: bold 16px;")
        header.addWidget(title)
        header.addStretch(1)
        self.close_btn = QPushButton("\u2715")
        self.close_btn.setFixedSize(34, 30)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.TXT_DIM}; font: bold 13px;
                           border: 1px solid {c.BG_INPUT}; border-radius: 6px; }}
            QPushButton:hover {{ background: {c.DANGER}; color: white; }}
        """)
        self.close_btn.clicked.connect(lambda: self.view._close_settings())
        header.addWidget(self.close_btn)
        p_l.addLayout(header)

        def choice_btn(text, sub, color, fn):
            b = QPushButton(text)
            b.setFixedHeight(46)
            b.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {color}; font: bold 13px;
                               border: 1px solid {color}; border-radius: 8px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN}; }}
            """)
            b.setToolTip(sub)
            b.clicked.connect(lambda checked=False, f=fn: self.view._act_settings(f))
            return b

        p_l.addWidget(choice_btn(
            "\u26a1  Quick Settings", "Toggles: Gamescope, Resolution, HUD, LiveSplit, Proton",
            c.ACCENT, self._quick_settings))
        p_l.addWidget(choice_btn(
            "\u2699  Advanced Settings", "Editor: notes, prefix, Proton, scripts, per-game flags",
            c.TXT_MAIN, self._advanced))

        layout.addWidget(panel, 0, Qt.AlignmentFlag.AlignCenter)
        panel.installEventFilter(_AbsorbFilter(panel))

    def _quick_settings(self):
        gid = self.game_id
        self.app.open_quick_settings(gid)

    def _advanced(self):
        self.app.show_editor()

    def showEvent(self, event):
        super().showEvent(event)
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(150)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._ov_anim = anim
        anim.start()

    def mousePressEvent(self, event):
        self.view._close_settings()
        event.accept()


class DashboardView(QWidget):
    def __init__(self, app, game_id):
        super().__init__()
        self.app = app
        self.game_id = game_id
        self._reflow_on_resize = True
        self.setStyleSheet("background: transparent;")
        self._hero_widget = None
        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._build()

    def _build(self, art_override=None):
        data = self.app.config_data[self.game_id]
        layout = self._layout
        if art_override is not None:
            hero = max(180, int(art_override))
        else:
            avail = self._stable_avail()
            hero = (self._hero_height_for_avail(avail)
                    if avail > 200 else 360)
            non_hero = getattr(self, '_non_hero_height', None)
            if non_hero:
                hero = min(hero, avail - 12 - non_hero)
            hero = max(180, hero)
        self._hero_height_used = hero
        self._hero_floor = 180
        self._hero_widget = None

        card = self._build_card(data)
        card.show()
        card_h = card.sizeHint().height()
        self._hero_floor = card_h + 60
        final_h = max(hero, card_h + 60)
        self._hero_height_used = final_h

        hero_box = QWidget()
        hero_box.setStyleSheet("background: transparent;")
        hero_box._hero_container = True
        grid = QGridLayout(hero_box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        grid.setRowStretch(0, 1)
        grid.setColumnStretch(0, 1)

        art = data.get("art_land") or data.get("art")
        backdrop = HeroBackdrop(art, c.ACCENT, c.BG_PANEL)
        backdrop.setFixedHeight(final_h)
        backdrop._hero_backdrop = True
        self._hero_widget = backdrop
        if self.isVisible():
            backdrop.start()
        grid.addWidget(backdrop, 0, 0)
        grid.addWidget(card, 0, 0,
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)

        layout.addWidget(hero_box)

        bottom = QWidget()
        bottom.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(30, 20, 30, 24)
        bl.setSpacing(12)
        bl.setAlignment(Qt.AlignmentFlag.AlignTop)

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
            bl.addWidget(notes_frame)

        self._details_btn = QPushButton("DETAILS  \u25b8")
        self._details_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.TXT_DIM}; font: bold 11px;
                           border: 1px solid {c.BG_INPUT}; border-radius: 6px;
                           padding: 6px 18px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN};
                                 border: 1px solid {c.ACCENT}; }}
        """)
        self._details_btn.clicked.connect(self._open_details)
        bl.addWidget(self._details_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(bottom)

        self._details_overlay = DetailsOverlay(self, self.app, self.game_id)
        self._art_overlay = ArtOverlay(self, self.app, self.game_id)
        self._settings_overlay = SettingsOverlay(self, self.app, self.game_id)

        layout.addStretch(1)
        self._reveal_widgets(layout)
        if art_override is None:
            self._fit_content()

    def _build_card(self, data):
        card = QFrame()
        card._hero_card = True
        card.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BORDER};
                      border-radius: 14px; }}
        """)
        card.setFixedWidth(self._card_width())
        cv = QVBoxLayout(card)
        cv.setContentsMargins(28, 20, 28, 20)
        cv.setSpacing(10)

        name = data.get("name", "Unknown")
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {c.ACCENT}; font: bold 22px;")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cv.addWidget(name_lbl)

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
        cv.addWidget(meta_lbl)

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
        cv.addWidget(play_btn)

        def accent_btn(text, color, font_size=11):
            b = QPushButton(text)
            b.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {color}; font: bold {font_size}px;
                               border: 1px solid {color}; border-radius: 6px; padding: 6px 12px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN}; }}
            """)
            return b

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.setSpacing(8)

        settings_btn = accent_btn("Settings", c.ACCENT)
        settings_btn.clicked.connect(self._open_settings)
        self._settings_btn = settings_btn
        btn_row.addWidget(settings_btn)

        art_btn = accent_btn("Artwork", c.ACCENT)
        art_btn.clicked.connect(self._open_art)
        self._art_btn = art_btn
        btn_row.addWidget(art_btn)

        fav_char = "\u2605" if data.get("favorite") else "\u2606"
        fav_btn = QPushButton(fav_char)
        fav_btn.setFixedSize(34, 32)
        fav_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.ACCENT}; font: 15px;
                           border: 1px solid {c.ACCENT}; border-radius: 6px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        fav_btn.clicked.connect(self._toggle_favorite)
        btn_row.addWidget(fav_btn)
        cv.addLayout(btn_row)
        return card

    def _card_width(self):
        ca = getattr(self.app, '_content_area', None)
        try:
            w = ca.width() if ca is not None else 0
        except RuntimeError:
            w = 0
        if w <= 0:
            w = self.width()
        return max(340, min(680, int(w * 0.72)))

    def _open_details(self):
        ov = self._details_overlay
        ov.setGeometry(self.rect())
        self._set_nav_enabled(False)
        ov.show()
        ov.raise_()
        if self.app.engine:
            self.app.engine.rescan(priority_widget=ov.close_btn)

    def _close_details(self):
        ov = self._details_overlay
        anim = getattr(ov, '_ov_anim', None)
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:
                pass
        try:
            ov.setGraphicsEffect(None)
        except RuntimeError:
            pass
        self._set_nav_enabled(True)
        ov.hide()
        if self.app.engine:
            self.app.engine.rescan(priority_widget=self._details_btn)

    @property
    def details_overlay_open(self):
        ov = getattr(self, '_details_overlay', None)
        try:
            return bool(ov is not None and ov.isVisible())
        except RuntimeError:
            return False

    @property
    def art_overlay_open(self):
        ov = getattr(self, '_art_overlay', None)
        try:
            return bool(ov is not None and ov.isVisible())
        except RuntimeError:
            return False

    @property
    def settings_overlay_open(self):
        ov = getattr(self, '_settings_overlay', None)
        try:
            return bool(ov is not None and ov.isVisible())
        except RuntimeError:
            return False

    def _open_settings(self):
        ov = self._settings_overlay
        ov.setGeometry(self.rect())
        self._set_nav_enabled(False)
        ov.show()
        ov.raise_()
        if self.app.engine:
            self.app.engine.rescan(priority_widget=ov.close_btn)

    def _close_settings(self):
        ov = self._settings_overlay
        anim = getattr(ov, '_ov_anim', None)
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:
                pass
        try:
            ov.setGraphicsEffect(None)
        except RuntimeError:
            pass
        self._set_nav_enabled(True)
        ov.hide()
        if self.app.engine:
            self.app.engine.rescan(priority_widget=self._settings_btn)

    def _act_settings(self, fn):
        """Close the settings chooser, then run the chosen action."""
        self._close_settings()
        fn()

    def _open_art(self):
        ov = self._art_overlay
        ov.setGeometry(self.rect())
        self._set_nav_enabled(False)
        ov.show()
        ov.raise_()
        if self.app.engine:
            self.app.engine.rescan(priority_widget=ov.close_btn)

    def _close_art(self):
        ov = self._art_overlay
        anim = getattr(ov, '_ov_anim', None)
        if anim is not None:
            try:
                anim.stop()
            except RuntimeError:
                pass
        try:
            ov.setGraphicsEffect(None)
        except RuntimeError:
            pass
        self._set_nav_enabled(True)
        ov.hide()
        if self.app.engine:
            self.app.engine.rescan(priority_widget=self._art_btn)

    def _act_art(self, fn):
        """Close the art overlay, then run the chosen action (browse/generate/
        remove re-present the dashboard or open the file browser)."""
        self._close_art()
        fn()

    def _set_nav_enabled(self, enabled):
        ovs = []
        for name in ('_details_overlay', '_art_overlay', '_settings_overlay'):
            ov = getattr(self, name, None)
            if ov is not None:
                ovs.append(ov)
        for w in self.findChildren(QPushButton):
            try:
                if any(ov.isAncestorOf(w) for ov in ovs):
                    continue
                if w.isEnabled() != enabled:
                    w.setEnabled(enabled)
            except RuntimeError:
                pass

    def _stable_avail(self):
        ca = getattr(self.app, '_content_area', None)
        try:
            h = ca.height() if ca is not None else 0
        except RuntimeError:
            h = 0
        if h > 200:
            return h - 36
        return self.height()

    def _hero_height_for_avail(self, avail_h):
        has_notes = bool(self.app.config_data.get(self.game_id, {}).get("notes"))
        if has_notes:
            return max(200, min(400, avail_h - 300))
        return max(220, min(430, avail_h - 260))

    def _fit_content(self):
        if self.details_overlay_open:
            return
        h = self.height()
        if h <= 200:
            return
        used = getattr(self, '_hero_height_used', 400)
        avail = self._stable_avail()
        desired = self._hero_height_for_avail(avail if avail > 200 else h)
        if self._hero_widget is not None:
            try:
                sh = self._layout.sizeHint().height()
                if self._hero_widget.isHidden():
                    non_hero = sh
                else:
                    non_hero = sh - used
                self._non_hero_height = max(0, non_hero)
                desired = min(desired, (avail - 12) - non_hero)
            except RuntimeError:
                pass
        floor = getattr(self, '_hero_floor', 180)
        desired = max(floor, desired)
        btn = getattr(self, '_details_btn', None)
        if btn is not None:
            try:
                bottom = btn.geometry().bottom()
            except RuntimeError:
                bottom = 0
            if bottom > h - 12:
                desired = min(desired, used - (bottom - (h - 12)))
        if abs(desired - used) > 12:
            self._rebuild(art_override=desired)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        ov = getattr(self, '_details_overlay', None)
        if ov is not None:
            try:
                ov.setGeometry(self.rect())
            except RuntimeError:
                pass
        self._fit_content()

    def _reveal_widgets(self, layout):
        """Show freshly built layout items so QWidgetItem::sizeHint() reports
        real sizes (hidden items contribute 0 to a layout's sizeHint)."""
        for i in range(layout.count()):
            it = layout.itemAt(i)
            w = it.widget()
            if w is not None:
                try:
                    if getattr(w, '_gi', None) is None:
                        w.show()
                    sub = getattr(w, 'layout', None)
                    if sub is not None:
                        sub = sub()
                        if sub is not None and sub.count():
                            self._reveal_widgets(sub)
                except RuntimeError:
                    pass
                continue
            sub = it.layout()
            if sub is not None:
                self._reveal_widgets(sub)

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

    def _rebuild(self, art_override=None):
        for name in ('_details_overlay', '_art_overlay', '_settings_overlay'):
            ov = getattr(self, name, None)
            if ov is not None:
                try:
                    ov.hide()
                    ov.deleteLater()
                except RuntimeError:
                    pass
            setattr(self, name, None)
        self._clear_layout(self._layout)
        self._build(art_override=art_override)

    def refresh(self):
        self._rebuild()

    def hideEvent(self, event):
        super().hideEvent(event)
        if getattr(self, '_hero_widget', None):
            try:
                self._hero_widget.stop()
            except RuntimeError:
                pass

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, '_hero_widget', None):
            try:
                self._hero_widget.start()
            except RuntimeError:
                pass
        QTimer.singleShot(0, self._fit_content)

    def _toggle_favorite(self):
        data = self.app.config_data[self.game_id]
        data["favorite"] = not data.get("favorite", False)
        self.app.config_manager.save_data(self.app.config_data)
        self.app.show_dashboard(self.game_id)

    def _browse_artwork(self, key="art_land"):
        """Browse a single art slot: 'art' = library portrait, 'art_land' =
        dashboard hero. Picking a portrait auto-derives the hero when none is
        set; picking a hero never touches the portrait (independent slots)."""
        prev_state = self.app.view_state
        self.app.view_state = "browser"
        self.app.engine.sound.play("modal")

        def on_selected(path):
            if path:
                data = self.app.config_data[self.game_id]
                if key == "art_land":
                    data["art_land"] = path
                else:
                    data["art"] = path
                    if not data.get("art_land"):
                        from launcher_pyqt.utils import derive_landscape
                        out = str(self.app.artwork_manager.artwork_dir)
                        land = derive_landscape(self.game_id, data.get("name", ""),
                                                c.ACCENT, c.BG_PANEL, out, path)
                        if land:
                            data["art_land"] = land
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
        data["art_land"] = ""
        self.app.config_manager.save_data(self.app.config_data)
        self.app.show_dashboard(self.game_id)

    def _generate_art(self):
        data = self.app.config_data[self.game_id]
        from launcher_pyqt.utils import generate_placeholder_art, derive_landscape
        out = str(self.app.artwork_manager.artwork_dir)
        name = data.get("name", "New Game")
        path = generate_placeholder_art(self.game_id, name, c.ACCENT, c.BG_PANEL, out)
        if path:
            land = derive_landscape(self.game_id, name, c.ACCENT, c.BG_PANEL, out, path)
            data["art"] = path
            if land:
                data["art_land"] = land
            self.app.config_manager.save_data(self.app.config_data)
            self.app.show_dashboard(self.game_id)
