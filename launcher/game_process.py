import os
import time
import subprocess
import threading
import signal
import psutil
import colors as c


class GameProcessManager:
    def __init__(self, app):
        self.app = app
        self.is_playing = False
        self.game_process = None
        self.current_running_game_id = 0
        self.launch_lock = False
        self.launch_lock_cooldown = 2000

    def try_launch(self):
        if self.launch_lock:
            return

        if self.is_playing:
            self.stop()
            return

        if not self.app.current_game_id:
            return

        d = self.app.games[self.app.current_game_id]
        exe = d.get('exe', '')
        if not exe:
            return

        proton = d.get('proton', "")
        p_path = self.app.proton_paths.get(proton, "")
        if not p_path:
            if self.app.play_btn and self.app.play_btn.winfo_exists():
                self.app.play_btn.configure(text="Non-valid Proton version selected\nPlease change it in the game settings", fg_color=c.DANGER)
            return

        if self.app.runningOnGamescope and d.get('gs_on'):
            self.app.spawn_controller_confirm_modal(msg="[4DMS Warn] we are running under gamescope already. please disable gamescope option first")
            return

        self.is_playing = True
        self.launch_lock = True
        if self.app.play_btn and self.app.play_btn.winfo_exists():
            self.app.play_btn.configure(text="       STOP   ", fg_color=c.DANGER)
        threading.Thread(target=self._run_process, daemon=True).start()
        self.app.after(self.launch_lock_cooldown, self._release_lock)

    def _release_lock(self):
        self.launch_lock = False

    def stop(self):
        """Deep searches for the game string in all running processes."""
        if not self.app.current_game_id:
            return

        game_data = self.app.games[self.app.current_game_id]
        exe_path = game_data.get("exe", "")
        if not exe_path:
            if self.game_process:
                self.game_process.terminate()
            self.game_process = None
            return

        target_name = os.path.basename(exe_path).lower()
        current_pid = os.getpid()
        matches = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                p_name = (proc.info['name'] or "").lower()
                p_cmd = " ".join(proc.info['cmdline'] or []).lower()

                if target_name in p_name or target_name in p_cmd:
                    matches.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if matches:
            matches.sort(key=lambda x: x.info['create_time'], reverse=True)

            for proc in matches:
                try:
                    if proc.info['pid'] == current_pid:
                        continue
                    print(f"DEBUG: Orderly kill of {proc.info['name']} (PID: {proc.info['pid']})")
                    proc.send_signal(signal.SIGTERM)
                    try:
                        proc.wait(timeout=1)
                    except psutil.TimeoutExpired:
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if self.game_process:
            self.game_process.terminate()

        self.game_process = None

    def _run_process(self):
        start_time = time.time()
        d = self.app.games[self.app.current_game_id]
        proton = d.get('proton', "")
        if not proton:
            self.app.after(0, self._reset_ui)
            return
        p_path = self.app.proton_paths.get(proton, "")
        if not p_path:
            self.app.after(0, self._reset_ui)
            return
        gameid = d.get('GAMEID', "0")

        try:
            if not d['exe']:
                self.app.after(0, self._reset_ui)
                return
            if not p_path:
                self.app.after(0, self._reset_ui)
                return

            game_id = self.app.current_game_id
            self.app.games[game_id]["last_played"] = str(time.time())
            self.app.games[game_id]["launch_count"] = self.app.games[game_id].get("launch_count", 0) + 1

            mangohud = "1" if d.get('useMangoHud', False) else "0"
            exe_path = os.path.abspath(d['exe'])
            exe_dir = os.path.dirname(exe_path)

            env = {
                **os.environ,
                "WINEPREFIX": d['prefix'],
                "MANGOHUD": mangohud,
                "STEAM_COMPAT_DATA_PATH": d['prefix'],
                "STEAM_COMPAT_CLIENT_INSTALL_PATH": os.path.expanduser("~/.steam/steam"),
                "PROTONPATH": p_path,
                "STEAM_COMPAT_APP_ID": gameid,
                "SteamAppId": gameid,
                "GAMEID": gameid,
                "WINEDLLOVERRIDES": "winemenubuilder.exe=d;mscoree=d;mshtml=d",
            }

            cmd = []
            if d.get('script'):
                cmd.append(d['script'])

            if d.get('gs_on') and self.app.has_gamescope and not self.app.runningOnGamescope:
                gs_w = str(d.get('gs_w', "1280"))
                gs_h = str(d.get('gs_h', "720"))
                if gs_w.isdigit() and gs_h.isdigit():
                    cmd.extend(["gamescope", "-w", gs_w, "-h", gs_h, "-f", "--"])

            cmd.extend(["umu-run", exe_path])

            self.game_process = subprocess.Popen(cmd, env=env, cwd=exe_dir)
            self.current_running_game_id = game_id

            self.app.after(500, self.app.iconify)
            self.game_process.wait()

        except Exception as e:
            print(f"Launch Error: {e}")
        finally:
            end_time = time.time()
            duration_minutes = round((end_time - start_time) / 60, 2)

            if self.game_process is not None:
                rgid = self.current_running_game_id
                pt = 0
                cgpt = self.app.games[rgid].get('playtime')
                if cgpt:
                    pt = float(cgpt)
                pt += duration_minutes
                self.app.games[rgid]["playtime"] = str(pt)
                self.app.config_manager.save_data(self.app.games)

            self.app.after(0, self._reset_ui)

    def _reset_ui(self):
        self.is_playing = False
        if self.app.play_btn and self.app.play_btn.winfo_exists():
            self.app.play_btn.configure(text="PLAY", fg_color=c.SUCCESS)
        self.game_process = None
        if self.current_running_game_id == self.app.current_game_id:
            self.app.show_dashboard(self.app.current_game_id)

        self.app.deiconify()
        self.app.state('normal')
        self.app.lift()
        self.app.focus_force()
