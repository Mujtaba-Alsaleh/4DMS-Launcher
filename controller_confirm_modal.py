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
        self.geometry("780x130")
        self.attributes('-topmost', True)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        txt = "Do you want to confirm the action?" if not msg else msg
        ctk.CTkLabel(self,text=txt).pack(side="left",pady=0,padx=20)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(padx=10, pady=(0, 15))

        self.confirm = ctk.CTkButton(header,text="Confirm",
            fg_color=c.SUCCESS,hover_color=c.ACCENT_HOVER, height=40, font=("Arial", 13, "bold"),
            command=lambda: self.finish()).pack(side="left", padx=5)
        rightheader = ctk.CTkFrame(self, fg_color="transparent")
        rightheader.pack(padx=10, pady=(0, 15))

        self.cancel = ctk.CTkButton(rightheader, text="Cancel", fg_color=c.DANGER,hover_color=c.DANGER_HOVER, width=100, height=40,
            command=self.cancel).pack(side="right", padx=5)

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
