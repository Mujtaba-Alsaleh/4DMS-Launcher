# 4DMS-Launcher
 Proton/Wine and retro games Launcher
 
python Build command:
    pyinstaller --onefile --windowed --add-data "resources:resources" --hidden-import="PIL._tkinter_finder" -n "4DMS Launcher" main.py

c++ build command:
    python -m nuitka --onefile --include-data-dir=resources=resources --include-module=PIL._tkinter_finder --output-filename=4DMS-Launcher --onefile-tempdir-spec="{TEMP}/4DMS" --python-flag=no_site --lto=yes --enable-plugin=tk-inter main.py
