import customtkinter as ctk
import colors as c


class ToastManager:
    def __init__(self, parent):
        self.parent = parent
        self.toasts = []
        self.max_visible = 3

    def show(self, message, duration_ms=2500):
        toast = ctk.CTkLabel(
            self.parent,
            text=message,
            font=("Arial", 13, "bold"),
            fg_color=c.BG_PANEL,
            text_color=c.TXT_MAIN,
            corner_radius=10,
            padx=16,
            pady=8
        )

        self.toasts.append(toast)
        self._reposition()

        toast.after(duration_ms, lambda: self._dismiss(toast))

    def _reposition(self):
        parent_w = self.parent.winfo_width()
        y_offset = -10
        for i, toast in enumerate(reversed(self.toasts)):
            try:
                toast.place(relx=0.5, rely=1.0, anchor="se",
                           x=-20, y=y_offset)
                y_offset -= 40
            except Exception:
                pass

    def _dismiss(self, toast):
        try:
            toast.place_forget()
            toast.destroy()
        except Exception:
            pass
        if toast in self.toasts:
            self.toasts.remove(toast)
        self._reposition()
