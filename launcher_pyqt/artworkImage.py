import os
from pathlib import Path
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap, QMovie
from PyQt6.QtCore import QSize, Qt


class GameImage(QLabel):
    def __init__(self, master, file_path, width=250, height=350, quality=85):
        super().__init__(master)
        self.original_path = file_path
        self._width = width
        self._height = height
        self.quality = quality
        self.is_playing = False
        self._movie = None
        self._pixmap = None

        self.setFixedSize(width, height)
        self.setScaledContents(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        if os.path.exists(file_path):
            self._load_initial()

    def _load_initial(self):
        ext = os.path.splitext(self.original_path)[1].lower()
        if ext in ('.webp', '.gif'):
            movie = QMovie(self.original_path)
            movie.setCacheMode(QMovie.CacheMode.CacheNone)
            movie.setScaledSize(QSize(self._width, self._height))
            self._movie = movie
            self.setMovie(movie)
        else:
            pix = QPixmap(self.original_path)
            if not pix.isNull():
                self._pixmap = pix.scaled(self._width, self._height,
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
                self.setPixmap(self._pixmap)

    def start(self):
        if self._movie and not self.is_playing:
            self.is_playing = True
            self._movie.start()

    def stop(self):
        if self._movie:
            self.is_playing = False
            self._movie.stop()
            self._movie.jumpToFrame(0)

    def lift_widget(self):
        self.raise_()

    def lower_widget(self):
        self.lower()

    def resize_to_parent(self):
        parent = self.parent()
        if parent:
            pw = parent.width()
            ph = parent.height()
            if pw > 1 and ph > 1:
                self._width = pw
                self._height = ph
                self.setFixedSize(pw, ph)
                if self._movie:
                    self._movie.setScaledSize(QSize(pw, ph))
                elif self._pixmap:
                    self._pixmap = QPixmap(self.original_path).scaled(pw, ph)
                    self.setPixmap(self._pixmap)
