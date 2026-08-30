# 4DMS-Launcher

A controller-native game launcher for Linux that runs Windows games via Proton using [umu-run](https://github.com/Open-Wine-Components/umu-launcher). Built with Python and PyQt6.

## Screenshots
<img width="1914" height="1123" alt="Screenshot_20260809_065707" src="https://github.com/user-attachments/assets/b70b06eb-88b7-4e29-bb80-0c56c686e10b" />

<img width="1910" height="1124" alt="Screenshot_20260809_065729" src="https://github.com/user-attachments/assets/5a1849d3-7edb-491e-a497-f142f035e292" />

<img width="1919" height="1124" alt="Screenshot_20260809_065753" src="https://github.com/user-attachments/assets/4da5f843-3488-41f0-a9de-724446515f40" />

<img width="1917" height="1122" alt="Screenshot_20260809_065823" src="https://github.com/user-attachments/assets/abe21b4c-7047-4f83-8a87-b9edf2c94550" />

## Features

- Launch Windows games through Proton/Wine on Linux via [umu-run](https://github.com/Open-Wine-Components/umu-launcher)
- Controller-native navigation (gamepad via the legacy Linux joystick API, no SDL) with full keyboard-layer and mouse parity
- In-app on-screen keyboard for text entry (no external Steam/Plasma keyboard needed)
- Game library with artwork, search, sort/filter, playtime tracking, and favorites
- Per-game configuration: Proton version, Gamescope, MangoHUD, Wineprefix, launch scripts
- LiveSplit integration for speedrunning (auto-launch via system Wine, TCP server, global hotkeys via evdev)
- UMU ID database for automatic Proton compatibility matching
- Prefix creator for setting up Wineprefixes
- Controller file browser for navigating paths with a gamepad
- Placeholder artwork generation for games without covers
- Themes: Deep Blue, Amber Glow, Synthwave

## Requirements

- Python 3.10+
- [umu-run](https://github.com/Open-Wine-Components/umu-launcher) installed and in PATH
- Wine (for LiveSplit, optional)
- PyQt6, psutil, Pillow (installed via `requirements.txt`)
- pw-play/paplay/aplay for sound effects (PipeWire/ALSA)

## Installation

```bash
git clone https://github.com/Mujtaba-Alsaleh/4DMS-Launcher.git
cd 4DMS-Launcher
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python launcher_pyqt/main.py
```

## Build (optional, single executable)

Create a standalone binary from a fresh venv in one go — installs the runtime deps plus PyInstaller, then builds:

```bash
cd 4DMS-Launcher
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt pyinstaller && \
pyinstaller --onefile --noconsole --clean --noconfirm \
  --paths . \
  --name "4DMS-Launcher" \
  --add-data "resources:resources" \
  --collect-submodules launcher_pyqt \
  --hidden-import colors \
  --hidden-import livesplit \
  launcher_pyqt/main.py
```

The result is a single self-contained executable at `dist/4DMS Launcher` (no console window, no Python install needed on the target machine). To rebuild after changes, just re-run the `pyinstaller` line — `--clean --noconfirm` clears the previous `build/` cache and overwrites the output. (Note: `--add-data` uses `:` on Linux; use `;` if building on Windows.)

## Project Structure

```
4DMS-Launcher/
├── launcher_pyqt/            # Active PyQt6 codebase
│   ├── main.py               # Entry point
│   ├── app.py                # Main window, view switching, keyboard layer
│   ├── config.py             # Configuration manager
│   ├── game_process.py       # Game launch/process management (umu-run)
│   ├── artwork.py            # Artwork management
│   ├── umu_database.py       # UMU ID lookup
│   ├── toast.py              # Toast notifications
│   ├── utils.py              # Shared utilities (placeholder art generator)
│   ├── ui.py                 # Design system (fonts, QSS, tab/button styles)
│   ├── input_engine.py       # Controller input + navigation (joystick API, no SDL)
│   ├── on_screen_keyboard.py # In-app controller keyboard
│   ├── quick_settings.py     # Quick-settings overlay (X button)
│   ├── add_game_modal.py     # Non-blocking add-game dialog
│   ├── controller_confirm_modal.py
│   ├── controller_file_browser.py
│   ├── pfx_creator.py        # Wineprefix creator
│   └── views/
│       ├── home.py           # Home view (featured + recently played carousel)
│       ├── library.py        # Game library grid + search
│       ├── dashboard.py      # Game detail view (hero art, floating card)
│       ├── editor.py         # Game settings editor
│       ├── global_settings.py
│       └── livesplit_view.py
├── colors.py                 # Theme constants (shared)
├── livesplit.py              # LiveSplit integration (shared)
├── resources/                # Icons, sounds, UMU database
```

## License

GPL-3.0 license
