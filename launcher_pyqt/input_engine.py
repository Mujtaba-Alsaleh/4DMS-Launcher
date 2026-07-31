import os, sys, time, struct, fcntl, glob, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QWidget, QPushButton, QLineEdit, QCheckBox, QComboBox, QApplication

import colors as c


# ---- Sound (no SDL, no pygame) -------------------------------------------

class SoundManager:
    def __init__(self):
        self._sounds = {
            "move":     Path(__file__).parent.parent / "resources" / "navigation.wav",
            "confirm":  Path(__file__).parent.parent / "resources" / "confirm.wav",
            "back":     Path(__file__).parent.parent / "resources" / "back.wav",
            "modal":    Path(__file__).parent.parent / "resources" / "modal.wav",
            "launch":   Path(__file__).parent.parent / "resources" / "launch.wav",
        }
        self._volumes = {
            "move": 0.1, "confirm": 0.4, "back": 0.4, "modal": 0.4, "launch": 1.0,
        }
        self._last_played = {}
        self._player = None
        for cmd in ("pw-play", "paplay", "aplay"):
            try:
                subprocess.run((cmd, "--version"), capture_output=True)
                self._player = cmd
                break
            except FileNotFoundError:
                continue

    def play(self, name):
        if self._player is None:
            return
        now = time.time()
        if name == "move":
            last = self._last_played.get("move", 0)
            if now - last < 0.1:
                return
            self._last_played["move"] = now
        path = self._sounds.get(name)
        if not path or not path.exists():
            return
        vol = self._volumes.get(name, 1.0)
        try:
            args = [self._player, str(path)]
            if self._player == "pw-play":
                args += ["--volume", str(min(1.0, max(0.0, vol)))]
            elif self._player == "paplay":
                args += [f"--volume={int(vol * 65536)}"]
            subprocess.Popen(
                args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


# ---- Joystick via /dev/input/js* (Linux legacy joystick API) --------------

_JS_EVENT_FMT = struct.Struct("IhBB")
_JS_EVENT_BUTTON = 0x01
_JS_EVENT_AXIS = 0x02
_JS_EVENT_INIT = 0x80

_JSIOCGAXES = 0x80016a11
_JSIOCGBUTTONS = 0x80016a12

_ANALOG_AXES = 6


class Joystick:
    def __init__(self, path: str):
        self.path = path
        self.fd: int | None = None
        self.axes: list[float] = []
        self.buttons: list[int] = []
        self.hats: list[tuple[int, int]] = []
        self._open()

    def _open(self):
        self.fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)

        buf = fcntl.ioctl(self.fd, _JSIOCGAXES, bytes(1))
        num_raw = buf[0]

        buf = fcntl.ioctl(self.fd, _JSIOCGBUTTONS, bytes(1))
        num_buttons = buf[0]

        if num_raw > _ANALOG_AXES:
            extra = num_raw - _ANALOG_AXES
            num_hats = extra // 2
            num_axes = _ANALOG_AXES
        else:
            num_hats = 0
            num_axes = num_raw

        self.axes = [0.0] * num_axes
        self.buttons = [0] * num_buttons
        self.hats = [(0, 0)] * num_hats

        self.poll()

    def get_button(self, n: int) -> int:
        try:
            return self.buttons[n]
        except IndexError:
            return 0

    def get_axis(self, n: int) -> float:
        try:
            return self.axes[n]
        except IndexError:
            return 0.0

    def get_hat(self, n: int) -> tuple[int, int]:
        try:
            return self.hats[n]
        except IndexError:
            return (0, 0)

    def get_numhats(self) -> int:
        return len(self.hats)

    def get_power_level(self) -> str:
        return "wired"

    def init(self):
        pass

    def poll(self):
        if self.fd is None:
            return
        try:
            data = os.read(self.fd, 4096)
        except (BlockingIOError, OSError):
            return
        offset = 0
        end = len(data)
        while offset + 8 <= end:
            _time, value, typ, number = _JS_EVENT_FMT.unpack_from(data, offset)
            offset += 8
            if typ & _JS_EVENT_INIT:
                continue
            if typ & _JS_EVENT_BUTTON:
                try:
                    self.buttons[number] = value
                except IndexError:
                    pass
            elif typ & _JS_EVENT_AXIS:
                if number < len(self.axes):
                    self.axes[number] = max(-1.0, min(1.0, value / 32767.0))
                elif number >= _ANALOG_AXES:
                    hat_idx = (number - _ANALOG_AXES) // 2
                    hat_axis = (number - _ANALOG_AXES) % 2
                    if hat_idx < len(self.hats):
                        hv = 0
                        if value > 0:
                            hv = 1
                        elif value < 0:
                            hv = -1
                        x, y = self.hats[hat_idx]
                        if hat_axis == 0:
                            x = hv
                        else:
                            y = hv
                        self.hats[hat_idx] = (x, y)

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None


