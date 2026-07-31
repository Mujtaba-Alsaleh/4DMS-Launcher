from PyQt6.QtWidgets import (QFrame, QPushButton, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QTextEdit, QPlainTextEdit,
                             QApplication)
import colors as c

_KEYS_ABC = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "back"],
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "enter"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l", ",", "."],
    ["shift", "z", "x", "c", "v", "b", "n", "m", "shift"],
    ["sym", "space", "close"],
]

_KEYS_SYM = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "back"],
    ["-", "_", "/", "\\", "@", "#", "$", "%", "&", "*", "enter"],
    ["(", ")", "[", "]", "{", "}", "=", "+", ";", ":", "\""],
    ["shift", "!", "?", "'", "<", ">", "|", "~", "shift"],
    ["abc", "space", "close"],
]

_KINDS = {
    "back": "back", "enter": "enter", "shift": "shift", "space": "space",
    "close": "close", "sym": "sym", "abc": "abc",
}

_KEY_TEXT = {
    "back": "\u232b",
    "enter": "ENTER",
    "shift": "SHIFT",
    "space": "SPACE",
    "close": "\u2715",
    "sym": "?123",
    "abc": "ABC",
}

_SPECIAL_STYLE = ("shift", "sym", "abc", "enter", "close", "back")


class OnScreenKeyboard(QFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._shift = False
        self._sym = False
        self._last_target = None
        self._rows = []
        self.setStyleSheet(
            f"background: {c.BG_PANEL}; border: 2px solid {c.BG_INPUT}; "
            f"border-radius: 14px;"
        )
        self._build()
        self.hide()

    def _key_style(self, special=False):
        bg = c.BG_FOCUS if special else c.BG_INPUT
        return f"""
            QPushButton {{ background: {bg}; color: {c.TXT_MAIN}; font: bold 14px;
                           border: 1px solid {c.BG_INPUT}; border-radius: 8px; }}
            QPushButton:hover {{ border: 1px solid {c.ACCENT}; }}
        """

    @property
    def rows(self):
        return self._rows

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        rows = _KEYS_SYM if self._sym else _KEYS_ABC
        for row in rows:
            hl = QHBoxLayout()
            hl.setSpacing(6)
            hl.addStretch(1)
            buttons = []
            for label in row:
                b = QPushButton("")
                b.setFixedHeight(46)
                b.setStyleSheet(self._key_style(label in _SPECIAL_STYLE))
                b.osk_key = True
                b.key_kind = _KINDS.get(label, "char")
                b.char = label
                b.clicked.connect(lambda checked=False, k=b: self._on_key(k))
                if label == "space":
                    hl.addWidget(b, 1)
                else:
                    hl.addWidget(b)
                buttons.append(b)
            hl.addStretch(1)
            layout.addLayout(hl)
            self._rows.append(buttons)
        self._relabel()

    def _relabel(self):
        rows = _KEYS_SYM if self._sym else _KEYS_ABC
        for r, row in enumerate(rows):
            for c, label in enumerate(row):
                b = self._rows[r][c]
                kind = _KINDS.get(label, "char")
                b.key_kind = kind
                b.char = label
                if kind == "char":
                    text = label.upper() if (self._shift and label.isalpha()) else label
                    text = text.replace("&", "&&")
                    b.setFixedSize(52, 46)
                elif kind == "space":
                    text = "SPACE"
                    b.setFixedHeight(46)
                elif kind == "shift":
                    text = "SHIFT" + (" \u25cf" if self._shift else "")
                    b.setFixedSize(82, 46)
                else:
                    text = _KEY_TEXT[kind]
                    b.setFixedSize(82 if kind in ("back", "enter") else 64, 46)
                b.setText(text)
                b.setStyleSheet(self._key_style(kind in _SPECIAL_STYLE))

    def _focus_target(self):
        fw = QApplication.focusWidget()
        if isinstance(fw, (QLineEdit, QTextEdit, QPlainTextEdit)):
            self._last_target = fw
            return fw
        t = self._last_target
        if t is not None:
            try:
                t.winId()
            except RuntimeError:
                self._last_target = None
                return None
        return t

    def _safe_call(self, t, func):
        if t is None:
            return
        try:
            func(t)
        except RuntimeError:
            self._last_target = None

    def _insert(self, text):
        t = self._focus_target()
        if t is None:
            return
        if isinstance(t, QLineEdit):
            self._safe_call(t, lambda x: x.insert(text))
        else:
            self._safe_call(t, lambda x: x.insertPlainText(text))

    def _backspace(self):
        t = self._focus_target()
        if t is None:
            return
        if isinstance(t, QLineEdit):
            self._safe_call(t, lambda x: x.backspace())
        else:
            def f(x):
                cur = x.textCursor()
                cur.deletePreviousChar()
                x.setTextCursor(cur)
            self._safe_call(t, f)

    def _enter(self):
        t = self._focus_target()
        if t is None:
            self._close_via_engine()
            return
        if isinstance(t, QLineEdit):
            self._close_via_engine()
        else:
            def f(x):
                cur = x.textCursor()
                cur.insertText("\n")
                x.setTextCursor(cur)
            self._safe_call(t, f)

    def _close_via_engine(self):
        eng = getattr(self.app, 'engine', None)
        if eng is not None and hasattr(eng, 'close_keyboard'):
            eng.close_keyboard()
        else:
            self.close()

    def _on_key(self, b):
        kind = getattr(b, 'key_kind', 'char')
        if kind == "char":
            text = b.char
            if self._shift and text.isalpha():
                text = text.upper()
                self._shift = False
                self._relabel()
            self._insert(text)
        elif kind == "space":
            self._insert(" ")
        elif kind == "back":
            self._backspace()
        elif kind == "enter":
            self._enter()
        elif kind == "shift":
            self._shift = not self._shift
            self._relabel()
        elif kind in ("sym", "abc"):
            self._sym = not self._sym
            self._shift = False
            self._relabel()
        elif kind == "close":
            self._close_via_engine()

    def open(self):
        fw = QApplication.focusWidget()
        if isinstance(fw, (QLineEdit, QTextEdit, QPlainTextEdit)):
            self._last_target = fw
        self._shift = False
        self._sym = False
        self._relabel()
        self.show()
        self._reposition()

    def close(self):
        self.hide()
        self._last_target = None

    def _reposition(self):
        p = self.parentWidget()
        if p is None:
            return
        pw = p.width()
        ph = p.height()
        w = min(pw - 24, 1000)
        self.setFixedWidth(w)
        self.adjustSize()
        self.setFixedSize(w, self.height())
        self.move((pw - w) // 2, max(8, ph - self.height() - 46))
        self.raise_()
