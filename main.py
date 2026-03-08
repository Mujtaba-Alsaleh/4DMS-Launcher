import os
import json
import subprocess
import pathlib
import customtkinter as ctk
from tkinter import filedialog, messagebox
from input_engine import UmuInputEngine
from editable_title import EditableTitle
import colors as c
import time
from PIL import Image
import shutil
import sys
import math
import threading
import psutil
import signal

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Configuration Paths ---
CONFIG_DIR = pathlib.Path(os.getenv("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")) / "4DMS-Launcher"
CONFIG_FILE = CONFIG_DIR / "games.json"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
ARTWORK_DIR = CONFIG_DIR / "Artwork"
ARTWORK_DIR.mkdir(parents=True, exist_ok=True)

class UmuLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.has_gamescope = None
        self.has_umu = None
        self.check_dependencies()
        self.ensure_data_file()

        # Window Setup
        self.title("4DMS Launcher")
        self.geometry("1600x1200")
        ctk.set_appearance_mode("dark")
        self.current_theme=""
        self.controller_ui_visible=False
        self.icon_anchors = {}
        self.is_playing = False
        self.game_process = None
        self.current_running_game_id=0
        self.launch_lock=False #(Prevents Spamming) while launching the game process
        self.launch_lock_cooldown=2000 # 2 seconds
        self.current_file_browser = None
        
        # Theme Setup - Using colors.py constants
        self.configure(fg_color=c.BG_MAIN)
        
        # State Management
        self.games = self.load_data() #current_theme is set here
        self.current_game_id = None
        self.view_state = "welcome" 
        self.proton_paths = self.scan_proton_versions()

        # --- Main Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)


        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=c.BG_PANEL)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        #####
        self.logo_container = ctk.CTkLabel(self.sidebar,text="",image=self.get_resources_icon(self.select_logo(),size=(128,128)))
        self.logo_container.pack(pady=20)
        self.logo_label = ctk.CTkLabel(self.sidebar, text="4DMS", font=("Arial", 28, "bold"), text_color=c.ACCENT)
        self.logo_label.pack(pady=30)
        
        self.library_btn = ctk.CTkButton(self.sidebar, text="Library", 
                                     height=50, font=("Arial", 14, "bold"),
                                     fg_color=c.BG_INPUT,
                                     hover_color=c.ACCENT_HOVER,
                                     command=self.show_library)
        self.library_btn.pack(pady=25,padx=20)
        
        self.add_btn = ctk.CTkButton(self.sidebar, text="+ ADD NEW GAME", 
                                     height=50, font=("Arial", 14, "bold"),
                                     fg_color=c.BG_INPUT,
                                     hover_color=c.ACCENT_HOVER,
                                     command=self.add_new_game)
        self.add_btn.pack(pady=25, padx=20)

        self.settings_btn = ctk.CTkButton(self.sidebar, text="⚙ SETTINGS", 
                                        height=50, font=("Arial", 14, "bold"),
                                        fg_color="transparent",
                                        command=self.show_global_settings)
        self.settings_btn.pack(pady=20, padx=20)

        self.exit_btn = ctk.CTkButton(self.sidebar, text="          ✖ EXIT",compound="left",anchor='w',
                                      fg_color="transparent",
                                      text_color=c.DANGER,
                                      width=220,height=70,
                                      hover_color=c.ACCENT_HOVER, # Subtle dark red hover
                                      command=self.quit)
        self.exit_btn.pack(side="bottom", pady=20, padx=20)

        # Create the icons as children of 'self' (the main window)
        self.controllerUI_icon_size=(24,24)
        self.icon_labels = {
            "A": ctk.CTkLabel(self, text="", image=self.get_resources_icon("button_a", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
            "B": ctk.CTkLabel(self, text="", image=self.get_resources_icon("button_b", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
            "X": ctk.CTkLabel(self, text="", image=self.get_resources_icon("button_x", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
            "Y": ctk.CTkLabel(self, text="", image=self.get_resources_icon("button_y", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
            "menu": ctk.CTkLabel(self, text="", image=self.get_resources_icon("button_menu", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
            "view": ctk.CTkLabel(self, text="", image=self.get_resources_icon("button_view", self.controllerUI_icon_size), fg_color=c.BG_MAIN),
        }

        # Hide them immediately
        for icon in self.icon_labels.values():
            icon.place_forget()
        

        self.icon_anchors = {} # { "A": widget_object }
        self.controller_ui_visible = False
        self.anchor_icon("view",self.exit_btn)

        # Icons Animation
        self.anim_offset = 0
        self.anim_direction = 1
        self.is_animating = False

        # Quitting using controller hold countdown
        self.quit_overlay = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=20, border_width=2, border_color=c.BG_FOCUS)
        self.quit_label = ctk.CTkLabel(self.quit_overlay, text="QUITTING...", font=("Arial", 24, "bold"))
        self.quit_label.pack(pady=(20, 5), padx=40)
        # The Progress Bar
        self.quit_progress = ctk.CTkProgressBar(self.quit_overlay, width=200, height=15, progress_color=c.BG_FOCUS)
        self.quit_progress.set(0)
        self.quit_progress.pack(pady=(0, 20), padx=40)
        # Keep it hidden
        self.quit_overlay.place_forget()
        # This frame acts as our "Blur/Dim" layer
        self.blur_overlay = ctk.CTkFrame(self, fg_color="#0a0a0a", corner_radius=0)



        # Content Panel
        self.panel = ctk.CTkFrame(self, corner_radius=20, fg_color=c.BG_MAIN)
        self.panel.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)

        # 1. Setup Status Bar FIRST
        self.setup_status_bar()

        # 2. Create a sub-frame for everything else
        self.content_container = ctk.CTkFrame(self.panel, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True)
        

        # --- Initialize Engines ---
        self.engine = UmuInputEngine(self)
        self.refresh_sidebar()
        self.show_welcome()
        
        self.run_loop()

    def ensure_data_file(self):
        if os.path.exists(CONFIG_FILE):
            return
            # We start with only settings. 
            # The game_xxxx keys will be added dynamically by'save_game' logic.
        default_data = {
                "settings": 
                {
                    "theme": "Deep Blue"
                }
        }
            
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_data, f, indent=4)
            print("Successfully initialized data.json with Deep Blue theme.")
        except Exception as e:
                print(f"Failed to create data file: {e}")

    def run_loop(self):
        self.engine.update()
        self.after(20, self.run_loop)

    def scan_proton_versions(self):
        paths = ["~/.steam/root/compatibilitytools.d", "~/.local/share/Steam/compatibilitytools.d",
                 "~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d"]
        found = {"Default (UMU Internal)": ""}
        for p in paths:
            full_path = pathlib.Path(p).expanduser()
            if full_path.exists():
                for d in full_path.iterdir():
                    if d.is_dir(): found[d.name] = str(d)
        return found

    def load_data(self):
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    # Apply theme immediately on load
                    theme_name = data.get("settings", {}).get("theme", "Deep Blue")
                    c.apply_theme(theme_name)
                    self.current_theme=theme_name
                    return data
            return {"games": {}, "settings": {"theme": "Deep Blue"}}

    def save_data(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.games, f, indent=4)

    def handle_back(self):
        priority_widget=None
        if self.view_state == "settings":
            self.show_dashboard(self.current_game_id)
            priority_widget=self.e_name
        elif self.view_state == "browser" and self.current_file_browser:
            self.current_file_browser.handle_select("..")
            return
        elif self.view_state == "library":
            self.view_state = "sidebar"
            priority_widget=self.library_btn
        elif self.view_state == "global_settings":
            self.show_welcome()
            priority_widget=self.library_btn
        elif self.view_state == "dashboard":
            self.show_library()
            return
        
        self.engine.rebuild_nav_map(priority_widget=priority_widget)

    def refresh_sidebar(self):
        self.show_welcome()
        self.engine.rebuild_nav_map()

    def show_welcome(self):
        self.view_state = "welcome"
        for w in self.content_container.winfo_children(): w.destroy()
        self.clear_controller_ui()
        ctk.CTkLabel(self.content_container, 
                     text="Welcome to 4DMS Launcher\nSelect a game or press + to add one", 
                     font=("Arial", 18), 
                     text_color=c.TXT_DIM).place(relx=0.5, rely=0.5, anchor="center")

    def show_library(self):
        self.view_state = "library"
        self.clear_controller_ui()
        
        # 1. Setup Scrollable Frame
        for w in self.content_container.winfo_children(): w.destroy()
        self.library_scroll = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")
        self.library_scroll.pack(fill="both", expand=True)
        
        # 2. Setup Grid Container (Use fill="x" to prevent centering issues)
        grid = ctk.CTkFrame(self.library_scroll, fg_color="transparent")
        grid.pack(fill="x", expand=True, padx=20, pady=20)
        
        num_cols = 5
        for i in range(num_cols):
            grid.grid_columnconfigure(i, weight=1, uniform="lib")

        # 3. Filter and Add Games
        # This ensures 'i' starts at 0 for the first valid game
        library_games = [(g_id, data) for g_id, data in self.games.items() if g_id != "settings"]

        for i, (g_id, data) in enumerate(library_games):
                # 1. The Card Container (Invisible, used for layout)
                card = ctk.CTkFrame(grid, fg_color="transparent")
                card.grid(row=i // num_cols, column=i % num_cols, padx=15, pady=20, sticky="nsew")

                # 2. The Poster Button
                # We use a fixed 2:3 ratio (e.g., 180x270) for that Steam look
                art=data.get("art")
                poster_btn = ctk.CTkButton(
                    card,
                    text="", # Text only if no image
                    image=self.get_art_image(art),
                    width=180,
                    height=270,
                    corner_radius=12,
                    fg_color=c.BG_INPUT,
                    border_width=0, # We will set this to 2 in sync_visuals when selected
                    command=lambda id=g_id: self.show_dashboard(id)
                )
                poster_btn.pack(fill="both", expand=True)

                # 3. The Game Title (Below the Art)
                # We use a small, bold label with 'wraplength' to handle long names
                lbl = ctk.CTkLabel(
                    card, 
                    text=data.get('name').upper(), 
                    font=("Arial", 11, "bold"),
                    text_color=c.TXT_MAIN,
                    wraplength=170
                )
                lbl.pack(pady=(8, 0))

        # 4. Connect to Engine
        self.engine.rebuild_nav_map_library(grid)

    def scroll_to_library_item(self, index):
        if not hasattr(self, 'library_scroll'): return
        
        canvas = self.library_scroll._parent_canvas
        widgets = self.engine.nav_list
        if not widgets or index >= len(widgets): return

        target = widgets[index]
        self.update_idletasks() # Force geometry update
        
        y_pos = target.winfo_y()
        item_height = target.winfo_height()
        total_height = canvas.bbox("all")[3] 
        
        if total_height <= 0: return

        # Fractions for scroll position
        scroll_top = y_pos / total_height
        scroll_bottom = (y_pos + item_height) / total_height
        current_min, current_max = canvas.yview()

        if scroll_top < current_min:
            canvas.yview_moveto(scroll_top - 0.01)
        elif scroll_bottom > current_max:
            view_size = current_max - current_min
            canvas.yview_moveto(scroll_bottom - view_size + 0.01)

    def show_dashboard(self, g_id):
        self.clear_controller_ui()
        self.check_dependencies() # refresh the check
        self.view_state = "dashboard"
        self.current_game_id = g_id
        data = self.games[g_id]
        for w in self.content_container.winfo_children(): w.destroy()

        # Display Artwork
        art_path = data.get("art")
        ctk_img = self.get_art_image(art_path)
        
        if ctk_img:
            ctk.CTkLabel(self.content_container, image=ctk_img, text="").pack(pady=(20, 0))
        else:
            # Placeholder if no art exists
            ctk.CTkFrame(self.content_container, width=400, height=225, 
                         fg_color=c.BG_PANEL, border_width=2, border_color=c.BG_INPUT).pack(pady=(20, 0))

        ctk.CTkLabel(self.content_container, text=data['name'], 
                     font=("Arial", 48, "bold"), text_color=c.TXT_MAIN).pack(pady=(20, 10))
        
        btn_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        btn_frame.pack(pady=20)
        

        play_btn_state = "normal" if self.has_umu else "disabled"
        if self.has_umu and not self.is_playing:
            play_btn_text="       PLAY   "
            play_btn_color=c.SUCCESS
        elif self.is_playing:
            play_btn_text="       STOP   "
            play_btn_color=c.DANGER
        else:
            play_btn_text="       UMU MISSING   "
            play_btn_color="#444444"

        self.play_btn = ctk.CTkButton(btn_frame, text=play_btn_text, 
                                compound="left", width=220, height=70,anchor='w',
                                state=play_btn_state, 
                                fg_color=play_btn_color, font=("Arial", 22, "bold"),
                                command=self.try_launch_game)
        self.play_btn.pack(side="left", padx=15)

        edit_btn = ctk.CTkButton(btn_frame, text="       SETTINGS   ",anchor='w',
                                compound="left", width=140, height=70, 
                                fg_color=c.BG_INPUT,
                                command=self.show_editor)
        edit_btn.pack(side="left", padx=15)

        self.art_btn = ctk.CTkButton(self.content_container, text="       SET ARTWORK   ",anchor='w',
                                     compound="left", width=140, height=70,fg_color=c.BG_INPUT, text_color=c.TXT_DIM,
                                     command=self.browse_artwork)
        self.art_btn.pack(pady=10)

        if ctk_img: # that mean image exist
            rm_art_btn = ctk.CTkButton(self.content_container, text="REMOVE ARTWORK",anchor='w',
                                     compound="left", width=20, height=20,fg_color=c.DANGER,hover_color=c.DANGER_HOVER, text_color=c.TXT_DIM,
                                     command=self.remove_artwork)
            rm_art_btn.pack(padx=10)

        self.anchor_icon("menu",self.play_btn)
        self.anchor_icon("X",edit_btn)
        self.anchor_icon("Y",self.art_btn)

        self.info_str = f"Proton: {data.get('proton')}\nGamescope: {'Enabled' if data.get('gs_on') and self.has_gamescope else 'Disabled'}\nPrefix: {data.get('prefix')}\nExecutable: {data.get('exe')}\nPlaytime: {self.format_playtime(data.get('playtime'))}"
        ctk.CTkLabel(self.content_container, text=self.info_str, text_color=c.TXT_DIM).pack(pady=20)
        
        self.engine.rebuild_nav_map(priority_widget=self.play_btn)
        self.update_idletasks()     # FORCE the window to calculate widget positions NOW
        self.after(50,self.update_controller_icons()) # delay it a bit for smoother pop in

    def show_editor(self):
        self.check_dependencies() # Refresh check
        self.view_state = "settings"
        data = self.games[self.current_game_id]
        for w in self.content_container.winfo_children(): w.destroy()

        self.clear_controller_ui()

        scroll = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent",scrollbar_button_color=c.ACCENT,scrollbar_button_hover_color=c.ACCENT_HOVER)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text="Game Settings", font=("Arial", 24, "bold"), text_color=c.ACCENT).pack(pady=10)
        
        def on_name_changed(new_name):
            print(f"Updating JSON with new name: {new_name}")
            data['name'] = new_name

        # 1. Title Area (Hero Section)
        # Give the game name massive priority
        self.e_name = EditableTitle(scroll, data['name'], callback=on_name_changed)
        self.e_name.pack(pady=(20, 40), fill="x")

        # 2. Settings Rows (No more clunky boxes)
        self.e_exe_btn, self.e_exe_lbl = self.create_setting_row(scroll, "Executable Path", data['exe'], True)
        self.e_prefix_btn, self.e_prefix_lbl = self.create_setting_row(scroll, "WINEPREFIX Path", data['prefix'], False)
        self.e_script_btn, self.e_script_lbl = self.create_setting_row(scroll, "Pre-launch Script Path", data['script'], True)

        # 3. Compatibility Layer (OptionMenu)
        comp_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        comp_frame.pack(fill="x", padx=60, pady=15)
        ctk.CTkLabel(comp_frame, text="COMPATIBILITY", font=("Arial", 11, "bold"), text_color=c.TXT_DIM).pack()
        
        self.e_proton = ctk.CTkOptionMenu(scroll, values=list(self.proton_paths.keys()), 
                                        width=300, height=40, fg_color=c.BG_INPUT, 
                                        button_color=c.BG_INPUT, dynamic_resizing=False)
        self.e_proton.set(data.get('proton', "Default (UMU Internal)"))
        self.e_proton.pack(pady=5)

        # 4. Gamescope (Simplified)
        gs_container = ctk.CTkFrame(scroll, fg_color="transparent")
        gs_container.pack(pady=20)

        self.gs_on_var = ctk.BooleanVar(value=data.get('gs_on', False))
        init_val = self.gs_on_var.get()
        self.gs_toggle_btn = ctk.CTkButton(
            gs_container, 
            text="GAMESCOPE: ENABLED" if init_val else "GAMESCOPE: DISABLED",
            font=("Arial", 14, "bold"),
            fg_color=c.SUCCESS if init_val else c.DANGER,
            height=45,
            width=300,
            corner_radius=20,
            command=self.toggle_gamescope_ui,
            state="normal" if self.has_gamescope else "disabled"
        )
        self.gs_toggle_btn.pack()

        res_row = ctk.CTkFrame(gs_container, fg_color="transparent")
        res_row.pack(pady=(0, 15))
        
        self.gs_w = ctk.CTkEntry(res_row, width=80, state="normal" if self.has_gamescope else "disabled" ,fg_color=c.BG_INPUT, justify="center")
        self.gs_w.insert(0, data.get('gs_w', "1280"))
        self.gs_w.pack(side="left", padx=5)
        
        # Add a "x" label between them for extra polish
        ctk.CTkLabel(res_row, text="x", font=("Arial", 16)).pack(side="left", padx=5)
        
        self.gs_h = ctk.CTkEntry(res_row, width=80, state="normal" if self.has_gamescope else "disabled" ,fg_color=c.BG_INPUT, justify="center")
        self.gs_h.insert(0, data.get('gs_h', "720"))
        self.gs_h.pack(side="left", padx=5)

        # Actions
        act_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        act_frame.pack(pady=40)
        
        ctk.CTkButton(act_frame, text="SAVE CHANGES", width=180, height=50, fg_color=c.SUCCESS, command=self.save_game).pack(side="left", padx=10)
        ctk.CTkButton(act_frame, text="DELETE", width=100, height=50, fg_color=c.DANGER, command=self.delete_game).pack(side="left", padx=10)

        footer_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        footer_frame.pack(side="bottom", pady=10)

        # Create a small helper for footer items
        def add_hint(hint_text,btn_hint):
            lbl = ctk.CTkLabel(footer_frame, text=f"        {hint_text}        ",
                               anchor='w',
                               compound="left",
                               font=("Arial", 12, "bold"), text_color=c.ACCENT)
            lbl.pack(side="left")
            self.anchor_icon(btn_hint,lbl)

        add_hint("SAVE CHANGES","Y")
        add_hint("DISCARD","B")
        add_hint("RESET","X")
        
        self.engine.rebuild_nav_map(priority_widget=self.e_exe_btn)
        self.update_idletasks()     # FORCE the window to calculate widget positions NOW
        self.after(50,self.update_controller_icons) # delay it a bit for smoother pop in

    def toggle_gamescope_ui(self):
        """Switches the Gamescope state and updates the UI button immediately."""
        # 1. Flip the boolean value
        current_val = self.gs_on_var.get()
        self.gs_on_var.set(not current_val)
        
        # 2. Update the button look
        new_val = self.gs_on_var.get()
        status_text = "GAMESCOPE: ENABLED" if new_val else "GAMESCOPE: DISABLED"
        status_color = c.SUCCESS if new_val else c.DANGER # Dim gray when off
        
        self.gs_toggle_btn.configure(text=status_text, fg_color=status_color)
        
        # 3. Enable/Disable the resolution inputs based on the toggle
        state = "normal" if new_val else "disabled"
        self.gs_w.configure(state=state)
        self.gs_h.configure(state=state)

    def create_setting_row(self, parent, label_text, value, is_file=True):
        """Creates a clean, transparent row that the controller can highlight as a whole."""
        # 1. Outer container for spacing
        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.pack(fill="x", padx=60, pady=10)

        # 2. Header Label (The 'Small Caps' style)
        ctk.CTkLabel(wrapper, text=label_text.upper(), 
                    font=("Arial", 10, "bold"), text_color=c.TXT_DIM).pack(pady=(0, 2))

        # 3. The Interactive Card
        # We use a Frame so we can pack multiple things inside it without 'grid' conflicts
        card = ctk.CTkFrame(wrapper, fg_color=c.BG_MAIN, height=45, corner_radius=8)
        card.pack(fill="x")
        card.pack_propagate(False) # Keep fixed height

        # 4. Content inside the card
        path_label = ctk.CTkLabel(card, text=value, font=("Arial", 13), 
                                fg_color="transparent", anchor="n")
        path_label.pack(side="left", padx=15, fill="x", expand=True)

        icon = "📄" if is_file else "📁"
        ctk.CTkButton(card, text=icon, font=("Arial", 14),command=lambda: self.browse(path_label, is_file), 
                    fg_color="transparent",anchor="n").pack(side="right", padx=15)

        # 5. Controller/Mouse Binding
        # We bind the click to the frame AND the labels inside it
        def on_click(event=None):
            self.browse(path_label, is_file)

        card.bind("<Button-1>", on_click)
        path_label.bind("<Button-1>", on_click)
        
        # Store reference for your InputEngine to find
        # You can now tell your engine: "If this widget is focused, change card's fg_color"
        return card, path_label
    
    def browse(self, entry, is_file):
        from controller_file_browser import ControllerFileBrowser
        def on_selected(path):
            if path:
                entry.configure(text=path)
        
        self.after(50,self.engine.sound.play("modal"))
        # Open our controller-friendly browser
        self.view_state = "browser"
        self.current_file_browser = ControllerFileBrowser(self,is_file=is_file, callback=on_selected, engine=self.engine)

    def add_new_game(self):
        g_id = f"game_{os.urandom(2).hex()}"
        self.games[g_id] = {
            "name": "New Game", 
            "exe": "", 
            "prefix": str(pathlib.Path.home() / "Games" / "umu-prefixes" / g_id),
            "gs_on": False, "gs_w": "1280", "gs_h": "800",
            "script": ""
        }
        self.current_game_id = g_id
        self.show_editor()

    def save_game(self):
        self.games[self.current_game_id].update({
            "name": self.e_name.label.cget("text"), "exe": self.e_exe_lbl.cget("text"), "prefix": self.e_prefix_lbl.cget("text"),
            "proton": self.e_proton.get(), "gs_on": self.gs_on_var.get(),
            "gs_w": self.gs_w.get(), "gs_h": self.gs_h.get(), "script": self.e_script_lbl.cget("text")
        })
        self.save_data()
        self.refresh_sidebar()
        self.show_dashboard(self.current_game_id)

    def delete_game(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to remove this game?"):
            del self.games[self.current_game_id]
            self.save_data()
            self.refresh_sidebar()
            self.show_welcome()

    def try_launch_game(self):
        if getattr(self, "launch_lock", True):
            return
        
        if hasattr(self, "is_playing") and self.is_playing:
                # If already playing, this button acts as "STOP"
                self.stop_current_game()
                return
        
        if not self.current_game_id: return
        # 1. Lock the UI
        self.is_playing = True
        self.launch_lock = True
        self.play_btn.configure(text="       STOP   ", fg_color=c.DANGER)
        threading.Thread(target=self.run_game_process, daemon=True).start()
        self.after(self.launch_lock_cooldown, self.release_launch_lock)

    def release_launch_lock(self):
        self.launch_lock = False

    def stop_current_game(self):
        """Deep searches for the game string in all running processes."""
        if not self.current_game_id: return
        
        # 1. Get the name from the EXE path and make it lowercase
        game_data = self.games[self.current_game_id]
        target_name = os.path.basename(game_data.get("exe")).lower()
        current_pid = os.getpid() # Get your launcher's PID
        matches = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                p_name = (proc.info['name'] or "").lower()
                p_cmd = " ".join(proc.info['cmdline'] or []).lower()

                if target_name in p_name or target_name in p_cmd:
                    matches.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if matches:
            # SORT: Newest (highest timestamp) first
            matches.sort(key=lambda x: x.info['create_time'], reverse=True)
            
            for proc in matches:
                try:
                    # SAFETY: Don't kill app by mistake!
                    if proc.info['pid'] == current_pid:
                        continue
                    # If it's the actual game (the newest), we terminate it
                    print(f"DEBUG: Orderly kill of {proc.info['name']} (PID: {proc.info['pid']})")
                    proc.send_signal(signal.SIGTERM)
                    
                    # Give the game a 1-second 'head start' to close before we hit the next process
                    # This allows gamescope to see the 'Primary child shut down!' message
                    proc.wait(timeout=1) 
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    continue
        else:
            # Fallback if no specific EXE found
            if hasattr(self, "game_process"):
                self.game_process.terminate()
        
        self.game_process = None
    
    def run_game_process(self):
        start_time = time.time()
        
        try:
            d = self.games[self.current_game_id]
            if not d['exe']: return
            
            env = {**os.environ, "WINEPREFIX": d['prefix']}
            p_path = self.proton_paths.get(d.get('proton', ""), "")
            if p_path: env["PROTONPATH"] = p_path
            
            cmd = []
            if d.get('script'): cmd.append(d['script'])
            if d.get('gs_on') and self.has_gamescope:
                cmd.extend([
                    "gamescope", 
                    "-w", str(d.get('gs_w', "1280")), 
                    "-h", str(d.get('gs_h', "720")), 
                    "-f", "--"
                ])
            
            cmd.extend(["umu-run", d['exe']])

            # Launch the game and keep a reference to the process
            self.game_process = subprocess.Popen(cmd, env=env)
            self.current_running_game_id = self.current_game_id

            # --- MINIMIZE THE APP ---
            # We do this slightly after the thread starts to ensure 
            # the OS focus transitions smoothly to the game.
            self.after(500, self.iconify)

            # This line BLOCKS this thread until the game closes
            self.game_process.wait() 
            
        except Exception as e:
            print(f"Launch Error: {e}")
        finally:
            # --- UNHOOKING ---
            end_time = time.time()
            duration_minutes = round((end_time - start_time) / 60, 2)
            
            # Save playtime to JSON
            pt=0
            cgpt=self.games[self.current_running_game_id].get('playtime')
            if cgpt:
                pt = float(cgpt)
            pt+=duration_minutes
            self.games[self.current_running_game_id]["playtime"]=str(pt)
            self.save_data()
            
            # Reset UI on the main thread
            self.after(0, self.reset_ui_after_play)

    def reset_ui_after_play(self):
        self.is_playing = False
        self.play_btn.configure(text="PLAY", fg_color=c.BG_FOCUS)
        self.game_process = None
        if self.current_running_game_id == self.current_game_id:
            self.show_dashboard(self.current_game_id) # To force update the playtime
        
        # UnMinimize the app after the game closed
        self.deiconify()
        self.state('normal') # Forces a redraw of the window state
        self.lift()          # Standard Tkinter 'bring to front'
        self.focus_force()

    def show_global_settings(self):
        self.view_state = "global_settings"
        for w in self.content_container.winfo_children(): w.destroy()
        self.clear_controller_ui()
        
        ctk.CTkLabel(self.content_container, text="Global Settings", font=("Arial", 32, "bold")).pack(pady=40)
        
        ctk.CTkLabel(self.content_container, text="Launcher Theme", font=("Arial", 14)).pack(pady=5)
        self.theme_menu = ctk.CTkOptionMenu(self.content_container, values=list(c.THEMES.keys()), width=300)
        self.theme_menu.set(self.games.get("settings", {}).get("theme", "Deep Blue"))
        self.theme_menu.pack(pady=10)
        
        save_btn = ctk.CTkButton(self.content_container, text="APPLY & RESTART", fg_color=c.ACCENT, 
                                 command=self.save_global_settings)
        save_btn.pack(pady=20)

        
        self.wipe_btn = ctk.CTkButton(
            self.content_container,
            text="CLEAN ARTWORK STORAGE",
            compound="left",
            fg_color=c.DANGER, 
            hover_color=c.DANGER_HOVER,
            command=self.clear_all_artwork
        )
        self.wipe_btn.pack(pady=20, padx=20)
        
        self.engine.rebuild_nav_map(priority_widget=self.theme_menu)

    def save_global_settings(self):
        new_theme = self.theme_menu.get()
        if "settings" not in self.games: self.games["settings"] = {}
        self.games["settings"]["theme"] = new_theme
        self.current_theme = new_theme
        self.save_data()
        
        # 1. Update the variables in colors.py
        c.apply_theme(new_theme)
        
        # 2. Run the visual refresh
        self.apply_theme_visuals()
        
        # 3. Go back home
        self.show_welcome()

        self.refresh_sidebar()

    def apply_theme_visuals(self):
        """Force-updates colors on all static UI elements including internal frames."""
        # 1. Main Backgrounds
        self.configure(fg_color=c.BG_MAIN)
        self.sidebar.configure(fg_color=c.BG_PANEL)
        self.content_container.configure(fg_color=c.BG_MAIN)
          
        # 2. Sidebar Header & Action Buttons
        if hasattr(self, 'logo_label'):
            self.logo_label.configure(text_color=c.ACCENT)

        self.library_btn.configure(
            fg_color=c.BG_INPUT, 
            hover_color=c.ACCENT_HOVER,
            text_color=c.TXT_MAIN
        )
        self.add_btn.configure(
            fg_color=c.BG_INPUT, 
            hover_color=c.ACCENT_HOVER,
            text_color=c.TXT_MAIN
        )
        self.settings_btn.configure(
            fg_color="transparent",
            text_color=c.TXT_DIM,
            hover_color=c.BG_INPUT
        )
        logo = self.get_resources_icon(self.select_logo(),size=(128,128))
        self.logo_container.configure(image=logo)
        self.logo_container.image=logo
        self.panel.configure(fg_color=c.BG_MAIN)
        self.lbl_clock.configure(text_color=c.TXT_MAIN)
        self.lbl_battery.configure(text_color=c.TXT_DIM)

        self.exit_btn.configure(text_color=c.DANGER)
        
        # 4. Refresh the list of games (this applies TXT_MAIN to buttons)
        self.refresh_sidebar()
    
    def select_logo(self):
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

    def setup_status_bar(self):
        """Creates a persistent bar for Time and Battery."""
        self.status_bar = ctk.CTkFrame(self.panel, fg_color="transparent", height=30)
        self.status_bar.pack(side="top", fill="x", padx=20, pady=(10, 0))
        
        self.lbl_clock = ctk.CTkLabel(self.status_bar, text="00:00", 
                                      font=("Arial", 14, "bold"), text_color=c.TXT_MAIN)
        self.lbl_clock.pack(side="right", padx=10)
        
        self.lbl_battery = ctk.CTkLabel(self.status_bar, text="100%", 
                                        font=("Arial", 14), text_color=c.TXT_DIM)
        self.lbl_battery.pack(side="right", padx=5)

        self.update_status_bar()

    def update_status_bar(self):
        """Updates the clock and battery every minute."""
        # Time
        current_time = time.strftime("%H:%M %p")
        self.lbl_clock.configure(text=current_time)
        
        # Battery
        battery = psutil.sensors_battery()
        if battery:
            percent = f"🔋 {int(battery.percent)}%"
            plugged = " ⚡" if battery.power_plugged else ""
            self.lbl_battery.configure(text=f"{percent}{plugged}", text_color=c.TXT_MAIN if battery.percent > 20 else c.DANGER)
        else:
            self.lbl_battery.configure(text="") # Desktop or no battery sensor

        # Update every 30 seconds
        self.after(30000, self.update_status_bar)

    def select_artwork(self,file_path):
        """Opens file dialog, copies image, deletes old version, and updates JSON."""
        if not self.current_game_id: return
        
        # file_path = filedialog.askopenfilename(
        #     filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp")]
        # )

        if file_path:
            # --- NEW CLEANUP LOGIC ---
            # Check if there's already an existing art path in our data
            old_art_path = self.games[self.current_game_id].get("art")
            if old_art_path and os.path.exists(old_art_path):
                try:
                    os.remove(old_art_path)
                except Exception as e:
                    print(f"Cleanup failed: {e}")
            # -------------------------

            ext = pathlib.Path(file_path).suffix
            # Use a timestamp or UUID if you want to be extra safe, 
            # but game_id is fine since we just deleted the old one.
            local_filename = f"{self.current_game_id}{ext}"
            dest_path = ARTWORK_DIR / local_filename
            
            shutil.copy2(file_path, dest_path)
            
            self.games[self.current_game_id]["art"] = str(dest_path)
            self.save_data()
            self.show_dashboard(self.current_game_id)
            self.refresh_sidebar()

    def browse_artwork(self):
        from controller_file_browser import ControllerFileBrowser
        def on_selected(path):
            self.select_artwork(path)

        self.after(50,self.engine.sound.play("modal"))
    
        # Open our controller-friendly browser
        self.view_state = "browser"
        self.current_file_browser = ControllerFileBrowser(self,is_file=True,is_art=True ,callback=on_selected, engine=self.engine)

    def remove_artwork(self):
        """deletes art, and updates JSON."""
        if not self.current_game_id: return

        # --- NEW CLEANUP LOGIC ---
        # Check if there's already an existing art path in our data
        art_path = self.games[self.current_game_id].get("art")
        if art_path and os.path.exists(art_path):
            try:
                os.remove(art_path)
            except Exception as e:
                print(f"Cleanup failed: {e}")
        # -------------------------
        self.games[self.current_game_id]["art"] = ""
        self.save_data()
        self.show_dashboard(self.current_game_id)
        self.refresh_sidebar()

    def clear_all_artwork(self):
        """Deletes every image in the Artwork folder and resets JSON entries."""
        # 1. Physical file deletion
        if ARTWORK_DIR.exists():
            for file in ARTWORK_DIR.iterdir():
                if file.is_file():
                    try:
                        file.unlink() # Deletes the file
                    except Exception as e:
                        print(f"Error deleting {file}: {e}")

        # 2. JSON Data Reset
        for g_id in self.games:
            # We only want to clear "art" from game entries, not the 'settings' block
            if isinstance(self.games[g_id], dict) and "art" in self.games[g_id]:
                self.games[g_id]["art"] = ""

        # 3. Commit and Refresh
        self.save_data()
        self.show_welcome()
        print("Storage Cleared: All artwork deleted.")

    def get_art_image(self, path, size=(180, 240)):
        """Loads and scales the image for the UI."""
        try:
            if path and os.path.exists(path):
                img = Image.open(path)
                # Use Resampling.LANCZOS for high quality on Legion Go screen
                return ctk.CTkImage(light_image=img, dark_image=img, size=size)
        except Exception as e:
            print(f"Image load error: {e}")
        return None

    def get_resources_icon(self, name, size=(42, 42)):
        """Loads a controller icon from the Artwork folder."""
        icon_path = resource_path(f"resources/{name}.png")
        
        if os.path.exists(icon_path):
            img = Image.open(icon_path).convert("RGBA")
            return ctk.CTkImage(light_image=img, dark_image=img, size=size)
        return None

    def check_dependencies(self):
        """Check if required system tools are installed."""
        self.has_umu = shutil.which("umu-run") is not None
        self.has_gamescope = shutil.which("gamescope") is not None

    def toggle_controller_UI(self,show=True):
        """Shows or hides the floating controller icons based on input mode."""
        self.controller_ui_visible = show
        if show:
            # 1. Update positions to match current anchored widgets
            self.update_controller_icons()
            # 2. Animate
            if not self.is_animating:
                self.animate_icons()
        else:
            # 3. Hide all floating labels from the screen
            for icon in self.icon_labels.values():
                icon.place_forget()

    def anchor_icon(self, key, widget):
        self.icon_anchors[key] = widget
    
    def clear_controller_ui(self):
        """Wipes non-persistent anchors and hides their labels."""
        # We create a list of keys to remove so we don't crash while iterating
        keys_to_remove = [k for k in self.icon_anchors.keys() if k != "view"]
        
        for key in keys_to_remove:
            # 1. Hide the physical label
            if key in self.icon_labels:
                self.icon_labels[key].place_forget()
            # 2. Remove from the map
            del self.icon_anchors[key]

        # Refresh the ones that stayed (like menu_view)
        self.update_controller_icons()

    def update_controller_icons(self):
        if not self.controller_ui_visible:
            for icon in self.icon_labels.values():
                icon.place_forget()
            return
        
        # Hide labels that aren't currently anchored
        for key, label in self.icon_labels.items():
            if key not in self.icon_anchors:
                label.place_forget()
        
        for key, widget in self.icon_anchors.items():
            try:
                if widget.winfo_exists() and widget.winfo_viewable():
                    # 1. Get Widget Dimensions
                    wx = widget.winfo_rootx() - self.winfo_rootx()
                    wy = widget.winfo_rooty() - self.winfo_rooty()
                    ww = widget.winfo_width()
                    wh = widget.winfo_height()

                    icon = self.icon_labels[key]
                    
                    # 2. Set Icon Specs (Match your 32x32 size)
                    iw, ih = 32, 32 

                    # 3. POSITION REFINEMENT
                    # Adjust these numbers to "nudge" the icons
                    # Current: Inside the left edge (x+5), Vertically Centered
                    target_x = wx + 8  
                    target_y = wy + (wh // 2) - (ih // 2)

                    # 4. Handle Special Cases (like the Exit Button)
                    if key == "view":
                        # Maybe put the exit icon on the on the far right?
                        target_x = wx + ww - iw - 24
                    
                    # 5. Background Match (Crucial for the "Black Box")
                    # If the icon is INSIDE the button, use button color.
                    # If the icon is OUTSIDE the button, use the parent color.
                    icon.configure(fg_color=widget.cget("fg_color"))

                    icon.place(x=target_x, y=target_y)
                    icon.lift()
            except Exception as e:
                pass

    def show_quit_progress(self, percent):
        """Shows the dimming 'blur' and the quit modal."""
        # 1. Show the "Blur" (Dimmer) first
        if not self.quit_overlay.winfo_ismapped():
                self.blur_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
                self.blur_overlay.lift()
                
                # 2. Show and center the Quit Modal
                self.quit_overlay.place(relx=0.5, rely=0.5, anchor="center")
                self.quit_overlay.lift()
        
        # 3. Update the bar
        self.quit_progress.set(percent)
        
        # Text feedback
        if percent > 0.9:
            self.quit_label.configure(text="RELEASE TO CANCEL", text_color="#ff4444")
        else:
            self.quit_label.configure(text="QUITTING APP...", text_color="white")

    def hide_quit_progress(self):
        """Clears both the modal and the blur."""
        self.quit_overlay.place_forget()
        self.blur_overlay.place_forget()
        self.quit_progress.set(0)

    def animate_icons(self):
        """Creates a 'Heartbeat' pulse by slightly shifting the icons."""
        if not self.controller_ui_visible:
            self.is_animating = False
            return

        self.is_animating = True
        
        # Heartbeat math: using a sine wave for smooth scaling effect
        # This oscillates between -2 and +2 pixels
        anim_speed=1
        t = time.time() * anim_speed  # Speed of the pulse
        offset = math.sin(t) * 2 

        for key, widget in self.icon_anchors.items():
            try:
                icon = self.icon_labels[key]
                # We must recalculate from the widget base to prevent "drifting"
                wx = widget.winfo_rootx() - self.winfo_rootx()
                wy = widget.winfo_rooty() - self.winfo_rooty()
                wh = widget.winfo_height()
                
                # Standard vertical center (16 is half of icon height 32)
                base_y = wy + (wh // 2) - 16
                
                # Apply the pulse offset
                icon.place(y=base_y + offset)
            except:
                pass

        self.after(30, self.animate_icons)

    def format_playtime(self, total_minutes):
        """Converts 135 minutes to '2h 15m'"""
        if not total_minutes:
            return "Not Played yet"
        m="minute"
        h="hour"

        total_minutes = float(total_minutes)
        
        # 2. If it's less than an hour, just show minutes
        if total_minutes < 60:
            value=int(total_minutes)
            return f"{value} {m if value == 1 else m+"s"}"
        
        # 3. Calculate Hours and the REMAINDER (Minutes)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        # 4. If minutes are 0, just show hours (e.g., '3h')
        if minutes == 0:
            return f"{hours} {h if hours == 1 else h+'s'}"
        
        minutes = int(minutes)
        hours = int(hours)
        return f"{hours} {h if hours == 1 else h+'s'} : {minutes} {m if minutes == 1 else m+"s"}"

if __name__ == "__main__":
    app = UmuLauncher()
    app.mainloop()