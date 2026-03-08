import pygame
import os
import time
import customtkinter as ctk
import colors as c
from controller_file_browser import ControllerFileBrowser
class UmuInputEngine:
    def __init__(self, app):
        self.app = app
        self.nav_list = []
        self.nav_index = 0
        self.last_input = 0
        self.cooldown = 0.35
        self.joysticks = []
        self.current_file_browser:ControllerFileBrowser=None
        self.in_file_browser=False
        
        self.app.bind("<Any-KeyPress>", lambda e: self.app.toggle_controller_UI(show=False))
        self.app.bind("<Button-1>", lambda e: self.app.toggle_controller_UI(show=False))

        self.quit_hold_start=0
        self.quit_duration=2

        try:
            os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
            pygame.init()
            pygame.joystick.init()
        except Exception as e:
            print(f"Controller initialization error: {e}")

    def refresh_hardware(self):
        if not self.joysticks and pygame.joystick.get_count() > 0:
            for i in range(pygame.joystick.get_count()):
                j = pygame.joystick.Joystick(i)
                j.init()
                self.joysticks.append(j)
                print(f"Detected Input Device: {j.get_name()}")

    def rebuild_nav_map(self, priority_widget=None):
        self.nav_list = []
        # 1. Sidebar Games
        for child in self.app.game_list_frame.winfo_children():
            if isinstance(child, ctk.CTkButton):
                self.nav_list.append(child)
        
        # 2. Sidebar Action Buttons
        self.nav_list.append(self.app.add_btn)
        self.nav_list.append(self.app.settings_btn)
        if hasattr(self.app, 'exit_btn'):
            self.nav_list.append(self.app.exit_btn)

        self._scan_widget_tree(self.app.panel)
        
        if priority_widget and priority_widget in self.nav_list:
            self.nav_index = self.nav_list.index(priority_widget)
        else:
            if self.nav_index >= len(self.nav_list):
                self.nav_index = 0
        
        self.sync_visuals()
    
    def rebuild_nav_map_file_browser(self, target_app_window:ControllerFileBrowser ,priority_widget=None):
        self.nav_list = []
        self.current_file_browser=target_app_window
        self._scan_widget_tree(target_app_window)
        
        if priority_widget and priority_widget in self.nav_list:
            self.nav_index = self.nav_list.index(priority_widget)
        else:
            if self.nav_index >= len(self.nav_list):
                self.nav_index = 0
        self.in_file_browser=True
        self.sync_visuals()

    def _scan_widget_tree(self, parent):
        for child in parent.winfo_children():
            if isinstance(child, (ctk.CTkButton, ctk.CTkEntry, ctk.CTkCheckBox, ctk.CTkOptionMenu)):
                if child not in self.nav_list:
                    self.nav_list.append(child)
            if child.winfo_children():
                self._scan_widget_tree(child)

    def press_current(self):
        if not self.nav_list: return
        target = self.nav_list[self.nav_index]
        
        # --- Visual Flash (Feedback) ---
        if hasattr(target, 'configure') and hasattr(target, 'cget'):
            orig = target.cget("fg_color")
            if not isinstance(target, ctk.CTkEntry):
                # Flash color is a neutral mid-gray to signify "pressed"
                target.configure(fg_color="#444444") 
                
                def reset_color(t=target, c_orig=orig):
                    try:
                        if t.winfo_exists():
                            # If still focused, revert to the Focus Blue, otherwise original
                            if t == self.nav_list[self.nav_index]:
                                if isinstance(t, (ctk.CTkOptionMenu, ctk.CTkCheckBox)):
                                    t.configure(fg_color=c.BG_FOCUS)
                                else:
                                    t.configure(fg_color=c_orig)
                            else:
                                t.configure(fg_color=c_orig)
                    except: pass
                self.app.after(100, reset_color)

        # 1. OptionMenu Cycle
        if isinstance(target, ctk.CTkOptionMenu):
            vals = target.cget("values")
            cur = target.get()
            if cur in vals:
                next_val = vals[(vals.index(cur) + 1) % len(vals)]
                target.set(next_val)
                if target._command: target._command(next_val)
            return

        # 2. CheckBox Toggle
        elif isinstance(target, ctk.CTkCheckBox):
            target.toggle()
            if target._command: target._command()
            return

        # 3. Standard Buttons / Entries
        elif hasattr(target, 'invoke'):
            target.invoke()
        
        if isinstance(target, ctk.CTkEntry):
            target.focus_set()
            target.select_range(0, 'end')
            target.icursor('end')

    def sync_visuals(self):
        """Standardizes visuals using colors.py constants."""
        if not self.nav_list: return
            
        for w in self.nav_list:
            try:
                if hasattr(w, 'configure'):
                    # Dropdowns and Checkboxes use BG_INPUT (from colors.py)
                    if isinstance(w, (ctk.CTkOptionMenu, ctk.CTkCheckBox)):
                        w.configure(fg_color=c.BG_INPUT)
                        if isinstance(w, ctk.CTkOptionMenu):
                            w.configure(button_color=c.BG_INPUT)
                    else:
                        w.configure(border_width=0)
            except: pass
            
        target = self.nav_list[self.nav_index]
        target.focus_set()
        
        try:
            # Highlight with the ACCENT color
            if not isinstance(target, ctk.CTkOptionMenu):
                target.configure(border_width=2, border_color=c.ACCENT)
            
            # Special color for focused interactive widgets
            if isinstance(target, (ctk.CTkOptionMenu, ctk.CTkCheckBox)):
                target.configure(fg_color=c.BG_FOCUS)
                if isinstance(target, ctk.CTkOptionMenu):
                    target.configure(button_color=c.BG_FOCUS)
                 
        except Exception as e:
            print(f"Visual sync error: {e}")
        
        #BOBING Animation
        # Get the currently focused widget from nav_list
        current_widget = self.nav_list[self.nav_index]
        
        # Find which icon is anchored to this widget
        for key, anchor_widget in self.app.icon_anchors.items():
            if anchor_widget == current_widget:
                self.bounce_icon(self.app.icon_labels[key])

        if self.current_file_browser and self.in_file_browser:
            self.current_file_browser.scroll_to_selected(selected_index=self.nav_index)

    def bounce_icon(self, icon_label):
        """Quickly pops the icon up and drops it back."""
        orig_y = icon_label.winfo_y()
        
        # Lift it 10 pixels up immediately
        icon_label.place(y=orig_y - 10)
        
        # Drop it back after 100ms
        self.app.after(100, lambda: icon_label.place(y=orig_y))

    def update(self):
        # 1. Global Focus & Safety Guard
        try:
            if not self.app.focus_displayof(): 
                return 
        except Exception: 
            return
        
        self.refresh_hardware()
        pygame.event.pump()
        
        now = time.time()
        # Tracking state for this specific frame across ALL controllers
        any_view_button_held = False
        cooldown_active = (now - self.last_input < self.cooldown)

        # --- PHASE 1: SENSOR SWEEP (Check all joysticks) ---
        for joy in self.joysticks:
            try:
                # Check the "View" button (6) specifically for the Quit Timer
                if joy.get_button(6):
                    any_view_button_held = True

                # --- PHASE 2: TAP ACTIONS (Only if no cooldown) ---
                if not cooldown_active:
                    # Button A (0) - Select/Press
                    if joy.get_button(0): 
                        self.trigger_input(self.press_current)
                        return # Exit loop after action to prevent double-inputs
                    
                    # Button B (1) - Back
                    elif joy.get_button(1): 
                        self.trigger_input(self.app.handle_back)
                        return
                    
                    # Button X (2) - Editor
                    elif joy.get_button(2): 
                        self.trigger_input(lambda: self.app.show_editor() if self.app.current_game_id else None)
                        return
                    
                    # Button Y (3) - Context Sensitive
                    elif joy.get_button(3):
                        if self.app.view_state == "settings":
                            self.trigger_input(self.app.save_game)
                        elif self.app.view_state == "dashboard":
                            self.trigger_input(self.app.select_artwork)
                        return

                    # Button Start (7) - Launch
                    elif joy.get_button(7): 
                        self.trigger_input(lambda: self.app.launch_game() if self.app.current_game_id else None)
                        return

                    # --- PHASE 3: NAVIGATION (D-Pad & Left Stick) ---
                    move_x, move_y = 0, 0

                    # 1. Capture Input
                    if joy.get_numhats() > 0:
                        hat = joy.get_hat(0)
                        move_x, move_y = hat[0], -hat[1]
                    if move_x == 0 and abs(joy.get_axis(0)) > 0.6:
                        move_x = 1 if joy.get_axis(0) > 0 else -1
                    if move_y == 0 and abs(joy.get_axis(1)) > 0.6:
                        move_y = 1 if joy.get_axis(1) > 0 else -1

                    if move_x != 0 or move_y != 0:
                        self.last_input = now
                        num_widgets = len(self.nav_list)
                        
                        if self.in_file_browser:
                            # We assume first 3 widgets are [Select, Cancel, Back]
                            # Everything from index 3 onwards is the 6-column grid
                            header_count = 3 
                            cols = 6

                            if self.nav_index < header_count:
                                # --- HEADER NAVIGATION LOGIC ---
                                if move_x != 0:
                                    new_index = (self.nav_index + move_x) % header_count
                                elif move_y == 1: # Moving Down from header to grid
                                    new_index = header_count # Snap to first grid item
                                elif move_y == -1: # Moving Up (nowhere to go)
                                    new_index = self.nav_index
                            else:
                                # --- GRID NAVIGATION LOGIC ---
                                grid_idx = self.nav_index - header_count
                                
                                if move_x != 0:
                                    # WRAPPING: (index + move) % total
                                    new_grid_idx = (grid_idx + move_x) % (num_widgets - header_count)
                                    new_index = header_count + new_grid_idx
                                
                                elif move_y != 0:
                                    new_grid_idx = grid_idx + (move_y * cols)
                                    
                                    # If moving UP and we exit the top of the grid, go to Header
                                    if new_grid_idx < 0:
                                        new_index = 0 # Snap to 'Select Folder'
                                    elif new_grid_idx < (num_widgets - header_count):
                                        new_index = header_count + new_grid_idx
                                    else:
                                        new_index = self.nav_index # Stay at bottom
                        else:
                            # Standard Vertical List Wrapping
                            new_index = (self.nav_index + move_y) % num_widgets

                        # Apply changes
                        if 0 <= new_index < num_widgets:
                            self.nav_index = new_index
                            self.sync_visuals()
                            if self.in_file_browser and self.current_file_browser:
                                self.current_file_browser.scroll_to_selected(self.nav_index)
                                self.app.toggle_controller_UI(show=True)
                            return

            except pygame.error:
                self.joysticks.remove(joy)

        # --- PHASE 4: THE GLOBAL QUIT TIMER (Processed AFTER all joysticks) ---
        if any_view_button_held:
            if self.quit_hold_start == 0:
                # Start the timer
                self.quit_hold_start = now
                self.app.show_quit_progress(0)
            else:
                # Continue the timer
                elapsed = now - self.quit_hold_start
                percent = min(elapsed / self.quit_duration, 1.0)
                
                # This only updates the bar, it doesn't re-place the whole UI (Flicker Fix)
                self.app.show_quit_progress(percent)

                if elapsed >= self.quit_duration:
                    self.app.quit()
        else:
            # Reset only if the button was previously held and is now released
            if self.quit_hold_start != 0:
                self.quit_hold_start = 0
                self.app.hide_quit_progress()

    def trigger_input(self, func):
        self.last_input = time.time()
        self.app.toggle_controller_UI(show=True)
        func()
