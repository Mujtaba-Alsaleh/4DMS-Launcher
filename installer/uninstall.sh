#! /usr/bin/env bash

if [ "$(id -u)" -eq 0 ]; then
  echo "This script must not be running as root" 1>&2
  exit 1
fi

echo "Not running as root. Proceeding."

NAME="4DMS-Launcher"
ICON="/usr/share/icons/hicolor/64x64/apps/$NAME.png"
PROGRAM="/usr/local/bin/$NAME"
DESKTOPFILE="$HOME/.local/share/applications/4DMS-Launcher.desktop"

if [[ ! -f "$PROGRAM" ]]; then 
  echo "$PROGRAM not found"
else
    echo "Type [Y] then Enter to confirm the removal of a file"
    sudo rm -i "$PROGRAM" 
fi




if [[ ! -f "$ICON" ]]; then
  echo "$ICON not found"  
else
    echo "Type [Y] then Enter to confirm the removal of a file"
    sudo rm -i "$ICON"
fi



if [[ ! -f "$DESKTOPFILE" ]]; then
    echo "$DESKTOPFILE not found"
  else
      echo "Type [Y] then Enter to confirm the removal of a file"
      rm -i "$DESKTOPFILE"
fi

echo "Finished uninstalling."
exit 0

