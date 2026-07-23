import customtkinter as ctk
import colors as c


class WelcomeView(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self,
            text="Welcome to 4DMS Launcher\nSelect a game or press + to add one",
            font=("Arial", 18),
            text_color=c.TXT_DIM
        ).place(relx=0.5, rely=0.5, anchor="center")
