import colors as c
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QEvent, QObject, QPropertyAnimation, QEasingCurve
from launcher_pyqt.utils import relative_time


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


class QuickSettingsOverlay(QFrame):
    """Compact per-game quick-settings sheet, opened by X on Home/Library/
    Dashboard. Every change applies + saves immediately. Dismissed by B/Esc,
    the close button, or clicking the dimmed backdrop."""

    RES_PRESETS = ["1280x720", "1920x1080", "1600x900", "1024x576"]

    def __init__(self, app):
        super().__init__(app._content_area)
        self.app = app
        self._game_id = None
        self._restore_gid = None
        self._restore_idx = 0
        self._ov_anim = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0, 0, 0, 160);")
        self._build()
        self.hide()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 48, 48, 48)

        self._panel = QFrame(self)
        self._panel.setMaximumWidth(560)
        self._panel.setStyleSheet(f"""
            QFrame {{ background: {c.BG_PANEL}; border: 1px solid {c.BG_INPUT};
                      border-radius: 12px; }}
        """)
        lay.addWidget(self._panel, 0, Qt.AlignmentFlag.AlignCenter)
        self._panel.installEventFilter(_AbsorbFilter(self))
        self._build_panel()

    def _build_panel(self):
        p_l = QVBoxLayout(self._panel)
        p_l.setContentsMargins(26, 20, 26, 22)
        p_l.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("QUICK SETTINGS")
        title.setStyleSheet(f"color: {c.ACCENT}; font: bold 15px;")
        header.addWidget(title)
        header.addStretch(1)
        self._close_btn = QPushButton("\u2715")
        self._close_btn.setFixedSize(34, 30)
        self._close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.TXT_DIM}; font: bold 13px;
                           border: 1px solid {c.BG_INPUT}; border-radius: 6px; }}
            QPushButton:hover {{ background: {c.DANGER}; color: white; }}
        """)
        self._close_btn.clicked.connect(lambda: self.app.close_quick_settings())
        header.addWidget(self._close_btn)
        p_l.addLayout(header)

        self._name_lbl = QLabel("")
        self._name_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 13px;")
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_l.addWidget(self._name_lbl)

        self.gs_btn = self._add_toggle_row(p_l, "GAMESCOPE", self._toggle_gs)
        self._res_btn = self._add_res_row(p_l, self._cycle_res)
        self.hud_btn = self._add_toggle_row(p_l, "MANGO HUD", self._toggle_hud)
        self.ls_btn = self._add_toggle_row(p_l, "LIVESPLIT", self._toggle_ls)

        proton_row = QHBoxLayout()
        plbl = QLabel("PROTON")
        plbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px;")
        proton_row.addWidget(plbl)
        proton_row.addStretch(1)
        self.proton_menu = QComboBox()
        self.proton_menu.addItem("Use Default")
        self.proton_menu.addItem("Default (UMU Internal)")
        for p in sorted(self.app.proton_paths.keys(), key=str.lower):
            if p != "Default (UMU Internal)":
                self.proton_menu.addItem(p)
        self.proton_menu.setStyleSheet(f"""
            QComboBox {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 12px;
                         border-radius: 6px; padding: 6px; }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
            QComboBox QAbstractItemView {{ background: {c.BG_PANEL}; color: {c.TXT_MAIN};
                                             selection-background-color: {c.ACCENT}; }}
        """)
        self.proton_menu.currentIndexChanged.connect(self._on_proton)
        proton_row.addWidget(self.proton_menu, 1)
        p_l.addLayout(proton_row)

        self._info_lbl = QLabel("")
        self._info_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 10px;")
        self._info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_l.addWidget(self._info_lbl)

    def open(self, gid):
        self._game_id = gid
        self.setGeometry(self.app._content_area.rect())
        data = self.app.config_data[gid]
        self._name_lbl.setText(data.get("name", ""))
        self._info_lbl.setText(self._info_text(data))
        self._refresh_widgets()
        eng = getattr(self.app, 'engine', None)
        self._restore_idx = eng.nav_index if (eng is not None and eng.nav_list) else 0
        self._restore_gid = None
        try:
            self._restore_gid = self.app._focused_game_id() or getattr(self.app, 'current_game_id', None)
        except Exception:
            pass
        self.show()
        self.raise_()
        if eng:
            eng.rescan(priority_widget=self.gs_btn)

    def close(self):
        self.hide()
        eng = getattr(self.app, 'engine', None)
        if not eng:
            return
        eng.rescan()
        idx = self._restore_idx
        if self._restore_gid:
            for i, w in enumerate(eng.nav_list):
                if getattr(w, 'game_id', None) == self._restore_gid:
                    idx = i
                    break
        if eng.nav_list:
            eng.nav_index = min(idx, len(eng.nav_list) - 1)
            eng.sync_visuals()

    # ---- rows -------------------------------------------------------------

    def _add_toggle_row(self, parent, label, handler):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px;")
        row.addWidget(lbl)
        row.addStretch(1)
        btn = QPushButton()
        btn.setFixedWidth(96)
        btn.clicked.connect(lambda checked=False, h=handler: h())
        row.addWidget(btn)
        parent.addLayout(row)
        return btn

    def _add_res_row(self, parent, handler):
        row = QHBoxLayout()
        lbl = QLabel("RESOLUTION")
        lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px;")
        row.addWidget(lbl)
        row.addStretch(1)
        btn = QPushButton()
        btn.setFixedWidth(96)
        btn.clicked.connect(lambda checked=False, h=handler: h())
        row.addWidget(btn)
        parent.addLayout(row)
        return btn

    # ---- toggles ----------------------------------------------------------

    def _toggle_gs(self):
        self._flip("gs_on")
        if self.app.config_data[self._game_id].get("gs_on"):
            self.app.config_data[self._game_id]["livesplit"] = False
        self._after_change()

    def _toggle_hud(self):
        self._flip("useMangoHud")
        self._after_change()

    def _toggle_ls(self):
        self._flip("livesplit")
        self._after_change()

    def _flip(self, key):
        if self._game_id is None:
            return
        d = self.app.config_data[self._game_id]
        d[key] = not bool(d.get(key, False))

    def _cycle_res(self):
        if self._game_id is None:
            return
        d = self.app.config_data[self._game_id]
        cur = f"{d.get('gs_w', '1280')}x{d.get('gs_h', '720')}"
        idx = self.RES_PRESETS.index(cur) if cur in self.RES_PRESETS else -1
        nxt = self.RES_PRESETS[(idx + 1) % len(self.RES_PRESETS)]
        w, h = nxt.split("x")
        d["gs_w"] = w
        d["gs_h"] = h
        self._after_change()

    def _on_proton(self, idx):
        if self._game_id is None:
            return
        text = self.proton_menu.currentText()
        self.app.config_data[self._game_id]["proton"] = "" if text == "Use Default" else text
        self.app.config_manager.save_data(self.app.config_data)

    def _after_change(self):
        self.app.config_manager.save_data(self.app.config_data)
        self._refresh_widgets()

    # ---- state sync -------------------------------------------------------

    def _info_text(self, data):
        lp = relative_time(data.get("last_played", ""))
        played = f"last played {lp}" if lp else "never played"
        return f"{data.get('launch_count', 0)} launches  \u2022  {played}"

    def _set_toggle(self, btn, on):
        if on:
            btn.setText("ON")
            btn.setStyleSheet(f"""
                QPushButton {{ background: {c.SUCCESS}; color: white; font: bold 11px;
                               border-radius: 4px; padding: 4px 12px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
            """)
        else:
            btn.setText("OFF")
            btn.setStyleSheet(f"""
                QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_DIM}; font: bold 11px;
                               border-radius: 4px; padding: 4px 12px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
            """)

    def _set_res_btn(self, w, h):
        self._res_btn.setText(f"{w}x{h}")
        self._res_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: bold 11px;
                           border-radius: 4px; padding: 4px 12px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)

    def _refresh_widgets(self):
        if self._game_id is None:
            return
        data = self.app.config_data[self._game_id]
        self._set_toggle(self.gs_btn, bool(data.get("gs_on", False)))
        self._set_toggle(self.hud_btn, bool(data.get("useMangoHud", False)))
        self._set_toggle(self.ls_btn, bool(data.get("livesplit", False)))
        ls_locked = self.app.runningOnGamescope or bool(data.get("gs_on", False))
        if ls_locked and self.ls_btn.isEnabled():
            self.ls_btn.setEnabled(False)
            self.ls_btn.setStyleSheet(f"""
                QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_DIM}; font: bold 11px;
                               border-radius: 4px; padding: 4px 12px; }}
            """)
        elif not ls_locked and not self.ls_btn.isEnabled():
            self.ls_btn.setEnabled(True)
            self._set_toggle(self.ls_btn, bool(data.get("livesplit", False)))
        self._set_res_btn(data.get("gs_w", "1280"), data.get("gs_h", "720"))
        cur = data.get("proton", "") or ""
        if cur:
            idx = self.proton_menu.findText(cur)
            if idx >= 0 and self.proton_menu.currentIndex() != idx:
                self.proton_menu.blockSignals(True)
                self.proton_menu.setCurrentIndex(idx)
                self.proton_menu.blockSignals(False)
        elif self.proton_menu.currentIndex() != 0:
            self.proton_menu.blockSignals(True)
            self.proton_menu.setCurrentIndex(0)
            self.proton_menu.blockSignals(False)

    # ---- dismiss ----------------------------------------------------------

    def mousePressEvent(self, event):
        self.app.close_quick_settings()
        event.accept()

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
