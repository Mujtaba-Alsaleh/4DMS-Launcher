import subprocess

import customtkinter as ctk
import colors as c
class EditableTitle(ctk.CTkFrame):
    def __init__(self, parent, initial_text, engine ,callback=None):
        # Set fg_color to transparent so it blends in
        super().__init__(parent, fg_color="transparent")
        self.text = initial_text
        self.callback = callback
        self.engine = engine


        self.controller_trigger = ctk.CTkButton(
            self,
            text="✎", 
            width=1,
            height=1,
            fg_color="transparent",
            border_width=0, # Hidden until focused
            corner_radius=8,
            command=self.enable_editing
        )
        self.controller_trigger.pack(side="right", padx=5)

        # 1. THE LABEL
        self.label = ctk.CTkLabel(
            self, text=self.text, 
            font=("Arial", 32, "bold"), # Bigger font for the "Hero" title
            text_color=c.ACCENT 
        )

        # Use a wider pady to give the title its own "Zone"
        self.label.pack(expand=True, fill="x", pady=(10, 30))
        self.label.bind("<Enter>", self._on_hover)
        self.label.bind("<Leave>", self._off_hover)
        self.label.bind("<Double-Button-1>", lambda e: self.enable_editing())
        # The subtle underline hint
        self.underline = ctk.CTkFrame(self, height=2, fg_color="transparent", width=100)
        self.underline.pack(fill="x")

        # 2. THE ENTRY
        self.entry = ctk.CTkEntry(self, font=("Arial", 24), justify="center")
        
        self.entry.bind("<Return>", lambda e: self.save_edit())
        self.entry.bind("<Escape>", lambda e: self.disable_editing())

    def enable_editing(self):
        self.label.pack_forget()
        self.entry.pack(expand=True, pady=5, fill='x')
        self.entry.delete(0, "end")
        self.entry.insert(0, self.text)
        self.entry.focus_set()

        self.engine.on_screen_keyboard_open = True # Tell input engine to ignore controller input while keyboard is open
        self.after(10, lambda: self.entry.select_range(0, 'end')) # Highlight all text
        self.after(20, lambda: self.entry.icursor('end'))       # Put cursor at end
        self.trigger_virtual_keyboard(show=True)  # Open on-screen keyboard for touch users


    def disable_editing(self):
        self.entry.pack_forget()
        self.label.pack(expand=True, fill="x")
        self.engine.on_screen_keyboard_open = False # Re-enable controller input
        self.trigger_virtual_keyboard(show=False) # Close on-screen keyboard


    def save_edit(self):
        new_text = self.entry.get().strip()
        if new_text:
            self.text = new_text
            self.label.configure(text=self.text)
            if self.callback:
                self.callback(self.text)
        self.disable_editing()

    def _on_hover(self, event):
            self.underline.configure(fg_color=c.ACCENT) # Flash the accent color
            self.label.configure(text_color="#FFFFFF")  # Make text pop

    def _off_hover(self, event):
        self.underline.configure(fg_color="transparent")
        self.label.configure(text_color=c.ACCENT)



    def trigger_virtual_keyboard(self, show=True):
        try:
            if show:
                subprocess.Popen(["steam", "steam://open/keyboard"])
            else:
                subprocess.Popen(["steam", "steam://close/keyboard"])
        except:
            pass