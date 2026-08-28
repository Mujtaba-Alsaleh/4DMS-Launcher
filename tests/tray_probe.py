import os, sys, tempfile, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.argv = ['probe']
tmp = tempfile.mkdtemp()
os.environ['XDG_CONFIG_HOME'] = tmp
os.environ['PYTHONUNBUFFERED'] = '1'
from PyQt6.QtWidgets import QApplication
app = QApplication([])
import launcher_pyqt.game_process as gpmod

EXE_OK = os.path.join(tmp, 'game.exe')
open(EXE_OK, 'w').write('x')
PFX = os.path.join(tmp, 'pfx')
os.makedirs(os.path.join(PFX, 'drive_c'), exist_ok=True)

def make_game(gid, exe, prefix):
    return {'name': 'Game', 'exe': exe, 'prefix': prefix, 'gs_on': False,
            'gs_w': '1280', 'gs_h': '800', 'script': '', 'store': 'none',
            'last_played': '0', 'launch_count': 0, 'favorite': False,
            'added_at': '1', 'notes': '', 'rating': 0, 'livesplit': False,
            'useMangoHud': False, 'art': '', 'art_land': ''}

class FakeProc:
    def __init__(self):
        self._terminated = False
        self.returncode = None; self.poll_count = 0
    def poll(self):
        self.poll_count += 1
        if self._terminated:
            self.returncode = 0; return 0
        return None
    def terminate(self): self._terminated = True
    def kill(self): self._terminated = True
    def wait(self, timeout=2):
        if self._terminated: return 0
        return None

from PyQt6.QtWidgets import QSystemTrayIcon
tray_available = QSystemTrayIcon.isSystemTrayAvailable()
from launcher_pyqt.app import LauncherWindow
w = LauncherWindow()
_FAKE_PROC = FakeProc()
gpmod.subprocess.Popen = lambda cmd, **kw: _FAKE_PROC
w.resize(1280, 800)
w.show()
app.processEvents()
gpm = w.game_process_manager

def spin(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)

# Test 1: launch -> window hidden, engine stopped
w.current_game_id = 'g'
w.config_data['g'] = make_game('g', EXE_OK, PFX)
w.show_dashboard('g')
spin(0.3)
gpm.launch_lock = False
gpm.try_launch()
spin(3.0)
t1 = (not w.isVisible() and gpm.is_playing and not w.engine._timer.isActive())
print('T1 hidden + engine stopped:', t1, 'isVisible=', w.isVisible())
assert t1

# Test 2: game exits -> window restored, engine restarted
_FAKE_PROC._terminated = True
spin(1.0)
t2 = (w.isVisible() and w.engine._timer.isActive() and not gpm.is_playing)
print('T2 restore-on-close:', t2, 'isVisible=', w.isVisible(),
      'engineActive=', w.engine._timer.isActive(), 'is_playing=', gpm.is_playing)
assert t2
print('tray_available(offscreen)=', tray_available)
print('TRAY PROBE OK')
