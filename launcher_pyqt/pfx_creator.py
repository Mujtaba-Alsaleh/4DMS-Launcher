import os, subprocess, threading
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QCheckBox, QTextEdit,
                             QGridLayout, QScrollArea, QFileDialog, QButtonGroup,
                             QFrame)
from PyQt6.QtCore import QTimer, pyqtSignal
import colors as c


class PrefixCreator(QWidget):
    log_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(bool)

    def __init__(self, parent=None, browser_callback=None, on_finish_callback=None, on_close_callback=None):
        super().__init__(parent)
        self.browser_callback = browser_callback
        self.on_finish_callback = on_finish_callback
        self.on_close_callback = on_close_callback
        self.is_running = False

        self.prefix_path = os.path.expanduser("~/Games/new_pfx")
        self.arch = "win64"
        self.deps = {
            "vcrun2022": False, "dotnet48": False, "corefonts": False,
            "d3dx9": False, "faudio": False, "xna40": False, "physx": False
        }

        self.log_signal.connect(self._append_log)
        self.finish_signal.connect(self._finish_process)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        form = QVBoxLayout(inner)
        form.setSpacing(15)

        # Path row
        path_row = QHBoxLayout()
        lbl = QLabel("Prefix Path:")
        lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 16px;")
        path_row.addWidget(lbl)
        self.path_label = QLabel(self.prefix_path)
        self.path_label.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 16px;")
        path_row.addWidget(self.path_label)
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedHeight(35)
        browse_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.ACCENT}; color: {c.TXT_MAIN}; font: bold 14px;
                           border-radius: 6px; padding: 4px 12px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        browse_btn.clicked.connect(self._browse_path)
        path_row.addWidget(browse_btn)
        form.addLayout(path_row)

        # Architecture row
        arch_row = QHBoxLayout()
        arch_lbl = QLabel("Architecture:")
        arch_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 16px;")
        arch_row.addWidget(arch_lbl)
        self.arch_group = QButtonGroup(self)
        self.arch_64 = QPushButton("64-bit (win64)")
        self.arch_64.setCheckable(True)
        self.arch_64.setChecked(True)
        self.arch_64.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 14px;
                           border: 1px solid {c.ACCENT}; border-radius: 6px; padding: 6px 14px; }}
            QPushButton:checked {{ background: {c.ACCENT}; color: {c.BG_MAIN}; border: 1px solid {c.ACCENT}; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        self.arch_64.clicked.connect(lambda: setattr(self, 'arch', 'win64'))
        self.arch_group.addButton(self.arch_64)
        arch_row.addWidget(self.arch_64)
        self.arch_32 = QPushButton("32-bit (win32)")
        self.arch_32.setCheckable(True)
        self.arch_32.setStyleSheet(self.arch_64.styleSheet())
        self.arch_32.clicked.connect(lambda: setattr(self, 'arch', 'win32'))
        self.arch_group.addButton(self.arch_32)
        arch_row.addWidget(self.arch_32)
        form.addLayout(arch_row)

        # Dependencies
        deps_lbl = QLabel("Common Dependencies")
        deps_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 18px;")
        form.addWidget(deps_lbl)

        deps_card = QFrame()
        deps_card.setStyleSheet(f"QFrame {{ background: {c.BG_PANEL}; border-radius: 8px; padding: 12px; }}")
        deps_grid = QGridLayout(deps_card)
        deps_grid.setContentsMargins(12, 12, 12, 12)
        deps_grid.setSpacing(10)
        self.dep_checkboxes = {}
        for idx, name in enumerate(self.deps.keys()):
            cb = QCheckBox(name)
            cb.setStyleSheet(f"""
                QCheckBox {{ color: {c.TXT_MAIN}; font: 14px; spacing: 6px; }}
                QCheckBox::indicator {{ width: 18px; height: 18px; }}
            """)
            self.dep_checkboxes[name] = cb
            deps_grid.addWidget(cb, idx // 3, idx % 3)
        form.addWidget(deps_card)

        # Buttons
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Create Prefix & Install")
        self.start_btn.setFixedHeight(45)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.SUCCESS}; color: {c.BG_MAIN}; font: bold 16px;
                           border-radius: 8px; padding: 8px; }}
            QPushButton:hover {{ background: {c.get_dimmed_accent(c.SUCCESS, 0.8)}; }}
            QPushButton:disabled {{ background: #555; }}
        """)
        self.start_btn.clicked.connect(self._start_process)
        btn_row.addWidget(self.start_btn)
        if self.on_close_callback:
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setFixedHeight(45)
            cancel_btn.setStyleSheet(f"""
                QPushButton {{ background: {c.DANGER}; color: {c.BG_MAIN}; font: bold 16px;
                               border-radius: 8px; padding: 8px; }}
                QPushButton:hover {{ background: {c.DANGER_HOVER}; }}
            """)
            cancel_btn.clicked.connect(self.on_close_callback)
            btn_row.addWidget(cancel_btn)
        form.addLayout(btn_row)

        # Log
        log_lbl = QLabel("Installation Log")
        log_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 16px;")
        form.addWidget(log_lbl)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(400)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{ background: {c.BG_INPUT}; color: {c.TXT_DIM};
                         font: 12px Consolas; border: 1px solid {c.BG_FOCUS};
                         border-radius: 6px; padding: 6px; }}
        """)
        form.addWidget(self.log_text)

    def _browse_path(self):
        if self.browser_callback:
            self.browser_callback(self.path_label, False)
            new_path = self.path_label.text()
            if new_path and new_path != self.prefix_path:
                self.prefix_path = new_path
        else:
            path = QFileDialog.getExistingDirectory(self, "Select Prefix Directory",
                                                    os.path.expanduser("~"))
            if path:
                self.prefix_path = path
                self.path_label.setText(path)

    def _append_log(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def log(self, message):
        self.log_signal.emit(message)

    def _start_process(self):
        if self.is_running:
            return
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.start_btn.setText("Running...")
        threading.Thread(target=self._run_wine_tasks, daemon=True).start()

    def _run_wine_tasks(self):
        prefix = self.prefix_path
        arch = self.arch
        os.makedirs(prefix, exist_ok=True)

        self.log("=" * 50)
        self.log("Starting Wine Prefix Creation")
        self.log("=" * 50)
        self.log(f"Path: {prefix}")
        self.log(f"Architecture: {arch}\n")

        env = os.environ.copy()
        env["WINEPREFIX"] = prefix
        env["WINEARCH"] = arch

        self.log("[Step 1/2] Creating Wine Prefix...")
        try:
            proc = subprocess.Popen(
                ["wineboot", "--init"], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            for line in proc.stdout:
                self.log(line.strip())
            proc.wait()
            if proc.returncode != 0:
                self.log("Error creating prefix.")
                self.finish_signal.emit(False)
                return
            self.log("Prefix created successfully.\n")
        except Exception as e:
            self.log(f"Error: {str(e)}")
            self.finish_signal.emit(False)
            return

        selected_deps = [name for name, cb in self.dep_checkboxes.items() if cb.isChecked()]
        if not selected_deps:
            self.log("No dependencies selected. Done.")
            self.finish_signal.emit(True)
            return

        self.log(f"[Step 2/2] Installing: {', '.join(selected_deps)}\n")
        try:
            proc = subprocess.Popen(
                ["winetricks"] + selected_deps, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            for line in proc.stdout:
                self.log(line.strip())
            proc.wait()
            if proc.returncode == 0:
                self.log("\nInstallation Complete!")
            else:
                self.log("\nFinished with errors.")
        except Exception as e:
            self.log(f"Error: {str(e)}")

        if self.on_finish_callback:
            QTimer.singleShot(2000, self._finish_on_editor)
        else:
            self.finish_signal.emit(True)

    def _finish_process(self, success):
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.start_btn.setText("Create Prefix & Install")

    def _finish_on_editor(self):
        if self.on_finish_callback:
            self.on_finish_callback(self.prefix_path)

    def on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
