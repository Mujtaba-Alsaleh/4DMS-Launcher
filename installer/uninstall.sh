#! /usr/bin/env bash

if [ "$(id -u)" -eq 0 ]; then
  echo "This script must not be running as root" 1>&2
  exit 1
fi

echo "Not running as root. Proceeding."

NAME="4DMS-Launcher"
ICON="/usr/share/icons/hicolor/64x64/apps/$NAME.png"
PROGRAM="/usr/local/bin/$NAME"
DESKTOP_FILE="$HOME/.local/share/applications/4DMS-Launcher.desktop"
CONFIG_DIR="$HOME/.config/$NAME"

if [[ ! -f "$PROGRAM" ]]; then 
  echo "$PROGRAM not found"
else
    echo "Type [Y] then Enter to confirm the removal of a file  (y/N)"
    sudo rm -vi "$PROGRAM"
fi




if [[ ! -f "$ICON" ]]; then
  echo "$ICON not found"  
else
    echo "Type [Y] then Enter to confirm the removal of a file  (y/N)"
    sudo rm -vi "$ICON"
fi



if [[ ! -f "$DESKTOP_FILE" ]]; then
    echo "$DESKTOP_FILE not found"
  else
      echo "Type [Y] then Enter to confirm the removal of a file  (y/N)"
      rm -vi "$DESKTOP_FILE"
fi

if [[ ! -d "$CONFIG_DIR" ]]; then
    echo "No Config files found. Skipping..."
    else
        read -p "Do you want to Delete all config data for the program? (y/N): " CONFIRM
        if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
            rm -vrf $CONFIG_DIR
        fi
fi

echo "The uninstaller finished. If you had any problem please consider reporting on github or reaching out. Good Bye"
exit 0

