# Probe harnesses

Controller/launch probes that verify behavior offscreen (no display needed):

```bash
source venv/bin/activate
QT_QPA_PLATFORM=offscreen python tests/tray_probe.py
```

Conventions:
- Offscreen platform: window never becomes active, so `QTest.keyClick` and `QShortcut`
  don't fire — tests call handlers directly.
- Patch `launcher_pyqt.game_process.subprocess.Popen` AFTER `LauncherWindow()`
  construction (SoundManager's `--version` check needs a real Popen).
- `QSystemTrayIcon.isSystemTrayAvailable()` is False offscreen, so the tray icon
  itself can't be exercised — only the hide/restore + engine controller-exclusivity
  mechanics.
- Each probe sets a temp `XDG_CONFIG_HOME` and `sys.argv = ['probe']`.
