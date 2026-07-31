import os
import re
import time

from PyQt6.QtGui import QPixmap


def normalize(text):
    if not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()


def resource_path(relative_path):
    if "__compiled__" in globals():
        return os.path.join(os.path.dirname(__file__), relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def format_playtime(total_minutes):
    if not total_minutes:
        return "Not Played yet"
    total_minutes = float(total_minutes)
    if total_minutes < 60:
        value = int(total_minutes)
        return f"{value} {'minute' if value == 1 else 'minutes'}"
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if minutes == 0:
        return f"{int(hours)} {'hour' if hours == 1 else 'hours'}"
    return f"{int(hours)}h {int(minutes)}m"


def relative_time(timestamp_str):
    if not timestamp_str:
        return ""
    try:
        ts = float(timestamp_str)
    except (ValueError, TypeError):
        return ""
    diff = time.time() - ts
    if diff < 0:
        return "Just now"
    if diff < 60:
        return "Just now"
    if diff < 3600:
        return f"{int(diff / 60)}m ago"
    if diff < 86400:
        return f"{int(diff / 3600)}h ago"
    days = int(diff / 86400)
    if days < 30:
        return f"{days}d ago"
    return f"{int(days / 7)}w ago"


def get_resources_icon(name, size=None):
    icon_path = resource_path(f"resources/{name}.png")
    if os.path.exists(icon_path):
        pixmap = QPixmap(icon_path)
        if size:
            pixmap = pixmap.scaled(size[0], size[1])
        return pixmap
    return None


def generate_placeholder_art(game_id, name, accent="#3d91ff", bg="#10161d", out_dir=None):
    """Render a themed placeholder poster (600x840 PNG) with QPainter. Zero deps."""
    try:
        from PyQt6.QtGui import (QImage, QPainter, QColor, QLinearGradient,
                                 QFont, QPainterPath, QPen)
        from PyQt6.QtCore import Qt, QRectF
        w, h = 600, 840
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        ac = QColor(accent)
        bgc = QColor(bg)
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, ac.darker(200))
        grad.setColorAt(0.55, bgc)
        grad.setColorAt(1.0, bgc.darker(115))
        p.fillRect(0, 0, w, h, grad)

        glow = QColor(ac)
        glow.setAlpha(40)
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(w * 0.5 - 260), int(h * 0.30), 520, 520)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(ac), 4))
        p.drawRoundedRect(6, 6, w - 12, h - 12, 24, 24)

        title = (name or "New Game").strip().upper() or "GAME"
        font = QFont()
        font.setBold(True)
        font.setPointSize(36)
        p.setFont(font)
        p.setPen(QColor(255, 255, 255))
        rect = QRectF(50, h * 0.42, w - 100, h * 0.30)
        lines = _wrap_title(p, title, int(rect.width()))
        line_h = 50
        total = len(lines) * line_h
        y = rect.top() + max(0, (rect.height() - total) / 2.0)
        for ln in lines:
            elided = p.fontMetrics().elidedText(ln, Qt.TextElideMode.ElideRight,
                                                int(rect.width()))
            p.drawText(QRectF(50, y, rect.width(), line_h),
                       Qt.AlignmentFlag.AlignCenter, elided)
            y += line_h

        p.setPen(QColor(ac))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(w * 0.5 - 60, h * 0.10, 120, 120), 0, 180 * 16)
        p.drawArc(QRectF(w * 0.5 - 40, h * 0.12, 80, 80), 180 * 16, 180 * 16)
        p.end()

        if out_dir is None:
            out_dir = os.path.join(os.path.abspath("."), "artwork")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"placeholder_{game_id}.png")
        img.save(path)
        return path
    except Exception:
        return None


def _wrap_title(painter, text, max_width):
    words = text.split()
    if not words:
        return [""]
    lines = []
    cur = ""
    for wd in words:
        trial = wd if not cur else f"{cur} {wd}"
        if painter.fontMetrics().horizontalAdvance(trial) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines or [""]