def _scan_js_devices() -> list[tuple[int, str]]:
    paths = sorted(glob.glob("/dev/input/js*"))
    result = []
    for p in paths:
        try:
            idx = int(p.rsplit("js", 1)[1])
            result.append((idx, p))
        except (ValueError, IndexError):
            pass
    return result


# ---- Navigation helpers ---------------------------------------------------

NAV_TYPES = (QPushButton, QLineEdit, QCheckBox, QComboBox)


# ---- Main engine ----------------------------------------------------------

class UmuInputEngineQt:
    def __init__(self, app):
        self.app = app
        self.nav_list = []
        self.nav_index = 0
        self.last_input = 0
        self._last_input_button = 0
        self.cooldown = 0.4
        self.button_cooldown = 0.15
        self.joysticks: list[Joystick] = []
        self._axes_armed = {0: True, 1: True}
        self._controller_detected_at = 0
        self._lib_prev_btn = None
        self._prev_view_state = None

        self.quit_hold_start = 0
        self.quit_duration = 2
        self.fast_scroll_active = False
        self.rb_hold_start = 0
        self.rb_hold_duration = 0.5

        self.on_screen_keyboard_open = False

        self._nav_mode = "none"
        self._modal_ref = None
        self._btn_prev = {}

        self.sound = SoundManager()

        self._timer = QTimer()
        self._timer.timeout.connect(self.update)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)

    def start(self):
        self._timer.start(20)

    def stop(self):
        self._timer.stop()

    def refresh_hardware(self):
        if self.joysticks:
            return
        for _idx, path in _scan_js_devices():
            try:
                joy = Joystick(path)
                self.joysticks.append(joy)
            except OSError:
                continue
        if self.joysticks:
            self._controller_detected_at = time.time()

    def _is_valid(self, w):
        try:
            return w and w.isVisible() and w.isEnabled()
        except RuntimeError:
            return False

    # ---- Nav state machine -------------------------------------------------

    def _determine_mode(self):
        modal = None
        try:
            modal = QApplication.activeModalWidget()
        except RuntimeError:
            pass
        if modal:
            from launcher_pyqt.controller_file_browser import ControllerFileBrowser
            from launcher_pyqt.controller_confirm_modal import ControllerConfirmModal
            if isinstance(modal, ControllerFileBrowser):
                return "file_browser", modal
            elif isinstance(modal, ControllerConfirmModal):
                return "modal", modal
            return "modal", modal
        vs = self.app.view_state
        if vs == "library":
            return "grid", None
        elif vs in ("dashboard", "settings", "global_settings", "prefix_creator", "livesplit"):
            return "list", None
        return "none", None

    def rescan(self, priority_widget=None):
        mode, modal = self._determine_mode()
        self._nav_mode = mode
        self._modal_ref = modal
        self.nav_list = []

        if mode == "none":
            self.nav_index = 0
            self.sync_visuals()
            return

        if mode == "grid":
            view = self.app.current_view()
            if view and hasattr(view, 'grid') and view.grid:
                for child in view.grid.findChildren(QWidget):
                    if hasattr(child, 'game_id') and child.isVisible():
                        self.nav_list.append(child)

        elif mode == "list":
            view = self.app.current_view()
            if view:
                self._scan_widget_tree(view)

        elif mode == "file_browser":
            self._scan_widget_tree(modal)

        elif mode == "modal":
            self._scan_widget_tree(modal)

        sidebar_btn_count = 0
        if mode in ("grid", "list") and self.app._sidebar.isVisible():
            sidebar_nav = [btn for btn in self.app.nav_widgets
                           if btn.isVisible() and btn.isEnabled()]
            sidebar_btn_count = len(sidebar_nav)
            self.nav_list = sidebar_nav
        self._sidebar_btn_count = sidebar_btn_count

        if priority_widget and priority_widget in self.nav_list:
            self.nav_index = self.nav_list.index(priority_widget)
        elif self.nav_index >= len(self.nav_list):
            self.nav_index = 0
        self.sync_visuals()

    def _scan_widget_tree(self, parent):
        for child in parent.findChildren(QWidget):
            try:
                if isinstance(child, NAV_TYPES) and child.isEnabled():
                    if child not in self.nav_list:
                        self.nav_list.append(child)
            except RuntimeError:
                pass

    # ---- Actions -----------------------------------------------------------

    def press_current(self):
        if not self.nav_list:
            return
        target = self.nav_list[self.nav_index]
        if not self._is_valid(target):
            return

        if isinstance(target, QComboBox):
            idx = target.currentIndex()
            nxt = (idx + 1) % target.count()
            target.setCurrentIndex(nxt)
            return
        elif isinstance(target, QCheckBox):
            target.toggle()
            return
        elif isinstance(target, QPushButton):
            target.animateClick()
            return
        elif isinstance(target, QLineEdit):
            target.setFocus()
            target.selectAll()
            if not self.on_screen_keyboard_open:
                self.on_screen_keyboard_open = True
                self.trigger_virtual_keyboard(show=True)
        elif self.on_screen_keyboard_open:
            self.on_screen_keyboard_open = False
            self.trigger_virtual_keyboard(show=False)

    # ---- Visual sync -------------------------------------------------------

    def sync_visuals(self):
        if not self.nav_list:
            self.nav_index = 0
            return
        if self.nav_index >= len(self.nav_list):
            self.nav_index = 0
        target = self.nav_list[self.nav_index]
        view_state = getattr(self.app, 'view_state', '')

        if view_state == "library":
            prev = getattr(self, '_lib_prev_btn', None)
            if prev and prev != target and self._is_valid(prev):
                try:
                    if hasattr(prev, 'game_image') and prev.game_image:
                        prev.game_image.stop()
                        prev.game_image.hide()
                        prev.game_image.lower_widget()
                        prev.game_image.setStyleSheet("")
                except: pass
            if hasattr(target, 'game_image') and target.game_image:
                target.game_image.show()
                target.game_image.raise_()
                target.game_image.start()
                target.game_image.setStyleSheet(
                    f"border: 3px solid {c.ACCENT}; border-radius: 8px; padding: 3px;"
                )
            self._lib_prev_btn = target
        elif self._prev_view_state == "library":
            prev = getattr(self, '_lib_prev_btn', None)
            if prev and self._is_valid(prev):
                try:
                    if hasattr(prev, 'game_image') and prev.game_image:
                        prev.game_image.stop()
                        prev.game_image.hide()
                        prev.game_image.lower_widget()
                        prev.game_image.setStyleSheet("")
                except: pass
            self._lib_prev_btn = None
        self._prev_view_state = view_state

        for w in self.nav_list:
            if not self._is_valid(w):
                continue
            is_target = (w == target)
            if hasattr(w, 'set_focused'):
                w.set_focused(is_target)
            self._apply_focus_style(w, is_target)

        if self._is_valid(target):
            try:
                target.setFocus()
            except: pass

    def _apply_focus_style(self, widget, focused):
        try:
            if hasattr(widget, 'game_image') and widget.game_image is not None:
                return
            base = getattr(widget, '_nav_base_style', None)
            current = widget.styleSheet()
            if focused:
                if base is None or current != base:
                    base = current
                    widget._nav_base_style = base
                focus_extra = ""
                if isinstance(widget, QPushButton):
                    focus_extra = f"""
                        QPushButton {{ border: 3px solid {c.TXT_MAIN} !important;
                                       border-radius: 6px !important; }}
                    """
                elif isinstance(widget, QLineEdit):
                    focus_extra = f"""
                        QLineEdit {{ border: 2px solid {c.ACCENT} !important; }}
                    """
                elif isinstance(widget, QCheckBox):
                    focus_extra = f"""
                        QCheckBox {{ background: {c.BG_FOCUS} !important; border-radius: 4px; }}
                    """
                elif isinstance(widget, QComboBox):
                    focus_extra = f"""
                        QComboBox {{ background: {c.BG_FOCUS} !important; }}
                    """
                widget.setStyleSheet(base + focus_extra)
            else:
                if base is not None:
                    widget.setStyleSheet(base)
        except RuntimeError:
            pass

    # ---- Update loop -------------------------------------------------------

    def update(self):
        try:
            if not self.app._main_window or not self.app._main_window.isVisible():
                return
        except RuntimeError:
            return

        for joy in self.joysticks:
            joy.poll()
        self.refresh_hardware()

        now = time.time()
        cooldown_active = (now - self.last_input < self.cooldown)
        button_cooldown_active = (now - self._last_input_button < self.button_cooldown)

        if self.on_screen_keyboard_open:
            for joy in self.joysticks:
                if joy.get_button(1):
                    self.on_screen_keyboard_open = False
                    self.trigger_virtual_keyboard(show=False)
                    self._last_input_button = time.time()
                    return
            return

        for joy in self.joysticks:
            try:
                if joy.get_button(6):
                    if self.quit_hold_start == 0:
                        self.quit_hold_start = now
                        self.app.show_quit_progress(0)
                    else:
                        elapsed = now - self.quit_hold_start
                        percent = min(elapsed / self.quit_duration, 1.0)
                        self.app.show_quit_progress(percent)
                        if elapsed >= self.quit_duration:
                            self.app.close()
                else:
                    if self.quit_hold_start != 0:
                        self.quit_hold_start = 0
                        self.app.hide_quit_progress()

                if self._controller_detected_at > 0 and (now - self._controller_detected_at) < 0.5:
                    return

                if not button_cooldown_active:
                    # rising-edge: only trigger on press, not hold
                    def rising(b):
                        cur = joy.get_button(b)
                        prev = self._btn_prev.get(b, False)
                        self._btn_prev[b] = cur
                        return cur and not prev

                    if rising(0):
                        self.trigger_input(self.press_current)
                        self.sound.play("confirm")
                        return
                    elif rising(1):
                        if self._nav_mode in ("file_browser", "modal") and self._modal_ref:
                            self.trigger_input(self._modal_ref._cancel)
                        else:
                            self.trigger_input(self.app.handle_back)
                        self.sound.play("back")
                        return

                    if self._nav_mode in ("file_browser", "modal"):
                        pass
                    elif rising(4):
                        if self._nav_mode == "grid":
                            self.trigger_input(self.app.current_view().cycle_sort)
                            self.sound.play("confirm")
                        return
                    elif rising(5):
                        if self._nav_mode == "grid":
                            self.trigger_input(self.app.current_view().cycle_filter)
                            self.sound.play("confirm")
                        return
                    elif rising(2):
                        if self._nav_mode == "grid" and getattr(self.app, 'current_game_id', None):
                            gid = self.app.current_game_id
                            self.trigger_input(lambda gid=gid: self.app.show_dashboard(gid))
                        elif self._nav_mode == "list":
                            self.trigger_input(lambda: self.app.show_editor() if getattr(self.app, 'current_game_id', None) else None)
                        self.sound.play("confirm")
                        return
                    elif rising(3):
                        vs = self.app.view_state
                        if vs == "settings":
                            self.trigger_input(self.app.save_game)
                        elif vs == "dashboard":
                            QTimer.singleShot(0, lambda: self.trigger_input(self.app.browse_artwork))
                        elif vs == "library":
                            self.trigger_input(self.app.current_view().toggle_favorite)
                        self.sound.play("confirm")
                        return
                    elif rising(7):
                        self.trigger_input(lambda: self.app.try_launch_game() if getattr(self.app, 'current_game_id', None) else None)
                        if getattr(self.app, 'current_game_id', None):
                            self.sound.play("launch")
                        return
                    elif rising(8):
                        self.trigger_input(self._toggle_sidebar)
                        self.sound.play("confirm")
                        return
                    elif rising(9):
                        self.trigger_input(lambda: setattr(self, 'fast_scroll_active', not self.fast_scroll_active))
                        return

                move_x, move_y = 0, 0
                if joy.get_numhats() > 0:
                    hat = joy.get_hat(0)
                    move_x, move_y = hat[0], hat[1]
                    if move_x != 0:
                        self._axes_armed[0] = False
                    if move_y != 0:
                        self._axes_armed[1] = False
                if move_x == 0:
                    ax0 = joy.get_axis(0)
                    if self._axes_armed.get(0, True) and abs(ax0) > 0.6:
                        move_x = 1 if ax0 > 0 else -1
                        self._axes_armed[0] = False
                    elif abs(ax0) < 0.3:
                        self._axes_armed[0] = True
                if move_y == 0:
                    ax1 = joy.get_axis(1)
                    if self._axes_armed.get(1, True) and abs(ax1) > 0.6:
                        move_y = 1 if ax1 > 0 else -1
                        self._axes_armed[1] = False
                    elif abs(ax1) < 0.3:
                        self._axes_armed[1] = True

                if (move_x != 0 or move_y != 0) and not cooldown_active:
                    self.last_input = now
                    num_widgets = len(self.nav_list)
                    new_index = self.nav_index
                    self.sound.play("move")
                    if num_widgets == 0:
                        return

                    if self._nav_mode == "file_browser":
                        fb = self._modal_ref
                        header_count = getattr(fb, 'header_count', 2) if fb else 2
                        cols = getattr(fb, 'num_cols', 4) if fb else 4
                        if self.nav_index < header_count:
                            if move_x != 0:
                                new_index = (self.nav_index + move_x) % header_count
                            elif move_y == 1:
                                new_index = header_count
                            elif move_y == -1:
                                new_index = self.nav_index
                            else:
                                new_index = self.nav_index
                        else:
                            grid_idx = self.nav_index - header_count
                            if move_x != 0:
                                new_grid_idx = (grid_idx + move_x) % (num_widgets - header_count)
                                new_index = header_count + new_grid_idx
                            elif move_y != 0:
                                new_grid_idx = grid_idx + (move_y * cols)
                                if new_grid_idx < 0:
                                    new_index = 0
                                elif new_grid_idx < (num_widgets - header_count):
                                    new_index = header_count + new_grid_idx
                                else:
                                    new_index = self.nav_index
                            else:
                                new_index = self.nav_index
                    elif self._nav_mode == "grid":
                        view = self.app.current_view()
                        cols = getattr(view, 'num_cols', 5)
                        step = 5 if self.fast_scroll_active else 1
                        sidebar_offset = getattr(self, '_sidebar_btn_count', 0)
                        grid_count = num_widgets - sidebar_offset
                        if self.nav_index < sidebar_offset:
                            if move_y != 0:
                                new_index = (self.nav_index + move_y) % sidebar_offset
                            elif move_x != 0:
                                cur = self.nav_list[self.nav_index]
                                cur_geo = cur.geometry()
                                cur_rx = cur.mapToGlobal(cur_geo.topLeft()).x()
                                cur_cy = cur.mapToGlobal(cur_geo.topLeft()).y() + cur_geo.height() / 2.0
                                best_idx = None
                                best_dist = float('inf')
                                for i in range(sidebar_offset):
                                    if i == self.nav_index or not self._is_valid(self.nav_list[i]):
                                        continue
                                    w = self.nav_list[i]
                                    w_geo = w.geometry()
                                    wx = w.mapToGlobal(w_geo.topLeft()).x()
                                    if (move_x > 0 and wx <= cur_rx) or (move_x < 0 and wx >= cur_rx):
                                        continue
                                    w_cy = w.mapToGlobal(w_geo.topLeft()).y() + w_geo.height() / 2.0
                                    y_dist = abs(w_cy - cur_cy)
                                    x_dist = abs(wx - cur_rx)
                                    score = y_dist * 2 + x_dist
                                    if score < best_dist:
                                        best_dist = score
                                        best_idx = i
                                new_index = best_idx if best_idx is not None else self.nav_index
                            else:
                                new_index = self.nav_index
                        else:
                            rel_idx = self.nav_index - sidebar_offset
                            if move_x != 0:
                                if self.fast_scroll_active:
                                    new_rel = (rel_idx + (move_x * step * cols)) % grid_count
                                else:
                                    new_rel = (rel_idx + move_x) % grid_count
                                new_index = sidebar_offset + new_rel
                            elif move_y != 0:
                                new_rel = rel_idx + (move_y * step * cols)
                                if new_rel < 0:
                                    if sidebar_offset > 0:
                                        new_index = sidebar_offset - 1
                                    else:
                                        new_index = self.nav_index
                                elif new_rel >= grid_count:
                                    new_index = self.nav_index
                                else:
                                    new_index = sidebar_offset + new_rel
                    elif self._nav_mode == "modal":
                        if move_x != 0 or move_y != 0:
                            new_index = (self.nav_index + (move_x or move_y)) % num_widgets
                        else:
                            new_index = self.nav_index
                        if self._modal_ref and hasattr(self._modal_ref, 'scroll_to_selected'):
                            self._modal_ref.scroll_to_selected(new_index)
                    else:
                        if move_x != 0:
                            cur = self.nav_list[self.nav_index]
                            if self._is_valid(cur):
                                cur_geo = cur.geometry()
                                cur_rx = cur.mapToGlobal(cur_geo.topLeft()).x()
                                cur_cy = cur.mapToGlobal(cur_geo.topLeft()).y() + cur_geo.height() / 2.0
                                best_idx = None
                                best_dist = float('inf')
                                for i, w in enumerate(self.nav_list):
                                    if i == self.nav_index or not self._is_valid(w):
                                        continue
                                    w_geo = w.geometry()
                                    wx = w.mapToGlobal(w_geo.topLeft()).x()
                                    if (move_x > 0 and wx <= cur_rx) or (move_x < 0 and wx >= cur_rx):
                                        continue
                                    w_cy = w.mapToGlobal(w_geo.topLeft()).y() + w_geo.height() / 2.0
                                    y_dist = abs(w_cy - cur_cy)
                                    x_dist = abs(wx - cur_rx)
                                    score = y_dist * 2 + x_dist
                                    if score < best_dist:
                                        best_dist = score
                                        best_idx = i
                                new_index = best_idx if best_idx is not None else self.nav_index
                        elif move_y != 0:
                            new_index = (self.nav_index + move_y) % num_widgets
                        else:
                            new_index = self.nav_index

                    if 0 <= new_index < num_widgets and new_index != self.nav_index:
                        self.nav_index = new_index
                        self.sync_visuals()
                        if self._nav_mode == "file_browser" and self._modal_ref:
                            self._modal_ref.scroll_to_selected(self.nav_index)
                        if self._nav_mode == "grid":
                            self.app.scroll_to_library_item(self.nav_index)
                        return

            except (OSError, IOError):
                if joy in self.joysticks:
                    joy.close()
                    self.joysticks.remove(joy)

    def trigger_input(self, func):
        self._last_input_button = time.time()
        func()

    def trigger_virtual_keyboard(self, show=True):
        try:
            if show:
                subprocess.Popen(["steam", "steam://open/keyboard"])
            else:
                subprocess.Popen(["steam", "steam://close/keyboard"])
        except: pass

    def _toggle_sidebar(self):
        self.app._toggle_sidebar_visibility()
