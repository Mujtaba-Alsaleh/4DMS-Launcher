import os, sys, time, signal, threading, pathlib, subprocess
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from PyQt6.QtCore import QTimer
import livesplit as ls


class GameProcessManager:
    def __init__(self, app):
        self.app = app
        self.is_playing = False
        self.game_process = None
        self.current_running_game_id = None
        self.launch_lock = False
        self.launch_lock_cooldown = 2000

    def try_launch(self):
        if self.is_playing:
            self.stop()
            return
        if self.launch_lock:
            return
        if not self.app.current_game_id:
            return

        data = self.app.config_data[self.app.current_game_id]
        exe = data.get('exe', '')
        if not exe:
            return

        proton = data.get('proton', "")
        p_path = self.app.proton_paths.get(proton, "")
        if not p_path and proton and proton != "Default (UMU Internal)":
            return

        if self.app.runningOnGamescope and data.get('gs_on'):
            self.app.spawn_controller_confirm_modal(msg="Running under gamescope already. Disable gamescope option first.")
            return

        self.is_playing = True
        self.launch_lock = True

        def _update_play_btn():
            try:
                if self.app.play_btn and self.app.play_btn.isVisible():
                    self.app.play_btn.setText("STOP")
                    self.app.play_btn.setStyleSheet(f"""
                        QPushButton {{ background: #e74c3c; color: white; font: bold 16px;
                                       border-radius: 8px; }}
                        QPushButton:hover {{ background: #c0392b; }}
                    """)
            except RuntimeError:
                pass
        QTimer.singleShot(0, _update_play_btn)
        threading.Thread(target=self._run_process, daemon=True).start()
        QTimer.singleShot(self.launch_lock_cooldown, self._release_lock)

    def _release_lock(self):
        self.launch_lock = False

    def stop(self):
        if not self.is_playing:
            return
        if not self.app.current_game_id:
            return
        import psutil
        data = self.app.config_data[self.app.current_game_id]
        exe_path = data.get("exe", "")
        if not exe_path and self.game_process:
            self.game_process.terminate()
            try:
                self.game_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.game_process.kill()
                self.game_process.wait(timeout=1)
            self.game_process = None
            self.is_playing = False
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
        if self.game_process:
            self.game_process.terminate()
            try:
                self.game_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.game_process.kill()
                try:
                    self.game_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
        self.app.livesplit.stop()
        self.game_process = None
        self.is_playing = False
        self._reset_ui()

    def _run_process(self):
        start_time = time.time()
        g_id = self.app.current_game_id
        data = self.app.config_data[g_id]
        proton = data.get('proton', "")
        p_path = self.app.proton_paths.get(proton, "")
        gameid = data.get('GAMEID', "0")
        exe_path = os.path.abspath(data['exe'])
        exe_dir = os.path.dirname(exe_path)

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
            self.game_process = subprocess.Popen(cmd, env=env, cwd=exe_dir,
                                                  preexec_fn=os.setsid if sys.platform.startswith('linux') else None)
            self.current_running_game_id = g_id

            data["last_played"] = str(time.time())
            data["launch_count"] = data.get("launch_count", 0) + 1
            self.app.config_data[g_id] = data
            self.app.config_manager.save_data(self.app.config_data)

            if data.get('livesplit', False) and ls.LiveSplitManager.is_installed():
                self.app.livesplit.launch(data['prefix'], p_path)
                threading.Thread(target=self._connect_livesplit, daemon=True).start()

            QTimer.singleShot(500, self.app.showMinimized)
            while self.is_playing and self.game_process and self.game_process.poll() is None:
                time.sleep(0.5)

        except Exception as e:
            print(f"Launch Error: {e}")
        finally:
            end_time = time.time()
            duration = round((end_time - start_time) / 60, 2)

            self.app.livesplit.stop_hotkeys()
            self.app.livesplit.disconnect()

            if self.current_running_game_id:
                rgid = self.current_running_game_id
                pt = float(self.app.config_data[rgid].get('playtime', 0))
                pt += duration
                self.app.config_data[rgid]["playtime"] = str(pt)
                self.app.config_manager.save_data(self.app.config_data)

            QTimer.singleShot(0, self._reset_ui)

    def _reset_ui(self):
        self.is_playing = False
        try:
            if self.app.play_btn and self.app.play_btn.isVisible():
                self.app.play_btn.setText("PLAY")
                self.app.play_btn.setStyleSheet(f"""
                    QPushButton {{ background: #2ecc71; color: white; font: bold 16px;
                                   border-radius: 8px; }}
                    QPushButton:hover {{ background: #27ae60; }}
                """)
        except RuntimeError:
            pass
        self.game_process = None
        if self.current_running_game_id == self.app.current_game_id:
            QTimer.singleShot(0, lambda: self.app.show_dashboard(self.app.current_game_id))
        self.app.showNormal()
        self.app.raise_()
        self.app.activateWindow()

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
