import time
import customtkinter as ctk
import colors as c
from launcher.utils import get_art_image, format_playtime, relative_time
from artworkImage import GameImage


SORT_OPTIONS = ["Last Played", "Name", "Play Count", "Date Added"]
FILTER_OPTIONS = ["All", "Favorites", "Recent"]


class LibraryView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.library_scroll = None
        self.grid = None
        self.sort_mode = "Last Played"
        self.filter_mode = "All"
        self.pack(fill="both", expand=True)
        self._build()

    def _get_sorted_games(self):
        games = [(g_id, data) for g_id, data in self.app.games.items() if g_id != "settings"]

        if self.filter_mode == "Favorites":
            games = [(g_id, d) for g_id, d in games if d.get("favorite")]
        elif self.filter_mode == "Recent":
            cutoff = time.time() - (7 * 86400)
            games = [(g_id, d) for g_id, d in games
                     if d.get("last_played") and float(d.get("last_played", "0")) > cutoff]

        if self.sort_mode == "Name":
            games.sort(key=lambda g: g[1].get("name", "").lower())
        elif self.sort_mode == "Play Count":
            games.sort(key=lambda g: g[1].get("launch_count", 0), reverse=True)
        elif self.sort_mode == "Date Added":
            games.sort(key=lambda g: g[1].get("added_at", "0"), reverse=True)
        else:
            games.sort(key=lambda g: g[1].get("last_played", "0"), reverse=True)

        return games

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=40)
        header.pack(fill="x", padx=20, pady=(10, 0))

        self.sort_label = ctk.CTkLabel(
            header,
            text=f"\u2195 Sort: {self.sort_mode}  |  Filter: {self.filter_mode}",
            font=("Arial", 12, "bold"),
            text_color=c.ACCENT
        )
        self.sort_label.pack(side="left", padx=5)

        games = self._get_sorted_games()

        if not games:
            empty_lbl = ctk.CTkLabel(
                self,
                text="No games found.\nPress + to add a game or adjust your filter.",
                font=("Arial", 16),
                text_color=c.TXT_DIM
            )
            empty_lbl.place(relx=0.5, rely=0.5, anchor="center")
            self.app.engine.rebuild_nav_map()
            return

        if not self.app.current_game_id and games:
            self.app.current_game_id = games[0][0]

        recent_games = []
        if self.sort_mode == "Last Played" and self.filter_mode == "All":
            recent_games = [(g_id, d) for g_id, d in games if d.get("last_played")][:5]

        self.library_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.library_scroll.pack(fill="both", expand=True)

        if recent_games:
            recent_section = ctk.CTkFrame(self.library_scroll, fg_color="transparent")
            recent_section.pack(fill="x", padx=20, pady=(10, 0))

            ctk.CTkLabel(recent_section, text="RECENTLY PLAYED",
                        font=("Arial", 12, "bold"), text_color=c.ACCENT).pack(anchor="w", pady=(0, 8))

            recent_row = ctk.CTkFrame(recent_section, fg_color="transparent")
            recent_row.pack(fill="x")

            for g_id, data in recent_games:
                card = ctk.CTkFrame(recent_row, fg_color="transparent")
                card.pack(side="left", padx=8, pady=5)

                art = data.get("art")
                poster = ctk.CTkButton(
                    card, text="",
                    image=get_art_image(art, size=(140, 200)),
                    width=140, height=200, corner_radius=10,
                    fg_color=c.BG_INPUT, hover_color=c.ACCENT_HOVER,
                    border_width=0,
                    command=lambda id=g_id: self._quick_launch(id)
                )
                poster.game_id = g_id
                poster.game_image = None
                if art:
                    gi = GameImage(poster, file_path=art, width=140, height=200, quality=30)
                    gi.place(relx=0, rely=0, relwidth=1, relheight=1)
                    gi.lower_widget()
                    poster.game_image = gi
                poster.pack()

                ctk.CTkLabel(card, text=data.get('name', '').upper(),
                           font=("Arial", 10, "bold"), text_color=c.TXT_MAIN,
                           wraplength=130).pack(pady=(4, 0))

                rt = relative_time(data.get('last_played'))
                if rt:
                    ctk.CTkLabel(card, text=rt, font=("Arial", 9),
                               text_color=c.TXT_DIM).pack()

            ctk.CTkFrame(self.library_scroll, height=10, fg_color="transparent").pack()

        self.grid = ctk.CTkFrame(self.library_scroll, fg_color="transparent")
        self.grid.pack(fill="x", padx=20, pady=10)

        num_cols = 5
        for i in range(num_cols):
            self.grid.grid_columnconfigure(i, uniform="lib")

        for i, (g_id, data) in enumerate(games):
            card = ctk.CTkFrame(self.grid, fg_color="transparent")
            card.grid(row=i // num_cols, column=i % num_cols, padx=15, pady=12, sticky="nsew")

            art = data.get("art")
            poster_btn = ctk.CTkButton(
                card, text="",
                image=get_art_image(art),
                width=180, height=270, corner_radius=12,
                fg_color=c.BG_INPUT, hover_color=c.ACCENT_HOVER,
                border_width=0,
                command=lambda id=g_id: self._quick_launch(id)
            )
            poster_btn.game_id = g_id
            poster_btn.game_image = None
            if art:
                gi = GameImage(poster_btn, file_path=art, width=180, height=270, quality=30)
                gi.place(relx=0, rely=0, relwidth=1, relheight=1)
                gi.lower_widget()
                poster_btn.game_image = gi
            poster_btn.pack()

            if data.get("favorite"):
                star = ctk.CTkLabel(card, text="\u2b50", font=("Arial", 14),
                                   fg_color="transparent", text_color="#ffd700")
                star.place(relx=0.9, rely=0.05, anchor="ne")

            name_text = data.get('name', '').upper()
            ctk.CTkLabel(card, text=name_text, font=("Arial", 11, "bold"),
                        text_color=c.TXT_MAIN, wraplength=170).pack(pady=(6, 0))

            pt = data.get('playtime')
            if pt:
                ctk.CTkLabel(card, text=format_playtime(pt), font=("Arial", 9),
                           text_color=c.TXT_DIM).pack()

        self.app.engine.rebuild_nav_map_library(self.grid)
        self.app.after(100, lambda: self.app.engine.rebuild_nav_map_library(self.grid))

    def _quick_launch(self, game_id):
        self.app.current_game_id = game_id
        self.app.game_process_manager.try_launch()

    def scroll_to_item(self, index):
        if not self.library_scroll:
            return

        canvas = self.library_scroll._parent_canvas
        widgets = self.app.engine.nav_list
        if not widgets or index >= len(widgets):
            return

        target = widgets[index]
        self.app.update_idletasks()

        y_pos = target.winfo_y()
        item_height = target.winfo_height()
        total_height = canvas.bbox("all")[3]

        if total_height <= 0:
            return

        scroll_top = y_pos / total_height
        scroll_bottom = (y_pos + item_height) / total_height
        current_min, current_max = canvas.yview()

        if scroll_top < current_min:
            canvas.yview_moveto(scroll_top - 0.01)
        elif scroll_bottom > current_max:
            view_size = current_max - current_min
            canvas.yview_moveto(scroll_bottom - view_size + 0.01)

    def _start_cover_anim(self, btn):
        if btn.game_image:
            btn.game_image.lift_widget()
            btn.game_image.start()
        try:
            btn.configure(border_width=2, border_color=c.ACCENT)
        except Exception:
            pass

    def _stop_cover_anim(self, btn):
        if btn.game_image:
            btn.game_image.stop()
            btn.game_image.lower_widget()
        try:
            btn.configure(border_width=0, fg_color=c.BG_INPUT)
        except Exception:
            pass

    def cycle_sort(self):
        idx = SORT_OPTIONS.index(self.sort_mode) if self.sort_mode in SORT_OPTIONS else 0
        self.sort_mode = SORT_OPTIONS[(idx + 1) % len(SORT_OPTIONS)]
        self.app.toast.show(f"Sort: {self.sort_mode}")
        self._rebuild()

    def cycle_filter(self):
        idx = FILTER_OPTIONS.index(self.filter_mode) if self.filter_mode in FILTER_OPTIONS else 0
        self.filter_mode = FILTER_OPTIONS[(idx + 1) % len(FILTER_OPTIONS)]
        self.app.toast.show(f"Filter: {self.filter_mode}")
        self._rebuild()

    def toggle_favorite(self):
        if not self.app.current_game_id:
            return
        game_id = self.app.current_game_id
        current = self.app.games[game_id].get("favorite", False)
        self.app.games[game_id]["favorite"] = not current
        self.app.config_manager.save_data(self.app.games)
        state = "added to" if not current else "removed from"
        self.app.toast.show(f"Favorites: {state}")
        self._rebuild()

    def _rebuild(self):
        for w in self.winfo_children():
            w.destroy()
        self._build()
