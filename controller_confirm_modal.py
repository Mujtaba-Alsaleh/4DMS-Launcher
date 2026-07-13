import os
import customtkinter as ctk
import colors as c
class ControllerConfirmModal(ctk.CTkToplevel):
    def __init__(self, parent,engine=None,on_result=None,msg=None):
        super().__init__(parent)

        # Validate engine early
        if not engine or not on_result:
            print("Cannot proceed without engine or empty on_result callback")
            self.result = False
            self.destroy()
            return

        self.engine = engine
        self.on_result = on_result  # Callback to send result back
        self.result = None  # Initialize result variable

        # UI Setup
        self.title("Confirm action")
        self.geometry("1365x335")
        self.attributes('-topmost', True)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        txt = "Do you want to confirm the action?" if not msg else msg
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(expand=True, fill="both", padx=20, pady=20)

        ctk.CTkLabel(content_frame,text=txt,
            width=330,
            anchor="center",
            justify="left",
            wraplength=1200
        ).pack(pady=(0, 20))

        self.confirm = ctk.CTkButton(content_frame,text="Confirm",
            fg_color=c.SUCCESS,hover_color=c.ACCENT_HOVER,
            height=40, 
            font=("Arial", 13, "bold"),
            command=lambda: self.finish())
        self.confirm.pack(side="left", padx=10)

        self.cancelbtn = ctk.CTkButton(content_frame, text="Cancel", fg_color=c.DANGER,hover_color=c.DANGER_HOVER, width=100, height=40,
            command=self.cancel)
        self.cancelbtn.pack(side="left", padx=10)

        self.update_idletasks()
        self.engine.rebuild_nav_map_modal(self)


    def finish(self):
        self.result = True
        self.on_result(self.result)
        self.withdraw()

    def cancel(self):
        self.result = False
        self.on_result(self.result)
        self.withdraw()

    def on_close(self):
        self.cancel()
