import os, sys, time, argparse, pathlib, shutil
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget,
                             QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

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
from launcher_pyqt.views.volume_overlay import VolumeOverlay
from launcher_pyqt.controller_confirm_modal import ControllerConfirmModal
from launcher_pyqt.controller_file_browser import ControllerFileBrowser

HINT_DEFS = {
    "library": [("A", "Launch"), ("X", "Details"), ("Y", "Fav"), ("LB/RB", "Sort/Filter"), ("Menu", "Sidebar")],
    "dashboard": [("A", "Play"), ("X", "Settings"), ("Y", "Artwork"), ("B", "Back"), ("Menu", "Sidebar")],
    "settings": [("Y", "Save"), ("B", "Back"), ("X", "Reload"), ("Menu", "Sidebar")],
    "sidebar": [],
    "global_settings": [("B", "Back")],
    "prefix_creator": [("B", "Back")],
    "browser": [("A", "Select"), ("B", "Back")],
    "modal": [],
}


class LauncherWindow(QMainWindow):
    signal_game_exit = pyqtSignal()

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
        self.play_btn = None
        self.livesplit = None

        self.has_gamescope = shutil.which("gamescope") is not None
        self.has_umu = shutil.which("umu-run") is not None

        self._setup_window()
        self._create_sidebar()
        self._create_main_content()
        self._create_controller_ui()
        self._create_quit_overlay()
        self._create_bottom_bar()

        self.toast = ToastManager(self._content_area)
        self.volume_overlay = VolumeOverlay(self._content_area)
        self.game_process_manager = GameProcessManager(self)
        self.engine = UmuInputEngineQt(self)

        self.show_library()

        self.engine.start()

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
                           padding: 12px; margin: 8px 20px;
                           border: 2px solid %s; }
            QPushButton:hover { background: %s; }
        """ % (c.ACCENT, c.TXT_MAIN, c.TXT_MAIN, c.ACCENT_HOVER)
        for btn in self.nav_widgets:
            if btn in (self.library_btn, self.add_btn, self.prefix_creator_btn, self.settings_btn):
                if btn == active_btn:
                    btn.setStyleSheet(active_style)
                else:
                    btn.setStyleSheet(base_style)

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

    def _create_controller_ui(self):
        self._icon_size = (24, 24)
        self._icon_labels = {}
        for key in ("A", "B", "X", "Y", "menu", "view"):
            lbl = QLabel(self._content_area)
            pix = get_resources_icon(f"button_{key.lower()}", self._icon_size)
            if pix:
                lbl.setPixmap(pix)
            lbl.hide()
            self._icon_labels[key] = lbl
        self._icon_anchors = {}

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

        # Hint labels (left)
        self._hint_labels = []
        self._hint_layout = QHBoxLayout()
        self._hint_layout.setSpacing(0)
        bb_layout.addLayout(self._hint_layout)

        bb_layout.addStretch(1)

        # Status (right)
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
        # Update hints
        for i in reversed(range(self._hint_layout.count())):
            w = self._hint_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        hints = HINT_DEFS.get(self.view_state, [])
        for btn_key, action in hints:
            lbl = QLabel(f"[{btn_key}] {action}  ")
            lbl.setStyleSheet(f"color: {c.TXT_DIM}; font: 11px; background: transparent;")
            self._hint_layout.addWidget(lbl)

        # Update clock + battery
        self._lbl_clock.setText(time.strftime("%H:%M %p"))
        import psutil
        battery = psutil.sensors_battery()
        if battery:
            percent = f"{int(battery.percent)}%"
            text = f"{percent}"
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
        match = {"Deep Blue": "logo", "Nordic": "logo_nordic", "Legion Red": "logo_red"}
        return match.get(self.current_theme, "logo")

    # ==================== NAVIGATION ====================

    def _push_nav(self):
        if self.view_state not in ("sidebar",):
            self.nav_stack.append(self.view_state)

    def handle_back(self):
        if self.view_state == "modal":
            return
        if self.view_state == "sidebar":
            if self.engine:
                self.engine._toggle_sidebar()
            return
        if self.nav_stack:
            prev = self.nav_stack.pop()
            if prev == "library":
                self.show_library()
                return
            elif prev == "dashboard" and self.current_game_id:
                self.show_dashboard(self.current_game_id)
                return
        if self.view_state == "settings":
            self.show_dashboard(self.current_game_id)
        elif self.view_state == "library":
            self.view_state = "sidebar"
            if self.engine:
                self.engine.rebuild_nav_map(include_sidebar=True, priority_widget=self.library_btn)
            return
        elif self.view_state in ("global_settings", "prefix_creator"):
            self.show_library()
            return
        elif self.view_state == "dashboard":
            self.show_library()
            return
        if self.engine:
            self.engine.rebuild_nav_map()

    def current_view(self):
        return self.stack.currentWidget()

    def show_library(self):
        self._push_nav()
        self.view_state = "library"
        self._clear_stack()
        view = LibraryView(self)
        self.stack.addWidget(view)
        self.stack.setCurrentWidget(view)
        self._update_bottom_bar()
        self._update_sidebar_active()
        if self.engine:
            def _lib_nav():
                v = self.current_view()
                if v and hasattr(v, 'grid') and v.grid:
                    self.engine.rebuild_nav_map_library(v.grid)
            QTimer.singleShot(100, _lib_nav)

    def show_dashboard(self, game_id):
        self._push_nav()
        self.view_state = "dashboard"
        self.current_game_id = game_id
        self._clear_stack()
        view = DashboardView(self, game_id)
        self.stack.addWidget(view)
        self.stack.setCurrentWidget(view)
        self._update_bottom_bar()
        self._update_sidebar_active()
        if self.engine:
            self.engine.rebuild_nav_map()

    def show_editor(self):
        self._push_nav()
        self.view_state = "settings"
        self._clear_stack()
        view = EditorView(self, self.current_game_id)
        self.stack.addWidget(view)
        self.stack.setCurrentWidget(view)
        self._update_bottom_bar()
        self._update_sidebar_active()
        if self.engine:
            self.engine.rebuild_nav_map()

    def show_global_settings(self):
        self._push_nav()
        self.view_state = "global_settings"
        self._clear_stack()
        view = GlobalSettingsView(self)
        self.stack.addWidget(view)
        self.stack.setCurrentWidget(view)
        self._update_bottom_bar()
        self._update_sidebar_active()
        if self.engine:
            self.engine.rebuild_nav_map()

    def create_pfx_menu(self):
        self._push_nav()
        self.view_state = "prefix_creator"
        self._clear_stack()
        from launcher_pyqt.pfx_creator import PrefixCreator
        view = PrefixCreator(self, browser_callback=self.browse)
        self.stack.addWidget(view)
        self.stack.setCurrentWidget(view)
        if self.engine:
            self.engine.rebuild_nav_map()
        self._update_bottom_bar()
        self._update_sidebar_active()

    def _clear_stack(self):
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

    # ==================== ACTIONS ====================

    def add_new_game(self):
        g_id = f"game_{os.urandom(2).hex()}"
        self.config_data[g_id] = {
            "name": "New Game",
            "exe": "", "prefix": str(pathlib.Path.home() / "Games" / "umu-prefixes" / g_id),
            "gs_on": False, "gs_w": "1280", "gs_h": "800",
            "script": "", "store": "none",
            "last_played": "", "launch_count": 0, "favorite": False,
            "added_at": str(time.time()), "notes": "", "rating": 0,
            "livesplit": False, "useMangoHud": False,
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
        prev_state = self.view_state
        self.view_state = "browser"
        browser = ControllerFileBrowser(self, is_file=is_file, callback=on_selected, engine=self.engine)
        browser.exec()
        self.view_state = prev_state

    def spawn_controller_confirm_modal(self, func=None, msg=None):
        current_vs = self.view_state
        self.view_state = "modal"

        def on_user_decision(confirmed):
            if confirmed and func:
                func()
            self.view_state = current_vs
            if self.engine:
                self.engine.rebuild_nav_map()

        modal = ControllerConfirmModal(self, engine=self.engine, on_result=on_user_decision, msg=msg)
        modal.exec()

    def apply_theme_visuals(self):
        self._sidebar.setStyleSheet(f"background: {c.BG_PANEL}; border: none;")
        self._content_area.setStyleSheet(f"background: {c.BG_MAIN}; border-radius: 20px;")
        self._bottom_bar.setStyleSheet(f"background: {c.BG_PANEL}; border-top: 1px solid {c.BG_INPUT};")
        self._update_sidebar_active()

    # ==================== CONTROLLER UI ====================

    def anchor_icon(self, key, widget):
        self._icon_anchors[key] = widget

    def clear_controller_ui(self):
        keys = [k for k in self._icon_anchors if k != "view"]
        for k in keys:
            del self._icon_anchors[k]
            if k in self._icon_labels:
                self._icon_labels[k].hide()

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
