import os
import json
import subprocess
import pathlib
import customtkinter as ctk
from tkinter import filedialog, messagebox
from input_engine import UmuInputEngine
import colors as c
import time
from PIL import Image
import shutil
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Configuration Paths ---
CONFIG_DIR = pathlib.Path(os.getenv("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")) / "umu-launcher"
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

        # Window Setup
        self.title("4DMS Launcher")
        self.geometry("1600x1000")
        ctk.set_appearance_mode("dark")
        self.current_theme=""
        self.ui_hidden=False
        self.widgets_data = {}
        
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
        
        self.game_list_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent",scrollbar_button_color=c.ACCENT,scrollbar_button_hover_color=c.ACCENT_HOVER)
        self.game_list_frame.pack(fill="both", expand=True, padx=10)
        
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

        self.exit_btn = ctk.CTkButton(self.sidebar, text="✖ EXIT",image=(self.get_resources_icon("button_menu_view",(80,80))), 
                                      fg_color="transparent",
                                      text_color=c.DANGER,
                                      hover_color=c.ACCENT_HOVER, # Subtle dark red hover
                                      command=self.quit)
        self.exit_btn.pack(side="bottom", pady=20, padx=20)

        self.add_widget_to_cache(self.exit_btn,"button_menu_view")

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
        if self.view_state == "settings":
            self.show_dashboard(self.current_game_id)
        else:
            self.show_welcome()
        self.engine.rebuild_nav_map()

    def refresh_sidebar(self):
        for w in self.game_list_frame.winfo_children(): w.destroy()
        for g_id, data in self.games.items():
            # SKIP the settings key! Only process game IDs
            if g_id == "settings": continue 
            img=self.get_art_image(data.get('art'),size=(64,64))
            btn = ctk.CTkButton(
                    self.game_list_frame, 
                    text=f"  {data['name']}", 
                    anchor="w", 
                    height=64, 
                    fg_color="transparent",
                    image=img,
                    text_color=c.TXT_MAIN,
                    hover_color=c.BG_INPUT,
                    command=lambda i=g_id: self.show_dashboard(i)
            )
            btn.pack(fill="x", pady=2)
        self.engine.rebuild_nav_map()

    def show_welcome(self):
        self.view_state = "welcome"
        self.current_game_id = None
        for w in self.content_container.winfo_children(): w.destroy()
        ctk.CTkLabel(self.content_container, 
                     text="Welcome to 4DMS Launcher\nSelect a game or press + to add one", 
                     font=("Arial", 18), 
                     text_color=c.TXT_DIM).place(relx=0.5, rely=0.5, anchor="center")

    def show_dashboard(self, g_id):
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
        
        icon_menu = self.get_resources_icon("button_menu")
        icon_x = self.get_resources_icon("button_x")
        icon_y = self.get_resources_icon("button_y")

        play_btn_state = "normal" if self.has_umu else "disabled"
        play_btn_text = " PLAY" if self.has_umu else " UMU MISSING"
        play_btn_color = c.SUCCESS if self.has_umu else "#444444"

        play_btn = ctk.CTkButton(btn_frame, text=play_btn_text, image=icon_menu, 
                                compound="left", width=220, height=70,
                                state=play_btn_state, 
                                fg_color=play_btn_color, font=("Arial", 22, "bold"),
                                command=self.launch_game)
        play_btn.pack(side="left", padx=15)

        edit_btn = ctk.CTkButton(btn_frame, text=" SETTINGS", image=icon_x,
                                compound="left", width=140, height=70, 
                                fg_color=c.BG_INPUT,
                                command=self.show_editor)
        edit_btn.pack(side="left", padx=15)

        self.art_btn = ctk.CTkButton(self.content_container, text="SET ARTWORK",image=icon_y,
                                     fg_color=c.BG_INPUT, text_color=c.TXT_DIM,
                                     command=self.select_artwork)
        self.art_btn.pack(pady=10)

        self.add_widget_to_cache(play_btn,"button_menu")
        self.add_widget_to_cache(edit_btn,"button_x")
        self.add_widget_to_cache(self.art_btn,"button_y")
        #Force refresh UI state we changed the view
        self.toggle_controller_UI(self.ui_hidden)

        info_str = f"Proton: {data.get('proton')}\nGamescope: {'Enabled' if data.get('gs_on') and self.has_gamescope else 'Disabled'}\nPrefix: {data.get('prefix')}\nExecutable: {data.get('exe')}"
        ctk.CTkLabel(self.content_container, text=info_str, text_color=c.TXT_DIM).pack(pady=20)
        

        self.engine.rebuild_nav_map(priority_widget=play_btn)

    def show_editor(self):
        self.check_dependencies() # Refresh check
        self.view_state = "settings"
        data = self.games[self.current_game_id]
        for w in self.content_container.winfo_children(): w.destroy()

        scroll = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent",scrollbar_button_color=c.ACCENT,scrollbar_button_hover_color=c.ACCENT_HOVER)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text="Game Settings", font=("Arial", 24, "bold"), text_color=c.ACCENT).pack(pady=10)
        
        self.e_name = self.create_input(scroll, "Display Name", data['name'])
        self.e_exe = self.create_input(scroll, "Executable Path", data['exe'], True)
        self.e_prefix = self.create_input(scroll, "WINEPREFIX Path", data['prefix'], False)

        ctk.CTkLabel(scroll, text="Compatibility Layer", font=("Arial", 12, "bold"), text_color=c.TXT_DIM).pack(pady=(15, 0))
        self.e_proton = ctk.CTkOptionMenu(scroll, values=list(self.proton_paths.keys()), 
                                         width=450, fg_color=c.BG_INPUT, button_color=c.BG_INPUT)
        self.e_proton.set(data.get('proton', "Default (UMU Internal)"))
        self.e_proton.pack(pady=5)

        # --- Gamescope Group ---
        self.gs_frame = ctk.CTkFrame(scroll, fg_color=c.BG_PANEL)
        self.gs_frame.pack(fill="x", padx=40, pady=10)
        
        cb_state = "normal" if self.has_gamescope else "disabled"
        cb_text = " Enable Gamescope" if self.has_gamescope else " Gamescope Not Found"
        cb_init_value = data.get('gs_on', False) if self.has_gamescope else False
        self.gs_on_var = ctk.BooleanVar(value=cb_init_value)
        self.gs_cb = ctk.CTkCheckBox(self.gs_frame, text=cb_text,state=cb_state, variable=self.gs_on_var, fg_color=c.BG_INPUT,text_color_disabled=c.TXT_DIM)
        self.gs_cb.pack(pady=(15, 10)) # Added top padding for better spacing
        
        # New: A container just for the resolution inputs to keep them centered
        res_container = ctk.CTkFrame(self.gs_frame, fg_color="transparent")
        res_container.pack(pady=(0, 15)) 
        
        self.gs_w = ctk.CTkEntry(res_container, width=80, state=cb_state,fg_color=c.BG_INPUT, justify="center")
        self.gs_w.insert(0, data.get('gs_w', "1280"))
        self.gs_w.pack(side="left", padx=5)
        
        # Add a "x" label between them for extra polish
        ctk.CTkLabel(res_container, text="x", font=("Arial", 16)).pack(side="left", padx=5)
        
        self.gs_h = ctk.CTkEntry(res_container, width=80, state=cb_state,fg_color=c.BG_INPUT, justify="center")
        self.gs_h.insert(0, data.get('gs_h', "720"))
        self.gs_h.pack(side="left", padx=5)
        self.e_script = self.create_input(scroll, "Pre-launch Script (Optional)", data.get('script', ""), True)

        # Actions
        act_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        act_frame.pack(pady=40)
        
        ctk.CTkButton(act_frame, text="SAVE CHANGES", width=180, height=50, fg_color=c.SUCCESS, command=self.save_game).pack(side="left", padx=10)
        ctk.CTkButton(act_frame, text="DELETE", width=100, height=50, fg_color=c.DANGER, command=self.delete_game).pack(side="left", padx=10)

        footer_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        footer_frame.pack(side="bottom", pady=10)

        # Create a small helper for footer items
        def add_hint(btn_name, hint_text):
            icon = self.get_resources_icon(btn_name)
            lbl = ctk.CTkLabel(footer_frame, text=f" {hint_text}   ", 
                               image=icon, compound="left",
                               font=("Arial", 12, "bold"), text_color=c.ACCENT)
            lbl.pack(side="left")
            self.add_widget_to_cache(lbl,btn_name)

        add_hint("button_y", "SAVE CHANGES")
        add_hint("button_b", "DISCARD")
        add_hint("button_x", "RESET")
        
        self.engine.rebuild_nav_map(priority_widget=self.e_name)

    def create_input(self, master, label, value, is_file=None):
        ctk.CTkLabel(master, text=label, font=("Arial", 12, "bold"), text_color=c.TXT_DIM).pack(pady=(10,0))
        f = ctk.CTkFrame(master, fg_color="transparent")
        f.pack(fill="x", padx=40, pady=5)
        e = ctk.CTkEntry(f, height=35, fg_color=c.BG_INPUT)
        e.insert(0, value)
        e.pack(side="left", expand=True, fill="x", padx=5)
        if is_file is not None:
            ctk.CTkButton(f, text="...", width=40, fg_color=c.BG_INPUT, command=lambda: self.browse(e, is_file)).pack(side="left")
        return e

    def browse(self, entry, is_file):
        path = filedialog.askopenfilename() if is_file else filedialog.askdirectory()
        if path:
            entry.delete(0, "end"); entry.insert(0, path)

    def add_new_game(self):
        g_id = f"game_{os.urandom(2).hex()}"
        self.games[g_id] = {
            "name": "New Game", "exe": "", 
            "prefix": str(pathlib.Path.home() / "Games" / "umu-prefixes" / g_id),
            "gs_on": False, "gs_w": "1280", "gs_h": "800"
        }
        self.current_game_id = g_id
        self.show_editor()

    def save_game(self):
        self.games[self.current_game_id].update({
            "name": self.e_name.get(), "exe": self.e_exe.get(), "prefix": self.e_prefix.get(),
            "proton": self.e_proton.get(), "gs_on": self.gs_on_var.get(),
            "gs_w": self.gs_w.get(), "gs_h": self.gs_h.get(), "script": self.e_script.get()
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

    def launch_game(self):
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
        subprocess.Popen(cmd, env=env)

    def show_global_settings(self):
        self.view_state = "global_settings"
        for w in self.content_container.winfo_children(): w.destroy()
        
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
        
        # 2. Sidebar Internal Scroll Frame
        # We set it to transparent or BG_PANEL to match the sidebar
        self.game_list_frame.configure(fg_color="transparent") 
        
        # 3. Sidebar Header & Action Buttons
        if hasattr(self, 'logo_label'):
            self.logo_label.configure(text_color=c.ACCENT)
            
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
        self.game_list_frame.configure(scrollbar_button_color=c.ACCENT,scrollbar_button_hover_color=c.ACCENT_HOVER)
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
        import psutil
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

    def select_artwork(self):
        """Opens file dialog, copies image, deletes old version, and updates JSON."""
        if not self.current_game_id: return
        
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp")]
        )
        
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

    def get_art_image(self, path, size=(225, 400)):
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
            img = Image.open(icon_path)
            return ctk.CTkImage(light_image=img, dark_image=img, size=size)
        return None

    def check_dependencies(self):
        """Check if required system tools are installed."""
        self.has_umu = shutil.which("umu-run") is not None
        self.has_gamescope = shutil.which("gamescope") is not None

    def toggle_controller_UI(self,hide:bool):
        """Only changes the global state and triggers the update."""
        if self.ui_hidden == hide:
            return
        
        self.ui_hidden = hide
        self.update_ui()
    
    def update_ui(self):
        """Decoupled: iterrates the cache and applies the logic."""
        for name in list(self.widgets_data.keys()):
            data = self.widgets_data[name]
            widget = data["ref"]
            path = data["path"]

            # 1. Check if widget still exists
            if not widget.winfo_exists():
                del self.widgets_data[name]
                continue

            # 2. Apply Visibility Logic
            if self.ui_hidden:
                widget.configure(image=None)
            else:
                # Re-create the image from path instead of reusing old object
                new_img = self.get_resources_icon(path)
                widget.configure(image=new_img)

    def add_widget_to_cache(self, widget, image_path):
        """Register a widget and its source path."""
        self.widgets_data[str(widget)] = {
            "ref": widget,
            "path": image_path
        }


if __name__ == "__main__":
    app = UmuLauncher()
    app.mainloop()