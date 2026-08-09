import os, sys, time, argparse, pathlib, shutil
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget,
                             QFrame, QLineEdit, QComboBox, QTextEdit, QPlainTextEdit,
                             QCheckBox, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon

import colors as c
import launcher_pyqt.ui as ui
from launcher_pyqt.config import ConfigManager, ARTWORK_DIR
from launcher_pyqt.umu_database import UMUDatabase
from launcher_pyqt.artwork import ArtworkManager
from launcher_pyqt.toast import ToastManager
from launcher_pyqt.utils import get_resources_icon
from launcher_pyqt.game_process import GameProcessManager
from launcher_pyqt.input_engine import UmuInputEngineQt
from launcher_pyqt.views.library import LibraryView
from launcher_pyqt.views.home import HomeView
from launcher_pyqt.views.dashboard import DashboardView
from launcher_pyqt.views.editor import EditorView
from launcher_pyqt.views.global_settings import GlobalSettingsView
from launcher_pyqt.controller_confirm_modal import ControllerConfirmModal
from launcher_pyqt.controller_file_browser import ControllerFileBrowser
from launcher_pyqt.on_screen_keyboard import OnScreenKeyboard
from launcher_pyqt.quick_settings import QuickSettingsOverlay
from launcher_pyqt.launch_status import LaunchStatusOverlay

HINT_DEFS = {
    "home": [("A", "Open"), ("MENU", "Launch"), ("X", "Quick-Set"), ("Y", "Fav"), ("LB/RB", "Tabs"), ("View", "Hold-Quit")],
    "library": [("A", "Open"), ("MENU", "Launch"), ("X", "Quick-Set"), ("Y", "Fav"), ("LB/RB", "Tabs"), ("View", "Hold-Quit")],
    "dashboard": [("A", "Play"), ("X", "Quick-Set"), ("Y", "Artwork"), ("B", "Back")],
    "settings": [("Y", "Save"), ("B", "Back")],
    "global_settings": [("B", "Back")],
    "prefix_creator": [("B", "Back")],
    "livesplit": [("B", "Back")],
}


