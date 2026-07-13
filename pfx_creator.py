import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import colors as c

class PrefixCreator(ctk.CTkFrame):
    def __init__(self, master,browser_callback=None,on_finish_callback=None,on_close_callback=None, **kwargs):
        # Forward master and any styling overrides down to the Frame initialization
        super().__init__(master, fg_color=c.BG_MAIN, **kwargs)

        self.browser_callback = browser_callback
        self.on_finish_callback = on_finish_callback
        self.master=master
        self.on_close_callback = on_close_callback
        if on_close_callback: #that means we are running on a modal/seperate window
            self.master.protocol("WM_DELETE_WINDOW", self.on_close)


        # Variables (scoped safely to this frame component)
        self.prefix_path = ctk.StringVar(value=os.path.expanduser("~/Games/new_pfx"))
        self.arch = ctk.StringVar(value="win64")
        self.deps = {
            "vcrun2022": ctk.BooleanVar(),
            "dotnet48": ctk.BooleanVar(),
            "corefonts": ctk.BooleanVar(),
            "d3dx9": ctk.BooleanVar(),
            "faudio": ctk.BooleanVar(),
            "xna40": ctk.BooleanVar(),
            "physx": ctk.BooleanVar()
        }
        self.is_running = False

        self.create_widgets()

    def create_widgets(self):
        # Main Scrollable Frame inside our parent component frame
        self.main_frame = ctk.CTkScrollableFrame(
            self,
            label_text="Configuration",
            fg_color=c.BG_PANEL,
            label_fg_color=c.BG_FOCUS,
            scrollbar_button_color=c.ACCENT,
            scrollbar_button_hover_color=c.ACCENT_HOVER
        )
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Section 1: Path & Architecture ---
        path_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        path_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(path_frame, text="Prefix Path:", width=100, anchor="w",
                     text_color=c.TXT_MAIN, font=("Arial", 16, "bold")).pack(side="left", padx=10)

        self.entry_path_lbl = ctk.CTkLabel(path_frame, text=self.prefix_path.get(), width=100, anchor="w",
                     text_color=c.TXT_MAIN, font=("Arial", 16, "bold"))
        self.entry_path_lbl.pack(side="left", padx=10)

        ctk.CTkButton(path_frame, text="Browse", command=self.browse_path, height=35, width=80,
                      fg_color=c.ACCENT, hover_color=c.ACCENT_HOVER,
                      text_color=c.TXT_MAIN, font=("Arial", 14, "bold")).pack(side="left", padx=5)

        arch_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        arch_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(arch_frame, text="Architecture:", width=100, anchor="w",
                     text_color=c.TXT_MAIN, font=("Arial", 16, "bold")).pack(side="left", padx=10)

        ctk.CTkRadioButton(arch_frame, text="64-bit (win64)", variable=self.arch, value="win64",
                           text_color=c.TXT_MAIN, font=("Arial", 14),
                           fg_color=c.ACCENT, hover_color=c.ACCENT_HOVER).pack(side="left", padx=10)

        ctk.CTkRadioButton(arch_frame, text="32-bit (win32)", variable=self.arch, value="win32",
                           text_color=c.TXT_MAIN, font=("Arial", 14),
                           fg_color=c.ACCENT, hover_color=c.ACCENT_HOVER).pack(side="left", padx=10)

        # --- Section 2: Dependencies ---
        ctk.CTkLabel(self.main_frame, text="Common Dependencies",
                     text_color=c.TXT_MAIN, font=("Arial", 18, "bold")).pack(anchor="w", pady=(10, 5))

        deps_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        deps_frame.pack(fill="x", pady=(0, 15))

        row, col = 0, 0
        for name, var in self.deps.items():
            cb = ctk.CTkCheckBox(deps_frame, text=name, variable=var,
                                 text_color=c.TXT_MAIN, font=("Arial", 14),
                                 fg_color=c.ACCENT, hover_color=c.ACCENT_HOVER,
                                 border_color=c.TXT_DIM)
            cb.grid(row=row, column=col, padx=15, pady=8, sticky="w")
            col += 1
            if col > 2:
                col = 0
                row += 1

        # --- Section 3: Actions ---
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 15))

        self.btn_start = ctk.CTkButton(btn_frame, text="Create Prefix & Install",
                                       command=self.start_process, height=45,
                                       fg_color=c.SUCCESS, hover_color=c.get_dimmed_accent(c.SUCCESS, 0.8),
                                       text_color=c.BG_MAIN, font=("Arial", 16, "bold"))
        self.btn_start.pack(side="left", padx=10, fill="x", expand=True)

        # --- Section 4: Live Log ---
        ctk.CTkLabel(self.main_frame, text="Installation Log",
                     text_color=c.TXT_MAIN, font=("Arial", 16, "bold")).pack(anchor="w", pady=(5, 5))

        self.log_text = ctk.CTkTextbox(self.main_frame, height=400,
                                       fg_color=c.BG_INPUT, border_color=c.BG_FOCUS,
                                       text_color=c.TXT_DIM, font=("Consolas", 12),
                                       scrollbar_button_color=c.ACCENT)
        self.log_text.pack(fill="both", expand=True, pady=(0, 10))
        self.log_text.configure(state="disabled")

    def browse_path(self):
        if self.browser_callback:
            path = self.browser_callback(self.entry_path_lbl, False)
        else:
            # Fallback to the local kdialog picker if no function was passed
            path = self.get_kde_dir()
            if path:
                self.entry_path_lbl.configure(text=path)

    def get_kde_dir(self):
        try:
            result = subprocess.run(
                ["kdialog", "--getexistingdirectory", "~/"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except FileNotFoundError:
            print("kdialog not found. Is KDE installed?")
        return None

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def start_process(self):
        if self.is_running:
            return
        self.is_running = True
        self.btn_start.configure(state="disabled", text="Running...")
        threading.Thread(target=self.run_wine_tasks, daemon=True).start()

    def run_wine_tasks(self):
        prefix = self.entry_path_lbl.cget("text")
        arch = self.arch.get()
        os.makedirs(prefix, exist_ok=True)

        self.log("=" * 50)
        self.log("Starting Wine Prefix Creation")
        self.log("=" * 50)
        self.log(f"Path: {prefix}")
        self.log(f"Architecture: {arch}\n")

        env = os.environ.copy()
        env["WINEPREFIX"] = prefix
        env["WINEARCH"] = arch

        self.log("[Step 1/2] Creating Wine Prefix...")
        try:
            proc = subprocess.Popen(
                ["wineboot", "--init"], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            for line in proc.stdout:
                self.log(line.strip())
            proc.wait()
            if proc.returncode != 0:
                self.log("❌ Error creating prefix.")
                self.finish_process(False)
                return
            self.log("✅ Prefix created successfully.\n")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            self.finish_process(False)
            return

        selected_deps = [name for name, var in self.deps.items() if var.get()]
        if not selected_deps:
            self.log("No dependencies selected. Done.")
            self.finish_process(True)
            return

        self.log(f"[Step 2/2] Installing: {', '.join(selected_deps)}\n")
        try:
            proc = subprocess.Popen(
                ["winetricks"] + selected_deps, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            for line in proc.stdout:
                self.log(line.strip())
            proc.wait()

            if proc.returncode == 0:
                self.log("\n✅ Installation Complete!")
                messagebox.showinfo("Success", "Prefix and dependencies installed successfully!")
            else:
                self.log("\n⚠️ Finished with errors.")
                messagebox.showwarning("Warning", "Installation finished with errors.")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")

        if self.on_finish_callback:
            self.after(2000,self.finish_on_editor)
        else:
            self.finish_process(True)

    def finish_process(self, success):
        self.is_running = False
        self.btn_start.configure(state="normal", text="Create Prefix & Install")

    def finish_on_editor(self):
        self.on_finish_callback(self.entry_path_lbl.cget('text'))
        self.master.withdraw()
    
    def on_close(self):
        self.on_close_callback()
        self.master.withdraw()

# Isolated debugging profile
if __name__ == "__main__":
    # If run directly by itself, generate a mock host window to test look/feel
    root = ctk.CTk()
    root.title("Isolated Module Test Window")
    root.geometry("900x750")

    # Global context setups remain safely here inside the test runner block
    c.apply_theme("Legion Red")
    ctk.set_appearance_mode("dark")
    ctk.set_widget_scaling(1.2)

    # Pass root down directly as master container
    test_widget = GamePrepManager(master=root)
    test_widget.pack(fill="both", expand=True)

    root.mainloop()
