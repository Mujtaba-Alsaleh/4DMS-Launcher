import os
import customtkinter as ctk
import colors as c
from launcher.utils import get_art_image, format_playtime
from artworkImage import GameImage


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, app, game_id):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.game_id = game_id
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        data = self.app.games[self.game_id]
        art_path = data.get("art")
        h = 240
        w = 180
        ctk_img = os.path.exists(art_path) if art_path else False

        if ctk_img:
            GameImage(self, file_path=art_path, width=w, height=h).pack(pady=(20, 0))
        else:
            ctk.CTkFrame(self, width=w, height=h,
                         fg_color=c.BG_PANEL, border_width=2, border_color=c.BG_INPUT).pack(padx=20, pady=5)

        ctk.CTkLabel(self, text=data['name'],
                     font=("Arial", 22, "bold"), text_color=c.TXT_MAIN).pack(pady=(20, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)

        play_btn_state = "normal" if self.app.has_umu else "disabled"
        play_btn_color = c.SUCCESS
        if self.app.has_umu and not self.app.game_process_manager.is_playing:
            play_btn_text = "PLAY"
            play_btn_color = c.SUCCESS
        elif self.app.game_process_manager.is_playing:
            play_btn_text = "STOP"
            play_btn_color = c.DANGER
        else:
            play_btn_text = "UMU MISSING"
            play_btn_color = "#444444"

        self.app.play_btn = ctk.CTkButton(btn_frame, text=play_btn_text,
                                          compound="left", width=180, height=40, anchor='center',
                                          state=play_btn_state,
                                          fg_color=play_btn_color,
                                          hover_color=c.ACCENT_HOVER,
                                          font=("Arial", 16, "bold"),
                                          command=self.app.game_process_manager.try_launch)
        self.app.play_btn.pack(side="left", padx=15, pady=5)

        edit_btn = ctk.CTkButton(btn_frame, text="SETTINGS", anchor='center',
                                 compound="left", width=140, height=40,
                                 fg_color=c.BG_INPUT,
                                 hover_color=c.ACCENT_HOVER,
                                 command=self.app.show_editor)
        edit_btn.pack(side="left", padx=15, pady=5)

        self.art_btn = ctk.CTkButton(self, text=" SET ARTWORK", anchor='center', font=("Arial", 11, "bold"),
                                     compound="left", width=140, height=40, fg_color=c.BG_INPUT, text_color=c.TXT_DIM, hover_color=c.ACCENT_HOVER,
                                     command=self._browse_artwork)
        self.art_btn.pack(pady=5)

        if ctk_img:
            rm_art_btn = ctk.CTkButton(self, text="   REMOVE ARTWORK", anchor='center', font=("Arial", 16, "bold"),
                                       compound="left", width=20, height=20, fg_color=c.DANGER, hover_color=c.DANGER_HOVER, text_color=c.TXT_DIM,
                                       command=self._remove_artwork)
            rm_art_btn.pack(padx=5)

        self.app.anchor_icon("menu", self.app.play_btn)
        self.app.anchor_icon("X", edit_btn)
        self.app.anchor_icon("Y", self.art_btn)

        self.info_border_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
            border_width=2,
            border_color=c.BG_INPUT
        )
        self.info_border_frame.pack(fill="x", padx=20, pady=10)

        self._create_info_panel(self.info_border_frame, data)

        self.app.engine.rebuild_nav_map(priority_widget=self.app.play_btn)
        self.app.update_idletasks()
        self.app.after(50, self.app.update_controller_icons)

    def _create_info_panel(self, parent, data):
        info_container = ctk.CTkFrame(parent, fg_color="transparent")
        info_container.pack(fill="x", padx=20, pady=3)

        def add_row(label, value, val_color=c.TXT_MAIN):
            row = ctk.CTkFrame(info_container, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, font=("Arial", 11, "bold"), text_color="gray").pack(side="left")
            ctk.CTkLabel(row, text=value, font=("Arial", 11), text_color=val_color).pack(side="right")

        add_row("PROTON", data.get('proton'), c.ACCENT)
        add_row("PREFIX", data.get('prefix'), "#bbbbbb")

        gs_active = data.get('gs_on') and self.app.has_gamescope
        add_row("GAMESCOPE", "ENABLED" if gs_active else "DISABLED", "#2ecc71" if gs_active else "#e74c3c")

        hud_active = data.get('useMangoHud', False)
        add_row("MANGOHUD", "ACTIVE" if hud_active else "OFF", "#2ecc71" if hud_active else "gray")

        add_row("PLAYTIME", format_playtime(data.get('playtime')), c.ACCENT)

    def _browse_artwork(self):
        from controller_file_browser import ControllerFileBrowser

        def on_selected(path):
            if path:
                self.app.artwork_manager.select(self.game_id, path, self.app.games, self.app.config_manager.save_data)
                self.app.show_dashboard(self.game_id)
                self.app.refresh_sidebar()

        self.app.after(50, self.app.engine.sound.play("modal"))
        self.app.view_state = "browser"
        self.app.current_file_browser = ControllerFileBrowser(self.app, is_file=True, is_art=True, callback=on_selected, engine=self.app.engine)

    def _remove_artwork(self):
        self.app.artwork_manager.remove(self.game_id, self.app.games, self.app.config_manager.save_data)
        self.app.show_dashboard(self.game_id)
        self.app.refresh_sidebar()