class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.args = self._parse_args()
        self._main_window = self

        self.config_manager = ConfigManager()
        self.config_manager.ensure_data_file()
        self.config_data, self.current_theme = self.config_manager.load_data()
        self.umu_db = UMUDatabase()
        self.artwork_manager = ArtworkManager(ARTWORK_DIR)
        self.runningOnGamescope = False

        self.view_state = "library"
        self.current_game_id = None
        self.proton_paths = self.config_manager.scan_proton_versions()
        self.nav_stack = []
        self._views = {}
        self.play_btn = None
        import livesplit as ls
        self.livesplit = ls.LiveSplitManager()

        self.has_gamescope = shutil.which("gamescope") is not None
        self.has_umu = shutil.which("umu-run") is not None

        self._setup_window()
        self._create_header()
        self._create_main_content()
        self._create_quit_overlay()
        self._create_bottom_bar()

        self.toast = ToastManager(self._content_area)
        self.game_process_manager = GameProcessManager(self)
        self.engine = UmuInputEngineQt(self)
        self.on_screen_keyboard = OnScreenKeyboard(self._content_area, self)
        self.quick_settings = QuickSettingsOverlay(self)
        self.launch_status = LaunchStatusOverlay(self)
        self._add_game_modal = None

        self.show_home()
        self.engine.start()
        self._setup_keyboard_shortcuts()

    def _setup_keyboard_shortcuts(self):
        self._kb_shortcuts = []
        for key in ("Up", "Down", "Left", "Right", "W", "A", "S", "D"):
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(lambda k=key: self._kb_move(k))
            self._kb_shortcuts.append(sc)
        for key in ("Return", "Enter"):
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(self._kb_activate)
            self._kb_shortcuts.append(sc)
        sc = QShortcut(QKeySequence("Space"), self)
        sc.activated.connect(self._kb_details)
        self._kb_shortcuts.append(sc)
        sc = QShortcut(QKeySequence("Q"), self)
        sc.activated.connect(lambda: self._kb_tab(-1))
        self._kb_shortcuts.append(sc)
        sc = QShortcut(QKeySequence("E"), self)
        sc.activated.connect(lambda: self._kb_tab(1))
        self._kb_shortcuts.append(sc)
        sc = QShortcut(QKeySequence("Escape"), self)
        sc.activated.connect(self._kb_back)
        self._kb_shortcuts.append(sc)
        sc = QShortcut(QKeySequence("R"), self)
        sc.activated.connect(self._kb_start)
        self._kb_shortcuts.append(sc)
        sc = QShortcut(QKeySequence("F"), self)
        sc.activated.connect(self._kb_favorite)
        self._kb_shortcuts.append(sc)

    def _kb_tab(self, direction):
        if self._kb_focus_is_text() or not self.engine:
            return
        if self.quick_settings_open:
            return
        if QApplication.activeModalWidget():
            return
        if time.time() - self.engine.last_input < self.engine.cooldown:
            return
        tabs = getattr(self, 'tab_buttons', [])
        if not tabs:
            return
        idx_map = {"home": 0, "library": 1, "dashboard": 1, "settings": 1,
                   "prefix_creator": 1, "livesplit": 2, "tools": 2,
                   "global_settings": 3}
        cur = idx_map.get(self.view_state, 1)
        nxt = (cur + direction) % len(tabs)
        key = tabs[nxt]._tab_key
        self.engine.trigger_input(lambda k=key: self._activate_tab(k))

    @staticmethod
    def _kb_focus_is_editable():
        fw = QApplication.focusWidget()
        return isinstance(fw, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox))

    @staticmethod
    def _kb_focus_is_text():
        fw = QApplication.focusWidget()
        return isinstance(fw, (QLineEdit, QTextEdit, QPlainTextEdit))

    def _kb_move(self, key):
        if self._kb_focus_is_editable() or not self.engine:
            return
        if time.time() - self.engine.last_input < self.engine.cooldown:
            return
        dx = dy = 0
        if key in ("Left", "A"):
            dx = -1
        elif key in ("Right", "D"):
            dx = 1
        elif key in ("Up", "W"):
            dy = -1
        elif key in ("Down", "S"):
            dy = 1
        self.engine._move_selection(dx, dy)

    def _kb_activate(self):
        if not self.engine:
            return
        fw = QApplication.focusWidget()
        nav_target = None
        if self.engine.nav_list and 0 <= self.engine.nav_index < len(self.engine.nav_list):
            nav_target = self.engine.nav_list[self.engine.nav_index]
        if fw is not nav_target:
            self.engine.trigger_input(self.engine.press_current)
            return
        if isinstance(fw, (QLineEdit, QTextEdit, QPlainTextEdit)):
            return
        if time.time() - self.engine.last_input < self.engine.cooldown:
            return
        if time.time() - self.engine._last_input_button < self.engine.button_cooldown:
            return
        if isinstance(fw, QPushButton):
            try:
                self.engine.trigger_input(fw.animateClick)
            except RuntimeError:
                pass
            return
        if isinstance(fw, QCheckBox):
            try:
                self.engine.trigger_input(fw.toggle)
            except RuntimeError:
                pass
            return
        if isinstance(fw, QComboBox):
            try:
                idx = fw.currentIndex()
                nxt = (idx + 1) % fw.count()
                self.engine.trigger_input(lambda fw=fw, nxt=nxt: fw.setCurrentIndex(nxt))
            except RuntimeError:
                pass
            return
        self.engine.trigger_input(self.engine.press_current)

    def _kb_details(self):
        if self._kb_focus_is_editable() or not self.engine:
            return
        osk = getattr(self, 'on_screen_keyboard', None)
        if osk is not None and osk.isVisible():
            return
        if self.quick_settings_open:
            return
        if QApplication.activeModalWidget():
            return
        if time.time() - self.engine.last_input < self.engine.cooldown:
            return
        if time.time() - self.engine._last_input_button < self.engine.button_cooldown:
            return
        view = self.current_view()
        if view is not None:
            if getattr(view, 'art_overlay_open', False):
                return
            if getattr(view, 'details_overlay_open', False):
                return
            if getattr(view, 'settings_overlay_open', False):
                return
        vs = self.view_state
        if vs in ("library", "home", "dashboard"):
            gid = self._focused_game_id() or self.current_game_id
            if gid:
                self.engine.trigger_input(lambda gid=gid: self.open_quick_settings(gid))

    def _focused_game_id(self):
        eng = getattr(self, 'engine', None)
        if eng and eng.nav_list and 0 <= eng.nav_index < len(eng.nav_list):
            w = eng.nav_list[eng.nav_index]
            try:
                if hasattr(w, 'game_id'):
                    return w.game_id
            except RuntimeError:
                pass
        return getattr(self, 'current_game_id', None)

    def _on_nav_focus(self, widget):
        try:
            v = self.current_view()
        except RuntimeError:
            return
        if v is None:
            return
        m = getattr(v, '_on_nav_focus', None)
        if m is not None:
            try:
                m(widget)
            except RuntimeError:
                pass

    def _kb_start(self):
        """R = Start/MENU: quick-launch the focused/current game."""
        if self._kb_focus_is_editable() or not self.engine:
            return
        if self.quick_settings_open:
            return
        if QApplication.activeModalWidget():
            return
        if time.time() - self.engine.last_input < self.engine.cooldown:
            return
        if time.time() - self.engine._last_input_button < self.engine.button_cooldown:
            return
        gid = self._focused_game_id() or self.current_game_id
        if gid:
            self.current_game_id = gid
            self.engine.trigger_input(self.try_launch_game)

    def _kb_favorite(self):
        """F = Y: favorite on home/library, artwork on dashboard, save in editor."""
        if self._kb_focus_is_editable() or not self.engine:
            return
        if self.quick_settings_open:
            return
        if QApplication.activeModalWidget():
            return
        if time.time() - self.engine.last_input < self.engine.cooldown:
            return
        if time.time() - self.engine._last_input_button < self.engine.button_cooldown:
            return
        vs = self.view_state
        if vs == "settings":
            self.engine.trigger_input(self.save_game)
        elif vs == "dashboard":
            view = self.current_view()
            if view is not None and not (getattr(view, 'details_overlay_open', False)
                                         or getattr(view, 'settings_overlay_open', False)
                                         or getattr(view, 'art_overlay_open', False)):
                self.engine.trigger_input(view._open_art)
        elif vs in ("home", "library"):
            gid = self._focused_game_id()
            if gid:
                self.engine.trigger_input(lambda gid=gid: self.toggle_favorite_for(gid))

    def _kb_back(self):
        if not self.engine:
            return
        osk = getattr(self, 'on_screen_keyboard', None)
        if osk is not None and osk.isVisible():
            self.engine.trigger_input(self.engine.close_keyboard)
            return
        if self.quick_settings_open:
            self.engine.trigger_input(self.close_quick_settings)
            return
        if self._kb_focus_is_editable():
            return
        if QApplication.activeModalWidget():
            return
        if time.time() - self.engine._last_input_button < self.engine.button_cooldown:
            return
        self.engine.trigger_input(self.handle_back)

    def _parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--fullscreen', action='store_true')
        return parser.parse_args()

    def _setup_window(self):
        self.setWindowTitle("4DMS Launcher")
        family = ui.register_fonts()
        self.setStyleSheet(ui.app_qss(family))
        logo = get_resources_icon("logo", (256, 256))
        if logo and not logo.isNull():
            self.setWindowIcon(QIcon(logo))
        if self.args.fullscreen:
            screen = QApplication.primaryScreen()
            geo = screen.geometry()
            self.setGeometry(geo)
            self.showFullScreen()
            self.runningOnGamescope = True
        else:
            self.setGeometry(0, 0, 1920, 1200)
            self.showNormal()

    def _create_header(self):
        self._header = QFrame(self)
        self._header.setStyleSheet(ui.header_style())
        self._header.setFixedHeight(58)

        hb = QHBoxLayout(self._header)
        hb.setContentsMargins(16, 6, 16, 6)
        hb.setSpacing(12)

        self._logo_btn = QPushButton()
        pm = get_resources_icon("logo", (44, 44))
        if pm:
            self._logo_btn.setIcon(QIcon(pm))
            self._logo_btn.setIconSize(pm.size())
        self._logo_btn.setFixedSize(46, 46)
        self._logo_btn.setToolTip("Home")
        self._logo_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; }")
        self._logo_btn.clicked.connect(self.show_home)
        hb.addWidget(self._logo_btn)

        self.tab_buttons = []
        hb.addStretch(1)
        tabs_box = QHBoxLayout()
        tabs_box.setSpacing(6)
        for key, label in ui.TABS:
            btn = QPushButton(label)
            btn._tab_key = key
            btn.setStyleSheet(ui.tab_style(False))
            btn._nav_base_style = ui.tab_style(False)
            btn.clicked.connect(
                lambda checked=False, k=key: self._activate_tab(k))
            tabs_box.addWidget(btn)
            self.tab_buttons.append(btn)
        hb.addLayout(tabs_box)
        hb.addStretch(1)

        self._header_right = QFrame()
        self._header_right.setStyleSheet(f"""
            QFrame {{ background: {c.BG_INPUT}; border-radius: 14px;
                      padding: 4px 12px; border: 1px solid {c.BORDER}; }}
        """)
        hr_lay = QHBoxLayout(self._header_right)
        hr_lay.setContentsMargins(10, 4, 10, 4)
        hr_lay.setSpacing(10)

        self._lbl_battery = QLabel()
        self._lbl_battery.setStyleSheet(
            f"color: {c.TXT_DIM}; font-size: 13px; background: transparent;")
        hr_lay.addWidget(self._lbl_battery)

        self._lbl_controller_battery = QLabel()
        self._lbl_controller_battery.setStyleSheet(
            f"color: {c.TXT_DIM}; font-size: 12px; background: transparent;")
        hr_lay.addWidget(self._lbl_controller_battery)

        self._lbl_clock = QLabel("00:00")
        self._lbl_clock.setStyleSheet(
            f"color: {c.TXT_MAIN}; font-weight: 600; font-size: 13px; background: transparent;")
        hr_lay.addWidget(self._lbl_clock)

        hb.addWidget(self._header_right)

        self._update_tab_active()
        self._update_header_right()

    def _update_header_right(self):
        self._lbl_clock.setText(time.strftime("%I:%M %p"))
        try:
            import psutil
            battery = psutil.sensors_battery()
        except Exception:
            battery = None
        if battery:
            percent = int(battery.percent)
            text = f"\U0001f50b {percent}%"
            if battery.power_plugged:
                text += " \u26a1"
            self._lbl_battery.setText(text)
            color = c.TXT_MAIN if percent > 20 else c.DANGER
            self._lbl_battery.setStyleSheet(
                f"color: {color}; font-size: 13px; background: transparent;")
        else:
            self._lbl_battery.setText("")
        ctrl = self._get_controller_battery()
        self._lbl_controller_battery.setText(ctrl)
        QTimer.singleShot(30000, self._update_header_right)

    def _activate_tab(self, key):
        if key == "home":
            self.show_home()
        elif key == "library":
            self.show_library()
        elif key == "tools":
            self.show_livesplit()
        elif key == "settings":
            self.show_global_settings()

    def _update_tab_active(self):
        idx_map = {"home": 0, "library": 1, "dashboard": 1, "settings": 1,
                   "prefix_creator": 1, "livesplit": 2, "tools": 2,
                   "global_settings": 3}
        active_idx = idx_map.get(self.view_state, 1)
        for i, btn in enumerate(self.tab_buttons):
            style = ui.tab_style(i == active_idx)
            btn.setStyleSheet(style)
            btn._nav_base_style = style
        eng = getattr(self, 'engine', None)
        focused = getattr(eng, '_prev_focus_target', None) if eng else None
        if focused in self.tab_buttons:
            try:
                eng._apply_focus_style(focused, True)
            except (RuntimeError, AttributeError, TypeError):
                pass

    def _create_main_content(self):
        self._content_area = QFrame(self)
        self._content_area.setStyleSheet(f"background: {c.BG_MAIN}; border: none;")

        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self._content_layout.addWidget(self.stack, 1)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._header)
        main_layout.addWidget(self._content_area, 1)
        self.setCentralWidget(main_widget)

    def _create_quit_overlay(self):
        self._quit_overlay = QFrame(self._content_area)
        self._quit_overlay.setStyleSheet(f"""
            background: #1a1a1a; border: 2px solid {c.BG_FOCUS}; border-radius: 20px;
        """)
        ql = QVBoxLayout(self._quit_overlay)
        self._quit_label = QLabel("QUITTING...")
        self._quit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._quit_label.setStyleSheet("color: white; font: bold 24px;")
        ql.addWidget(self._quit_label)
        self._quit_progress = QLabel()
        self._quit_progress.setFixedSize(200, 15)
        self._quit_progress.setStyleSheet(f"""
            background: {c.BG_INPUT}; border-radius: 7px;
        """)
        ql.addWidget(self._quit_progress, alignment=Qt.AlignmentFlag.AlignCenter)
        self._quit_overlay.resize(280, 100)
        self._quit_overlay.hide()

    def _create_bottom_bar(self):
        self._bottom_bar = QFrame(self._content_area)
        self._bottom_bar.setFixedHeight(40)
        self._bottom_bar.setStyleSheet(
            f"background: {c.BG_PANEL}; border-top: 1px solid {c.BORDER};")
        bb_layout = QHBoxLayout(self._bottom_bar)
        bb_layout.setContentsMargins(16, 3, 16, 3)
        bb_layout.setSpacing(10)

        self._hint_layout = QHBoxLayout()
        self._hint_layout.setSpacing(14)
        bb_layout.addLayout(self._hint_layout)

        bb_layout.addStretch(1)

        self._content_layout.addWidget(self._bottom_bar)
        self._update_bottom_bar()

    def _update_bottom_bar(self):
        while self._hint_layout.count():
            item = self._hint_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        hints = HINT_DEFS.get(self.view_state, [])
        for key, action in hints:
            self._hint_layout.addWidget(ui.hint_pill(key, action))

    def _get_controller_battery(self):
        if not hasattr(self, 'engine'):
            return ""
        for joy in self.engine.joysticks:
            try:
                level = joy.get_power_level()
                if level in ("wired",):
                    return ""
                elif level in ("max", "full"):
                    return "\U0001f7e2"
                elif level == "medium":
                    return "\U0001f7e1"
                elif level == "low":
                    return "\U0001f534"
                elif level == "empty":
                    return "\u26ab"
            except Exception:
                pass
        return ""

    # ==================== NAVIGATION ====================

    def open_quick_settings(self, gid):
        qs = getattr(self, 'quick_settings', None)
        if qs is not None and gid:
            qs.open(gid)

    def close_quick_settings(self):
        qs = getattr(self, 'quick_settings', None)
        if qs is not None:
            qs.close()

    @property
    def quick_settings_open(self):
        qs = getattr(self, 'quick_settings', None)
        try:
            return bool(qs is not None and qs.isVisible())
        except RuntimeError:
            return False

    def _push_nav(self):
        if self.view_state not in ("sidebar",):
            self.nav_stack.append(self.view_state)

    def handle_back(self):
        if self.quick_settings_open:
            self.close_quick_settings()
            return
        view = self.current_view()
        if view is not None:
            if getattr(view, 'art_overlay_open', False):
                if hasattr(view, '_close_art'):
                    view._close_art()
                return
            if getattr(view, 'details_overlay_open', False):
                if hasattr(view, '_close_details'):
                    view._close_details()
                return
            if getattr(view, 'settings_overlay_open', False):
                if hasattr(view, '_close_settings'):
                    view._close_settings()
                return
        vs = self.view_state
        if vs in ("home", "library"):
            self.nav_stack.clear()
            return
        elif vs == "dashboard":
            self.nav_stack.clear()
            self.show_library()
            return
        elif vs == "settings" and self.current_game_id:
            self.nav_stack.clear()
            self.show_dashboard(self.current_game_id)
            return
        elif vs in ("global_settings", "prefix_creator", "livesplit", "tools"):
            self.nav_stack.clear()
            self.show_library()
            return
        if self.nav_stack:
            prev = self.nav_stack.pop()
            if prev == "library":
                self.show_library()
                return
            elif prev == "dashboard" and self.current_game_id:
                self.show_dashboard(self.current_game_id)
                return
            elif prev == "settings" and self.current_game_id:
                self.show_editor()
                return
        if self.engine:
            self.engine.rescan()

    def current_view(self):
        return self.stack.currentWidget()

    def _present_view(self, key, view_state, factory, force_new=False):
        osk = getattr(self, 'on_screen_keyboard', None)
        if osk is not None and osk.isVisible():
            if self.engine:
                self.engine.close_keyboard()
            else:
                osk.close()
        qs = getattr(self, 'quick_settings', None)
        if qs is not None and qs.isVisible():
            qs.close()
        self._prune_stale_views()
        is_new = False
        if force_new and key in self._views:
            old = self._views.pop(key)
            self.stack.removeWidget(old)
            old.deleteLater()
        if key not in self._views:
            view = factory()
            self._views[key] = view
            self.stack.addWidget(view)
            is_new = True
        view = self._views[key]
        self._push_nav()
        self.view_state = view_state
        self.stack.setCurrentWidget(view)
        if not is_new and hasattr(view, 'refresh'):
            view.refresh()
        self._update_bottom_bar()
        self._update_tab_active()
        if self.engine:
            QTimer.singleShot(0, self.engine.rescan)
        self._animate_view_fade()

    def _animate_view_fade(self):
        prev = getattr(self, '_view_fade_anim', None)
        if prev is not None:
            try:
                prev.stop()
            except RuntimeError:
                pass
            self._view_fade_anim = None
        try:
            self.stack.setGraphicsEffect(None)
        except RuntimeError:
            pass
        eff = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(eff)
        eff.setOpacity(0.0)
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(160)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda a=anim: self._fade_finished(a))
        self._view_fade_anim = anim
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _fade_finished(self, anim):
        if getattr(self, '_view_fade_anim', None) is anim:
            self._view_fade_anim = None
        try:
            self.stack.setGraphicsEffect(None)
        except RuntimeError:
            pass

    def _prune_stale_views(self):
        for key in [k for k in self._views
                    if isinstance(k, tuple) and k[0] in ("dashboard", "editor")
                    and k[1] not in self.config_data]:
            w = self._views.pop(key)
            self.stack.removeWidget(w)
            w.deleteLater()

    def _purge_game_views(self, gid):
        for key in [k for k in self._views
                    if isinstance(k, tuple) and k[0] in ("dashboard", "editor")
                    and k[1] == gid]:
            w = self._views.pop(key)
            self.stack.removeWidget(w)
            w.deleteLater()

    def show_home(self):
        self._present_view("home", "home", lambda: HomeView(self))

    def show_livesplit(self):
        def factory():
            from launcher_pyqt.views.livesplit_view import LiveSplitView
            return LiveSplitView(self)
        self._present_view("livesplit", "livesplit", factory)

    def show_library(self):
        self._present_view("library", "library", lambda: LibraryView(self))

    def show_dashboard(self, game_id):
        self.current_game_id = game_id
        self._present_view(("dashboard", game_id), "dashboard",
                           lambda: DashboardView(self, game_id))

    def show_editor(self):
        gid = self.current_game_id
        self._present_view(("editor", gid), "settings",
                           lambda: EditorView(self, gid))

    def show_global_settings(self):
        self._present_view("global_settings", "global_settings",
                           lambda: GlobalSettingsView(self))

    def create_pfx_menu(self, finish_callback=None):
        def factory():
            from launcher_pyqt.pfx_creator import PrefixCreator
            return PrefixCreator(self, browser_callback=self.browse,
                                 on_finish_callback=finish_callback)
        self._present_view("prefix_creator", "prefix_creator", factory,
                           force_new=True)

    # ==================== ACTIONS ====================

    def open_add_game(self):
        from launcher_pyqt.add_game_modal import AddGameModal
        if self.engine:
            self.engine.sound.play("modal")
        modal = AddGameModal(self, engine=self.engine)
        self._add_game_modal = modal
        modal.finished.connect(lambda r: self._on_add_game_done(modal))
        modal.open()

    def _on_add_game_done(self, modal):
        if getattr(self, '_add_game_modal', None) is modal:
            self._add_game_modal = None
        if not modal.result:
            return
        g_id = modal.result["gid"]
        self.config_data[g_id] = {
            "name": modal.result["name"],
            "exe": modal.result["exe"],
            "prefix": modal.result["prefix"],
            "gs_on": False, "gs_w": "1280", "gs_h": "800",
            "script": "", "store": "none",
            "last_played": "", "launch_count": 0, "favorite": False,
            "added_at": str(time.time()), "notes": "", "rating": 0,
            "livesplit": False, "useMangoHud": False,
            "art": modal.result["art"],
            "art_land": modal.result.get("art_land", ""),
        }
        self.config_manager.save_data(self.config_data)
        self.current_game_id = g_id
        self.show_dashboard(g_id)
        QTimer.singleShot(200, lambda: self.open_quick_settings(g_id))

    def jump_to_letter(self, letter):
        self.show_library()
        lib = self._views.get("library")
        if lib is not None and hasattr(lib, "scroll_to_letter"):
            QTimer.singleShot(0, lambda l=letter: lib.scroll_to_letter(l))

    def add_new_game(self):
        g_id = f"game_{os.urandom(2).hex()}"
        from launcher_pyqt.utils import generate_placeholder_art, derive_landscape
        out = str(ARTWORK_DIR)
        art_path = generate_placeholder_art(g_id, "New Game", c.ACCENT, c.BG_PANEL, out)
        art_land = derive_landscape(g_id, "New Game", c.ACCENT, c.BG_PANEL, out, art_path)
        self.config_data[g_id] = {
            "name": "New Game",
            "exe": "", "prefix": str(pathlib.Path.home() / "Games" / "umu-prefixes" / g_id),
            "gs_on": False, "gs_w": "1280", "gs_h": "800",
            "script": "", "store": "none",
            "last_played": "", "launch_count": 0, "favorite": False,
            "added_at": str(time.time()), "notes": "", "rating": 0,
            "livesplit": False, "useMangoHud": False,
            "art": art_path or "",
            "art_land": art_land or "",
        }
        self.current_game_id = g_id
        self.show_editor()

    def save_game(self):
        v = self.current_view()
        if hasattr(v, 'save'):
            v.save()

    def scroll_to_library_item(self, index):
        v = self.current_view()
        if hasattr(v, 'scroll_to_item'):
            v.scroll_to_item(index)
        if self.engine and 0 <= index < len(self.engine.nav_list):
            btn = self.engine.nav_list[index]
            if hasattr(btn, 'game_id'):
                self.current_game_id = btn.game_id

    def try_launch_game(self):
        self.game_process_manager.try_launch()

    def browse_artwork(self):
        v = self.current_view()
        if hasattr(v, '_browse_artwork'):
            v._browse_artwork()

    def toggle_favorite(self):
        v = self.current_view()
        if hasattr(v, 'toggle_favorite'):
            v.toggle_favorite()

    def toggle_favorite_for(self, game_id):
        if game_id not in self.config_data:
            return
        current = self.config_data[game_id].get("favorite", False)
        self.config_data[game_id]["favorite"] = not current
        self.config_manager.save_data(self.config_data)
        state = "added to" if not current else "removed from"
        self.toast.show(f"Favorites: {state}")
        v = self.current_view()
        if hasattr(v, '_rebuild'):
            v._rebuild()
        elif hasattr(v, 'refresh'):
            v.refresh()

    def browse(self, label, is_file):
        def on_selected(path):
            if path:
                label.setText(path)

        self.engine.sound.play("modal")
        browser = ControllerFileBrowser(self, is_file=is_file, callback=on_selected, engine=self.engine)
        browser.exec()

    def spawn_controller_confirm_modal(self, func=None, msg=None):
        def on_user_decision(confirmed):
            if confirmed and func:
                func()

        modal = ControllerConfirmModal(self, engine=self.engine, on_result=on_user_decision, msg=msg)
        modal.exec()

    def apply_theme_visuals(self):
        self._header.setStyleSheet(ui.header_style())
        self._content_area.setStyleSheet(f"background: {c.BG_MAIN}; border: none;")
        self._bottom_bar.setStyleSheet(
            f"background: {c.BG_PANEL}; border-top: 1px solid {c.BORDER};")
        self._update_tab_active()
        self._update_bottom_bar()
        self._update_header_right()

    # ==================== QUIT OVERLAY ====================

    def show_quit_progress(self, percent):
        self._quit_overlay.show()
        self._quit_overlay.raise_()
        pw = self._content_area.width()
        ph = self._content_area.height()
        self._quit_overlay.move(pw // 2 - 140, ph // 2 - 50)
        self._quit_progress.setFixedWidth(int(200 * percent))
        if percent > 0.9:
            self._quit_label.setText("RELEASE TO CANCEL")
            self._quit_label.setStyleSheet("color: #ff4444; font: bold 24px;")
        else:
            self._quit_label.setText("QUITTING...")
            self._quit_label.setStyleSheet("color: white; font: bold 24px;")

    def hide_quit_progress(self):
        self._quit_overlay.hide()

    def closeEvent(self, event):
        if self.engine:
            self.engine.stop()
        if self.game_process_manager and self.game_process_manager.is_playing:
            self.game_process_manager.stop()
        if event:
            event.accept()
        os._exit(0)
