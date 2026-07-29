import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QComboBox, QFrame,
                             QScrollArea)
from PyQt6.QtCore import Qt
import colors as c


class EditorView(QWidget):
    def __init__(self, app, game_id):
        super().__init__()
        self.app = app
        self.game_id = game_id
        self.setStyleSheet("background: transparent;")
        self.e_name = None
        self.e_exe_lbl = None
        self.e_prefix_lbl = None
        self.e_script_lbl = None
        self.e_proton = None
        self.gs_on_var = False
        self.gs_toggle_btn = None
        self.gs_w = None
        self.gs_h = None
        self.useMangoHud = False
        self.useMangoHudToggle = None
        self.usePrefixCreatorForPFX = False
        self.usePrefixCreatorForPFXToggle = None
        self.umu_id_lbl = None
        self.useLiveSplit = False
        self.useLiveSplitToggle = None
        self._build()

    def _build(self):
        data = self.app.config_data[self.game_id]
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(0)

        # Game name
        self.e_name = QLineEdit()
        self.e_name.setText(data.get('name', ''))
        self.e_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.e_name.setStyleSheet(f"""
            QLineEdit {{ font: bold 24px; color: {c.ACCENT};
                         background: transparent; border: none;
                         border-bottom: 1px solid {c.ACCENT}; }}
            QLineEdit:focus {{ border-bottom: 2px solid {c.ACCENT}; }}
        """)
        self.e_name.textChanged.connect(self._on_name_changed)
        layout.addWidget(self.e_name)
        layout.addSpacing(24)

        # Section: FILES & DIRECTORIES
        sec1_title = QLabel("FILES & DIRECTORIES")
        sec1_title.setStyleSheet(f"color: {c.ACCENT}; font: bold 14px;")
        layout.addWidget(sec1_title)

        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet(f"background: {c.BG_FOCUS};")
        layout.addWidget(sep1)
        layout.addSpacing(12)

        self.e_exe_lbl, self.e_exe_btn = self._create_row(layout, "Executable", data.get('exe', ''), True)
        layout.addSpacing(6)
        pfx_toggle = QPushButton("Prefix Creator Mode: DISABLED")
        pfx_toggle.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.TXT_DIM}; font: bold 10px;
                           border: 1px solid {c.BG_FOCUS}; border-radius: 4px; padding: 4px 10px; }}
            QPushButton:hover {{ color: {c.ACCENT}; border-color: {c.ACCENT}; }}
        """)
        pfx_toggle.clicked.connect(lambda: self._toggle_pfx_creator(pfx_toggle, data))
        self.usePrefixCreatorForPFX = False
        self.usePrefixCreatorForPFXToggle = pfx_toggle
        self.e_prefix_lbl, self.e_prefix_btn = self._create_row(layout, "WINEPREFIX", data.get('prefix', ''), False, is_prefix=True, extra_btn=pfx_toggle)
        layout.addSpacing(6)

        self.e_script_lbl, _ = self._create_row(layout, "Pre-launch Script", data.get('script', ''), True)
        layout.addSpacing(6)

        # UMU ID
        id_row = QHBoxLayout()
        self.umu_id_lbl = QLabel(f"UMU-ID: {data.get('GAMEID', 'Not Configured')}")
        self.umu_id_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 11px Consolas;")
        id_row.addWidget(self.umu_id_lbl)
        id_row.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.ACCENT}; font: bold 11px;
                           border: none; padding: 4px 8px; }}
            QPushButton:hover {{ color: {c.ACCENT_HOVER}; }}
        """)
        refresh_btn.clicked.connect(lambda: self._refresh_umu_id(data))
        id_row.addWidget(refresh_btn)
        layout.addLayout(id_row)
        layout.addSpacing(20)

        # Section: COMPATIBILITY & PERFORMANCE
        sec2_title = QLabel("COMPATIBILITY & PERFORMANCE")
        sec2_title.setStyleSheet(f"color: {c.ACCENT}; font: bold 14px;")
        layout.addWidget(sec2_title)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background: {c.BG_FOCUS};")
        layout.addWidget(sep2)
        layout.addSpacing(12)

        # Proton
        compat_lbl = QLabel("Compatibility Layer")
        compat_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 11px; padding: 2px 0;")
        layout.addWidget(compat_lbl)

        self.e_proton = QComboBox()
        self.e_proton.addItems(list(self.app.proton_paths.keys()))
        self.e_proton.setCurrentText(data.get('proton', "Default (UMU Internal)"))
        self.e_proton.setStyleSheet(f"""
            QComboBox {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN};
                         font: 12px; border-radius: 6px; padding: 8px; }}
            QComboBox::drop-down {{ border: none; }}
        """)
        layout.addWidget(self.e_proton)
        layout.addSpacing(10)

        # Gamescope
        self.gs_on_var = data.get('gs_on', False)
        gs_row = QHBoxLayout()
        self.gs_toggle_btn = QPushButton(
            "GAMESCOPE VIRTUAL DISPLAY" + ("  ON" if self.gs_on_var else "  OFF")
        )
        self.gs_toggle_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.SUCCESS if self.gs_on_var else c.DANGER}; font: bold 11px;
                           border: 1px solid {c.SUCCESS if self.gs_on_var else c.DANGER};
                           border-radius: 6px; padding: 8px 14px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        self.gs_toggle_btn.clicked.connect(self._toggle_gamescope)
        gs_row.addWidget(self.gs_toggle_btn)

        gs_res_lbl = QLabel("W:")
        gs_res_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 11px; padding-left: 12px;")
        gs_row.addWidget(gs_res_lbl)
        self.gs_w = QLineEdit(data.get('gs_w', '1280'))
        self.gs_w.setFixedWidth(60)
        self.gs_w.setStyleSheet(f"""
            QLineEdit {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN};
                         font: 11px Consolas; border-radius: 4px; padding: 6px; }}
        """)
        gs_row.addWidget(self.gs_w)
        sep_lbl = QLabel("x")
        sep_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 12px;")
        gs_row.addWidget(sep_lbl)
        self.gs_h = QLineEdit(data.get('gs_h', '720'))
        self.gs_h.setFixedWidth(60)
        self.gs_h.setStyleSheet(self.gs_w.styleSheet())
        gs_row.addWidget(self.gs_h)
        gs_row.addStretch()
        layout.addLayout(gs_row)
        layout.addSpacing(8)

        # MangoHud
        self.useMangoHud = data.get('useMangoHud', False)
        self.useMangoHudToggle = QPushButton(
            "MANGO HUD" + ("  ON" if self.useMangoHud else "  OFF")
        )
        self.useMangoHudToggle.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.SUCCESS if self.useMangoHud else c.DANGER}; font: bold 11px;
                           border: 1px solid {c.SUCCESS if self.useMangoHud else c.DANGER};
                           border-radius: 6px; padding: 8px 14px; text-align: left; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        self.useMangoHudToggle.clicked.connect(self._toggle_mangohud)
        layout.addWidget(self.useMangoHudToggle)
        layout.addSpacing(8)

        # LiveSplit
        self.useLiveSplit = data.get('livesplit', False)
        gs_active = self.gs_on_var
        if gs_active:
            self.useLiveSplit = False
            ls_text = "LIVE SPLIT  OFF (Gamescope)"
            ls_color = c.BG_INPUT
        else:
            ls_text = "LIVE SPLIT" + ("  ON" if self.useLiveSplit else "  OFF")
            ls_color = c.SUCCESS if self.useLiveSplit else c.DANGER
        self.useLiveSplitToggle = QPushButton(ls_text)
        self.useLiveSplitToggle.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {ls_color}; font: bold 11px;
                           border: 1px solid {ls_color};
                           border-radius: 6px; padding: 8px 14px; text-align: left; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        if gs_active:
            self.useLiveSplitToggle.setEnabled(False)
        else:
            self.useLiveSplitToggle.clicked.connect(self._toggle_livesplit)
        layout.addWidget(self.useLiveSplitToggle)
        layout.addSpacing(20)

        # Actions
        act_row = QHBoxLayout()
        act_row.setSpacing(12)
        save_btn = QPushButton("SAVE CHANGES")
        save_btn.setFixedSize(220, 48)
        save_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.SUCCESS}; font: bold 14px;
                           border: 1px solid {c.SUCCESS}; border-radius: 8px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; color: {c.TXT_MAIN}; }}
        """)
        save_btn.clicked.connect(self.save)
        act_row.addWidget(save_btn)

        del_btn = QPushButton("DELETE GAME")
        del_btn.setFixedSize(150, 48)
        del_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.DANGER}; font: bold 13px;
                           border: 1px solid {c.DANGER}; border-radius: 8px; }}
            QPushButton:hover {{ background: {c.DANGER_HOVER}; color: {c.TXT_MAIN}; }}
        """)
        del_btn.clicked.connect(self.delete)
        act_row.addWidget(del_btn)
        act_row.addStretch()
        layout.addLayout(act_row)

        layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

        if self.app.engine:
            self.app.engine.rebuild_nav_map(priority_widget=self.e_name)

    def _create_row(self, parent, label_text, value, is_file=True, is_prefix=False, extra_btn=None):
        row = QHBoxLayout()
        lbl = QLabel(label_text.upper())
        lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px; min-width: 130px;")
        row.addWidget(lbl)
        val_lbl = QLabel(value if value else "")
        val_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: 12px;")
        row.addWidget(val_lbl, 1)
        clear_btn = QPushButton("x")
        clear_btn.setFixedSize(24, 24)
        clear_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.DANGER}; font: bold 12px;
                           border: none; }}
            QPushButton:hover {{ background: {c.DANGER_HOVER}; border-radius: 4px; }}
        """)
        clear_btn.clicked.connect(lambda: val_lbl.setText(""))
        row.addWidget(clear_btn)
        if extra_btn:
            row.addWidget(extra_btn)
        browse_btn = QPushButton("Browse" if is_file else "Folder")
        browse_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.ACCENT}; font: bold 11px;
                           border: none; padding: 4px 10px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; border-radius: 4px; }}
        """)
        if is_prefix:
            browse_btn.clicked.connect(lambda: self._browse_prefix(val_lbl))
        else:
            browse_btn.clicked.connect(lambda: self.app.browse(val_lbl, is_file))
        row.addWidget(browse_btn)
        parent.addLayout(row)
        return val_lbl, browse_btn

    def _browse_prefix(self, label):
        if self.usePrefixCreatorForPFX:
            self._open_pfx_creator(label)
        else:
            self.app.browse(label, False)

    def _open_pfx_creator(self, label):
        from launcher_pyqt.pfx_creator import PrefixCreator
        from PyQt6.QtWidgets import QDialog, QVBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("PFX Creator")
        dialog.resize(800, 700)

        def on_finish(path):
            label.setText(path)
            dialog.accept()

        def on_close():
            dialog.reject()

        pfx = PrefixCreator(parent=dialog, browser_callback=self.app.browse,
                            on_finish_callback=on_finish, on_close_callback=on_close)
        layout = QVBoxLayout(dialog)
        layout.addWidget(pfx)
        dialog.setLayout(layout)
        dialog.exec()

    def _on_name_changed(self, new_name):
        data = self.app.config_data[self.game_id]
        umu_id = self.app.umu_db.lookup(new_name, data.get('store', 'none'))
        if self.umu_id_lbl:
            self.umu_id_lbl.setText(f"UMU-ID: {umu_id}")

    def _toggle_gamescope(self):
        self.gs_on_var = not self.gs_on_var
        text = "GAMESCOPE VIRTUAL DISPLAY" + ("  ON" if self.gs_on_var else "  OFF")
        color = c.SUCCESS if self.gs_on_var else c.DANGER
        self.gs_toggle_btn.setText(text)
        self.gs_toggle_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {color}; font: bold 11px;
                           border: 1px solid {color};
                           border-radius: 6px; padding: 8px 14px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        if self.gs_on_var:
            self.useLiveSplit = False
            self.useLiveSplitToggle.setEnabled(False)
            self.useLiveSplitToggle.setText("LIVE SPLIT  OFF (Gamescope)")
            self.useLiveSplitToggle.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {c.BG_FOCUS}; font: bold 11px;
                               border: 1px solid {c.BG_FOCUS};
                               border-radius: 6px; padding: 8px 14px; }}
            """)
        else:
            self.useLiveSplitToggle.setEnabled(True)
            self._update_ls_button()

    def _toggle_mangohud(self):
        self.useMangoHud = not self.useMangoHud
        color = c.SUCCESS if self.useMangoHud else c.DANGER
        self.useMangoHudToggle.setText("MANGO HUD" + ("  ON" if self.useMangoHud else "  OFF"))
        self.useMangoHudToggle.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {color}; font: bold 11px;
                           border: 1px solid {color};
                           border-radius: 6px; padding: 8px 14px; text-align: left; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)

    def _toggle_pfx_creator(self, btn, data):
        self.usePrefixCreatorForPFX = not self.usePrefixCreatorForPFX
        if self.usePrefixCreatorForPFX:
            btn.setText("Prefix Creator Mode: ACTIVE")
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {c.SUCCESS}; font: bold 11px;
                               border: none; text-align: left; padding: 4px 2px; }}
                QPushButton:hover {{ color: {c.ACCENT_HOVER}; }}
            """)
        else:
            btn.setText("Prefix Creator Mode: DISABLED")
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {c.TXT_DIM}; font: bold 11px;
                               border: none; text-align: left; padding: 4px 2px; }}
                QPushButton:hover {{ color: {c.ACCENT}; }}
            """)

    def _update_ls_button(self):
        color = c.SUCCESS if self.useLiveSplit else c.DANGER
        text = "LIVE SPLIT" + ("  ON" if self.useLiveSplit else "  OFF")
        self.useLiveSplitToggle.setText(text)
        self.useLiveSplitToggle.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {color}; font: bold 11px;
                           border: 1px solid {color};
                           border-radius: 6px; padding: 8px 14px; text-align: left; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)

    def _toggle_livesplit(self):
        self.useLiveSplit = not self.useLiveSplit
        self._update_ls_button()

    def _refresh_umu_id(self, data):
        umu_id = self.app.umu_db.lookup(data.get('name', ''), data.get('store', 'none'))
        if self.umu_id_lbl:
            self.umu_id_lbl.setText(f"UMU-ID: {umu_id}")

    def save(self):
        gs_active = self.gs_on_var
        data = self.app.config_data[self.game_id]
        umu_text = self.umu_id_lbl.text().replace("UMU-ID: ", "") if self.umu_id_lbl else ""
        data.update({
            "name": self.e_name.text(),
            "exe": self.e_exe_lbl.text(),
            "prefix": self.e_prefix_lbl.text(),
            "proton": self.e_proton.currentText(),
            "gs_on": gs_active,
            "gs_w": self.gs_w.text(),
            "gs_h": self.gs_h.text(),
            "script": self.e_script_lbl.text(),
            "GAMEID": umu_text,
            "useMangoHud": self.useMangoHud,
            "livesplit": self.useLiveSplit and not gs_active
        })
        self.app.config_data[self.game_id] = data
        self.app.config_manager.save_data(self.app.config_data)
        self.app.show_dashboard(self.game_id)

    def delete(self):
        del self.app.config_data[self.game_id]
        self.app.config_manager.save_data(self.app.config_data)
        self.app.show_library()
