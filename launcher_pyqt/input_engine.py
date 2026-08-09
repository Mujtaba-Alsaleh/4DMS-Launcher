import os, sys, time, struct, fcntl, glob, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtCore import QTimer, Qt, QObject, QEvent
from PyQt6.QtWidgets import (QWidget, QPushButton, QLineEdit, QTextEdit,
                             QPlainTextEdit, QCheckBox, QComboBox, QApplication,
                             QScrollArea)

import colors as c


class HoverFilter(QObject):
    """Mouse hover follows the controller nav cursor (K/M visual parity)."""

    def __init__(self, engine):
        super().__init__()
        self._engine = engine

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter and isinstance(obj, QWidget):
            self._engine.hover_widget(obj)
        return False


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

        self._nav_mode = "none"
        self._modal_ref = None
        self._btn_prev = {}
        self._prev_focus_target = None
        self._nav_index_before_osk = 0

        self.sound = SoundManager()
        self.sound.play("launch")

        self._timer = QTimer()
        self._timer.timeout.connect(self.update)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)

        try:
            QApplication.instance().focusChanged.connect(self._on_focus_changed)
        except Exception:
            pass
        self._hover_filter = HoverFilter(self)
        QApplication.instance().installEventFilter(self._hover_filter)

    def hover_widget(self, widget):
        try:
            if self._nav_mode == "none" or QApplication.activeModalWidget():
                return
            w = widget
            while w is not None:
                if isinstance(w, (QLineEdit, QComboBox, QCheckBox)):
                    return
                if w in self.nav_list:
                    idx = self.nav_list.index(w)
                    if idx != self.nav_index:
                        self.nav_index = idx
                        self.sync_visuals()
                    return
                w = w.parentWidget()
        except (RuntimeError, TypeError):
            pass

    def _on_focus_changed(self, old, new):
        try:
            if not new:
                return
            osk = getattr(self.app, 'on_screen_keyboard', None)
            osk_open = osk is not None and osk.isVisible()
            if isinstance(new, (QLineEdit, QTextEdit, QPlainTextEdit)):
                if osk_open and osk is not None:
                    osk._last_target = new
                if QApplication.mouseButtons() and not osk_open:
                    self.open_keyboard()
                    return
            elif osk_open and not getattr(new, 'osk_key', False) and not isinstance(
                    new, (QLineEdit, QTextEdit, QPlainTextEdit)):
                self.close_keyboard()
                return
            if self._nav_mode == "none" or QApplication.activeModalWidget():
                return
            w = new
            while w is not None:
                if w in self.nav_list:
                    idx = self.nav_list.index(w)
                    if idx != self.nav_index:
                        self.nav_index = idx
                        self.sync_visuals()
                    return
                w = w.parentWidget()
        except (RuntimeError, TypeError):
            pass

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
        osk = getattr(self.app, 'on_screen_keyboard', None)
        try:
            if osk is not None and osk.isVisible():
                return "keyboard", osk
        except RuntimeError:
            pass
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
        agm = getattr(self.app, '_add_game_modal', None)
        if agm is not None:
            try:
                if agm.isVisible():
                    return "modal", agm
            except RuntimeError:
                pass
        qs = getattr(self.app, 'quick_settings', None)
        try:
            if qs is not None and qs.isVisible():
                return "quick_settings", qs
        except RuntimeError:
            pass
        vs = self.app.view_state
        if vs == "library":
            return "grid", None
        elif vs in ("home", "dashboard", "settings", "global_settings", "prefix_creator", "livesplit"):
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
            if view:
                header = getattr(view, '_header_nav', None) or []
                for w in header:
                    if self._is_valid(w) and w not in self.nav_list:
                        self.nav_list.append(w)
                grid = getattr(view, 'grid', None)
                if grid:
                    for child in grid.findChildren(QWidget):
                        if hasattr(child, 'game_id') and child.isVisible() and child not in self.nav_list:
                            self.nav_list.append(child)

        elif mode == "list":
            view = self.app.current_view()
            if view:
                self._scan_widget_tree(view)

        elif mode == "keyboard":
            self._scan_widget_tree(modal)

        elif mode == "quick_settings":
            self._scan_widget_tree(modal)

        elif mode == "file_browser":
            self._scan_widget_tree(modal)

        elif mode == "modal":
            self._scan_widget_tree(modal)

        tabs = []
        if mode in ("grid", "list"):
            tab_btns = getattr(self.app, 'tab_buttons', [])
            tabs = [b for b in tab_btns if self._is_valid(b)]
        self._tabs_btn_count = len(tabs)
        self._tab_keys = [b._tab_key for b in tabs]
        self._tabs_active_idx = self._tab_active_index()
        self.nav_list = tabs + self.nav_list

        view_changed = self.app.view_state != getattr(self, '_prev_view_state', None)
        if priority_widget and priority_widget in self.nav_list:
            self.nav_index = self.nav_list.index(priority_widget)
        elif view_changed and tabs and len(self.nav_list) > len(tabs):
            header = getattr(view, '_header_nav', None) if mode == "grid" else None
            skip = len(header) if header else 0
            if len(self.nav_list) > len(tabs) + skip:
                self.nav_index = len(tabs) + skip
            else:
                self.nav_index = len(tabs)
        elif self.nav_index >= len(self.nav_list):
            self.nav_index = 0
        self.sync_visuals()

    def _tab_active_index(self):
        keys = getattr(self, '_tab_keys', [])
        if not keys:
            return 0
        idx_map = {"home": 0, "library": 1, "dashboard": 1, "settings": 1,
                   "prefix_creator": 1, "livesplit": 2, "tools": 2,
                   "global_settings": 3}
        idx = idx_map.get(self.app.view_state, 1)
        return idx if idx < len(keys) else 0

    def _scan_widget_tree(self, parent):
        for child in parent.findChildren(QWidget):
            try:
                if getattr(child, '_mouse_only', False):
                    continue
                if isinstance(child, NAV_TYPES) and child.isEnabled() and child.isVisible():
                    if child not in self.nav_list:
                        self.nav_list.append(child)
            except RuntimeError:
                pass

    def _details_open(self):
        view = self.app.current_view()
        if view is None:
            return False
        return bool(getattr(view, 'details_overlay_open', False)
                    or getattr(view, 'art_overlay_open', False)
                    or getattr(view, 'settings_overlay_open', False))

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
        elif hasattr(target, 'game_id'):
            gid = getattr(target, 'game_id', None)
            if gid:
                self.app.show_dashboard(gid)
            return
        elif isinstance(target, (QLineEdit, QTextEdit, QPlainTextEdit)):
            target.setFocus()
            target.selectAll()
            osk = getattr(self.app, 'on_screen_keyboard', None)
            if osk is not None and osk.isVisible():
                self.close_keyboard()
            else:
                self.open_keyboard()

    # ---- Visual sync -------------------------------------------------------

    def _clear_focus(self, widget):
        if widget is None:
            return
        try:
            if hasattr(widget, 'set_focused'):
                widget.set_focused(False)
            if hasattr(widget, 'game_image') and widget.game_image is not None:
                widget.game_image.stop()
                widget.game_image.hide()
            base = getattr(widget, '_nav_base_style', None)
            if base is not None:
                widget.setStyleSheet(base)
        except (RuntimeError, TypeError):
            pass

    def sync_visuals(self):
        prev_focus = getattr(self, '_prev_focus_target', None)
        if not self.nav_list:
            if prev_focus is not None:
                self._clear_focus(prev_focus)
                self._prev_focus_target = None
            self.nav_index = 0
            return
        if self.nav_index >= len(self.nav_list):
            self.nav_index = 0
        target = self.nav_list[self.nav_index]
        if prev_focus is not None and prev_focus is not target and prev_focus not in self.nav_list:
            self._clear_focus(prev_focus)
        self._prev_focus_target = target
        try:
            nf = getattr(self.app, '_on_nav_focus', None)
            if nf is not None:
                nf(target)
        except RuntimeError:
            pass
        view_state = getattr(self.app, 'view_state', '')

        if view_state in ("library", "home"):
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
        elif self._prev_view_state in ("library", "home"):
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
                if self._nav_mode not in ("grid", "file_browser"):
                    self._ensure_scrolled(target)
                if isinstance(target, (QLineEdit, QTextEdit, QPlainTextEdit)):
                    pass
                elif isinstance(target, QComboBox) and self._nav_mode == "quick_settings":
                    pass
                elif self._nav_mode == "keyboard":
                    fw = QApplication.focusWidget()
                    if not isinstance(fw, (QLineEdit, QTextEdit, QPlainTextEdit)):
                        target.setFocus()
                else:
                    target.setFocus()
            except Exception:
                pass

    def _ensure_scrolled(self, widget):
        """Scroll any QScrollArea ancestor so the focused widget is visible.
        Programmatic setFocus() does NOT auto-scroll scroll areas, so nav
        could land on (and click) buttons that are off-screen. Home carousel
        posters animate instead (see HomeView._scroll_to_poster)."""
        if getattr(self.app, 'view_state', '') == "home" and hasattr(widget, 'game_id'):
            try:
                v = self.app.current_view()
                if v is not None and hasattr(v, '_scroll_to_poster'):
                    v._scroll_to_poster(widget)
                    return
            except RuntimeError:
                pass
        p = widget.parentWidget()
        while p is not None:
            try:
                if isinstance(p, QScrollArea):
                    p.ensureWidgetVisible(widget, 8, 8)
                    return
            except (RuntimeError, AttributeError):
                return
            p = p.parentWidget()

    def _apply_focus_style(self, widget, focused):
        try:
            if hasattr(widget, 'game_image'):
                return
            base = getattr(widget, '_nav_base_style', None)
            current = widget.styleSheet()
            if focused:
                if base is None:
                    base = current
                    widget._nav_base_style = base
                focus_extra = ""
                if isinstance(widget, QPushButton):
                    focus_extra = f"""
                        QPushButton {{ border: 3px solid {c.FOCUS_RING} !important;
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
                if base is not None and current != base:
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
                        if self._nav_mode != "keyboard":
                            self.sound.play("confirm")
                        return
                    elif rising(1):
                        if self._nav_mode == "keyboard":
                            self.trigger_input(self.close_keyboard)
                        elif self._nav_mode == "quick_settings":
                            self.trigger_input(self.app.close_quick_settings)
                        elif self._nav_mode in ("file_browser", "modal") and self._modal_ref:
                            self.trigger_input(self._modal_ref._cancel)
                        else:
                            self.trigger_input(self.app.handle_back)
                        self.sound.play("back")
                        return

                    if self._nav_mode in ("file_browser", "modal", "keyboard"):
                        pass
                    elif rising(4):
                        if self._nav_mode in ("grid", "list"):
                            self.trigger_input(lambda: self.app._kb_tab(-1))
                            self.sound.play("confirm")
                        return
                    elif rising(5):
                        if self._nav_mode in ("grid", "list"):
                            self.trigger_input(lambda: self.app._kb_tab(1))
                            self.sound.play("confirm")
                        return
                    elif rising(2):
                        if self._nav_mode != "quick_settings":
                            vs = self.app.view_state
                            if vs in ("home", "library", "dashboard") and not self._details_open():
                                gid = self.app._focused_game_id() or getattr(self.app, 'current_game_id', None)
                                if gid:
                                    self.trigger_input(lambda gid=gid: self.app.open_quick_settings(gid))
                        self.sound.play("confirm")
                        return
                    elif rising(3):
                        if self._nav_mode == "quick_settings":
                            self.sound.play("confirm")
                            return
                        vs = self.app.view_state
                        if vs == "settings":
                            self.trigger_input(self.app.save_game)
                        elif vs == "dashboard" and not self._details_open():
                            view = self.app.current_view()
                            if view is not None and not getattr(view, 'art_overlay_open', False):
                                QTimer.singleShot(0, lambda: self.trigger_input(view._open_art))
                        elif vs in ("library", "home"):
                            gid = self.app._focused_game_id()
                            if gid:
                                self.trigger_input(lambda gid=gid: self.app.toggle_favorite_for(gid))
                        self.sound.play("confirm")
                        return
                    elif rising(7):
                        if self._nav_mode == "quick_settings":
                            return
                        gid = self.app._focused_game_id() or getattr(self.app, 'current_game_id', None)
                        if gid:
                            self.app.current_game_id = gid
                            self.trigger_input(self.app.try_launch_game)
                            self.sound.play("launch")
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
                    self._move_selection(move_x, move_y)

            except (OSError, IOError):
                if joy in self.joysticks:
                    joy.close()
                    self.joysticks.remove(joy)

    def _move_selection(self, move_x, move_y):
        self.last_input = time.time()
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
            tabs = getattr(self, '_tabs_btn_count', 0)
            header = getattr(view, '_header_nav', None) if view else None
            header_count = len(header) if header else 0
            grid_count = num_widgets - tabs - header_count
            if grid_count <= 0:
                new_index = self.nav_index
            elif self.nav_index < tabs:
                if move_x != 0:
                    new_index = (self.nav_index + move_x) % tabs
                elif move_y == 1:
                    if getattr(self, '_tabs_active_idx', 0) != self.nav_index:
                        self.app._activate_tab(self._tab_keys[self.nav_index])
                    else:
                        new_index = tabs
                else:
                    new_index = self.nav_index
            elif self.nav_index < tabs + header_count:
                rel = self.nav_index - tabs
                if move_x != 0:
                    new_index = tabs + ((rel + move_x) % header_count)
                elif move_y == 1:
                    new_index = tabs + header_count
                elif move_y == -1:
                    new_index = getattr(self, '_tabs_active_idx', 0)
                else:
                    new_index = self.nav_index
            else:
                rel_idx = self.nav_index - tabs - header_count
                if move_x != 0:
                    if self.fast_scroll_active:
                        new_rel = (rel_idx + (move_x * step * cols)) % grid_count
                    elif move_x == -1 and rel_idx % cols == 0:
                        new_rel = min(rel_idx + (cols - 1), grid_count - 1)
                    elif move_x == 1 and rel_idx % cols == cols - 1:
                        new_rel = max(rel_idx - (cols - 1), 0)
                    elif move_x == 1 and rel_idx == grid_count - 1 and rel_idx % cols != cols - 1:
                        new_rel = rel_idx - (rel_idx % cols)
                    else:
                        new_rel = rel_idx + move_x
                    new_index = tabs + header_count + new_rel
                elif move_y != 0:
                    new_rel = rel_idx + (move_y * step * cols)
                    if new_rel < 0:
                        if header_count:
                            col = rel_idx % cols
                            hidx = 0 if col == 0 else header_count - 1
                            new_index = tabs + hidx
                        else:
                            new_index = getattr(self, '_tabs_active_idx', 0)
                    elif new_rel >= grid_count:
                        new_index = self.nav_index
                    else:
                        new_index = tabs + header_count + new_rel
        elif self._nav_mode == "modal":
            if move_x != 0 or move_y != 0:
                new_index = (self.nav_index + (move_x or move_y)) % num_widgets
            else:
                new_index = self.nav_index
            if self._modal_ref and hasattr(self._modal_ref, 'scroll_to_selected'):
                self._modal_ref.scroll_to_selected(new_index)
        elif self._nav_mode == "keyboard":
            new_index = self._move_selection_keyboard(move_x, move_y)
        else:
            tabs = getattr(self, '_tabs_btn_count', 0)
            if tabs and self.nav_index < tabs:
                if move_x != 0:
                    new_index = (self.nav_index + move_x) % tabs
                elif move_y == 1:
                    if getattr(self, '_tabs_active_idx', 0) != self.nav_index:
                        self.app._activate_tab(self._tab_keys[self.nav_index])
                    else:
                        new_index = tabs
                else:
                    new_index = self.nav_index
            elif move_x != 0:
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
                        if tabs and i < tabs:
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
                if tabs and self.nav_index == tabs and move_y == -1:
                    new_index = getattr(self, '_tabs_active_idx', 0)
                else:
                    content_count = num_widgets - tabs
                    if content_count <= 0:
                        new_index = self.nav_index
                    else:
                        start = self.nav_index - tabs if tabs else self.nav_index
                        for step in range(1, content_count):
                            idx = tabs + ((start + move_y * step) % content_count)
                            if self._is_valid(self.nav_list[idx]):
                                new_index = idx
                                break
                        else:
                            new_index = self.nav_index
            else:
                new_index = self.nav_index

        if 0 <= new_index < num_widgets and new_index != self.nav_index:
            self.nav_index = new_index
            self.sync_visuals()
            if self._nav_mode == "file_browser" and self._modal_ref:
                self._modal_ref.scroll_to_selected(self.nav_index)
            if self._nav_mode == "grid":
                self.app.scroll_to_library_item(self.nav_index)

    def trigger_input(self, func):
        self._last_input_button = time.time()
        func()

    def open_keyboard(self):
        osk = getattr(self.app, 'on_screen_keyboard', None)
        if osk is None:
            return
        self._nav_index_before_osk = self.nav_index
        osk.open()
        self.rescan()
        self.nav_index = 0
        self.sync_visuals()
        if self.nav_list:
            try:
                self.nav_list[0].setFocus()
            except RuntimeError:
                pass
        self.sound.play("confirm")

    def close_keyboard(self):
        osk = getattr(self.app, 'on_screen_keyboard', None)
        if osk is None:
            return
        osk.close()
        self.rescan()
        self.nav_index = max(0, min(self._nav_index_before_osk, len(self.nav_list) - 1))
        self.sync_visuals()

    def _move_selection_keyboard(self, move_x, move_y):
        if move_x == 0 and move_y == 0:
            return self.nav_index
        widgets = self.nav_list
        if not widgets or self.nav_index >= len(widgets):
            return self.nav_index
        osk = getattr(self.app, 'on_screen_keyboard', None)
        rows = getattr(osk, 'rows', None)
        if not rows:
            return self.nav_index
        cur = widgets[self.nav_index]
        try:
            cur_x = cur.mapTo(osk, cur.rect().center()).x()
        except (RuntimeError, AttributeError):
            return self.nav_index
        rr = cc = -1
        for r, row in enumerate(rows):
            for c, b in enumerate(row):
                if b is cur:
                    rr, cc = r, c
                    break
            if rr >= 0:
                break
        if rr < 0:
            return self.nav_index
        if move_x != 0:
            row = rows[rr]
            nb = row[(cc + move_x) % len(row)]
            try:
                return widgets.index(nb)
            except ValueError:
                return self.nav_index
        nr = rr + move_y
        if not (0 <= nr < len(rows)):
            return self.nav_index
        best = None
        best_dist = float('inf')
        for b in rows[nr]:
            try:
                bx = b.mapTo(osk, b.rect().center()).x()
            except RuntimeError:
                continue
            d = abs(bx - cur_x)
            if d < best_dist:
                best_dist = d
                best = b
        if best is None:
            return self.nav_index
        try:
            return widgets.index(best)
        except ValueError:
            return self.nav_index
