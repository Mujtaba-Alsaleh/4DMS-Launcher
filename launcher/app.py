import os
import argparse
import time
import math
import shutil
import customtkinter as ctk

import colors as c
from input_engine import UmuInputEngine
from launcher.config import ConfigManager, ARTWORK_DIR
from launcher.umu_database import UMUDatabase
from launcher.artwork import ArtworkManager
from launcher.game_process import GameProcessManager
from launcher.toast import ToastManager
from launcher.utils import resource_path, get_resources_icon, get_art_image
from launcher.views.welcome import WelcomeView
from launcher.views.library import LibraryView
from launcher.views.dashboard import DashboardView
from launcher.views.editor import EditorView
from launcher.views.global_settings import GlobalSettingsView
from launcher.views.volume_overlay import VolumeOverlay
from pfx_creator import PrefixCreator
from controller_confirm_modal import ControllerConfirmModal
from controller_file_browser import ControllerFileBrowser


HINT_DEFS = {
    "welcome": [],
    "library": [("A", "Launch"), ("X", "Details"), ("Y", "Fav"), ("LB/RB", "Sort/Filter"), ("Menu", "Sidebar")],
    "dashboard": [("A", "Play"), ("X", "Settings"), ("Y", "Artwork"), ("B", "Back"), ("Menu", "Sidebar")],
    "settings": [("Y", "Save"), ("B", "Back"), ("X", "Reload"), ("Menu", "Sidebar")],
    "sidebar": [],
    "global_settings": [("B", "Back")],
    "prefix_creator": [("B", "Back")],
    "browser": [("A", "Select"), ("B", "Back")],
    "modal": [],
}


class UmuLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        parser = argparse.ArgumentParser()
        parser.add_argument('--fullscreen', action='store_true', help='Force fullscreen geometry for Gamescope')
        args = parser.parse_args()

        self.has_gamescope = None
        self.has_umu = None
        self.check_dependencies()

        self.config_manager = ConfigManager()
        self.config_manager.ensure_data_file()
        self.games, self.current_theme = self.config_manager.load_data()
        self.umu_db = UMUDatabase()
        self.artwork_manager = ArtworkManager(ARTWORK_DIR)
        self.runningOnGamescope = False

        self.title("4DMS Launcher")

        if args.fullscreen:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+0+0")
            self.overrideredirect(True)
            self.runningOnGamescope = True
        else:
            self.geometry("1920x1200")

        ctk.set_appearance_mode("dark")
        self.controller_ui_visible = False
        self.icon_anchors = {}
        self.current_file_browser = None
        self.current_game_id = None
        self.view_state = "welcome"
        self.proton_paths = self.config_manager.scan_proton_versions()
        self.current_view = None
        self.play_btn = None
        self.nav_stack = []

        self.configure(fg_color=c.BG_MAIN)

        # --- Main Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=c.BG_PANEL)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.logo_container = ctk.CTkLabel(self.sidebar, text="", image=get_resources_icon(self._select_logo(), size=(128, 128)))
        self.logo_container.pack(pady=20)
        self.logo_label = ctk.CTkLabel(self.sidebar, text="4DMS", font=("Arial", 28, "bold"), text_color=c.ACCENT)
        self.logo_label.pack(pady=30)

        self.library_btn = ctk.CTkButton(self.sidebar, text="\U0001f3ae Library",
                                         height=50, font=("Arial", 14, "bold"),
                                         fg_color=c.ACCENT,
                                         hover_color=c.ACCENT_HOVER,
                                         command=self.show_library)
        self.library_btn.pack(pady=25, padx=20)

        self.add_btn = ctk.CTkButton(self.sidebar, text="+ ADD NEW GAME",
                                     height=50, font=("Arial", 14, "bold"),
                                     fg_color=c.ACCENT,
                                     hover_color=c.ACCENT_HOVER,
                                     command=self.add_new_game)
        self.add_btn.pack(pady=25, padx=20)

        self.prefix_creator_btn = ctk.CTkButton(self.sidebar, text="\U0001f4e6 Prefix Creator",
                                                height=50, font=("Arial", 14, "bold"),
                                                fg_color=c.ACCENT,
                                                hover_color=c.ACCENT_HOVER,
                                                command=self.create_pfx_menu)
        self.prefix_creator_btn.pack(pady=20, padx=20)

        self.settings_btn = ctk.CTkButton(self.sidebar, text="\u2699 SETTINGS",
                                          height=50, font=("Arial", 14, "bold"),
                                          fg_color=c.ACCENT,
                                          hover_color=c.ACCENT_HOVER,
                                          command=self.show_global_settings)
        self.settings_btn.pack(pady=20, padx=20)

        self.exit_btn = ctk.CTkButton(self.sidebar, text="\u2716 EXIT       ", anchor='center', font=("Arial", 14, "bold"),
                                      fg_color="transparent",
                                      text_color=c.DANGER,
                                      height=50,
                                      hover_color=c.ACCENT_HOVER,
                                      command=self.quit)
        self.exit_btn.pack(side="bottom", pady=20, padx=20)

        # Controller UI Icons
        self.controllerUI_icon_size = (24, 24)
        self.icon_labels = {
            "A": ctk.CTkLabel(self, text="", image=get_resources_icon("button_a", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
            "B": ctk.CTkLabel(self, text="", image=get_resources_icon("button_b", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
            "X": ctk.CTkLabel(self, text="", image=get_resources_icon("button_x", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
            "Y": ctk.CTkLabel(self, text="", image=get_resources_icon("button_y", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
            "menu": ctk.CTkLabel(self, text="", image=get_resources_icon("button_menu", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
            "view": ctk.CTkLabel(self, text="", image=get_resources_icon("button_view", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
        }

        for icon in self.icon_labels.values():
            icon.place_forget()

        self.icon_anchors = {}
        self.controller_ui_visible = False
        self.anchor_icon("view", self.exit_btn)

        self.anim_offset = 0
        self.anim_direction = 1
        self.is_animating = False

        # Quit overlay
        self.quit_overlay = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=20, border_width=2, border_color=c.BG_FOCUS)
        self.quit_label = ctk.CTkLabel(self.quit_overlay, text="QUITTING...", font=("Arial", 24, "bold"))
        self.quit_label.pack(pady=(20, 5), padx=40)
        self.quit_progress = ctk.CTkProgressBar(self.quit_overlay, width=200, height=15, progress_color=c.BG_FOCUS)
        self.quit_progress.set(0)
        self.quit_progress.pack(pady=(0, 20), padx=40)
        self.quit_overlay.place_forget()
        self.blur_overlay = ctk.CTkFrame(self, fg_color="#0a0a0a", corner_radius=0)

        # Content Panel
        self.panel = ctk.CTkFrame(self, corner_radius=20, fg_color=c.BG_MAIN)
        self.panel.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)

        self.setup_status_bar()

        self.content_container = ctk.CTkFrame(self.panel, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True)

        # Button Hint Bar
        self.hint_frame = ctk.CTkFrame(self.panel, fg_color="transparent", height=30)
        self.hint_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 5))
        self.hint_labels = []

        # Toast Manager
        self.toast = ToastManager(self)

        # Volume Overlay
        self.volume_overlay = VolumeOverlay(self)

        # Managers
        self.game_process_manager = GameProcessManager(self)

        # Input Engine
        self.engine = UmuInputEngine(self)

        game_count = sum(1 for k in self.games if k != "settings")
        if game_count > 0:
            self.show_library()
        else:
            self.show_welcome()

        self.run_loop()

    # ==================== NAVIGATION ====================

    def run_loop(self):
        self.engine.update()
        self.after(20, self.run_loop)

    def _push_nav(self):
        if self.view_state not in ("welcome", "sidebar"):
            self.nav_stack.append(self.view_state)

    def handle_back(self):
        if self.view_state == "modal":
            return

        if self.view_state == "browser" and self.current_file_browser:
            self.current_file_browser.handle_select("..")
            return

        if self.nav_stack:
            prev = self.nav_stack.pop()
            if prev == "library":
                self.show_library()
                return
            elif prev == "dashboard" and self.current_game_id:
                self.show_dashboard(self.current_game_id)
                return

        if self.view_state == "settings":
            self.show_dashboard(self.current_game_id)
        elif self.view_state == "library":
            self.view_state = "sidebar"
            self.engine.rebuild_nav_map(priority_widget=self.library_btn)
            return
        elif self.view_state in ("global_settings", "prefix_creator", "welcome"):
            self.show_welcome()
            self.engine.rebuild_nav_map(priority_widget=self.library_btn)
            return
        elif self.view_state == "dashboard":
            self.show_library()
            return

        self.engine.rebuild_nav_map()

    def refresh_sidebar(self):
        self.show_welcome()
        self.engine.rebuild_nav_map()

    def show_welcome(self):
        self.view_state = "welcome"
        for w in self.content_container.winfo_children():
            w.destroy()
        self.clear_controller_ui()
        self.current_view = WelcomeView(self.content_container, self)
        self._update_hint_bar()
        self.engine.rebuild_nav_map()

    def show_library(self):
        self._push_nav()
        self.view_state = "library"
        self.clear_controller_ui()
        for w in self.content_container.winfo_children():
            w.destroy()
        self.current_view = LibraryView(self.content_container, self)
        self._update_hint_bar()

    def show_dashboard(self, g_id):
        self._push_nav()
        self.clear_controller_ui()
        self.check_dependencies()
        self.view_state = "dashboard"
        self.current_game_id = g_id
        for w in self.content_container.winfo_children():
            w.destroy()
        self.current_view = DashboardView(self.content_container, self, g_id)
        self._update_hint_bar()

    def show_editor(self):
        if self.view_state == "settings":
            def do_reload():
                self.check_dependencies()
                self.view_state = "settings"
                for w in self.content_container.winfo_children():
                    w.destroy()
                self.clear_controller_ui()
                self.current_view = EditorView(self.content_container, self, self.current_game_id)
            self.spawn_controller_confirm_modal(func=do_reload, msg="Discard unsaved changes and reload?")
            return
        self._push_nav()
        self.check_dependencies()
        self.view_state = "settings"
        for w in self.content_container.winfo_children():
            w.destroy()
        self.clear_controller_ui()
        self.current_view = EditorView(self.content_container, self, self.current_game_id)
        self._update_hint_bar()

    def show_global_settings(self):
        self._push_nav()
        self.view_state = "global_settings"
        for w in self.content_container.winfo_children():
            w.destroy()
        self.clear_controller_ui()
        self.current_view = GlobalSettingsView(self.content_container, self)
        self._update_hint_bar()

    def create_pfx_menu(self):
        self._push_nav()
        self.view_state = "prefix_creator"
        for w in self.content_container.winfo_children():
            w.destroy()
        self.clear_controller_ui()
        frame = PrefixCreator(
            master=self.content_container,
            browser_callback=self.browse
        )
        frame.pack(fill="both", expand=True)
        self.engine.rebuild_nav_map()
        self._update_hint_bar()

    # ==================== HINT BAR ====================

    def _update_hint_bar(self):
        for lbl in self.hint_labels:
            lbl.destroy()
        self.hint_labels.clear()

        hints = HINT_DEFS.get(self.view_state, [])
        for btn_key, action in hints:
            lbl = ctk.CTkLabel(
                self.hint_frame,
                text=f"[{btn_key}] {action}  ",
                font=("Arial", 11),
                text_color=c.TXT_DIM,
                fg_color="transparent"
            )
            lbl.pack(side="left", padx=4)
            self.hint_labels.append(lbl)

    # ==================== SHARED UTILITIES ====================

    def add_new_game(self):
        import pathlib
        g_id = f"game_{os.urandom(2).hex()}"
        self.games[g_id] = {
            "name": "New Game",
            "exe": "",
            "prefix": str(pathlib.Path.home() / "Games" / "umu-prefixes" / g_id),
            "gs_on": False, "gs_w": "1280", "gs_h": "800",
            "script": "",
            "last_played": "", "launch_count": 0, "favorite": False,
            "added_at": str(time.time()), "notes": "", "rating": 0
        }
        self.current_game_id = g_id
        self.show_editor()

    def browse(self, entry, is_file):
        def on_selected(path):
            if path:
                entry.configure(text=path)

        self.after(50, self.engine.sound.play("modal"))
        self.view_state = "browser"
        self.current_file_browser = ControllerFileBrowser(self, is_file=is_file, callback=on_selected, engine=self.engine)

    def spawn_toplevel(self, parent, title="Window"):
        win = ctk.CTkToplevel(parent)
        win.title(title)
        win.transient(parent)
        win.geometry("1600x1200")
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        return win

    def spawn_controller_confirm_modal(self, func=None, msg=None):
        current_view_state = self.view_state
        self.view_state = "modal"

        def on_user_decision(confirmed: bool):
            if confirmed:
                if func:
                    func()
            self.view_state = current_view_state
            self.engine.rebuild_nav_map()

        modal = ControllerConfirmModal(self, engine=self.engine, on_result=on_user_decision, msg=msg)

    def check_dependencies(self):
        self.has_umu = shutil.which("umu-run") is not None
        self.has_gamescope = shutil.which("gamescope") is not None

    # ==================== PROXY METHODS (for input_engine compatibility) ====================

    def save_game(self):
        if self.current_view and hasattr(self.current_view, 'save'):
            self.current_view.save()

    def scroll_to_library_item(self, index):
        if self.current_view and hasattr(self.current_view, 'scroll_to_item'):
            self.current_view.scroll_to_item(index)
            widgets = self.engine.nav_list
            if 0 <= index < len(widgets):
                btn = widgets[index]
                if hasattr(btn, 'game_id'):
                    self.current_game_id = btn.game_id

    def try_launch_game(self):
        self.game_process_manager.try_launch()

    def browse_artwork(self):
        if self.current_view and hasattr(self.current_view, '_browse_artwork'):
            self.current_view._browse_artwork()

    def toggle_favorite(self):
        if self.current_view and hasattr(self.current_view, 'toggle_favorite'):
            self.current_view.toggle_favorite()

    # ==================== THEME ====================

    def apply_theme_visuals(self):
        self.configure(fg_color=c.BG_MAIN)
        self.sidebar.configure(fg_color=c.BG_PANEL)
        self.content_container.configure(fg_color=c.BG_MAIN)

        if hasattr(self, 'logo_label'):
            self.logo_label.configure(text_color=c.ACCENT)

        self.library_btn.configure(fg_color=c.ACCENT, hover_color=c.ACCENT_HOVER, text_color=c.TXT_MAIN)
        self.add_btn.configure(fg_color=c.ACCENT, hover_color=c.ACCENT_HOVER, text_color=c.TXT_MAIN)
        self.prefix_creator_btn.configure(fg_color=c.ACCENT, text_color=c.TXT_MAIN, hover_color=c.ACCENT_HOVER)
        self.settings_btn.configure(fg_color=c.ACCENT, text_color=c.TXT_MAIN, hover_color=c.ACCENT_HOVER)
        self.exit_btn.configure(fg_color=c.DANGER, text_color=c.TXT_MAIN, hover_color=c.DANGER_HOVER)

        logo = get_resources_icon(self._select_logo(), size=(128, 128))
        self.logo_container.configure(image=logo)
        self.logo_container.image = logo
        self.panel.configure(fg_color=c.BG_MAIN)
        self.lbl_clock.configure(text_color=c.TXT_MAIN)
        self.lbl_battery.configure(text_color=c.TXT_DIM)
        self.exit_btn.configure(text_color=c.DANGER)

        self.refresh_sidebar()

    def _select_logo(self):
        match self.current_theme:
            case "Deep Blue":
                return "logo"
            case "Nordic":
                return "logo_nordic"
            case "Legion Red":
                return "logo_red"
            case _:
                return "logo"
        return "logo"

    # ==================== STATUS BAR ====================

    def setup_status_bar(self):
        self.status_bar = ctk.CTkFrame(self.panel, fg_color="transparent", height=30)
        self.status_bar.pack(side="top", fill="x", padx=20, pady=(10, 0))

        self.lbl_clock = ctk.CTkLabel(self.status_bar, text="00:00",
                                      font=("Arial", 14, "bold"), text_color=c.TXT_MAIN)
        self.lbl_clock.pack(side="right", padx=10)

        self.lbl_battery = ctk.CTkLabel(self.status_bar, text="100%",
                                        font=("Arial", 14), text_color=c.TXT_DIM)
        self.lbl_battery.pack(side="right", padx=5)

        self.lbl_controller_battery = ctk.CTkLabel(self.status_bar, text="",
                                                   font=("Arial", 12), text_color=c.TXT_DIM)
        self.lbl_controller_battery.pack(side="right", padx=5)

        self.update_status_bar()

    def update_status_bar(self):
        import psutil
        current_time = time.strftime("%H:%M %p")
        self.lbl_clock.configure(text=current_time)

        battery = psutil.sensors_battery()
        if battery:
            percent = f"\U0001f50b {int(battery.percent)}%"
            plugged = " \u26a1" if battery.power_plugged else ""
            self.lbl_battery.configure(text=f"{percent}{plugged}", text_color=c.TXT_MAIN if battery.percent > 20 else c.DANGER)
        else:
            self.lbl_battery.configure(text="")

        ctrl_icon = self._get_controller_battery()
        self.lbl_controller_battery.configure(text=ctrl_icon)

        self.after(30000, self.update_status_bar)

    def _get_controller_battery(self):
        if not hasattr(self, 'engine'):
            return "\U0001f50c"
        for joy in self.engine.joysticks:
            try:
                level = joy.get_power_level()
                if level == "wired":
                    return "\U0001f50c"
                elif level == "max" or level == "full":
                    return "\U0001f7e2"
                elif level == "medium":
                    return "\U0001f7e1"
                elif level == "low":
                    return "\U0001f534"
                elif level == "empty":
                    return "\u26ab"
            except Exception:
                pass
        return ""

    # ==================== CONTROLLER UI ====================

    def toggle_controller_UI(self, show=True):
        self.controller_ui_visible = show
        if show:
            self.update_controller_icons()
            if not self.is_animating:
                self.animate_icons()
        else:
            for icon in self.icon_labels.values():
                icon.place_forget()

    def anchor_icon(self, key, widget):
        self.icon_anchors[key] = widget

    def clear_controller_ui(self):
        keys_to_remove = [k for k in self.icon_anchors.keys() if k != "view"]
        for key in keys_to_remove:
            if key in self.icon_labels:
                self.icon_labels[key].place_forget()
            del self.icon_anchors[key]
        self.update_controller_icons()

    def update_controller_icons(self):
        if not self.controller_ui_visible:
            for icon in self.icon_labels.values():
                icon.place_forget()
            return

        for key, label in self.icon_labels.items():
            if key not in self.icon_anchors:
                label.place_forget()

        for key, widget in self.icon_anchors.items():
            try:
                if widget.winfo_exists() and widget.winfo_viewable():
                    wx = widget.winfo_rootx() - self.winfo_rootx()
                    wy = widget.winfo_rooty() - self.winfo_rooty()
                    ww = widget.winfo_width()
                    wh = widget.winfo_height()

                    icon = self.icon_labels[key]
                    iw, ih = 32, 32
                    offset_from_target = 5
                    target_x = wx + offset_from_target
                    target_y = wy + (wh // 2) - (ih // 2)

                    if key == "view":
                        target_x = wx + ww - iw - 24

                    icon.configure(fg_color=widget.cget("fg_color"))
                    icon.place(x=target_x, y=target_y)
                    icon.lift()
            except Exception:
                pass

    def show_quit_progress(self, percent):
        if not self.quit_overlay.winfo_ismapped():
            self.blur_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.blur_overlay.lift()
            self.quit_overlay.place(relx=0.5, rely=0.5, anchor="center")
            self.quit_overlay.lift()

        self.quit_progress.set(percent)

        if percent > 0.9:
            self.quit_label.configure(text="RELEASE TO CANCEL", text_color="#ff4444")
        else:
            self.quit_label.configure(text="QUITTING APP...", text_color="white")

    def hide_quit_progress(self):
        self.quit_overlay.place_forget()
        self.blur_overlay.place_forget()
        self.quit_progress.set(0)

    def animate_icons(self):
        if not self.controller_ui_visible:
            self.is_animating = False
            return

        self.is_animating = True
        anim_speed = 1
        t = time.time() * anim_speed
        offset = math.sin(t) * 2

        for key, widget in self.icon_anchors.items():
            try:
                icon = self.icon_labels[key]
                wx = widget.winfo_rootx() - self.winfo_rootx()
                wy = widget.winfo_rooty() - self.winfo_rooty()
                wh = widget.winfo_height()
                base_y = wy + (wh // 2) - 16
                icon.place(y=base_y + offset)
            except:
                pass

        self.after(30, self.animate_icons)
