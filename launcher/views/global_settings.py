import customtkinter as ctk
import colors as c
import livesplit as ls


class GlobalSettingsView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.theme_menu = None
        self.wipe_btn = None
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Global Settings", font=("Arial", 32, "bold")).pack(pady=40)

        ctk.CTkLabel(self, text="Launcher Theme", font=("Arial", 14)).pack(pady=5)
        self.theme_menu = ctk.CTkOptionMenu(self, values=list(c.THEMES.keys()), width=300)
        self.theme_menu.set(self.app.games.get("settings", {}).get("theme", "Deep Blue"))
        self.theme_menu.pack(pady=10)

        save_btn = ctk.CTkButton(self, text="APPLY THEME", fg_color=c.ACCENT, hover_color=c.ACCENT_HOVER,
                                 command=self._save)
        save_btn.pack(pady=20)

        ctk.CTkLabel(self, text="Startup Behavior", font=("Arial", 14)).pack(pady=(20, 5))
        self.skip_welcome_var = ctk.BooleanVar(
            value=self.app.games.get("settings", {}).get("skip_welcome", False)
        )
        skip_toggle = ctk.CTkSwitch(
            self, text="Skip Welcome Screen (go to Library if games exist)",
            variable=self.skip_welcome_var, onvalue=True, offvalue=False,
            command=self._save_skip_welcome
        )
        skip_toggle.pack(pady=10)

        self.wipe_btn = ctk.CTkButton(
            self,
            text="CLEAN ARTWORK STORAGE",
            compound="left",
            fg_color=c.DANGER,
            hover_color=c.DANGER_HOVER,
            command=self._clear_artwork
        )
        self.wipe_btn.pack(pady=20, padx=20)

        if ls.LiveSplitManager.is_installed():
            self._build_hotkey_section()

        self.app.engine.rebuild_nav_map(priority_widget=self.theme_menu)

    def _save(self):
        new_theme = self.theme_menu.get()
        if "settings" not in self.app.games:
            self.app.games["settings"] = {}
        self.app.games["settings"]["theme"] = new_theme
        self.app.current_theme = new_theme
        self.app.config_manager.save_data(self.app.games)

        c.apply_theme(new_theme)
        self.app.apply_theme_visuals()
        self.app.show_welcome()
        self.app.refresh_sidebar()

    def _clear_artwork(self):
        self.app.artwork_manager.clear_all(self.app.games, self.app.config_manager.save_data)
        self.app.show_welcome()

    def _save_skip_welcome(self):
        if "settings" not in self.app.games:
            self.app.games["settings"] = {}
        self.app.games["settings"]["skip_welcome"] = self.skip_welcome_var.get()
        self.app.config_manager.save_data(self.app.games)

    def _build_hotkey_section(self):
        card = ctk.CTkFrame(self, fg_color=c.BG_PANEL, corner_radius=12, border_color=c.BG_FOCUS, border_width=1)
        card.pack(fill="x", padx=40, pady=(20, 10))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=15, pady=12)

        ctk.CTkLabel(inner, text="LIVESPLIT HOTKEYS", font=("Arial", 13, "bold"), text_color=c.ACCENT).pack(anchor="w", pady=(0, 8))

        actions = [
            ("startorsplit", "Split"),
            ("reset", "Reset"),
            ("undo", "Undo"),
            ("skip", "Skip"),
            ("swap", "Prev Comparison"),
        ]
        self._hk_labels = {}

        mgr = ls.LiveSplitManager(app=self.app)
        current = mgr.parse_settings()

        for action, label in actions:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=label, font=("Arial", 11), text_color=c.TXT_MAIN, width=120, anchor="w").pack(side="left")

            key_name = current.get(action, ("None", 0))[0]
            key_lbl = ctk.CTkLabel(row, text=key_name, font=("Consolas", 11, "bold"),
                                   fg_color=c.ACCENT, text_color=c.BG_MAIN, width=100, height=24, corner_radius=4)
            key_lbl.pack(side="left", padx=(0, 8))
            self._hk_labels[action] = key_lbl

            btn = ctk.CTkButton(row, text="Rebind", font=("Arial", 10, "bold"), width=60, height=24,
                                fg_color=c.BG_FOCUS, hover_color=c.ACCENT_HOVER,
                                command=lambda a=action, b=key_lbl: self._rebind_hotkey(a, b))
            btn.pack(side="left")

    def _rebind_hotkey(self, action, label_widget):
        label_widget.configure(text="...", fg_color=c.DANGER)
        self.app.update_idletasks()

        mgr = ls.LiveSplitManager(app=self.app)
        mgr.load_hotkeys()

        def on_key(key_name):
            if key_name:
                mgr.save_hotkey(action, key_name)
                label_widget.configure(text=key_name, fg_color=c.ACCENT)
            else:
                old = mgr._hotkeys.get(action, ("None", 0))[0]
                label_widget.configure(text=old, fg_color=c.ACCENT)

        mgr.capture_next_key(on_key)
