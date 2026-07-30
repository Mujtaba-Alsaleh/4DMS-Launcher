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
