import sys, os, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from PyQt6.QtWidgets import QApplication
from launcher_pyqt.app import LauncherWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("4DMS Launcher")
    win = LauncherWindow()
    win.show()
    sys.exit(app.exec())
