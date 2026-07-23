import os
import subprocess
import customtkinter as ctk
import colors as c


class VolumeOverlay(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color="#1a1a1a", corner_radius=16,
                        border_width=2, border_color=c.BG_FOCUS)
        self.app = app
        self.visible = False
        self.dismiss_job = None

        self.icon_label = ctk.CTkLabel(self, text="\U0001f50a", font=("Arial", 20),
                                       fg_color="transparent", text_color=c.TXT_MAIN)
        self.icon_label.pack(side="left", padx=(16, 8), pady=10)

        self.bar = ctk.CTkProgressBar(self, width=200, height=14,
                                      progress_color=c.ACCENT, fg_color=c.BG_INPUT)
        self.bar.pack(side="left", padx=(0, 16), pady=10)
        self.bar.set(0.5)

        self.pct_label = ctk.CTkLabel(self, text="50%", font=("Arial", 12, "bold"),
                                      fg_color="transparent", text_color=c.TXT_DIM, width=40)
        self.pct_label.pack(side="left", padx=(0, 8), pady=10)

        self.place_forget()
        self._has_pactl = self._check_pactl()

    def _check_pactl(self):
        try:
            result = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                                   capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False

    def get_volume(self):
        if not self._has_pactl:
            return 50
        try:
            result = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                                   capture_output=True, text=True, timeout=2)
            for part in result.stdout.split("/"):
                part = part.strip()
                if part.endswith("%"):
                    return int(part.replace("%", ""))
        except Exception:
            pass
        return 50

    def set_volume(self, percent):
        percent = max(0, min(150, percent))
        if not self._has_pactl:
            return
        try:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"],
                          timeout=2)
        except Exception:
            pass

    def toggle_mute(self):
        if not self._has_pactl:
            return
        try:
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
                          timeout=2)
        except Exception:
            pass

    def show(self):
        if not self._has_pactl:
            return
        vol = self.get_volume()
        self.bar.set(vol / 100)
        self.pct_label.configure(text=f"{vol}%")
        if vol == 0:
            self.icon_label.configure(text="\U0001f507")
        elif vol < 33:
            self.icon_label.configure(text="\U0001f508")
        elif vol < 66:
            self.icon_label.configure(text="\U0001f509")
        else:
            self.icon_label.configure(text="\U0001f50a")

        self.place(relx=0.5, rely=0.9, anchor="center")
        self.lift()
        self.visible = True
        self._schedule_dismiss()

    def hide(self):
        self.place_forget()
        self.visible = False
        if self.dismiss_job:
            self.app.after_cancel(self.dismiss_job)
            self.dismiss_job = None

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()

    def _schedule_dismiss(self):
        if self.dismiss_job:
            self.app.after_cancel(self.dismiss_job)
        self.dismiss_job = self.app.after(2000, self.hide)

    def adjust(self, delta):
        vol = self.get_volume()
        new_vol = max(0, min(150, vol + delta))
        self.set_volume(new_vol)
        self.show()
