"""'Add a game' modal: NAME field + Browse for exe/prefix, plus a CREATE
prefix flow (deps prompt + background wine prefix creation).

- Selecting an exe auto-fills the name (exe basename -> exe dirname ->
  exe dirname's parent) when the title is still empty.
- The prefix row offers Browse (pick an existing folder) or Create (build a
  `<name>_pfx` next to the exe in the background, after choosing deps).
- Controller-aware: modal nav mode scans QLineEdit/QPushButton/QCheckBox
  children; opened non-blocking via app.open_add_game."""
import os, pathlib, threading
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QCheckBox, QGridLayout,
                             QFrame, QStackedWidget, QWidget,
                             QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
import colors as c
from launcher_pyqt.pfx_creator import DEP_NAMES, create_wine_prefix

_GENERIC_STEMS = {"game", "start", "launcher", "main", "app", "play", "run",
                  "bin", "setup", "install", "loader", "x", "exe", "sample"}


def _prettify(stem):
    import re
    parts = re.split(r"[^0-9A-Za-z]+", stem)
    return " ".join(p[:1].upper() + p[1:] for p in parts if p).strip()


def _suggest_name(exe_path):
    """Best-guess game title from the exe path: exe basename first, then the
    exe directory name, then that directory's parent name."""
    p = pathlib.Path(exe_path)
    candidates = []
    stem = _prettify(p.stem)
    if stem:
        candidates.append(stem)
    dir_name = _prettify(p.parent.name)
    if dir_name:
        candidates.append(dir_name)
    parent_name = _prettify(p.parent.parent.name)
    if parent_name:
        candidates.append(parent_name)
    for cand in candidates:
        if cand.lower() in _GENERIC_STEMS:
            continue
        return cand
    return candidates[0] if candidates else ""


def _suggest_candidates(exe_path):
    """Return up to 3 (label, name) candidates from an exe path for the
    user to pick from: the exe basename, the directory name, and that
    directory's parent name."""
    p = pathlib.Path(exe_path)
    seen = set()
    result = []
    for label, path_part in [("exe", p.stem), ("folder", p.parent.name),
                             ("parent", p.parent.parent.name)]:
        name = _prettify(path_part)
        if name and name.lower() not in seen and name.lower() not in _GENERIC_STEMS:
            seen.add(name.lower())
            result.append((label, name))
    return result


class _BrowseCapture:
    """Fake label for app.browse's setText callback; records the path on the
    modal (and auto-fills the title for the exe) and keeps the button label
    elided."""

    def __init__(self, btn, owner, attr):
        self._btn = btn
        self._owner = owner
        self._attr = attr

    def setText(self, path):
        setattr(self._owner, self._attr, path)
        if self._attr == "_exe_path":
            self._owner._on_exe_picked(path)
        self._btn.setToolTip(path)
        self._btn.setText(_elide(path, 36))


def _elide(path, n):
    return path if len(path) <= n else "…" + path[-(n - 1):]


