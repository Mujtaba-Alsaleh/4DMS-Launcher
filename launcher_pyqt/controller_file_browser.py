import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QWidget, QGridLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from launcher_pyqt.controller_confirm_modal import ControllerConfirmModal
import colors as c


class ControllerFileBrowser(QDialog):
    def __init__(self, parent, is_file=True, is_art=False, callback=None, engine=None):
        super().__init__(parent)
        self.is_file = is_file
        self.is_art = is_art
        self.callback = callback
        self.current_path = os.path.expanduser("~")
        self.engine = engine
        self.num_cols = 4
        self.allowed_file_extensions = (".jpg", ".png", ".webp", ".jpeg") if is_art else (".exe", ".sh")

        self.setWindowTitle("Select Path")
        self.resize(1000, 700)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Path bar
        path_frame = QWidget()
        path_frame.setStyleSheet(f"background: {c.BG_INPUT}; border-radius: 6px;")
        path_row = QHBoxLayout(path_frame)
        path_row.setContentsMargins(12, 8, 12, 8)
        loc_lbl = QLabel("Location:")
        loc_lbl.setStyleSheet(f"color: {c.ACCENT}; font: bold 11px;")
        path_row.addWidget(loc_lbl)
        self._path_label = QLabel(self.current_path)
        self._path_label.setStyleSheet(f"color: {c.TXT_MAIN}; font: 12px;")
        self._path_label.setWordWrap(True)
        path_row.addWidget(self._path_label, 1)
        layout.addWidget(path_frame)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        if not self.is_file:
            select_btn = QPushButton("Select This Directory")
            select_btn.setStyleSheet(f"""
                QPushButton {{ background: {c.SUCCESS}; color: white; font: bold 13px;
                               border-radius: 6px; padding: 8px 18px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
            """)
            select_btn.clicked.connect(lambda: self._finish(self.current_path))
            toolbar.addWidget(select_btn)

        back_btn = QPushButton("\u2190  Up")
        back_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 12px;
                           border-radius: 6px; padding: 8px 14px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; border: 1px solid {c.ACCENT}; }}
        """)
        back_btn.clicked.connect(lambda: self._handle_select(".."))
        toolbar.addWidget(back_btn)

        if not self.is_file:
            new_btn = QPushButton("+ New Folder")
            new_btn.setStyleSheet(f"""
                QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 12px;
                               border-radius: 6px; padding: 8px 14px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; border: 1px solid {c.ACCENT}; }}
            """)
            new_btn.clicked.connect(self._ask_directory_creation)
            toolbar.addWidget(new_btn)

        toolbar.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.DANGER}; font: bold 12px;
                           border: 1px solid {c.DANGER}; border-radius: 6px; padding: 8px 16px; }}
            QPushButton:hover {{ background: {c.DANGER_HOVER}; color: {c.TXT_MAIN}; }}
        """)
        cancel_btn.clicked.connect(self._cancel)
        toolbar.addWidget(cancel_btn)
        layout.addLayout(toolbar)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ border: 1px solid {c.BG_FOCUS}; border-radius: 8px;
                           background: transparent; }}
            QScrollBar:vertical {{ background: {c.BG_INPUT}; width: 8px; border-radius: 4px; }}
            QScrollBar::handle:vertical {{ background: {c.ACCENT}; border-radius: 4px;
                                            min-height: 30px; }}
            QScrollBar::add-line:vertical {{ height: 0; }}
            QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self.inner = QWidget()
        self.inner.setStyleSheet("background: transparent;")
        self.scroll.setWidget(self.inner)
        layout.addWidget(self.scroll)

        self._grid_layout = QGridLayout()
        self._grid_layout.setSpacing(8)
        inner_layout = QVBoxLayout(self.inner)
        inner_layout.setContentsMargins(12, 12, 12, 12)
        inner_layout.addLayout(self._grid_layout)
        inner_layout.addStretch()

        self._populate()

    def _populate(self):
        self._clear_grid()
        self._path_label.setText(self.current_path)
        self.setWindowTitle(f"Select Path \u2014 {os.path.basename(self.current_path) or self.current_path}")

        try:
            items = sorted(os.listdir(self.current_path))
            entries = []
            for i in items:
                full = os.path.join(self.current_path, i)
                if os.path.isdir(full):
                    entries.append((i, full, True))
                elif self.is_file and i.lower().endswith(self.allowed_file_extensions):
                    entries.append((i, full, False))
        except PermissionError:
            perm_lbl = QLabel("Permission Denied")
            perm_lbl.setStyleSheet(f"color: {c.DANGER}; font: 18px; padding: 40px;")
            perm_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid_layout.addWidget(perm_lbl, 1, 0, 1, self.num_cols)
            return

        if not entries:
            empty_lbl = QLabel("No matching items")
            empty_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 14px; padding: 40px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid_layout.addWidget(empty_lbl, 1, 0, 1, self.num_cols)
            return

        num_cols = self.num_cols
        for idx, (item, full_path, is_dir) in enumerate(entries):
            icon = "\U0001f4c1" if is_dir else "\U0001f4c4"
            display = f"{icon}  {item}"

            btn = QPushButton(display)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(f"""
                QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 12px;
                               border-radius: 6px; padding: 12px 10px; text-align: left; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; border: 1px solid {c.ACCENT}; }}
            """)
            btn.clicked.connect(lambda checked=False, p=full_path: self._handle_select(p))
            self._grid_layout.addWidget(btn, idx // num_cols, idx % num_cols)

        if self.engine:
            self.engine.rebuild_nav_map_file_browser(self)

    def _clear_grid(self):
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
            else:
                sub = item.layout()
                if sub:
                    while sub.count():
                        child = sub.takeAt(0)
                        cw = child.widget()
                        if cw:
                            cw.setParent(None)
                            cw.deleteLater()

    def _handle_select(self, path):
        if path == "..":
            new_path = os.path.dirname(self.current_path)
        else:
            new_path = path
        if os.path.isdir(new_path):
            self.current_path = new_path
            self._populate()
        else:
            self._finish(new_path)

    def _cleanup(self):
        if self.engine:
            self.engine.in_file_browser = False
            self.engine.rebuild_nav_map()

    def _finish(self, path):
        if self.callback:
            self.callback(path)
        self._cleanup()
        self.accept()

    def _cancel(self):
        self._cleanup()
        self.reject()

    def closeEvent(self, event):
        self._cleanup()
        event.accept()

    def scroll_to_selected(self, selected_index):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(int(selected_index / self.num_cols) * 90)

    def _create_directory(self):
        path = os.path.join(self.current_path, "pfx")
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        self._populate()

    def _on_user_decision(self, confirmed):
        if self.engine:
            self.engine.rebuild_nav_map_file_browser(self)
        if confirmed:
            self._create_directory()

    def _ask_directory_creation(self):
        modal = ControllerConfirmModal(self, engine=self.engine,
                                       on_result=self._on_user_decision,
                                       msg=f"Create new folder at\n{os.path.join(self.current_path, 'pfx')}?")
        modal.exec()
