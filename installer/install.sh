#! /usr/bin/env bash

if [ "$(id -u)" -eq 0 ]; then
  echo "This script must not be running as root" 1>&2
  exit 1
fi

echo "Not running as root. Proceeding."

WORKINGDIRECTORY=$(pwd)
NAME="4DMS-Launcher"
ICON="icon.png"
DESKTOPFILE="4DMS-Launcher.desktop"
ICON_TARGET="/usr/share/icons/hicolor/64x64/apps/"
PROGRAM="$WORKINGDIRECTORY/$NAME"
PROGRAM_PATH_TARGET="/usr/local/bin/"
DESKTOPFILE_TARGET="$HOME/.local/share/applications/"

if [[ ! -f "$PROGRAM" ]]; then
  echo "program file not found. Exiting.."
  sleep 0.2
  exit 1
fi

if [[ ! -f "$WORKINGDIRECTORY/$ICON" || ! -f "$WORKINGDIRECTORY/$DESKTOPFILE" ]]; then
  echo "Icon or desktop file are not found. Exiting.."
  sleep 0.2
  exit 1
fi

sudo cp "$WORKINGDIRECTORY/$ICON" "$ICON_TARGET/$NAME.png"
sudo cp "$PROGRAM" "$PROGRAM_PATH_TARGET"
cp "$WORKINGDIRECTORY/$DESKTOPFILE" "$DESKTOPFILE_TARGET"

echo "Finished installing. Enjoy Gaming :)"
exit 0

