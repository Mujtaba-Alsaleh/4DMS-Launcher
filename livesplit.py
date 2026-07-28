import os
import socket
import struct
import threading
import subprocess
import zipfile
import pathlib
import select
import urllib.request
import xml.etree.ElementTree as ET
import colors as c

LIVESPLIT_VERSION = "1.8.37"
LIVESPLIT_URL = f"https://github.com/LiveSplit/LiveSplit/releases/download/{LIVESPLIT_VERSION}/LiveSplit_{LIVESPLIT_VERSION}.zip"
LIVESPLIT_DIR = pathlib.Path.home() / ".local" / "share" / "4DMS-Launcher" / "LiveSplit"
LIVESPLIT_EXE = LIVESPLIT_DIR / "LiveSplit.exe"
SETTINGS_CFG = LIVESPLIT_DIR / "settings.cfg"

LIVESPLIT_PORT = 16834
HOTKEYS_FILE = LIVESPLIT_DIR / "hotkeys.json"

REF_LIVESPLIT_DIR = pathlib.Path.home() / "LiveSplit"
REF_LIVESPLIT_EXE = REF_LIVESPLIT_DIR / "LiveSplit.exe"
REF_WINEPREFIX = pathlib.Path.home() / ".local" / "share" / "livesplit"

KEYNAME_TO_CODE = {
    "None": 0,
    "D1": 2, "D2": 3, "D3": 4, "D4": 5, "D5": 6,
    "D6": 7, "D7": 8, "D8": 9, "D9": 10, "D0": 11,
    "A": 30, "B": 48, "C": 46, "D": 32, "E": 18,
    "F": 33, "G": 34, "H": 35, "I": 23, "J": 36,
    "K": 37, "L": 38, "M": 50, "N": 49, "O": 24,
    "P": 25, "Q": 16, "R": 19, "S": 31, "T": 20,
    "U": 22, "V": 47, "W": 17, "X": 45, "Y": 21, "Z": 44,
    "F1": 59, "F2": 60, "F3": 61, "F4": 62, "F5": 63,
    "F6": 64, "F7": 65, "F8": 66, "F9": 67, "F10": 68,
    "F11": 87, "F12": 88,
    "NumPad0": 82, "NumPad1": 79, "NumPad2": 80, "NumPad3": 81,
    "NumPad4": 75, "NumPad5": 76, "NumPad6": 77, "NumPad7": 71,
    "NumPad8": 72, "NumPad9": 80,
    "Add": 78, "Subtract": 74, "Multiply": 55, "Divide": 98,
    "Decimal": 83, "NumPadEnter": 96,
    "Space": 57, "Backspace": 14, "Tab": 15, "Enter": 28,
    "Escape": 1, "CapsLock": 58,
    "PageUp": 104, "PageDown": 109, "Home": 102, "End": 107,
    "Insert": 110, "Delete": 111,
    "LeftArrow": 105, "RightArrow": 106, "UpArrow": 103, "DownArrow": 108,
    "LeftShift": 42, "RightShift": 54,
    "LeftControl": 29, "RightControl": 97,
    "LeftAlt": 56, "RightAlt": 100,
    "PrintScreen": 99, "ScrollLock": 70, "Pause": 119,
    "OemOpenBrackets": 26, "OemCloseBrackets": 27, "OemPipe": 43,
    "OemSemicolon": 39, "OemQuotes": 40, "OemComma": 51,
    "OemPeriod": 52, "OemMinus": 12, "OemPlus": 13,
}

MOD_SHIFT = 1
MOD_CTRL = 2
MOD_ALT = 4

EV_KEY = 0x01
KEY_DOWN = 0x01
KEY_UP = 0x00

INPUT_EVENT_SIZE = 24

