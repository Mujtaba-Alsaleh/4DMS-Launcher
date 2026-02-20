import pygame
import os
import time
import customtkinter as ctk
import colors as c

class UmuInputEngine:
    def __init__(self, app):
        self.app = app
        self.nav_list = []
        self.nav_index = 0
        self.last_input = 0
        self.cooldown = 0.2
        self.joysticks = []
        
        self.app.bind("<Any-KeyPress>", lambda e: self.app.toggle_controller_UI(hide=True))
        self.app.bind("<Button-1>", lambda e: self.app.toggle_controller_UI(hide=True))

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

    def update(self):

        try:
            # If a messagebox is open, focus_displayof might fail or return a non-widget
            if not self.app.focus_displayof():
                return 
        except Exception:
            # If we are in a weird focus state (like a popup), just wait
            return
        
        if time.time() - self.last_input < self.cooldown: return
        
        self.refresh_hardware()
        pygame.event.pump()
        for joy in self.joysticks:
            try:
                if joy.get_button(0): self.trigger_input(self.press_current); return
                elif joy.get_button(1): self.trigger_input(self.app.handle_back); return
                elif joy.get_button(2): self.trigger_input(lambda: self.app.show_editor() if self.app.current_game_id else None); return
                # 'Y' Button Logic
                elif joy.get_button(3):
                    if self.app.view_state == "settings":
                        self.trigger_input(self.app.save_game)
                    elif self.app.view_state == "dashboard":
                        self.trigger_input(self.app.select_artwork)
                    return
                elif joy.get_button(6) and joy.get_button(7): 
                    self.app.quit()
                    return
                elif joy.get_button(7): 
                    self.trigger_input(lambda: self.app.launch_game() if self.app.current_game_id else None)
                    
                    return
                
                move = 0
                if joy.get_numhats() > 0:
                    hat = joy.get_hat(0)
                    if hat[1] == -1: move = 1
                    elif hat[1] == 1: move = -1
                
                if move == 0 and abs(joy.get_axis(1)) > 0.6:
                    move = 1 if joy.get_axis(1) > 0 else -1

                if move != 0:
                    self.last_input = time.time()
                    self.nav_index = (self.nav_index + move) % len(self.nav_list)
                    self.sync_visuals()
                    self.app.toggle_controller_UI(hide=False)
            except pygame.error:
                self.joysticks.remove(joy)

    def trigger_input(self, func):
        self.last_input = time.time()
        self.app.toggle_controller_UI(hide=False)
        func()
