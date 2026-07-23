import os
import json
import pathlib
import time
import shutil
import colors as c


# --- Configuration Paths ---
CONFIG_DIR = pathlib.Path(os.getenv("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")) / "4DMS-Launcher"
CONFIG_FILE = CONFIG_DIR / "games.json"
ARTWORK_DIR = CONFIG_DIR / "Artwork"


class ConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        ARTWORK_DIR.mkdir(parents=True, exist_ok=True)

    def ensure_data_file(self):
        if os.path.exists(CONFIG_FILE):
            return
        default_data = {
            "settings": {
                "theme": "Deep Blue"
            }
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_data, f, indent=4)
            print("Successfully initialized data.json with Deep Blue theme.")
        except Exception as e:
            print(f"Failed to create data file: {e}")

    def load_data(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                theme_name = data.get("settings", {}).get("theme", "Deep Blue")
                c.apply_theme(theme_name)
                self._migrate(data)
                return data, theme_name
        return {"games": {}, "settings": {"theme": "Deep Blue"}}, "Deep Blue"

    def save_data(self, data):
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def scan_proton_versions(self):
        paths = ["~/.steam/root/compatibilitytools.d", "~/.local/share/Steam/compatibilitytools.d",
                 "~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d"]
        found = {"Default (UMU Internal)": ""}
        for p in paths:
            full_path = pathlib.Path(p).expanduser()
            if full_path.exists():
                for d in full_path.iterdir():
                    if d.is_dir():
                        found[d.name] = str(d)
        return found

    def _migrate(self, data):
        now = str(time.time())
        for g_id, g_data in data.items():
            if g_id == "settings" or not isinstance(g_data, dict):
                continue
            g_data.setdefault("last_played", "")
            g_data.setdefault("launch_count", 0)
            g_data.setdefault("favorite", False)
            g_data.setdefault("added_at", now)
            g_data.setdefault("notes", "")
            g_data.setdefault("rating", 0)
