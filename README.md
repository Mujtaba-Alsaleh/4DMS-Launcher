# 4DMS-Launcher

A controller-native game launcher for Linux that runs Windows games via Proton using [umu-run](https://github.com/Open-Wine-Components/umu-launcher). Built with Python and CustomTkinter.

## Features

- Launch Windows games through Proton/Wine on Linux
- Built-in controller support (gamepad navigation, button prompts, volume overlay)
- Per-game configuration: Proton version, Gamescope, MangoHUD, Wineprefix, launch scripts
- Steam on-screen keyboard integration
- Game library with artwork, playtime tracking, and favorites
- UMU ID database for automatic Proton compatibility matching
- Prefix creator for setting up Wineprefixes
- File browser for navigating paths with controller

## Requirements

- Python 3.10+
- [umu-run](https://github.com/Open-Wine-Components/umu-launcher) installed and in PATH
- pygame-ce (`pip install pygame-ce`)
- CustomTkinter (`pip install customtkinter`)
- Steam (optional, for on-screen keyboard)

## Installation

```bash
git clone https://github.com/your-username/4DMS-Launcher.git
cd 4DMS-Launcher
pip install -r requirements.txt
python main.py
```

## Building

### PyInstaller (onefile)

```bash
pyinstaller --onefile --windowed \
  --add-data "resources:resources" \
  --hidden-import="PIL._tkinter_finder" \
  -n "4DMS Launcher" \
  main.py
```

### Nuitka (onefile)

Requires `patchelf` installed on the system.

```bash
python -m nuitka --onefile \
  --include-data-dir=resources=resources \
  --include-module=PIL._tkinter_finder \
  --output-filename=4DMS-Launcher \
  --onefile-tempdir-spec="{TEMP}/4DMS" \
  --python-flag=no_site \
  --lto=yes \
  --enable-plugin=tk-inter \
  main.py
```

## Project Structure

```
4DMS-Launcher/
├── main.py                  # Entry point
├── colors.py                # Theme constants
├── input_engine.py          # Controller input handling
├── controller_file_browser.py
├── controller_confirm_modal.py
├── artworkImage.py          # Game artwork rendering
├── pfx_creator.py           # Wineprefix creator
├── resources/               # Icons, sounds, UMU database
│   └── umu-database.csv
└── launcher/
    ├── app.py               # Main application window
    ├── config.py            # Configuration manager
    ├── game_process.py      # Game launch/process management
    ├── artwork.py           # Artwork management
    ├── umu_database.py      # UMU ID lookup
    ├── toast.py             # Toast notifications
    ├── utils.py             # Shared utilities
    └── views/
        ├── library.py       # Game library grid
        ├── dashboard.py     # Game detail view
        ├── editor.py        # Game settings editor
        ├── global_settings.py
        ├── volume_overlay.py
        └── welcome.py
```

## License

GPL-3.0 license
