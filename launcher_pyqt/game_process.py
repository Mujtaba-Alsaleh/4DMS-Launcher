import os, sys, time, signal, threading, pathlib, subprocess
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import livesplit as ls


class GameProcessManager(QObject):
    launch_ready = pyqtSignal()
    launch_failed = pyqtSignal(str)
    launch_finished = pyqtSignal()

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.is_playing = False
        self.launching = False
        self.game_process = None
        self.current_running_game_id = None
        self.launch_lock = False
        self.launch_lock_cooldown = 2000
        self._cancel_event = threading.Event()
        self._FIRST_RUN_CAP = 120.0
        self._GRACE_SECONDS = 2.0

        # Signals are emitted from the spawn worker thread (no Qt event loop);
        # queued connections route them to the main thread, where UI updates
        # are safe. QTimer.singleShot from a plain thread never fires.
        self.launch_ready.connect(self._on_launch_ready)
        self.launch_failed.connect(self._on_launch_failed)
        self.launch_finished.connect(self._reset_ui)

    def _on_launch_ready(self):
        self._set_play_btn("stop")
        self._hide_launch_status()
        try:
            self.app.hide_to_tray()
        except RuntimeError:
            pass

    def _on_launch_failed(self, msg):
        try:
            self.app.toast.show(msg, duration_ms=5000)
        except RuntimeError:
            pass

    def _resolve_proton(self, data):
        proton = data.get('proton', "") or ""
        if proton:
            return proton
        return self.app.config_data.get("settings", {}).get("default_proton", "") or ""

    def _is_first_run(self, prefix):
        return not self._prefix_ready(prefix)

    def _prefix_ready(self, prefix):
        return bool(prefix) and os.path.isdir(os.path.join(prefix, "drive_c"))

    def _set_play_btn(self, state):
        btn = getattr(self.app, 'play_btn', None)
        if btn is None:
            return
        if state == "stop":
            txt, bg, hover = "STOP", "#e74c3c", "#c0392b"
        elif state == "launching":
            txt, bg, hover = "LAUNCHING\u2026", "#f39c12", "#e67e22"
        else:
            txt, bg, hover = "PLAY", "#2ecc71", "#27ae60"
        try:
            if not btn.isVisible():
                return
            btn.setText(txt)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {bg}; color: white; font: bold 16px;
                               border-radius: 8px; }}
                QPushButton:hover {{ background: {hover}; }}
            """)
        except RuntimeError:
            pass

    def _show_launch_status(self, g_id, data, first_run=False):
        st = getattr(self.app, 'launch_status', None)
        if st is not None:
            try:
                st.show_status(g_id, data, first_run=first_run)
            except RuntimeError:
                pass

    def _hide_launch_status(self):
        st = getattr(self.app, 'launch_status', None)
        if st is not None:
            try:
                st.hide_status()
            except RuntimeError:
                pass

    def try_launch(self):
        if self.launching:
            self.cancel_launch()
            return
        if self.is_playing:
            self.stop()
            return
        if self.launch_lock:
            return
        if not self.app.current_game_id:
            return

        g_id = self.app.current_game_id
        data = self.app.config_data.get(g_id)
        if not data:
            return

        if not data.get('script'):
            exe = data.get('exe', '')
            name = data.get('name', 'This game')
            if not exe:
                self.app.toast.show(
                    f"No executable is set for {name}.\nOpen Game Settings and set one.",
                    duration_ms=5000)
                return
            if not os.path.isfile(exe):
                self.app.toast.show(
                    f"Executable not found for {name}:\n{exe}\nThe file was moved or deleted. Update it in Game Settings.",
                    duration_ms=6000)
                return

        proton = self._resolve_proton(data)
        p_path = self.app.proton_paths.get(proton, "")
        if not p_path and proton and proton != "Default (UMU Internal)":
            self.app.toast.show(f"Proton not found: {proton}", duration_ms=4000)
            return

        if self.app.runningOnGamescope and data.get('gs_on'):
            self.app.spawn_controller_confirm_modal(msg="Running under gamescope already. Disable gamescope option first.")
            return

        self.is_playing = True
        self.launching = True
        self.launch_lock = True
        self._cancel_event.clear()

        self._set_play_btn("launching")
        first_run = self._is_first_run(data.get('prefix', ""))
        self._show_launch_status(g_id, data, first_run=first_run)
        threading.Thread(target=self._run_process, daemon=True).start()
        QTimer.singleShot(self.launch_lock_cooldown, self._release_lock)

    def cancel_launch(self):
        if not self.launching and not self.is_playing:
            return
        self._cancel_event.set()
        try:
            self.app.toast.show("Launch cancelled", duration_ms=2500)
        except RuntimeError:
            pass
        self._set_play_btn("play")
        self._hide_launch_status()

    def _refresh_library_badges(self):
        views = self.app._views if hasattr(self.app, '_views') else {}
        for key in ("library", "home"):
            view = views.get(key)
            if view and hasattr(view, '_update_running_badges'):
                try:
                    view._update_running_badges()
                except RuntimeError:
                    pass

    def _release_lock(self):
        self.launch_lock = False

    def _terminate_process(self):
        proc = self.game_process
        if proc is None:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
        except Exception:
            pass
        self.game_process = None

    def stop(self):
        if not self.is_playing:
            return
        if not self.app.current_game_id:
            return
        self._cancel_event.set()
        self.launching = False
        self._hide_launch_status()
        import psutil
        data = self.app.config_data[self.app.current_game_id]
        exe_path = data.get("exe", "")
        if not exe_path and self.game_process:
            self._terminate_process()
            self.is_playing = False
            self.current_running_game_id = None
            self._reset_ui()
            return
        target_name = os.path.basename(exe_path).lower()
        current_pid = os.getpid()
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    p_name = (proc.info['name'] or "").lower()
                    p_cmd = " ".join(proc.info['cmdline'] or []).lower()
                    if target_name in p_name or target_name in p_cmd:
                        if proc.info['pid'] == current_pid:
                            continue
                        proc.send_signal(signal.SIGTERM)
                        try:
                            proc.wait(timeout=1)
                        except psutil.TimeoutExpired:
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"Stop error: {e}")
        self._terminate_process()
        self.app.livesplit.stop()
        self.is_playing = False
        self.current_running_game_id = None
        self._reset_ui()

    def _run_process(self):
        start_time = time.time()
        failed = None
        spawned_ok = False
        g_id = self.app.current_game_id
        data = self.app.config_data[g_id]
        proton = self._resolve_proton(data)
        p_path = self.app.proton_paths.get(proton, "")
        gameid = data.get('GAMEID', "0")
        exe_path = os.path.abspath(data['exe'])
        exe_dir = os.path.dirname(exe_path)
        prefix = data.get('prefix', "")
        first_run = bool(prefix) and self._is_first_run(prefix)

        env = {
            **os.environ,
            "WINEPREFIX": data['prefix'],
            "MANGOHUD": "1" if data.get('useMangoHud', False) else "0",
            "STEAM_COMPAT_DATA_PATH": data['prefix'],
            "STEAM_COMPAT_CLIENT_INSTALL_PATH": os.path.expanduser("~/.steam/steam"),
            "STEAM_COMPAT_APP_ID": gameid,
            "SteamAppId": gameid,
            "GAMEID": gameid,
            "WINEDLLOVERRIDES": "winemenubuilder.exe=d;mscoree=d;mshtml=d",
        }
        if p_path:
            env["PROTONPATH"] = p_path
            env["UMU_PROTON"] = p_path

        cmd = []
        if data.get('script'):
            cmd.append(data['script'])
        if data.get('gs_on') and self.app.has_gamescope and not self.app.runningOnGamescope:
            gs_w = str(data.get('gs_w', "1280"))
            gs_h = str(data.get('gs_h', "720"))
            if gs_w.isdigit() and gs_h.isdigit():
                cmd.extend(["gamescope", "-w", gs_w, "-h", gs_h, "-f", "--"])
        cmd.extend(["umu-run", exe_path])

        try:
            if self._cancel_event.is_set() or not self.is_playing:
                failed = "Launch cancelled"
            else:
                self.game_process = subprocess.Popen(cmd, env=env, cwd=exe_dir,
                                                      preexec_fn=os.setsid if sys.platform.startswith('linux') else None)
                spawned_ok = True
                self.current_running_game_id = g_id

                data["last_played"] = str(time.time())
                data["launch_count"] = data.get("launch_count", 0) + 1
                self.app.config_data[g_id] = data
                self.app.config_manager.save_data(self.app.config_data)

                if data.get('livesplit', False) and ls.LiveSplitManager.is_installed():
                    self.app.livesplit.launch(data['prefix'], p_path)
                    threading.Thread(target=self._connect_livesplit, daemon=True).start()

                # Grace window: keep the launcher visible (spinner + status) until
                # the game process is confirmed alive. First runs wait for the
                # prefix bootstrap (drive_c) instead, capped at _FIRST_RUN_CAP.
                deadline = time.time() + (self._FIRST_RUN_CAP if first_run else self._GRACE_SECONDS)
                while time.time() < deadline:
                    if self._cancel_event.is_set() or not self.is_playing:
                        self._terminate_process()
                        failed = "Launch cancelled"
                        break
                    if self.game_process.poll() is not None:
                        failed = f"Game exited during launch (exit code {self.game_process.returncode})"
                        break
                    if first_run and self._prefix_ready(prefix):
                        break
                    time.sleep(0.25)

        except Exception as e:
            print(f"Launch Error: {e}")
            failed = f"Launch error: {e}"

        finally:
            if failed is None:
                self.launching = False
                self.launch_ready.emit()
            elif failed != "Launch cancelled":
                self.launch_failed.emit(failed)

            if spawned_ok:
                while self.is_playing and self.game_process and self.game_process.poll() is None:
                    time.sleep(0.5)

                duration = round((time.time() - start_time) / 60, 2)
                rgid = self.current_running_game_id
                if rgid and rgid in self.app.config_data:
                    pt = float(self.app.config_data[rgid].get('playtime', 0))
                    pt += duration
                    self.app.config_data[rgid]["playtime"] = str(pt)
                    self.app.config_manager.save_data(self.app.config_data)

            self.app.livesplit.stop_hotkeys()
            self.app.livesplit.disconnect()

            self.launching = False
            self.launch_finished.emit()

    def _reset_ui(self):
        self.is_playing = False
        self.launching = False
        rgid = self.current_running_game_id
        self.current_running_game_id = None
        self._set_play_btn("play")
        self._hide_launch_status()
        self.game_process = None
        QTimer.singleShot(0, self._refresh_library_badges)
        if rgid == self.app.current_game_id:
            QTimer.singleShot(0, lambda: self.app.show_dashboard(self.app.current_game_id))
        self.app.restore_from_tray()

    def _connect_livesplit(self):
        for attempt in range(12):
            if not self.is_playing:
                return
            if self.app.livesplit.process and self.app.livesplit.process.poll() is not None:
                return
            time.sleep(5)
            if self.app.livesplit.connect():
                self.app.livesplit.launch_hotkey_listener()
                return
