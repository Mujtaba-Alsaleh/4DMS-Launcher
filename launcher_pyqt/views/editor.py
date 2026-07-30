from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QComboBox, QFrame,
                             QScrollArea)
from PyQt6.QtCore import Qt, QTimer
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
        layout.setSpacing(12)

        # Title
        title = QLabel("GAME SETTINGS")
        title.setStyleSheet(f"color: {c.ACCENT}; font: bold 22px;")
        layout.addWidget(title)

        # Name
        name_lbl = QLabel("GAME NAME".upper())
        name_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px;")
        layout.addWidget(name_lbl)
        self.e_name = QLineEdit(data.get("name", ""))
        self.e_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.e_name.setStyleSheet(f"""
            QLineEdit {{ font: bold 24px; color: {c.ACCENT};
                          background: transparent; border: none;
                          border-bottom: 1px solid {c.BG_INPUT}; }}
            QLineEdit:focus {{ border-bottom: 2px solid {c.ACCENT}; }}
        """)
        layout.addWidget(self.e_name)

        # Divider
        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet(f"background: {c.BG_INPUT};")
        layout.addWidget(sep1)

        # ---- EXE row
        self.e_exe_lbl = QLabel(data.get("exe", ""))
        self._create_row(layout, "EXE Path", self.e_exe_lbl, is_file=True)

        # ---- WINEPREFIX row
        self.e_prefix_lbl = QLabel(data.get("prefix", ""))
        pfx_toggle = QPushButton("PFX Creator")
        pfx_toggle.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: bold 10px;
                           border-radius: 4px; padding: 4px 8px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; border: 1px solid {c.ACCENT}; }}
        """)
        pfx_toggle.clicked.connect(self._launch_pfx_creator)
        self._create_row(layout, "WINEPREFIX", self.e_prefix_lbl, is_file=False, extra_btn=pfx_toggle)

        # ---- UMU ID row
        umu_lbl = QLabel("UMU GAME ID".upper())
        umu_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px;")
        layout.addWidget(umu_lbl)
        store_row = QHBoxLayout()
        self.e_proton = QComboBox()
        self.e_proton.addItem("Default (UMU Internal)")
        for p in sorted(self.app.proton_paths.keys(), key=str.lower):
            self.e_proton.addItem(p)
        current = data.get("proton", "Default (UMU Internal)")
        idx = self.e_proton.findText(current)
        if idx >= 0:
            self.e_proton.setCurrentIndex(idx)
        self.e_proton.setStyleSheet(f"""
            QComboBox {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 12px;
                         border-radius: 6px; padding: 8px; }}
            QComboBox:hover {{ border: 1px solid {c.ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{ background: {c.BG_PANEL}; color: {c.TXT_MAIN};
                                             selection-background-color: {c.ACCENT}; }}
        """)
        store_row.addWidget(self.e_proton)
        umu_id = QLineEdit(data.get("GAMEID", ""))
        umu_id.setPlaceholderText("UMU Game ID (optional)")
        umu_id.setStyleSheet(f"""
            QLineEdit {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 12px;
                         border-radius: 6px; padding: 8px; }}
            QLineEdit:focus {{ border: 1px solid {c.ACCENT}; }}
        """)
        store_row.addWidget(umu_id)
        self.umu_id_lbl = umu_id
        layout.addLayout(store_row)

        # ---- Script row
        self.e_script_lbl = QLabel(data.get("script", ""))
        self._create_row(layout, "Launch Script (optional)", self.e_script_lbl, is_file=True)

        # Divider
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background: {c.BG_INPUT};")
        layout.addWidget(sep2)

        # ---- Gamescope toggle
        gs_row = QHBoxLayout()
        gs_lbl = QLabel("GAMESCOPE".upper())
        gs_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px;")
        gs_row.addWidget(gs_lbl)
        self.gs_on_var = data.get('gs_on', False)
        self.gs_toggle_btn = QPushButton("ON" if self.gs_on_var else "OFF")
        self.gs_toggle_btn.setStyleSheet(self._toggle_style(self.gs_on_var))
        self.gs_toggle_btn.clicked.connect(self._toggle_gamescope)
        gs_row.addStretch()
        gs_row.addWidget(self.gs_toggle_btn)
        layout.addLayout(gs_row)

        gs_dim_row = QHBoxLayout()
        gs_w_lbl = QLabel("W:")
        gs_w_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 11px;")
        gs_dim_row.addWidget(gs_w_lbl)
        self.gs_w = QLineEdit(data.get('gs_w', '1280'))
        self.gs_w.setFixedWidth(70)
        self.gs_w.setStyleSheet(f"""
            QLineEdit {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 12px;
                         border-radius: 4px; padding: 4px; text-align: center; }}
        """)
        gs_dim_row.addWidget(self.gs_w)
        gs_h_lbl = QLabel("H:")
        gs_h_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 11px;")
        gs_dim_row.addWidget(gs_h_lbl)
        self.gs_h = QLineEdit(data.get('gs_h', '720'))
        self.gs_h.setFixedWidth(70)
        self.gs_h.setStyleSheet(self.gs_w.styleSheet())
        gs_dim_row.addWidget(self.gs_h)
        gs_dim_row.addStretch()
        layout.addLayout(gs_dim_row)

        # ---- MangoHud toggle
        hud_row = QHBoxLayout()
        hud_lbl = QLabel("MANGO HUD".upper())
        hud_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px;")
        hud_row.addWidget(hud_lbl)
        self.useMangoHud = data.get('useMangoHud', False)
        self.useMangoHudToggle = QPushButton("ON" if self.useMangoHud else "OFF")
        self.useMangoHudToggle.setStyleSheet(self._toggle_style(self.useMangoHud))
        self.useMangoHudToggle.clicked.connect(self._toggle_mangohud)
        hud_row.addStretch()
        hud_row.addWidget(self.useMangoHudToggle)
        layout.addLayout(hud_row)

        # ---- LiveSplit toggle
        ls_row = QHBoxLayout()
        ls_lbl = QLabel("LIVESPLIT".upper())
        ls_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px;")
        ls_row.addWidget(ls_lbl)
        self.useLiveSplit = data.get('livesplit', False)
        self.useLiveSplitToggle = QPushButton("ON" if self.useLiveSplit else "OFF")
        self.useLiveSplitToggle.setStyleSheet(self._toggle_style(self.useLiveSplit))
        self.useLiveSplitToggle.clicked.connect(self._toggle_livesplit)
        ls_row.addStretch()
        ls_row.addWidget(self.useLiveSplitToggle)
        layout.addLayout(ls_row)

        if self.app.runningOnGamescope:
            self.useLiveSplitToggle.setEnabled(False)
            self.useLiveSplitToggle.setStyleSheet(f"""
                QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_DIM}; font: bold 11px;
                               border-radius: 4px; padding: 4px 12px; }}
            """)

        # ---- Notes
        notes_lbl = QLabel("NOTES".upper())
        notes_lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px;")
        layout.addWidget(notes_lbl)
        notes_input = QLineEdit(data.get("notes", ""))
        from launcher_pyqt.utils import normalize
        notes_input.setStyleSheet(f"""
            QLineEdit {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: 11px;
                         border-radius: 6px; padding: 8px; }}
            QLineEdit:focus {{ border: 1px solid {c.ACCENT}; }}
        """)
        self._notes_input = notes_input
        layout.addWidget(notes_input)

        # Action row
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
            self.app.engine.rescan(priority_widget=self.e_name)

    def _create_row(self, parent, label_text, value, is_file=True, extra_btn=None):
        row = QHBoxLayout()
        lbl = QLabel(label_text.upper())
        lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: bold 10px; min-width: 130px;")
        row.addWidget(lbl)
        val_lbl = value
        val_lbl.setStyleSheet(f"color: {c.TXT_MAIN}; font: 12px;")
        row.addWidget(val_lbl, 1)
        clear_btn = QPushButton("x")
        clear_btn.setFixedSize(24, 24)
        clear_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_DIM}; font: bold 12px;
                           border-radius: 12px; }}
            QPushButton:hover {{ background: {c.DANGER}; color: white; }}
        """)
        clear_btn.clicked.connect(lambda: val_lbl.setText(""))
        row.addWidget(clear_btn)
        browse_btn = QPushButton("Browse")
        browse_btn.setStyleSheet(f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_MAIN}; font: bold 10px;
                           border-radius: 4px; padding: 4px 8px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; border: 1px solid {c.ACCENT}; }}
        """)
        browse_btn.clicked.connect(lambda: self.app.browse(val_lbl, is_file))
        row.addWidget(browse_btn)
        if extra_btn:
            row.addWidget(extra_btn)
        parent.addLayout(row)

    def _toggle_style(self, on):
        if on:
            return f"""
                QPushButton {{ background: {c.SUCCESS}; color: white; font: bold 11px;
                               border-radius: 4px; padding: 4px 12px; }}
                QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
            """
        return f"""
            QPushButton {{ background: {c.BG_INPUT}; color: {c.TXT_DIM}; font: bold 11px;
                           border-radius: 4px; padding: 4px 12px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """

    def _toggle_gamescope(self):
        self.gs_on_var = not self.gs_on_var
        self.gs_toggle_btn.setText("ON" if self.gs_on_var else "OFF")
        self.gs_toggle_btn.setStyleSheet(self._toggle_style(self.gs_on_var))
        if self.gs_on_var:
            self.useLiveSplit = False
            self.useLiveSplitToggle.setText("OFF")
            self.useLiveSplitToggle.setStyleSheet(self._toggle_style(False))

    def _toggle_mangohud(self):
        self.useMangoHud = not self.useMangoHud
        self.useMangoHudToggle.setText("ON" if self.useMangoHud else "OFF")
        self.useMangoHudToggle.setStyleSheet(self._toggle_style(self.useMangoHud))

    def _toggle_livesplit(self):
        if self.gs_on_var:
            return
        self.useLiveSplit = not self.useLiveSplit
        self.useLiveSplitToggle.setText("ON" if self.useLiveSplit else "OFF")
        self.useLiveSplitToggle.setStyleSheet(self._toggle_style(self.useLiveSplit))

    def _launch_pfx_creator(self):
        gid = self.game_id
        app = self.app
        def _on_pfx_done(p):
            if p:
                app.config_data[gid]['prefix'] = p
            QTimer.singleShot(0, app.handle_back)
        app.create_pfx_menu(finish_callback=_on_pfx_done)

    def save(self):
        data = self.app.config_data[self.game_id]
        gs_active = self.gs_on_var
        from launcher_pyqt.umu_database import UMUDatabase
        umu_db = UMUDatabase()
        store = data.get('store', 'none')
        umu_text = self.umu_id_lbl.text().strip()
        if not umu_text:
            gid = self.app.config_data[self.game_id].get('GAMEID', '')
            if not gid:
                gid = umu_db.lookup(self.e_name.text().strip(), store)
            umu_text = gid
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
            "livesplit": self.useLiveSplit and not gs_active,
            "notes": self._notes_input.text(),
        })
        self.app.config_data[self.game_id] = data
        self.app.config_manager.save_data(self.app.config_data)
        self.app.show_dashboard(self.game_id)

    def delete(self):
        if self.app.game_process_manager.is_playing:
            return
        name = self.app.config_data[self.game_id].get('name', 'Unknown')
        msg = f'Delete "{name}" and all its data?'
        self.app.spawn_controller_confirm_modal(func=self._confirm_delete, msg=msg)

    def _confirm_delete(self):
        del self.app.config_data[self.game_id]
        self.app.config_manager.save_data(self.app.config_data)
        self.app.show_library()