class AddGameModal(QDialog):
    pfx_done_signal = pyqtSignal(bool, str)

    def __init__(self, parent, engine=None):
        super().__init__(parent)
        self.engine = engine
        self.result = None
        self._exe_path = ""
        self._prefix_path = ""

        self.setWindowTitle("Add a game")
        self.setFixedSize(560, 500)
        self.setModal(True)
        self.setStyleSheet(f"background: {c.BG_PANEL};")

        if self.engine:
            self.finished.connect(lambda: QTimer.singleShot(0, self.engine.rescan))
        self.pfx_done_signal.connect(self._pfx_done)

        self._build()

    # ---- helpers ----------------------------------------------------------

    def _field_style(self):
        return f"""
            QLineEdit {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 13px;
                         border-radius: 8px; padding: 8px 12px;
                         border: 1px solid {c.BG_INPUT}; }}
            QLineEdit:focus {{ border: 1px solid {c.ACCENT}; }}
        """

    def _btn_style(self, color=None):
        color = color or c.ACCENT
        return f"""
            QPushButton {{ background: {c.SURFACE}; color: {color}; font: 12px;
                           border-radius: 8px; padding: 9px 10px;
                           border: 1px solid {color}; text-align: center; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN}; }}
            QPushButton:disabled {{ color: {c.TXT_DIM}; border-color: {c.BG_INPUT};
                                    background: {c.BG_INPUT}; }}
        """

    def _field_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px;")
        return lbl

    def _rescan(self):
        if self.engine:
            QTimer.singleShot(0, self.engine.rescan)

    def _on_exe_picked(self, path):
        if not self._name.text().strip():
            self._show_suggestions(path)
        self._refresh_create()

    def _show_suggestions(self, exe_path):
        """Show clickable suggestion buttons when the name field is empty."""
        lay = self._suggest_lay
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        candidates = _suggest_candidates(exe_path)
        if not candidates:
            self._suggest_frame.hide()
            return
        hint = QLabel("Did you mean:")
        hint.setStyleSheet(f"color: {c.TXT_DIM}; font: 11px;")
        lay.addWidget(hint)
        for label, name in candidates:
            btn = QPushButton(name)
            btn.setToolTip(f"Use {label} name")
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {c.ACCENT};
                               font: bold 12px; border: 1px solid {c.ACCENT};
                               border-radius: 6px; padding: 5px 12px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN}; }}
            """)
            btn.clicked.connect(lambda checked=False, n=name: self._apply_suggestion(n))
            lay.addWidget(btn)
        lay.addStretch(1)
        self._suggest_frame.show()

    def _apply_suggestion(self, name):
        self._name.setText(name)
        self._name.setFocus()
        self._suggest_frame.hide()

    def _on_name_changed(self, text):
        """Hide suggestions as soon as the user types anything."""
        if text.strip() and self._suggest_frame.isVisible():
            self._suggest_frame.hide()

    def _refresh_create(self):
        if not self._exe_path:
            self._create_btn.setEnabled(False)
            self._create_btn.setToolTip("Pick the executable first")
        else:
            self._create_btn.setEnabled(True)
            self._create_btn.setToolTip("Create a new Wine prefix for this game")

    def _page1(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(self._field_label("NAME"))
        self._name = QLineEdit()
        self._name.setPlaceholderText("e.g. Hollow Knight")
        self._name.setStyleSheet(self._field_style())
        self._name.textChanged.connect(self._on_name_changed)
        lay.addWidget(self._name)

        self._suggest_frame = QFrame()
        self._suggest_frame.setStyleSheet(
            f"QFrame {{ background: {c.BG_INPUT}; border-radius: 8px; padding: 4px; }}")
        self._suggest_lay = QHBoxLayout(self._suggest_frame)
        self._suggest_lay.setContentsMargins(8, 6, 8, 6)
        self._suggest_lay.setSpacing(6)
        self._suggest_frame.hide()
        lay.addWidget(self._suggest_frame)

        lay.addWidget(self._field_label("EXECUTABLE"))
        self._exe_btn = QPushButton("Browse for executable…")
        self._exe_btn.setStyleSheet(self._btn_style())
        self._exe_btn.setToolTip("")
        self._exe_btn.clicked.connect(
            lambda checked=False: self.parent().browse(
                _BrowseCapture(self._exe_btn, self, "_exe_path"), True))
        lay.addWidget(self._exe_btn)

        lay.addWidget(self._field_label("WINEPREFIX"))
        prefix_row = QHBoxLayout()
        prefix_row.setSpacing(8)
        self._prefix_btn = QPushButton("Browse…")
        self._prefix_btn.setStyleSheet(self._btn_style())
        self._prefix_btn.setToolTip("")
        self._prefix_btn.clicked.connect(
            lambda checked=False: self.parent().browse(
                _BrowseCapture(self._prefix_btn, self, "_prefix_path"), False))
        prefix_row.addWidget(self._prefix_btn, 1)
        self._create_btn = QPushButton("Create…")
        self._create_btn.setStyleSheet(self._btn_style(c.SUCCESS))
        self._create_btn.setToolTip("Pick the executable first")
        self._create_btn.setEnabled(False)
        self._create_btn.clicked.connect(self._show_create_page)
        prefix_row.addWidget(self._create_btn)
        lay.addLayout(prefix_row)

        lay.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: bold 13px;
                           border-radius: 9px; padding: 6px 26px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; border: 1px solid {c.ACCENT}; }}
        """)
        cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(cancel_btn)

        self._add_btn = QPushButton("Add")
        self._add_btn.setFixedHeight(38)
        self._add_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.SUCCESS}; color: #ffffff; font: bold 13px;
                           border-radius: 9px; padding: 6px 32px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        self._add_btn.clicked.connect(self._finish)
        btn_row.addWidget(self._add_btn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)
        return w

    def _page2(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        title = QLabel("CREATE WINEPREFIX")
        title.setStyleSheet(f"color: {c.ACCENT}; font: bold 16px;")
        lay.addWidget(title)

        self._pfx_info = QLabel("")
        self._pfx_info.setWordWrap(True)
        self._pfx_info.setStyleSheet(f"color: {c.TXT_MAIN}; font: 12px;")
        lay.addWidget(self._pfx_info)

        deps_card = QFrame()
        deps_card.setStyleSheet(
            f"QFrame {{ background: {c.BG_INPUT}; border-radius: 8px; }}")
        dg = QGridLayout(deps_card)
        dg.setContentsMargins(12, 12, 12, 12)
        dg.setSpacing(10)
        self._dep_cbs = {}
        for idx, name in enumerate(DEP_NAMES):
            cb = QCheckBox(name)
            cb.setStyleSheet(f"""
                QCheckBox {{ color: {c.TXT_MAIN}; font: 12px; spacing: 6px; }}
                QCheckBox::indicator {{ width: 18px; height: 18px; }}
            """)
            self._dep_cbs[name] = cb
            dg.addWidget(cb, idx // 3, idx % 3)
        lay.addWidget(deps_card)

        lay.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)
        back_btn = QPushButton("Back")
        back_btn.setFixedHeight(38)
        back_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: bold 13px;
                           border-radius: 9px; padding: 6px 26px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; border: 1px solid {c.ACCENT}; }}
        """)
        back_btn.clicked.connect(self._show_page1)
        btn_row.addWidget(back_btn)

        self._confirm_pfx_btn = QPushButton("Create Prefix")
        self._confirm_pfx_btn.setFixedHeight(38)
        self._confirm_pfx_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.SUCCESS}; color: #ffffff; font: bold 13px;
                           border-radius: 9px; padding: 6px 24px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        self._confirm_pfx_btn.clicked.connect(self._start_pfx)
        btn_row.addWidget(self._confirm_pfx_btn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)
        return w

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(12)

        header = QLabel("+  ADD A GAME")
        header.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 18px;")
        layout.addWidget(header)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._page1())
        self._stack.addWidget(self._page2())
        layout.addWidget(self._stack)

    def _show_page1(self):
        self._stack.setCurrentIndex(0)
        self._refresh_create()
        self._rescan()

    def _show_create_page(self):
        pfx = self._pfx_path()
        self._pfx_info.setText(
            f"This will create a new Wine prefix at:\n{pfx}\n\n"
            "Select the components to install, then confirm. The prefix is "
            "created in the background while you finish adding the game.")
        self._stack.setCurrentIndex(1)
        self._rescan()

    def _pfx_path(self):
        name = self._name.text().strip() or _suggest_name(self._exe_path) or "game"
        safe = "".join(ch for ch in name if ch.isalnum() or ch in " _-").strip() or "game"
        exe_dir = str(pathlib.Path(self._exe_path).parent) if self._exe_path else ""
        if exe_dir:
            return os.path.join(exe_dir, f"{safe}_pfx")
        return os.path.join(os.path.expanduser("~"), "Games", f"{safe}_pfx")

    def _start_pfx(self):
        prefix = self._pfx_path()
        self._prefix_path = prefix
        self._prefix_btn.setText(_elide(prefix, 36))
        self._prefix_btn.setToolTip(prefix)
        deps = [name for name, cb in self._dep_cbs.items() if cb.isChecked()]

        self._confirm_pfx_btn.setEnabled(False)
        self._confirm_pfx_btn.setText("Creating…")
        self._add_btn.setEnabled(False)
        self._stack.setCurrentIndex(0)
        self._show_page1()

        def work():
            ok = create_wine_prefix(prefix, deps)
            self.pfx_done_signal.emit(ok, prefix)

        threading.Thread(target=work, daemon=True).start()

    def _pfx_done(self, ok, prefix):
        self._confirm_pfx_btn.setEnabled(True)
        self._confirm_pfx_btn.setText("Create Prefix")
        self._add_btn.setEnabled(True)
        self._refresh_create()
        app = self.parent()
        toast = getattr(app, 'toast', None)
        if toast is not None:
            try:
                toast.show(f"Prefix {'created' if ok else 'failed'}: {os.path.basename(prefix)}")
            except Exception:
                pass

    # ---- modal events -----------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        if self.engine:
            QTimer.singleShot(0, self.engine.rescan)
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(120)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._pop_anim = anim
        anim.start()

    def _finish(self):
        name = self._name.text().strip()
        if not name:
            self._name.setFocus()
            return
        g_id = f"game_{os.urandom(2).hex()}"
        from launcher_pyqt.utils import generate_placeholder_art, derive_landscape
        from launcher_pyqt.config import ARTWORK_DIR
        out = str(ARTWORK_DIR)
        art_path = generate_placeholder_art(g_id, name, c.ACCENT, c.BG_PANEL, out)
        art_land = derive_landscape(g_id, name, c.ACCENT, c.BG_PANEL, out, art_path)
        self.result = {
            "gid": g_id, "name": name,
            "exe": self._exe_path,
            "prefix": self._prefix_path or self._pfx_path()
            if self._exe_path else str(pathlib.Path.home() / "Games" / "umu-prefixes" / g_id),
            "art": art_path or "",
            "art_land": art_land or "",
        }
        self.accept()

    def _cancel(self):
        self.result = None
        self.reject()
