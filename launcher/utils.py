import os
import re
import sys
import time
import customtkinter as ctk
from PIL import Image


def normalize(text):
    """Converts 'wUthering-waves' -> 'wutheringwaves'"""
    if not text: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()


def resource_path(relative_path):
    if "__compiled__" in globals():
        return os.path.join(os.path.dirname(__file__), relative_path)
    elif hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def format_playtime(total_minutes):
    """Converts 135 minutes to '2h 15m'"""
    if not total_minutes:
        return "Not Played yet"
    m = "minute"
    h = "hour"

    total_minutes = float(total_minutes)

    if total_minutes < 60:
        value = int(total_minutes)
        return f"{value} {m if value == 1 else m + 's'}"

    hours = total_minutes // 60
    minutes = total_minutes % 60

    if minutes == 0:
        return f"{hours} {h if hours == 1 else h + 's'}"

    minutes = int(minutes)
    hours = int(hours)
    return f"{hours} {h if hours == 1 else h + 's'} : {minutes} {m if minutes == 1 else m + 's'}"


def relative_time(timestamp_str):
    """Converts an epoch timestamp string to 'Just now', '5m ago', '2h ago', etc."""
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
        mins = int(diff / 60)
        return f"{mins}m ago"
    if diff < 86400:
        hours = int(diff / 3600)
        return f"{hours}h ago"
    days = int(diff / 86400)
    if days < 30:
        return f"{days}d ago"
    weeks = int(days / 7)
    return f"{weeks}w ago"


def get_resources_icon(name, size=(42, 42)):
    """Loads a controller icon from the resources folder."""
    icon_path = resource_path(f"resources/{name}.png")
    if os.path.exists(icon_path):
        img = Image.open(icon_path).convert("RGBA")
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    return None


def get_art_image(path, size=(180, 240)):
    """Loads and scales the image for the UI."""
    try:
        if path and os.path.exists(path):
            img = Image.open(path)
            return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception as e:
        print(f"Image load error: {e}")
    return None
