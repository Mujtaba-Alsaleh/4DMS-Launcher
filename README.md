# 4DMS-Launcher

A controller-native game launcher for Linux that runs Windows games via Proton using [umu-run](https://github.com/Open-Wine-Components/umu-launcher). Built with Python and PyQt6.

## Features

- Launch Windows games through Proton/Wine on Linux
- Built-in controller support (gamepad navigation via legacy joystick API, button prompts, volume overlay)
- Per-game configuration: Proton version, Gamescope, MangoHUD, Wineprefix, launch scripts
- LiveSplit integration for speedrunning (auto-launch, TCP server, global hotkeys via evdev)
- Steam on-screen keyboard integration
- Game library with artwork, playtime tracking, and favorites
- UMU ID database for automatic Proton compatibility matching
- Prefix creator for setting up Wineprefixes
- File browser for navigating paths with controller
- Themes: Deep Blue, Amber Glow, Synthwave

## Requirements

- Python 3.10+
- [umu-run](https://github.com/Open-Wine-Components/umu-launcher) installed and in PATH
- Wine (for LiveSplit, optional)
- PyQt6 (`pip install PyQt6`)
- psutil (`pip install psutil`)
- Pillow (`pip install Pillow`)
- Steam (optional, for on-screen keyboard)

## Installation

```bash
git clone https://github.com/your-username/4DMS-Launcher.git
cd 4DMS-Launcher
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python launcher_pyqt/main.py
```

## Project Structure

```
4DMS-Launcher/
├── launcher_pyqt/            # Active PyQt6 codebase
│   ├── main.py               # Entry point
│   ├── app.py                # Main application window
│   ├── config.py             # Configuration manager
│   ├── game_process.py       # Game launch/process management
│   ├── artwork.py            # Artwork management
│   ├── umu_database.py       # UMU ID lookup
│   ├── toast.py              # Toast notifications
│   ├── utils.py              # Shared utilities
│   ├── input_engine.py       # Controller input (joystick API, no SDL/pygame)
│   ├── controller_confirm_modal.py
│   ├── controller_file_browser.py
│   ├── pfx_creator.py        # Wineprefix creator
│   └── views/
│       ├── library.py        # Game library grid
│       ├── dashboard.py      # Game detail view
│       ├── editor.py         # Game settings editor
│       ├── global_settings.py
│       └── volume_overlay.py
├── colors.py                 # Theme constants (shared)
├── livesplit.py              # LiveSplit integration (shared)
├── resources/                # Icons, sounds, UMU database
└── launcher/                 # Legacy CustomTkinter codebase (inactive)
```

## License

GPL-3.0 license