LIVESPLIT_SETTINGS_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<Settings version="1.8.18">
  <HotkeyProfiles>
    <HotkeyProfile name="Default">
      <SplitKey>NumPad1</SplitKey>
      <ResetKey>NumPad3</ResetKey>
      <SkipKey>NumPad2</SkipKey>
      <UndoKey>NumPad8</UndoKey>
      <PauseKey />
      <ToggleGlobalHotkeys />
      <SwitchComparisonPrevious>NumPad4</SwitchComparisonPrevious>
      <SwitchComparisonNext>NumPad6</SwitchComparisonNext>
      <GlobalHotkeysEnabled>False</GlobalHotkeysEnabled>
      <DeactivateHotkeysForOtherPrograms>True</DeactivateHotkeysForOtherPrograms>
      <DoubleTapPrevention>True</DoubleTapPrevention>
      <HotkeyDelay>0</HotkeyDelay>
      <AllowGamepadsAsHotkeys>False</AllowGamepadsAsHotkeys>
    </HotkeyProfile>
  </HotkeyProfiles>
  <WarnOnReset>True</WarnOnReset>
  <RaceViewer>SpeedRunsLive</RaceViewer>
  <AgreedToSRLRules>False</AgreedToSRLRules>
  <EnableDPIAwareness>False</EnableDPIAwareness>
  <UILanguage>
  </UILanguage>
  <RecentSplits />
  <RecentLayouts />
  <LastComparison>Personal Best</LastComparison>
  <SimpleSumOfBest>False</SimpleSumOfBest>
  <RefreshRate>60</RefreshRate>
  <ServerPort>16834</ServerPort>
  <ServerStartup>1</ServerStartup>
  <ServerState>1</ServerState>
  <ComparisonGeneratorStates>
    <Generator name="Best Segments">True</Generator>
    <Generator name="Best Split Times">False</Generator>
    <Generator name="Average Segments">True</Generator>
    <Generator name="Median Segments">False</Generator>
    <Generator name="Worst Segments">False</Generator>
    <Generator name="Balanced PB">False</Generator>
    <Generator name="Latest Run">False</Generator>
    <Generator name="None">False</Generator>
  </ComparisonGeneratorStates>
  <RaceProviderPlugins>
    <Plugin name="LiveSplit.Racetime.dll" enabled="False">
      <LoadChatHistory>True</LoadChatHistory>
      <HideResults>False</HideResults>
    </Plugin>
    <Plugin name="SRL" enabled="False" />
  </RaceProviderPlugins>
  <ActiveAutoSplitters />
