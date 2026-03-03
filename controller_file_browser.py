import os
import customtkinter as ctk
import colors as c
class ControllerFileBrowser(ctk.CTkToplevel):
    def __init__(self, parent, is_file=True, callback=None,engine=None):
        super().__init__(parent)
        self.is_file = is_file
        self.callback = callback
        self.current_path = os.path.expanduser("~")
        self.engine=engine
        # UI Setup
        self.title("Select Path")
        self.geometry("1024x800")
        self.attributes('-topmost', True)
        
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.refresh_list()

    def refresh_list(self):
        for child in self.list_frame.winfo_children():
            child.destroy()

        self.list_frame._parent_canvas.yview_moveto(0)

        # --- Header Controls (Still use pack for top bar) ---
        header = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(0, 15))

        if not self.is_file:
            select_btn = ctk.CTkButton(header, 
                text=f"➔ SELECT FOLDER: {os.path.basename(self.current_path) or self.current_path}",
                fg_color=c.SUCCESS, height=40, font=("Arial", 13, "bold"),
                command=lambda: self.finish(self.current_path))
            select_btn.pack(side="left", expand=True, fill="x", padx=5)

        ctk.CTkButton(header, text="✖ Cancel", fg_color=c.DANGER, width=100, height=40,
                    command=self.cancel).pack(side="right", padx=5)
        ctk.CTkButton(header, text="⮬ Back", fg_color="#3d3d3d", width=100, height=40,
                    command=lambda: self.handle_select("..")).pack(side="right", padx=5)

        # --- The Grid Container ---
        # We use a standard Frame inside the scroll frame to hold the grid
        grid_container = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        grid_container.pack(fill="both", expand=True, padx=5)

        # Configure columns to be equal width
        num_cols = 6
        for col in range(num_cols):
            grid_container.grid_columnconfigure(col, weight=1)

        try:
            items = sorted(os.listdir(self.current_path))
            valid_items = [i for i in items if os.path.isdir(os.path.join(self.current_path, i)) or 
                        (self.is_file and i.lower().endswith(".exe"))]

            for i, item in enumerate(valid_items):
                full_path = os.path.join(self.current_path, item)
                is_dir = os.path.isdir(full_path)
                
                color = "#1f538d" if is_dir else "#2b2b2b"
                icon = "📁" if is_dir else "📄"
                
                # Wrap text to keep boxes uniform
                display_name = f"{icon}\n{self.truncate_text(item, 15)}"
                
                btn = ctk.CTkButton(
                    grid_container,
                    text=display_name,
                    fg_color=color,
                    height=90,
                    width=100, # Minimum width, weight=1 will stretch it
                    corner_radius=8,
                    command=lambda p=full_path: self.handle_select(p)
                )
                btn.grid(row=i // num_cols, column=i % num_cols, padx=4, pady=4, sticky="nsew")

        except PermissionError:
            ctk.CTkLabel(grid_container, text="🔒 Permission Denied", font=("Arial", 16)).pack(pady=40)

        self.update_idletasks()
        if self.engine:
            self.engine.rebuild_nav_map_file_browser(self)

    def truncate_text(self, text, max_len=18):
        return text[:max_len] + "..." if len(text) > max_len else text

    def handle_select(self, path):
        if path == "..":
            new_path = os.path.dirname(self.current_path)
        else:
            new_path = path

        if os.path.isdir(new_path):
            self.current_path = new_path
            self.refresh_list()
        else:
            self.finish(new_path)

    def finish(self, path):
        if self.callback:
            self.callback(path)
        self.engine.rebuild_nav_map()
        self.engine.in_file_browser=False
        self.master.view_state="settings"
        self.destroy()
    
    def cancel(self):
        self.engine.rebuild_nav_map()
        self.engine.in_file_browser=False
        self.master.view_state="settings"
        self.destroy()

    def scroll_to_selected(self, selected_index):
        """Accurate scrolling by comparing screen coordinates."""
        if not self.list_frame.winfo_children():
            return

        # Find the actual button widget in the nav_list
        # (Assuming self.engine.nav_list[selected_index] is the widget)
        target = self.engine.nav_list[selected_index]
        
        canvas = self.list_frame._parent_canvas
        
        # Get the Y coordinate of the button relative to the top of the ScrollableFrame
        # We use winfo_rooty (absolute screen Y) to find the relative distance
        target_y = target.winfo_rooty()
        frame_y = self.list_frame.winfo_rooty()
        
        relative_y = target_y - frame_y
        item_height = target.winfo_height()
        
        # Get the height of the visible area (the 'window' we see through)
        visible_height = canvas.winfo_height()

        # If the item is below the current view
        if relative_y + item_height > visible_height:
            # Scroll down by the difference
            canvas.yview_scroll(1, "units") 
        
        # If the item is above the current view
        elif relative_y < 0:
            # Scroll up
            canvas.yview_scroll(-1, "units")