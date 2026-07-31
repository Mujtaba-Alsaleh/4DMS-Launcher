import os, sys, time, argparse, pathlib, shutil
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget,
                             QFrame, QLineEdit, QComboBox, QTextEdit, QPlainTextEdit,
                             QCheckBox, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon

import colors as c
from launcher_pyqt.config import ConfigManager, ARTWORK_DIR
from launcher_pyqt.umu_database import UMUDatabase
from launcher_pyqt.artwork import ArtworkManager
from launcher_pyqt.toast import ToastManager
from launcher_pyqt.utils import get_resources_icon
from launcher_pyqt.game_process import GameProcessManager
from launcher_pyqt.input_engine import UmuInputEngineQt
from launcher_pyqt.views.library import LibraryView
from launcher_pyqt.views.dashboard import DashboardView
from launcher_pyqt.views.editor import EditorView
from launcher_pyqt.views.global_settings import GlobalSettingsView
from launcher_pyqt.controller_confirm_modal import ControllerConfirmModal
from launcher_pyqt.controller_file_browser import ControllerFileBrowser
from launcher_pyqt.on_screen_keyboard import OnScreenKeyboard

HINT_DEFS = {
    "library": [("A", "Launch"), ("X", "Details"), ("Y", "Fav"), ("LB/RB", "Sort/Filter"), ("View", "Hold-Quit")],
    "dashboard": [("A", "Play"), ("X", "Settings"), ("Y", "Artwork"), ("B", "Back")],
    "settings": [("Y", "Save"), ("B", "Back"), ("Menu", "Sidebar")],
    "global_settings": [("B", "Back"), ("Menu", "Sidebar")],
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
        self._sidebar_visible = True

        game_count = sum(1 for k in self.config_data if k != "settings")
        if game_count > 0:
            self._sidebar_visible = False

        self.has_gamescope = shutil.which("gamescope") is not None
        self.has_umu = shutil.which("umu-run") is not None

        self._setup_window()
        self._create_sidebar()
        self._create_main_content()
        self._create_quit_overlay()
        self._create_bottom_bar()

        self.toast = ToastManager(self._content_area)
        self.game_process_manager = GameProcessManager(self)
        self.engine = UmuInputEngineQt(self)
        self.on_screen_keyboard = OnScreenKeyboard(self._content_area, self)

        self._sidebar_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self._sidebar_shortcut.activated.connect(self._toggle_sidebar_visibility)

        self.show_library()
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
        sc = QShortcut(QKeySequence("Escape"), self)
        sc.activated.connect(self._kb_back)
        self._kb_shortcuts.append(sc)

    @staticmethod
    def _kb_focus_is_editable():
        fw = QApplication.focusWidget()
        return isinstance(fw, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox))

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
        if QApplication.activeModalWidget():
            return
        if time.time() - self.engine.last_input < self.engine.cooldown:
            return
        if time.time() - self.engine._last_input_button < self.engine.button_cooldown:
            return
        vs = self.view_state
        if vs == "library" and getattr(self, 'current_game_id', None):
            gid = self.current_game_id
            self.engine.trigger_input(lambda gid=gid: self.show_dashboard(gid))
        elif vs == "dashboard":
            self.engine.trigger_input(self.show_editor)

    def _kb_back(self):
        if not self.engine:
            return
        osk = getattr(self, 'on_screen_keyboard', None)
        if osk is not None and osk.isVisible():
            self.engine.trigger_input(self.engine.close_keyboard)
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
        self.setStyleSheet(f"""
            QPushButton[focused="true"] {{ border: 3px solid {c.ACCENT} !important; }}
            QLineEdit[focused="true"] {{ border: 2px solid {c.ACCENT} !important; }}
            QCheckBox[focused="true"] {{ background: {c.BG_FOCUS} !important; }}
            QComboBox[focused="true"] {{ background: {c.BG_FOCUS} !important; }}
            QScrollBar:vertical {{ background: {c.BG_INPUT}; width: 8px; border-radius: 4px; }}
            QScrollBar::handle:vertical {{ background: {c.ACCENT}; border-radius: 4px;
                                            min-height: 30px; }}
            QScrollBar::add-line:vertical {{ height: 0; }}
            QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{ background: {c.BG_INPUT}; height: 8px; border-radius: 4px; }}
            QScrollBar::handle:horizontal {{ background: {c.ACCENT}; border-radius: 4px;
                                              min-width: 30px; }}
            QScrollBar::add-line:horizontal {{ width: 0; }}
            QScrollBar::sub-line:horizontal {{ width: 0; }}
            QToolTip {{ background: {c.BG_PANEL}; color: {c.TXT_MAIN};
                        border: 1px solid {c.ACCENT}; border-radius: 4px; padding: 4px; }}
        """)
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

    def _create_sidebar(self):
        self._sidebar = QFrame(self)
        self._sidebar.setFixedWidth(280)
        self._sidebar.setStyleSheet(f"background: {c.BG_PANEL}; border: none;")
        if not self._sidebar_visible:
            self._sidebar.hide()

        sb_layout = QVBoxLayout(self._sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        logo_lbl = QLabel()
        logo = get_resources_icon(self._select_logo(), (128, 128))
        if logo:
            logo_lbl.setPixmap(logo)
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setFixedHeight(160)
        sb_layout.addWidget(logo_lbl)

        title = QLabel("4DMS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {c.ACCENT}; font: bold 28px; padding: 10px;")
        sb_layout.addWidget(title)

        self.nav_widgets = []
        btn_style = f"""
            QPushButton {{ background: {c.ACCENT}; color: {c.TXT_MAIN};
                           font: bold 14px; border-radius: 8px;
                           padding: 12px; margin: 8px 20px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; border: 1px solid {c.TXT_MAIN}; }}
        """

        self.library_btn = QPushButton("Library")
        self.library_btn.setStyleSheet(btn_style)
        self.library_btn.clicked.connect(self.show_library)
        sb_layout.addWidget(self.library_btn)
        self.nav_widgets.append(self.library_btn)

        self.add_btn = QPushButton("+ ADD NEW GAME")
        self.add_btn.setStyleSheet(btn_style)
        self.add_btn.clicked.connect(self.add_new_game)
        sb_layout.addWidget(self.add_btn)
        self.nav_widgets.append(self.add_btn)

        self.prefix_creator_btn = QPushButton("Prefix Creator")
        self.prefix_creator_btn.setStyleSheet(btn_style)
        self.prefix_creator_btn.clicked.connect(self.create_pfx_menu)
        sb_layout.addWidget(self.prefix_creator_btn)
        self.nav_widgets.append(self.prefix_creator_btn)

        self.livesplit_btn = QPushButton("LiveSplit")
        self.livesplit_btn.setStyleSheet(btn_style)
        self.livesplit_btn.clicked.connect(self.show_livesplit)
        sb_layout.addWidget(self.livesplit_btn)
        self.nav_widgets.append(self.livesplit_btn)

        self.settings_btn = QPushButton("SETTINGS")
        self.settings_btn.setStyleSheet(btn_style)
        self.settings_btn.clicked.connect(self.show_global_settings)
        sb_layout.addWidget(self.settings_btn)
        self.nav_widgets.append(self.settings_btn)

        sb_layout.addStretch()

        self.exit_btn = QPushButton("EXIT")
        self.exit_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c.DANGER};
                           font: bold 14px; border: none; padding: 12px;
                           margin: 8px 20px; }}
            QPushButton:hover {{ background: {c.ACCENT_HOVER}; }}
        """)
        self.exit_btn.clicked.connect(self.close)
        sb_layout.addWidget(self.exit_btn)
        self.nav_widgets.append(self.exit_btn)

        self._update_sidebar_active()

    def _update_sidebar_active(self):
        active_map = {
            "library": self.library_btn,
            "dashboard": self.library_btn,
            "settings": self.library_btn,
            "global_settings": self.settings_btn,
            "prefix_creator": self.prefix_creator_btn,
            "livesplit": self.livesplit_btn,
        }
        active_btn = active_map.get(self.view_state)
        base_style = """
            QPushButton { background: %s; color: %s;
                           font: bold 14px; border-radius: 8px;
                           padding: 12px; margin: 8px 20px; }
            QPushButton:hover { background: %s; border: 1px solid %s; }
        """ % (c.ACCENT, c.TXT_MAIN, c.ACCENT_HOVER, c.TXT_MAIN)
        active_style = """
            QPushButton { background: %s; color: %s;
                           font: bold 14px; border-radius: 8px;
                           border: none; padding: 12px; margin: 8px 20px; }
            QPushButton:hover { background: %s; }
        """ % (c.BG_FOCUS, c.ACCENT, c.BG_INPUT)
        for btn in self.nav_widgets:
            if btn in (self.library_btn, self.add_btn, self.prefix_creator_btn, self.livesplit_btn, self.settings_btn):
                new_style = active_style if btn == active_btn else base_style
                btn.setStyleSheet(new_style)
                btn._nav_base_style = new_style
        eng = getattr(self, 'engine', None)
        focused = getattr(eng, '_prev_focus_target', None) if eng else None
        if focused in self.nav_widgets:
            try:
                eng._apply_focus_style(focused, True)
            except (RuntimeError, AttributeError, TypeError):
                pass

    def _create_main_content(self):
        self._content_area = QFrame(self)
        self._content_area.setStyleSheet(f"background: {c.BG_MAIN}; border-radius: 20px;")

        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self._content_layout.addWidget(self.stack, 1)

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._sidebar)
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
        self._bottom_bar.setFixedHeight(36)
        self._bottom_bar.setStyleSheet(f"background: {c.BG_PANEL}; border-top: 1px solid {c.BG_INPUT};")
        bb_layout = QHBoxLayout(self._bottom_bar)
        bb_layout.setContentsMargins(16, 2, 16, 2)
        bb_layout.setSpacing(8)

        self._hint_layout = QHBoxLayout()
        self._hint_layout.setSpacing(0)
        bb_layout.addLayout(self._hint_layout)

        bb_layout.addStretch(1)

        self._lbl_battery = QLabel()
        self._lbl_battery.setStyleSheet(f"color: {c.TXT_DIM}; font: 12px; background: transparent;")
        bb_layout.addWidget(self._lbl_battery)

        self._lbl_controller_battery = QLabel()
        self._lbl_controller_battery.setStyleSheet(f"color: {c.TXT_DIM}; font: 11px; background: transparent;")
        bb_layout.addWidget(self._lbl_controller_battery)

        self._lbl_clock = QLabel("00:00")
        self._lbl_clock.setStyleSheet(f"color: {c.TXT_MAIN}; font: bold 12px; background: transparent;")
        bb_layout.addWidget(self._lbl_clock)

        self._content_layout.addWidget(self._bottom_bar)
        self._update_bottom_bar()

    def _update_bottom_bar(self):
        while self._hint_layout.count():
            item = self._hint_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        hints = HINT_DEFS.get(self.view_state, [])
        for btn_key, action in hints:
            lbl = QLabel(f"[{btn_key}] {action}  ")
            lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 11px; background: transparent;")
            self._hint_layout.addWidget(lbl)

        self._lbl_clock.setText(time.strftime("%I:%M %p"))
        import psutil
        battery = psutil.sensors_battery()
        if battery:
            percent = f"{int(battery.percent)}%"
            text = f"🔋 {percent}"
            if battery.power_plugged:
                text += " \u26a1"
            self._lbl_battery.setText(text)
            color = c.TXT_MAIN if battery.percent > 20 else c.DANGER
            self._lbl_battery.setStyleSheet(f"color: {color}; font: 12px; background: transparent;")
        else:
            self._lbl_battery.setText("")
        ctrl = self._get_controller_battery()
        self._lbl_controller_battery.setText(ctrl)
        QTimer.singleShot(30000, self._update_bottom_bar)

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

    def _select_logo(self):
        return "logo"

    # ==================== NAVIGATION ====================

    def _push_nav(self):
        if self.view_state not in ("sidebar",):
            self.nav_stack.append(self.view_state)

    def handle_back(self):
        vs = self.view_state
        if vs == "library":
            self.nav_stack.clear()
            self._toggle_sidebar_visibility()
            return
        elif vs == "dashboard":
            self.nav_stack.clear()
            self.show_library()
            return
        elif vs == "settings" and self.current_game_id:
            self.nav_stack.clear()
            self.show_dashboard(self.current_game_id)
            return
        elif vs in ("global_settings", "prefix_creator", "livesplit"):
            self.nav_stack.clear()
            self.show_library(sidebar=True)
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

    def _hide_sidebar_for_view(self):
        anim = getattr(self, '_sidebar_anim', None)
        if anim is not None:
            anim.stop()
            self._sidebar_anim = None
        if self._sidebar_visible:
            self._sidebar_visible = False
            self._sidebar.setMinimumWidth(280)
            self._sidebar.setMaximumWidth(280)
            self._sidebar.hide()

    def current_view(self):
        return self.stack.currentWidget()

    def _toggle_sidebar_visibility(self):
        self._sidebar_visible = not self._sidebar_visible
        self._animate_sidebar()

    def _animate_sidebar(self):
        show = self._sidebar_visible
        anim = getattr(self, '_sidebar_anim', None)
        if anim is not None:
            anim.stop()
            self._sidebar_anim = None
        if show:
            start_w = 0
            self._sidebar.setMinimumWidth(0)
            self._sidebar.setMaximumWidth(0)
            self._sidebar.setVisible(True)
        else:
            start_w = self._sidebar.width()
        anim = QPropertyAnimation(self._sidebar, b"maximumWidth", self)
        anim.setDuration(180)
        anim.setStartValue(start_w)
        anim.setEndValue(280 if show else 0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(lambda v: self._sidebar.setMinimumWidth(v))
        anim.finished.connect(self._sidebar_anim_done)
        self._sidebar_anim = anim
        anim.start()

    def _sidebar_anim_done(self):
        self._sidebar_anim = None
        self._sidebar.setMinimumWidth(280)
        self._sidebar.setMaximumWidth(280)
        self._sidebar.setVisible(self._sidebar_visible)
        v = self.current_view()
        if v is not None and hasattr(v, '_rebuild') and not getattr(v, '_reflow_on_resize', False):
            v._rebuild()
        if self.engine:
            self.engine.rescan()

    def _present_view(self, key, view_state, factory, force_new=False):
        osk = getattr(self, 'on_screen_keyboard', None)
        if osk is not None and osk.isVisible():
            if self.engine:
                self.engine.close_keyboard()
            else:
                osk.close()
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
        self._update_sidebar_active()
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

    def show_livesplit(self):
        self._hide_sidebar_for_view()
        def factory():
            from launcher_pyqt.views.livesplit_view import LiveSplitView
            return LiveSplitView(self)
        self._present_view("livesplit", "livesplit", factory)

    def show_library(self, sidebar=False):
        if sidebar:
            if not self._sidebar_visible:
                self._sidebar_visible = True
                self._sidebar.setMinimumWidth(280)
                self._sidebar.setMaximumWidth(280)
                self._sidebar.show()
        else:
            self._hide_sidebar_for_view()
        self._present_view("library", "library", lambda: LibraryView(self))

    def show_dashboard(self, game_id):
        self._hide_sidebar_for_view()
        self.current_game_id = game_id
        self._present_view(("dashboard", game_id), "dashboard",
                           lambda: DashboardView(self, game_id))

    def show_editor(self):
        self._hide_sidebar_for_view()
        gid = self.current_game_id
        self._present_view(("editor", gid), "settings",
                           lambda: EditorView(self, gid))

    def show_global_settings(self):
        self._hide_sidebar_for_view()
        self._present_view("global_settings", "global_settings",
                           lambda: GlobalSettingsView(self))

    def create_pfx_menu(self, finish_callback=None):
        self._hide_sidebar_for_view()
        def factory():
            from launcher_pyqt.pfx_creator import PrefixCreator
            return PrefixCreator(self, browser_callback=self.browse,
                                 on_finish_callback=finish_callback)
        self._present_view("prefix_creator", "prefix_creator", factory,
                           force_new=True)

    # ==================== ACTIONS ====================

    def add_new_game(self):
        g_id = f"game_{os.urandom(2).hex()}"
        from launcher_pyqt.utils import generate_placeholder_art
        art_path = generate_placeholder_art(g_id, "New Game", c.ACCENT, c.BG_PANEL, str(ARTWORK_DIR))
        self.config_data[g_id] = {
            "name": "New Game",
            "exe": "", "prefix": str(pathlib.Path.home() / "Games" / "umu-prefixes" / g_id),
            "gs_on": False, "gs_w": "1280", "gs_h": "800",
            "script": "", "store": "none",
            "last_played": "", "launch_count": 0, "favorite": False,
            "added_at": str(time.time()), "notes": "", "rating": 0,
            "livesplit": False, "useMangoHud": False,
            "art": art_path or "",
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
        self._sidebar.setStyleSheet(f"background: {c.BG_PANEL}; border: none;")
        self._content_area.setStyleSheet(f"background: {c.BG_MAIN}; border-radius: 20px;")
        self._bottom_bar.setStyleSheet(f"background: {c.BG_PANEL}; border-top: 1px solid {c.BG_INPUT};")
        self._update_sidebar_active()

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
