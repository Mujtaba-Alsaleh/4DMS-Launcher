import customtkinter as ctk
import colors as c


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