</Settings>'''


class LiveSplitManager:
    def __init__(self, app=None):
        self.app = app
        self.process = None
        self.hotkey_thread = None
        self._stop_event = threading.Event()
        self._socket = None
        self._hotkeys = {}
        self._key_map = {}

    @staticmethod
    def is_installed():
        return REF_LIVESPLIT_EXE.exists() or LIVESPLIT_EXE.exists()

    @staticmethod
    def _get_exe_path():
        if REF_LIVESPLIT_EXE.exists():
            return REF_LIVESPLIT_EXE
        return LIVESPLIT_EXE

    @staticmethod
    def _get_settings_path():
        ref_cfg = REF_LIVESPLIT_DIR / "settings.cfg"
        if ref_cfg.exists():
            return ref_cfg
        return SETTINGS_CFG

    @staticmethod
    def download(progress_callback=None):
        LIVESPLIT_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = LIVESPLIT_DIR / f"LiveSplit_{LIVESPLIT_VERSION}.zip"

        if progress_callback:
            progress_callback(f"Downloading LiveSplit {LIVESPLIT_VERSION}...")

        urllib.request.urlretrieve(LIVESPLIT_URL, str(zip_path))

        if progress_callback:
            progress_callback("Extracting...")

        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            zf.extractall(str(LIVESPLIT_DIR))
        zip_path.unlink(missing_ok=True)

        LiveSplitManager.ensure_settings()

        if progress_callback:
            progress_callback("Done.")

    @staticmethod
    def ensure_settings():
        if not SETTINGS_CFG.exists():
            SETTINGS_CFG.write_text(LIVESPLIT_SETTINGS_TEMPLATE)

    def launch(self, prefix, proton_path):
        if not self.is_installed():
            return False

        if self.process and self.process.poll() is None:
            return True

        self.process = None

        self.ensure_settings()

        exe_path = self._get_exe_path()

        if REF_WINEPREFIX.exists():
            wineprefix = str(REF_WINEPREFIX)
        else:
            wineprefix = str(LIVESPLIT_DIR)

        env = {
            **os.environ,
            "WINEPREFIX": wineprefix,
        }

        cmd = ["wine", str(exe_path)]

        try:
            self.process = subprocess.Popen(
                cmd, env=env, cwd=str(exe_path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            print(f"LiveSplit launch error: {e}")
            return False

    def launch_hotkey_listener(self):
        if not self.load_hotkeys():
            print("LiveSplit: no hotkeys configured")
            return False
        self._stop_event.clear()
        self.hotkey_thread = threading.Thread(target=self._evdev_hotkey_loop, daemon=True)
        self.hotkey_thread.start()
        return True

    def stop_hotkeys(self):
        self._stop_event.set()
        if self.hotkey_thread:
            self.hotkey_thread.join(timeout=2)
            self.hotkey_thread = None

    def stop(self):
        self.stop_hotkeys()
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def connect(self, host="127.0.0.1", port=LIVESPLIT_PORT, timeout=3.0):
        self.disconnect()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            self._socket = s
            return True
        except Exception as e:
            print(f"LiveSplit TCP connect error: {e}")
            return False

    def disconnect(self):
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def send_command(self, command):
        if not self._socket:
            return False
        try:
            self._socket.sendall((command + "\r\n").encode("utf-8"))
            return True
        except Exception as e:
            print(f"LiveSplit TCP send error: {e}")
            self._socket = None
            return False

    def _evdev_hotkey_loop(self):
        kb_devices = []
        seen = set()
        by_path = pathlib.Path("/dev/input/by-path")
        if by_path.exists():
            for entry in sorted(by_path.iterdir()):
                if entry.name.endswith("-event-kbd"):
                    real = entry.resolve()
                    real_str = str(real)
                    if real_str in seen:
                        continue
                    seen.add(real_str)
                    kb_devices.append(real_str)

        if not kb_devices:
            return

        fds = []
        for dev in kb_devices:
            try:
                fd = os.open(dev, os.O_RDONLY)
                fds.append(fd)
            except Exception:
                pass

        if not fds:
            return

        tcp_cmd_map = {
            "startorsplit": "startorsplit",
            "reset": "reset",
            "pause": "pause",
            "undo": "unsplit",
            "skip": "skipsplit",
            "swap": "swap",
        }

        poll_obj = select.poll()
        for fd in fds:
            poll_obj.register(fd, select.POLLIN)

        print(f"LiveSplit: listening on {len(fds)} keyboard devices (evdev)")

        try:
            while not self._stop_event.is_set():
                ready = poll_obj.poll(200)
                if not ready:
                    continue

                for fd, _ in ready:
                    try:
                        data = os.read(fd, INPUT_EVENT_SIZE)
                    except OSError:
                        continue

                    if len(data) < INPUT_EVENT_SIZE:
                        continue

                    _, _, ev_type, code, value = struct.unpack("qqHHi", data)

                    if ev_type != EV_KEY or value > 1:
                        continue

                    action_info = self._key_map.get(code)
                    if not action_info:
                        continue

                    action, _ = action_info
                    if value != KEY_DOWN:
                        continue

                    tcp_cmd = tcp_cmd_map.get(action)
                    if tcp_cmd:
                        self.send_command(tcp_cmd)
                        print(f"LiveSplit hotkey: {action} -> {tcp_cmd}")
        finally:
            for fd in fds:
                try:
                    os.close(fd)
                except Exception:
                    pass

    def parse_settings(self):
        cfg_path = self._get_settings_path()
        if not cfg_path.exists():
            return {}
        try:
            tree = ET.parse(str(cfg_path))
            root = tree.getroot()
            hotkeys = {}

            hk_profiles = root.find("HotkeyProfiles")
            if hk_profiles is not None:
                profile = hk_profiles.find("HotkeyProfile")
                if profile is not None:
                    tag_to_action = {
                        "SplitKey": "startorsplit",
                        "ResetKey": "reset",
                        "PauseKey": "pause",
                        "UndoKey": "undo",
                        "SkipKey": "skip",
                        "SwitchComparisonPrevious": "swap",
                    }
                    for tag, action in tag_to_action.items():
                        elem = profile.find(tag)
                        if elem is not None and elem.text and elem.text.strip():
                            key_name = elem.text.strip()
                            if key_name and key_name != "None":
                                hotkeys[action] = (key_name, 0)
                    return hotkeys

            return hotkeys
        except Exception as e:
            print(f"LiveSplit settings parse error: {e}")
            return {}

    def load_hotkeys(self):
        self._hotkeys = self._load_hotkeys_file() or self.parse_settings()
        self._key_map = {}
        for action, (key_name, mods) in self._hotkeys.items():
            code = KEYNAME_TO_CODE.get(key_name, 0)
            if code:
                self._key_map[code] = (action, mods)
        return bool(self._key_map)

    def _load_hotkeys_file(self):
        if not HOTKEYS_FILE.exists():
            return {}
        try:
            import json
            data = json.loads(HOTKEYS_FILE.read_text())
            return {k: (v, 0) for k, v in data.items()}
        except Exception:
            return {}

    def _save_hotkeys_file(self):
        try:
            import json
            data = {action: key_name for action, (key_name, _) in self._hotkeys.items()}
            HOTKEYS_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"LiveSplit save_hotkeys_file error: {e}")

    def save_hotkey(self, action, key_name):
        cfg_path = self._get_settings_path()
        if not cfg_path.exists():
            return
        try:
            tree = ET.parse(str(cfg_path))
            root = tree.getroot()
            hk_profiles = root.find("HotkeyProfiles")
            if hk_profiles is not None:
                profile = hk_profiles.find("HotkeyProfile")
                if profile is not None:
                    action_to_tag = {
                        "startorsplit": "SplitKey",
                        "reset": "ResetKey",
                        "pause": "PauseKey",
                        "undo": "UndoKey",
                        "skip": "SkipKey",
                        "swap": "SwitchComparisonPrevious",
                    }
                    tag = action_to_tag.get(action)
                    if tag:
                        elem = profile.find(tag)
                        if elem is None:
                            elem = ET.SubElement(profile, tag)
                        elem.text = key_name
            tree.write(str(cfg_path), xml_declaration=True, encoding="UTF-8")
            self._hotkeys[action] = (key_name, 0)
            self._save_hotkeys_file()
            self.load_hotkeys()
        except Exception as e:
            print(f"LiveSplit save_hotkey error: {e}")

    def capture_next_key(self, callback, dev_path=None):
        KEYSYM_TO_KEYNAME = {
            "Return": "Enter", "space": "Space", "BackSpace": "Backspace",
            "Tab": "Tab", "Escape": "Escape", "Caps_Lock": "CapsLock",
            "Delete": "Delete", "Insert": "Insert",
            "Prior": "PageUp", "Next": "PageDown", "Home": "Home", "End": "End",
            "Left": "LeftArrow", "Right": "RightArrow", "Up": "UpArrow", "Down": "DownArrow",
            "Print": "PrintScreen", "Scroll_Lock": "ScrollLock", "Pause": "Pause",
            "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4", "F5": "F5",
            "F6": "F6", "F7": "F7", "F8": "F8", "F9": "F9", "F10": "F10",
            "F11": "F11", "F12": "F12",
            "KP_0": "NumPad0", "KP_1": "NumPad1", "KP_2": "NumPad2", "KP_3": "NumPad3",
            "KP_4": "NumPad4", "KP_5": "NumPad5", "KP_6": "NumPad6", "KP_7": "NumPad7",
            "KP_8": "NumPad8", "KP_9": "NumPad9",
            "KP_Add": "Add", "KP_Subtract": "Subtract", "KP_Multiply": "Multiply",
            "KP_Divide": "Divide", "KP_Decimal": "Decimal", "KP_Enter": "NumPadEnter",
            "bracketleft": "OemOpenBrackets", "bracketright": "OemCloseBrackets",
            "backslash": "OemPipe", "semicolon": "OemSemicolon",
            "apostrophe": "OemQuotes", "comma": "OemComma",
            "period": "OemPeriod", "minus": "OemMinus", "equal": "OemPlus",
        }
        self._capture_callback = callback
        self._keysym_map = KEYSYM_TO_KEYNAME

        def _on_key(event):
            self.app.unbind("<KeyPress>", self._bind_id)
            key_name = self._keysym_map.get(event.keysym)
            if not key_name:
                if len(event.keysym) == 1:
                    key_name = event.keysym.upper()
            self._capture_callback(key_name)

        self.app.unbind("<KeyPress>", getattr(self, '_bind_id', None))
        self._bind_id = self.app.bind("<KeyPress>", _on_key)
