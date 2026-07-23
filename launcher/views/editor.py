import os
import pathlib
import customtkinter as ctk
import colors as c
from pfx_creator import PrefixCreator


class EditorView(ctk.CTkFrame):
    def __init__(self, parent, app, game_id):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.game_id = game_id
        self.pack(fill="both", expand=True)

        self.e_name = None
        self.e_exe_btn = None
        self.e_exe_lbl = None
        self.e_prefix_btn = None
        self.e_prefix_lbl = None
        self.e_script_btn = None
        self.e_script_lbl = None
        self.e_proton = None
        self.gs_on_var = None
        self.gs_toggle_btn = None
        self.gs_w = None
        self.gs_h = None
        self.useMangoHud = None
        self.useMangoHudToggle = None
        self.usePrefixCreatorForPFX = None
        self.usePrefixCreatorForPFXToggle = None
        self.umu_id_lbl = None
        self.umu_id_btn = None

        self.app.current_view = self
        self._build()

    def _build(self):
        data = self.app.games[self.game_id]

        main_layout = ctk.CTkFrame(self, fg_color="transparent")
        main_layout.pack(fill="both", expand=True, padx=20, pady=(10, 5))

        header_frame = ctk.CTkFrame(main_layout, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header_frame, text="GAME MANAGEMENT",
            font=("Arial", 11, "bold"), text_color=c.TXT_DIM
        ).pack(anchor="center")

        def on_name_changed(new_name):
            data['name'] = new_name
            umu_id = self.app.umu_db.lookup(new_name, data.get('store', 'none'))
            print(f"UMU ID for '{new_name}': {umu_id}")
            if self.umu_id_lbl is not None:
                self.umu_id_lbl.configure(text=umu_id)

        self.e_name = ctk.CTkEntry(
            header_frame, font=("Arial", 24, "bold"), justify="center",
            fg_color="transparent", border_color=c.ACCENT, border_width=1,
            text_color=c.ACCENT
        )
        self.e_name.insert(0, data['name'])
        self.e_name.pack(pady=(2, 0), anchor="center", fill="x")

        def _save_name(e=None):
            new_name = self.e_name.get().strip()
            if new_name and new_name != data['name']:
                on_name_changed(new_name)
            self.app.focus_set()

        self.e_name.bind("<Return>", _save_name)
        self.e_name.bind("<Escape>", lambda e: (self.e_name.delete(0, "end"), self.e_name.insert(0, data['name']), self.app.focus_set()))

        layout_grid = ctk.CTkFrame(main_layout, fg_color="transparent")
        layout_grid.pack(fill="both", expand=True)
        layout_grid.grid_columnconfigure(0, weight=1, uniform="columns")
        layout_grid.grid_columnconfigure(1, weight=1, uniform="columns")

        # LEFT CARD: DIRECTORIES & PATHS
        path_card = ctk.CTkFrame(layout_grid, fg_color=c.BG_PANEL, corner_radius=12, border_color=c.BG_FOCUS, border_width=1)
        path_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=5)

        inner_left = ctk.CTkFrame(path_card, fg_color="transparent")
        inner_left.pack(fill="both", expand=True, padx=15, pady=12)

        ctk.CTkLabel(inner_left, text="FILES & DIRECTORIES", font=("Arial", 13, "bold"), text_color=c.ACCENT).pack(anchor="w", pady=(0, 8))

        self.e_exe_btn, self.e_exe_lbl = self._create_setting_row(inner_left, "Executable Path", data['exe'], True)
        self.e_prefix_btn, self.e_prefix_lbl = self._create_setting_row(inner_left, "WINEPREFIX Path", data['prefix'], False)

        self.usePrefixCreatorForPFX = ctk.BooleanVar(value=False)

        def toggle_use_pfx_creator():
            current_val = self.usePrefixCreatorForPFX.get()
            self.usePrefixCreatorForPFX.set(not current_val)
            new_val = self.usePrefixCreatorForPFX.get()
            self.usePrefixCreatorForPFXToggle.configure(
                text="Prefix Creator Mode: ACTIVE" if new_val else "Prefix Creator Mode: DISABLED",
                fg_color=c.SUCCESS if new_val else c.BG_INPUT
            )
            if new_val:
                self.e_prefix_btn.configure(command=self._open_pfx_creator, text="\U0001f6e0\ufe0f Setup Prefix")
            else:
                self.e_prefix_btn.configure(command=lambda: self.app.browse(self.e_prefix_lbl, False), text="\U0001f4c1 Browse Folder")

        self.usePrefixCreatorForPFXToggle = ctk.CTkButton(
            inner_left, text="Prefix Creator Mode: DISABLED", font=("Arial", 11, "bold"), height=34,
            fg_color=c.BG_INPUT, text_color=c.TXT_MAIN, hover_color=c.ACCENT_HOVER, command=toggle_use_pfx_creator
        )
        self.usePrefixCreatorForPFXToggle.pack(fill="x", pady=(4, 8))

        self.e_script_btn, self.e_script_lbl = self._create_setting_row(inner_left, "Pre-launch Script Path", data['script'], True)

        ctk.CTkFrame(inner_left, height=6, fg_color="transparent").pack()

        id_group = ctk.CTkFrame(inner_left, fg_color=c.BG_INPUT, height=38, corner_radius=6)
        id_group.pack(fill="x", pady=(6, 0))

        self.umu_id_lbl = ctk.CTkLabel(id_group, text=f"UMU-ID: {data.get('GAMEID', 'Not Configured')}", font=("Consolas", 11), text_color=c.TXT_DIM)
        self.umu_id_lbl.pack(side="left", padx=12, fill="y")

        self.umu_id_btn = ctk.CTkButton(
            id_group, text="\U0001f504 Refresh", width=80, height=26, fg_color=c.ACCENT, text_color=c.BG_MAIN, font=("Arial", 11, "bold"), hover_color=c.ACCENT_HOVER,
            command=lambda: self._refresh_umu_id(data['name'], data.get('store', 'none'))
        )
        self.umu_id_btn.pack(side="right", padx=6, pady=6)

        # RIGHT CARD: PERFORMANCE & RUNTIME
        perf_card = ctk.CTkFrame(layout_grid, fg_color=c.BG_PANEL, corner_radius=12, border_color=c.BG_FOCUS, border_width=1)
        perf_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=5)

        inner_right = ctk.CTkFrame(perf_card, fg_color="transparent")
        inner_right.pack(fill="both", expand=True, padx=15, pady=12)

        ctk.CTkLabel(inner_right, text="PERFORMANCE", font=("Arial", 13, "bold"), text_color=c.ACCENT).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(inner_right, text="Compatibility Layer", font=("Arial", 11, "bold"), text_color=c.TXT_DIM).pack(anchor="w", pady=(0, 2))
        self.e_proton = ctk.CTkOptionMenu(
            inner_right, values=list(self.app.proton_paths.keys()),
            height=36, fg_color=c.BG_INPUT, button_color=c.BG_FOCUS, dynamic_resizing=False, font=("Arial", 12)
        )
        self.e_proton.set(data.get('proton', "Default (UMU Internal)"))
        self.e_proton.pack(fill="x", pady=(0, 10))

        gs_box = ctk.CTkFrame(inner_right, fg_color=c.BG_INPUT, corner_radius=8)
        gs_box.pack(fill="x", pady=(0, 8))

        gs_inner = ctk.CTkFrame(gs_box, fg_color="transparent")
        gs_inner.pack(fill="both", expand=True, padx=12, pady=12)

        self.gs_on_var = ctk.BooleanVar(value=data.get('gs_on', False))
        init_val = self.gs_on_var.get()
        self.gs_toggle_btn = ctk.CTkButton(
            gs_inner,
            text="GAMESCOPE VIRTUAL DISPLAY: ENABLED" if init_val else "GAMESCOPE VIRTUAL DISPLAY: DISABLED",
            font=("Arial", 11, "bold"),
            fg_color=c.SUCCESS if init_val else c.DANGER,
            hover_color=c.ACCENT_HOVER, height=34,
            command=self._toggle_gamescope_ui,
            state="normal" if self.app.has_gamescope else "disabled"
        )
        self.gs_toggle_btn.pack(fill="x", pady=(0, 8))

        res_row = ctk.CTkFrame(gs_inner, fg_color="transparent")
        res_row.pack(anchor="w")

        ctk.CTkLabel(res_row, text="Target Resolution: ", font=("Arial", 11), text_color=c.TXT_MAIN).pack(side="left")

        self.gs_w = ctk.CTkEntry(res_row, width=65, height=26, state="normal" if self.app.has_gamescope else "disabled", fg_color=c.BG_PANEL, justify="center", font=("Consolas", 11))
        self.gs_w.insert(0, data.get('gs_w', "1280"))
        self.gs_w.pack(side="left", padx=4)

        ctk.CTkLabel(res_row, text="x", font=("Arial", 12), text_color=c.TXT_DIM).pack(side="left", padx=2)

        self.gs_h = ctk.CTkEntry(res_row, width=65, height=26, state="normal" if self.app.has_gamescope else "disabled", fg_color=c.BG_PANEL, justify="center", font=("Consolas", 11))
        self.gs_h.insert(0, data.get('gs_h', "720"))
        self.gs_h.pack(side="left", padx=4)

        self.useMangoHud = ctk.BooleanVar(value=data.get('useMangoHud', False))
        self.useMangoHudToggle = ctk.CTkButton(
            inner_right, text="MangoHud Performance Overlay: ON" if self.useMangoHud.get() else "MangoHud Performance Overlay: OFF",
            font=("Arial", 11, "bold"), height=34,
            fg_color=c.SUCCESS if self.useMangoHud.get() else c.DANGER, hover_color=c.ACCENT_HOVER, command=self._toggle_mangohud
        )
        self.useMangoHudToggle.pack(fill="x", pady=(4, 0))

        # LOWER GLOBAL ACTIONS BAR
        act_frame = ctk.CTkFrame(main_layout, fg_color="transparent")
        act_frame.pack(pady=(15, 5))

        ctk.CTkButton(
            act_frame, text="SAVE CHANGES (Y)", width=200, height=44,
            fg_color=c.SUCCESS, text_color=c.BG_MAIN, font=("Arial", 13, "bold"),
            hover_color=c.ACCENT_HOVER, command=self.save
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            act_frame, text="DELETE GAME", width=130, height=44,
            fg_color=c.DANGER, text_color=c.TXT_MAIN, font=("Arial", 12, "bold"),
            hover_color=c.DANGER_HOVER, command=lambda: self.app.spawn_controller_confirm_modal(self.delete)
        ).pack(side="left", padx=10)

        # CONTROLLER NAVIGATION FOOTER
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(side="bottom", pady=(0, 10))

        def add_hint(hint_text, btn_hint):
            lbl = ctk.CTkLabel(
                footer_frame, text=f"        {hint_text}        ",
                anchor='w', compound="left", font=("Arial", 11, "bold"), text_color=c.ACCENT
            )
            lbl.pack(side="left")
            self.app.anchor_icon(btn_hint, lbl)

        add_hint("  SAVE CHANGES", "Y")
        add_hint("  BACK", "B")
        add_hint("  RELOAD", "X")

        self.app.engine.rebuild_nav_map(priority_widget=self.e_exe_btn)
        self.app.update_idletasks()
        self.app.after(50, self.app.update_controller_icons)

    def _toggle_gamescope_ui(self):
        current_val = self.gs_on_var.get()
        self.gs_on_var.set(not current_val)
        new_val = self.gs_on_var.get()
        status_text = "GAMESCOPE VIRTUAL DISPLAY: ENABLED" if new_val else "GAMESCOPE VIRTUAL DISPLAY: DISABLED"
        status_color = c.SUCCESS if new_val else c.DANGER
        self.gs_toggle_btn.configure(text=status_text, fg_color=status_color)
        state = "normal" if new_val else "disabled"
        self.gs_w.configure(state=state)
        self.gs_h.configure(state=state)

    def _toggle_mangohud(self):
        current_val = self.useMangoHud.get()
        self.useMangoHud.set(not current_val)
        new_val = self.useMangoHud.get()
        self.useMangoHudToggle.configure(text="MangoHud Performance Overlay: ON" if new_val else "MangoHud Performance Overlay: OFF", fg_color=c.SUCCESS if new_val else c.DANGER)

    def _editor_clear_label(self, target: ctk.CTkLabel):
        target.configure(text="")

    def _create_setting_row(self, parent, label_text, value, is_file=True) -> tuple:
        display_text = value if value else ""

        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(wrapper, text=label_text.upper(),
                     font=("Arial", 10, "bold"), text_color=c.TXT_DIM).pack(anchor="w", pady=(0, 2))

        card = ctk.CTkFrame(wrapper, fg_color=c.BG_MAIN, height=38, corner_radius=6)
        card.pack(fill="x")
        card.pack_propagate(False)

        path_label = ctk.CTkLabel(card, text=display_text, font=("Arial", 12),
                                  fg_color="transparent", anchor="w")
        path_label.pack(side="left", padx=12, fill="both", expand=True)

        icon = "\U0001f4c4 Browse Executable" if is_file else "\U0001f4c1 Browse Folder"

        ctk.CTkButton(card, text="\u274c Clear", font=("Arial", 12), command=lambda: self._editor_clear_label(path_label),
                      fg_color="transparent", hover_color=c.DANGER_HOVER, width=32, height=38).pack(side="right", padx=2)

        btn = ctk.CTkButton(card, text=icon, font=("Arial", 12), command=lambda: self.app.browse(path_label, is_file),
                            fg_color="transparent", hover_color=c.ACCENT_HOVER, width=32, height=38)
        btn.pack(side="right", padx=2)

        def on_click(event=None):
            self.app.browse(path_label, is_file)

        card.bind("<Button-1>", on_click)
        path_label.bind("<Button-1>", on_click)

        return btn, path_label

    def _open_pfx_creator(self):
        def on_finish(new_val):
            self.e_prefix_lbl.configure(text=new_val)
            self.app.view_state = "settings"
            self.app.engine.rebuild_nav_map()

        def on_close():
            self.app.view_state = "settings"
            self.app.engine.rebuild_nav_map()

        win = self.app.spawn_toplevel(self.app, "PFX Creator")
        frame = PrefixCreator(master=win, browser_callback=self.app.browse, on_finish_callback=on_finish, on_close_callback=on_close)
        frame.pack(fill="both", expand=True)
        self.app.engine.rebuild_nav_map_modal(frame)
        self.app.view_state = "modal"

    def _refresh_umu_id(self, title, store):
        umu_id = self.app.umu_db.lookup(title, store)
        print(f"UMU ID for '{title}' ({store}): {umu_id}")
        if self.umu_id_lbl is not None:
            self.umu_id_lbl.configure(text=umu_id)

    def save(self):
        self.app.games[self.game_id].update({
            "name": self.e_name.get(), "exe": self.e_exe_lbl.cget("text"), "prefix": self.e_prefix_lbl.cget("text"),
            "proton": self.e_proton.get(), "gs_on": self.gs_on_var.get(),
            "gs_w": self.gs_w.get(), "gs_h": self.gs_h.get(), "script": self.e_script_lbl.cget("text"),
            "GAMEID": self.umu_id_lbl.cget("text"),
            "useMangoHud": self.useMangoHud.get()
        })
        self.app.config_manager.save_data(self.app.games)
        self.app.refresh_sidebar()
        self.app.show_dashboard(self.game_id)

    def delete(self):
        del self.app.games[self.game_id]
        self.app.config_manager.save_data(self.app.games)
        self.app.refresh_sidebar()
        self.app.show_welcome()
