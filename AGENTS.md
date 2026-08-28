# 4DMS-Launcher — Project Context

## Architecture
- Python/PyQt6 game launcher for Linux, runs Windows games via umu-run/Proton
- `launcher_pyqt/main.py` (thin entry point) → `launcher_pyqt/app.py` → views in `launcher_pyqt/views/`
- View classes are `QWidget` subclasses receiving `app` reference via constructor (no circular imports)
- Startup view is **Home** (`show_home()`), not library
- Active codebase: `launcher_pyqt/` — legacy `launcher/` (CustomTkinter) and root modules (`colors.py`, `livesplit.py`, `pfx_creator.py`) still present but not used by the launcher
- No pygame/SDL — controller input via legacy Linux joystick API (`/dev/input/js*`), sound via `pw-play`/`paplay`/`aplay`
- No new pip dependencies; venv activation: `source venv/bin/activate` (bash, not fish)

## Key Patterns
- All button actions use `trigger_input()` for consistent cooldown handling
- Controller 0.5s grace period (`_controller_detected_at`) to avoid phantom presses
- `play_btn` requires `winfo_exists()` guards (widget destroyed after view switch)
- `GameImage` (QLabel subclass) — DO NOT call `start()` in `__init__` during build; only start on controller navigation when parent has final rendered size
- `GameImage.stop()` uses `getattr` for safe attribute access (attributes may not exist on partially initialized objects)
- Steam keyboard auto-opens on QLineEdit focus via `press_current()` in input engine (global, not per-widget)
- `WINEDLLOVERRIDES` uses single semicolon separator
- Game process `cwd` set to exe directory for modloader compatibility
- `STEAM_COMPAT_CLIENT_INSTALL_PATH` defaults to `~/.steam/steam`

## LiveSplit Integration
- `livesplit.py` in project root (NOT in `launcher/` — same level as `colors.py`, `pfx_creator.py`)
- Uses **system `wine`** (not `umu-run`) to launch LiveSplit — umu-run exits with code 53 for .NET apps
- LiveSplit runs in its own Wine prefix at `~/.local/share/livesplit/` (has gdiplus via winetricks, .NET via mono)
- Reference install detected at `~/LiveSplit/LiveSplit.exe` and `~/LiveSplit/settings.cfg` — used preferentially over our download
- `settings.cfg` must have `<ServerStartup>1</ServerStartup>` and `<ServerState>1</ServerState>` for TCP Server to auto-start
- Hotkey profile format: `<HotkeyProfiles><HotkeyProfile><SplitKey>NumPad1</SplitKey>` (NOT `<Hotkeys><startorsplit>`)
- `settings.cfg` template generated on download/launch with Server enabled
- TCP Server on `localhost:16834` — retry loop every 5s for up to 60s (12 attempts)
- Hotkey remapping UI in **Global Settings** view (NOT in game editor) — per-game toggle stays in editor
- Key capture uses tkinter `<KeyPress>` events (not `/dev/input`) — maps keysyms to .NET key names (KP_1→NumPad1, etc.)
- Runtime global hotkey listener uses `/dev/input/by-path/*-event-kbd` with blocking reads (no EVIOCGRAB, no O_NONBLOCK) via `select.poll()`
- Deduplicates keyboard devices by resolved symlink path (usb- and usbv2- point to same event device)
- Hotkey bindings saved to `hotkeys.json` to survive LiveSplit overwriting `settings.cfg` on exit; falls back to parsing settings.cfg
- On game exit naturally: `stop_hotkeys()` + `disconnect()` closes TCP, but LiveSplit process stays alive (for mid-speedrun crash recovery)
- On manual STOP button: `stop()` kills LiveSplit process entirely
- On relaunch: skips launching if LiveSplit process already running, reconnects TCP + hotkeys
- LiveSplit toggle grays out when Gamescope is enabled (gamescope can't render windows)
- Toast notification after fresh download: "LiveSplit installed! Bind shortcuts in Settings."
- `LIVESPLIT_VERSION = "1.8.37"`, download URL from GitHub releases

## Navigation System
- `rebuild_nav_map()` scans widget tree for CTkButton/CTkEntry/CTkCheckBox/CTkOptionMenu
- Library grid: `rebuild_nav_map_library(grid)` scans poster buttons
- Standard vertical list: horizontal movement finds nearest widget by screen position (weighted y_dist*2 + x_dist)
- Button 8 (Menu) toggles sidebar with state caching
- `nav_stack` with `_push_nav()` for back navigation
- Library posters have `game_id` attribute; `scroll_to_library_item` syncs `current_game_id`

## Library Animation (GameImage on covers)
- GameImage created during `_build()` with hardcoded dimensions, placed with `place(relx=0, rely=0, relwidth=1, relheight=1)` and `lower_widget()`
- Animation is controller-only (no mouse hover bindings — they fight with controller logic)
- `_start_cover_anim(btn)`: lifts canvas, starts animation, adds border feedback
- `_stop_cover_anim(btn)`: stops animation, lowers canvas, resets border
- `sync_visuals()` handles controller navigation: calls `_stop_cover_anim(prev)` then `_start_cover_anim(target)`
- Poster buttons skip standard focus styling (border_width=3) in `sync_visuals` via `is_poster` check
- `GameImage.start()` reads parent's `winfo_width()/winfo_height()` for correct sizing

## Completed Work (Session Notes)
### Session 2026-08-04 (Steam-Deck shell M1 + Home/Library M2)
- **Tabs replace sidebar.** Header row: logo (→Home) top-left, centered Home/Library/Tools/Settings tabs (LB/RB + Q/E cycle via `_kb_tab`), battery + clock top-right (30s `_update_header_right`). Bottom bar = hint pills only (`ui.hint_pill`). No sidebar, full-bleed content.
- **Nav is tabs-first** (`input_engine.py`): `rescan` prepends `app.tab_buttons`; Down on non-active tab activates it, Down on active tab enters content, Up at content top → active tab, tab row wraps. Focus ring = `c.FOCUS_RING`.
- **`launcher_pyqt/ui.py`** = design-system module: `register_fonts()` (bundled Inter TTFs in `resources/fonts/`), `app_qss`, `header_style`, `tab_style`, `hint_pill` (glyph PNGs via `GLYPH_PATHS`, text fallback for LB/RB).
- **`colors.py` retokenized**: every theme has `SURFACE/SURFACE_HOVER/BORDER/ON_ACCENT/FOCUS_RING/SCRIM`; legacy keys kept.
- **Home (`views/home.py`)**: recent-games carousel (10 max, `HomePoster(QPushButton)` so list-mode nav picks it up; horizontal QScrollArea auto-scrolled by engine `_ensure_scrolled`), A-Z quick-jump strip (26 letters → `jump_to_letter` scrolls library to first game starting with that letter), empty states (no games → "+ Add a Game" CTA; games but no recents → "Browse Library"). A on a poster → dashboard; X → details; Y → fav.
- **Library (`views/library.py`)**: always A-Z (sort/filter feature removed; `cycle_sort`/`cycle_filter`/combos gone). Header = search + green `+` button (→ `open_add_game`). RECENTLY PLAYED row removed (moved to Home).
- **Add-game modal (`launcher_pyqt/add_game_modal.py`)**: name/exe/prefix + Browse (via `app.browse`), Cancel/Add, controller-aware (modal nav mode; `_cancel` handles B). On Add: placeholder art + config save + show_editor. Triggered from library `+` and home CTA via `app.open_add_game`.
- **Favorite refactor**: `app.toggle_favorite_for(gid)` + `app._focused_game_id()` (reads focused nav widget's `game_id`; Home/Dashboard/Editor-safe); X/Y button handlers in engine use it for `home` too.
- **Post-M2 tweaks**: Q/E tab cycling uses `_kb_focus_is_text()` (QLineEdit/QTextEdit only) so it works when a QComboBox is focused (Settings tab); A-Z strip buttons are `_mouse_only = True` (skipped by `_scan_widget_tree`, mouse-clickable only); Home carousel ends with a Steam-style `BrowsePoster` "ALL GAMES" tile (appended last, A → `show_library`) instead of a separate Browse button.
- **Testing**: `/tmp/opencode/m1_test.py` 32/32, `/tmp/opencode/m2_test.py` 14/14 (`QT_QPA_PLATFORM=offscreen`). Config path is `$XDG_CONFIG_HOME/4DMS-Launcher/games.json` (capital `4DMS-Launcher`). QPushButton `animateClick` clicks emit ~100ms later — spin ≥ 0.4s before asserting view changes. Home `_build` uses a persistent `self._layout` (never re-create a QVBoxLayout on an already-laid-out widget).

### Phases 1-7 UX (completed in prior sessions)
- Critical fixes, high-impact UX (toast, volume overlay, hints, skip welcome), data enrichment (last_played, launch_count, favorite, etc.), library enhancements (sort/filter/favorites/recently played), navigation (nav_stack, back), handheld features (controller battery, volume overlay), light cleanup

### This Session (PyQt6 port in launcher_pyqt/)

**PyQt6 migration completed:**
- `launcher_pyqt/` is now the active codebase — all views ported to PyQt6 (LibraryView, DashboardView, EditorView, GlobalSettingsView, VolumeOverlay)
- Controller input via UmuInputEngineQt (PyQt6-native QTimer-based update loop)

**Pygame completely removed:**
- Joystick input replaced with direct `/dev/input/js*` reading via legacy Linux joystick API (`struct`, `fcntl`, `os.read`)
- Sound replaced with `pw-play` (PipeWire native) / `paplay` / `aplay` via `subprocess.Popen`
- No SDL at all — eliminates Wayland corruption / KDE logout on shutdown
- `pygame-ce` removed from `requirements.txt`

**Editor redesign:**
- Separated game settings into clear full-width sections with divider lines (no card frames)
- PFX Creator toggle moved into WINEPREFIX row (inline button)
- SAVE button restyled to match DELETE (transparent, colored border, no hint)

**Library view fixes:**
- Custom `PosterWidget` (QWidget subclass with `paintEvent` for pixmap + rounded clip)
- GameImage animation on focus via `show()`/`hide()` (not `raise_()`/`lower()`)
- `rebuild_nav_map_library` scans by `hasattr(game_id)` instead of QPushButton search

**Game stop logic fix:**
- `stop()` now sets `is_playing = False` and calls `_reset_ui()` directly (was relying on daemon thread `finally` block, which never ran if `umu-run` caught SIGTERM)
- `_run_process` uses polling loop (`while is_playing and poll() is None: sleep(0.5)`) instead of blocking `wait()`
- Aggressive process kill: terminate → 2s timeout → kill → 1s timeout
- `_reset_ui()` wraps `play_btn` access in `try/except RuntimeError` (widget may be deleted)

**Exit crash / KDE logout fix:**
- `closeEvent` calls `os._exit(0)` after stopping engine/game process — bypasses all Python cleanup (daemon threads, GC, module unloading)
- `stop()` guarded by `if not self.is_playing: return` — no-op when no game running
- `.is_playing` check prevents `stop()` from running during exit from editor view

**Themes:**
- Removed Nordic, Legion Red
- Added Amber Glow (warm amber `#ffa726` on dark sepia) and Synthwave (hot pink `#ff2d95` on deep indigo)

**Other fixes:**
- Hat Y direction fixed (no negation — legacy js API convention matches analog sticks)
- Cooldown increased from 0.35 → 0.4
- Joystick battery stub (`get_power_level()` returns "wired")
- Controller file browser: removed duplicate `closeEvent`, removed `WindowStaysOnTopHint`, grid restored to 4 columns

### Session 2026-07-30

**Dashboard polish:**
- Info fields: removed `setWordWrap(True)`, added tooltip for long exe/prefix paths, `setFixedWidth(100)` on labels for alignment
- Button style unified: Browse Artwork, Game Settings, favorite star switched to transparent+colored-border (matching editor SAVE/DELETE style)

**PFX Creator fixes:**
- Arch buttons: added `QButtonGroup` for exclusive selection (64-bit/32-bit can't both be checked)
- Deps checkboxes: wrapped in `QFrame` card with `BG_PANEL` background for visibility against transparent inner widget
- SIGSEGV on finish: replaced direct Qt UI calls from background thread with `pyqtSignal` (log_signal, finish_signal) — thread-safe signal/slot routing

**Library layout compactness:**
- Added `scroll_layout.setAlignment(AlignTop)` to prevent content stretching on tall screens
- Recently played posters: 110→80px wide, spacing 8→4, font sizes reduced
- Main grid spacing: 20→12px, poster width adaptive `min(170, max(130, ...))` — shrinks on narrow screens (handheld)

### Session 2026-07-31 (UX overhaul, Phases P0-P8)

**P0 — Persistent views (`app.py`):**
- `self._views = {}` cache; `_present_view(key, view_state, factory, force_new=False)` with `_prune_stale_views()` (config-deleted games) and `_purge_game_views(gid)` (on delete)
- Cache keys: `"library"`, `"global_settings"`, `("dashboard", gid)`, `("editor", gid)` (tuples for per-game views)
- `_present_view` refuses re-`addWidget` for cached views; `is_new` flag skips redundant `refresh()`; view switch calls `_update_bottom_bar` + `_update_sidebar_active` + `engine.rescan()`
- `_clear_stack` removed; `_toggle_sidebar_visibility` calls `_rebuild()` + `rescan()`
- LibraryView `refresh()` compares `_data_sig()` (gid,name,art,playtime,last_played,favorite,launch_count); `hideEvent`→`_stop_animations()`; `_build()` nulls `grid`/`_scroll_area` at start (stale-ref fix on empty search)
- DashboardView persistent `_layout` + `_clear_layout(layout)` deep-clear (recurses into sub-layouts) + `_rebuild()`; `refresh()`→`_rebuild()`
- Editor unsaved edits intentionally preserved across view switches (only Y/Save commits)

**P1 — Game-centric dashboard (`views/dashboard.py`):**
- Hero art 300×400 (was 210×280); name 26px; meta line `playtime • last_played • launch_count` via `format_playtime`+`relative_time` (fallback "Never played")
- PLAY button fixedHeight 52 themed `c.SUCCESS` + `c.get_dimmed_accent(c.SUCCESS, 0.8)` hover; STOP state uses `c.DANGER`
- Notes frame shown when `data["notes"]` non-empty; collapsible DETAILS section (hidden by default, `_toggle_details()` rescans) with Exe/Prefix/Proton/Store/Launch Count + `_remove_artwork` inside
- `ArtworkWidget` passes real w/h to `GameImage` (was hardcoded 210×280)

**P2 — Library search + sort/filter parity (`views/library.py`):**
- Header: `QLineEdit` search (placeholder "Search games...", clear button), `sort_combo`/`filter_combo` QComboBoxes, `_stats_lbl` result count
- IMPORTANT: `self._search.setText(self.search_text)` BEFORE connecting `textChanged` in `_build` — otherwise rebuild resets box to empty while `search_text` still filters (desync after `refresh()`)
- `cycle_sort`/`cycle_filter` set `setCurrentText` on combos (controller-visible state); `_rebuild` lives in combo signal handlers (no double rebuild)
- `_get_sorted_games` filters by name substring; empty state message updated

**P3 — Artwork browser (`controller_file_browser.py`):**
- `ArtCell(QPushButton)` subclass: paints rounded thumbnail + filename, custom `set_focused()`/`paintEvent` focus ring, stays in `NAV_TYPES` for controller nav; `_load_thumb` uses `QImageReader.setScaledSize` (no full-image decode)
- Adaptive columns: `_compute_cols()` = `clamp(2, (w-32)//200, 6)`; recomputed in `_populate` and `resizeEvent` (uses `event.size()`, not `self.width()`); `scroll_to_selected` uses `_cell_h`
- `QPainter.drawPixmap(QRectF, ...)` requires explicit source rect — pass `.toRect()` instead

**P4 — Navigation / sidebar (`input_engine.py`):**
- Movement block extracted from `update()` into `_move_selection(move_x, move_y)` (reusable by keyboard layer; shared cooldown via `self.last_input`)
- `rescan()` now PREPENDS visible sidebar buttons to `nav_list` (was replacing → grid unreachable while sidebar shown)
- Sidebar↔grid edge transitions: down from last sidebar → first poster; right from sidebar → first poster; left from grid col 0 → last sidebar; up from grid row 0 → last sidebar
- `library.scroll_to_item` guards `hasattr(target, 'game_id')` (sidebar buttons aren't in the scroll area)
- HINT_DEFS: removed stale `X Reload`; `settings`→`[Y Save, B Back, Menu Sidebar]`; library adds `[View Hold-Quit]`
- `_update_bottom_bar` hint-clearing: `takeAt` loop (not `deleteLater`-only) — fixes duplicated hints on every view switch / 30s timer tick

**P5 — Keyboard layer (`app.py` + `input_engine.py`):**
- QShortcuts (WindowShortcut) on main window: arrows+WASD→`_kb_move`, Enter/Space→`_kb_activate`, Esc→`_kb_back`
- Guard rails: `_kb_focus_is_editable()` (QLineEdit/QTextEdit/QPlainTextEdit/QComboBox) — shortcuts never hijack typing or open combo dropdowns; `_kb_activate` returns when a QPushButton/QCheckBox is focused (native activation); both check engine cooldowns
- `focusChanged` hook → `_on_focus_changed`: mouse clicks on nav widgets sync `nav_index` (controller state parity), guarded vs modal + re-entrancy (idx==nav_index no-op)
- `HoverFilter` (app-level Enter-event filter) → `hover_widget()`: mouse hover follows the same nav cursor; skips editable widgets

**P6 — Icon + hover:**
- Window icon from `resources/logo.png` via `get_resources_icon` + `QIcon` (setWindowIcon)
- Hover parity handled by P5 `HoverFilter` (single nav cursor driven by controller OR mouse)

**P7 — Juice (≤200ms ease-out only):**
- `PosterWidget`: `zoom` pyqtProperty + QPropertyAnimation (180ms OutCubic, 1.0→1.07) driven by `set_focused`; `stop_animations()` for view-hide cleanup; RUNNING badge (SUCCESS pill, top-right, live via `_update_running_badges`)
- GameProcessManager calls `_refresh_library_badges()` on launch/stop (`current_running_game_id` clears on stop too)
- Smooth library scroll: `scroll_to_item` computes scrollbar target via `mapTo(scroll_area.widget())` + `_animate_scroll` (180ms OutCubic on scrollbar `value`)
- Toast fade-in/out via `QGraphicsOpacityEffect` (150ms in / 200ms out); confirm modal fade-in (120ms)
- NOT done (deferred): bg-dot artwork, grid/filter chips (stats label instead), view fade-in (whole-screen opacity = guardrail violation), favorite pulse

**P8 — Placeholder art (`utils.py`):**
- `generate_placeholder_art(game_id, name, accent, bg, out_dir)` → 600×840 PNG via pure QPainter (accent-tinted gradient, glow disc, thin border, wrapped uppercase title, arc motif); ~60KB, <50ms, zero deps
- Auto-set in `add_new_game` (new games only, no backfill); "Generate Art" button in dashboard DETAILS frame (SUCCESS-themed, `_generate_art` saves + re-presents dashboard)

**Testing:** headless smoke suite run with `QT_QPA_PLATFORM=offscreen` (14 checks: caching, reuse, search empty/restore, keyboard move, hover sync, badges, hints, toast, dashboard stability). Note: offscreen top-level `resize()` does NOT deliver `resizeEvent` — test adaptive columns via `_populate()` after `resize`+`processEvents`.

### Session 2026-07-31 (fixes + polish round)

**Bug fixes:**
- **A button / Enter didn't launch from library grid**: `press_current()` had no branch for `PosterWidget` (a `QWidget`, not `QPushButton`) — fell through every type check and no-op'd. Added `elif hasattr(target, 'game_id'): self.app.try_launch_game()` (`input_engine.py`)
- **`QCheckBox` NameError** in `_kb_activate`: added `QCheckBox` to `app.py` imports
- **Stuck highlight** (two root causes in `input_engine.py`):
  - `_apply_focus_style` re-captured `_nav_base_style` whenever `sync_visuals` re-ran on an already-focused widget (hover/`focusChanged` retriggers), baking the focus style into the "base" so it never un-applied → now base captured once (`base is None`) and only restored when `current != base`
  - Widgets that left `nav_list` while focused (view switch, sidebar hide, purge) kept their focus style → added `_prev_focus_target` + `_clear_focus()` (set_focused(False), game_image stop/hide, base restore); `sync_visuals` clears the stale target when it's no longer in `nav_list` or the list empties
  - `_update_sidebar_active` kept `_nav_base_style` in sync with the new stylesheet (re-applies focus ring to a currently-focused sidebar button); active indicator changed from a 2px full border (looked like a stuck focus ring) to `BG_FOCUS` bg + 6px accent left bar

**Dashboard (`views/dashboard.py`):**
- "Generate Art" + "Remove Artwork" moved OUT of the collapsible DETAILS frame into an always-visible centered row under the button row (details frame now holds only labels)
- Hidden DETAILS buttons were still reachable because list-mode vertical nav wrapped through all `nav_list` entries without validity checks → `_move_selection` list-mode now scans for the nearest valid (visible+enabled) widget in the move direction; `_scan_widget_tree` also filters `isVisible()`

**Back navigation (ESC / B) — `handle_back` rewrite (`app.py`):**
- library (root) → toggles sidebar ON; with sidebar on → hides it
- dashboard → library; editor → dashboard
- global_settings / prefix_creator / livesplit → library + sidebar shown (`show_library(sidebar=True)` new param)
- `nav_stack.clear()` on every deterministic back; `_kb_back` no-ops when a modal dialog is open

**Animations (now noticeable):**
- **Sidebar slide**: `_toggle_sidebar_visibility` → `QPropertyAnimation` on `maximumWidth` (180ms OutCubic, min-width stepped via `valueChanged`); `_rebuild`+`rescan` deferred to `_sidebar_anim_done`; `_hide_sidebar_for_view` stops any running anim
- **View transition fade**: `_present_view` → `_animate_view_fade` — `QGraphicsOpacityEffect` on the stack 0.0→1.0 (160ms OutCubic), effect removed on finish; guards against overlapping fades (stops previous anim first) to avoid deleted-effect crashes
- **Poster zoom contained**: `PosterWidget` zoom range 0.92 (unfocused) → 1.0 (focused) so the scaled rounded rect NEVER exceeds the widget's square bounds (previous 1.0→1.07 clipped the rounded corners, exposing square corners); RUNNING badge now anchored to the drawn rect
- **`PosterWidget._zoom_anim` safety**: `QPropertyAnimation(self, ...)` uses `self` as *target* (parent is nullptr!) — the C++ anim can be destroyed while the Python wrapper lives → `stop_animations()`/`_animate_zoom()` guard with `getattr` + `try/except RuntimeError` (same pattern as `GameImage.stop()`)

**Testing:** headless suite `QT_QPA_PLATFORM=offscreen` (18 checks: launch/enter, QCheckBox, double-sync restore, view-switch clear, back-nav spec incl. sidebar toggle, gen/rm art outside DETAILS + not hidden-navigable, zoom containment, fade cleanup, anim teardown). NOTE: offscreen `processEvents()` does NOT flush `deleteLater` — the harness must call `app.sendPostedEvents(None, QEvent.Type.DeferredDelete)` after spinning, otherwise stale rebuilt widgets show with old geometry.

### Session 2026-07-31 (sidebar sliver + flash kill round)

**Sidebar active style (`app.py._update_sidebar_active`):**
- Removed `border-left: 6px solid ACCENT` from the active sidebar button — it rendered as a persistent accent sliver (~50×80px block) under the sidebar slide. Active style is now `BG_FOCUS` bg + accent-colored text + `BG_INPUT` hover (matches editor SAVE/DELETE family, no fake focus ring).

**Library flash on sidebar toggle — reflow, don't rebuild:**
- Root cause found by frame analysis: `_sidebar_anim_done` called `v._rebuild()` on the library mid-animation; a full grid rebuild re-created highlighting + re-scanned nav, spiking accent pixels (~1261→2510) and churning the right edge.
- Fix: `_sidebar_anim_done` skips `_rebuild()` when the view declares `_reflow_on_resize = True`; only LibraryView does.
- Library `resizeEvent` → `_do_reflow` → `_reflow_grid`: re-parents existing cards into a recomputed column count (`same formula as _build`) without rebuilding, swapping the scroll-area widget, or resetting scroll position. Cards keep their poster width (only column count adapts) — verified no horizontal overflow. `_reflow_on_resize` views must keep `num_cols` in sync (grid nav reads it).
- Verified: accent px stable at ~2497 after toggle, right-edge churn decays to 0 during anim.

**Keyboard clicking (`app.py._kb_activate`):**
- QShortcut consumes Enter/Space (verified via QTest: focused QPushButton/QCheckBox get 0 native clicks) — so `_kb_activate` clicks them itself, gated through `engine.trigger_input` + cooldowns: QPushButton→`fw.animateClick`, QCheckBox→`fw.toggle`, QComboBox→cycle `(currentIndex+1) % count()`, else `engine.press_current` (poster launch, etc.).

**Space = Details (`app.py._kb_details`):**
- Space no longer `_kb_activate`; it's `_kb_details`: library → `show_dashboard(current_game_id)`, dashboard → `show_editor`. Guards: editable focus, active modal, both cooldowns. HINT_DEFS not updated (still shows "X Details").

**Search focus preservation (`views/library.py._on_search_changed`):**
- During grid rebuild the search `QLineEdit` isn't in `nav_list`, so the engine refocuses the nav target after rescan — the search box would lose focus. Fix: deferred `QTimer.singleShot(0, ...)` refocus + cursor/scroll restore, which runs AFTER the engine's own deferred rescan-refocus (scheduled later → fires later). Reverted the `_build(priority=...)` param attempt.

**On-screen keyboard:** replaced in the next session — see "On-screen keyboard" section below (Plasma/Steam virtual keyboard was removed).

**Testing:** headless suite at `/tmp/opencode/smoke.py` — `QT_QPA_PLATFORM=offscreen`, temp `XDG_CONFIG_HOME` with `games.json` (15 fake games), 24/24 PASS. Conventions: `spin(n)` = processEvents×n with sleeps; `key()` = `QTest.keyClick` + ~0.3s event pumping (QPushButton `clicked` emits ~100ms after `animateClick`); `QTest.keyClicks(window, ...)` does NOT reach the focus widget — target `QApplication.focusWidget()`.

### Session 2026-07-31 (dashboard-nav fix + in-app on-screen keyboard)

**Dashboard nav dead-after-represent fix (`app.py._present_view`):**
- Root cause: on re-presenting a cached dashboard, `refresh()`→`_rebuild()` leaves old widgets pending `deleteLater` while `engine.rescan()` runs synchronously → `nav_list` fills with stale/deleted widgets; after deletion every nav target is destroyed → dead navigation until a mouse click triggers rescan.
- Fix: `_present_view` defers rescan via `QTimer.singleShot(0, self.engine.rescan)` (library already did this). Also removed all redundant `_build`-end rescans in `dashboard.py`/`editor.py`/`livesplit_view.py`/`global_settings.py` — the priority widget is always the first nav widget, so the deferred rescan handles focus. Offscreen `deleteLater` flushes only with `sendPostedEvents(None, QEvent.Type.DeferredDelete)` (the smoke harness convention).

**On-screen keyboard (`launcher_pyqt/on_screen_keyboard.py`) — replaces Plasma/Steam virtual keyboard:**
- `OnScreenKeyboard(QFrame)` child of `_content_area` (not top-level) — hidden on view switch, stays in content bounds. Rows: ABC + ?123 (sym) layouts with IDENTICAL row lengths (relabel-only toggle). Keys = flat `QPushButton`s with `osk_key=True`/`key_kind`/`char` attrs so `_scan_widget_tree` picks them up.
- `_nav_mode == "keyboard"` (new, first in `_determine_mode`): scans only the OSK; nav is position-based (`_move_selection_keyboard` uses `mapTo(ref, center)` with ref = OSK — `mapTo(self)` crashes since engine isn't a QWidget; score `|dx|*2 + |dy|`, nearest-in-direction).
- `open_keyboard()`/`close_keyboard()` in engine: `_nav_index_before_osk` saves/restores the field's index; `open_keyboard` moves focus to first key so keyboard-layer arrows/Esc work; `close_keyboard` restores focus to the field. Both sound via "confirm".
- Editable targets are `QLineEdit`/`QTextEdit`/`QPlainTextEdit` (press_current field branch) → `setFocus`+`selectAll`, then toggle OSK. `sync_visuals` in keyboard mode never steals focus from an editable widget (guards setFocus) — but OSK key buttons DO get focus (so arrows/Esc/QShortcut-Enter work); insertion uses `QApplication.focusWidget()` if editable else cached `_last_target`.
- Shift is one-shot for alpha chars (`text.upper()` + `_shift=False` + `_relabel()`); sym/abc toggle relabels buttons in place.
- `_on_focus_changed` (engine): mouse-click into an editable (`QApplication.mouseButtons()`) opens OSK; focus moving to a non-OSK non-editable widget while open closes it; editable/osk_key widgets never auto-close. No modal gates — OSK works over modals too.
- `_kb_back`: Esc closes OSK BEFORE the editable-focus guard (reordered) and before modal check. `_kb_details`/`_kb_activate` gate on OSK visible (no details-nav while typing; Enter activates the focused key via `fw.animateClick`).
- `_present_view` closes the OSK (via `engine.close_keyboard()` to restore nav) on every view switch. `trigger_virtual_keyboard`/`_plasma_keyboard_available`/`on_screen_keyboard_open` removed.
- Note: keyboard-layer Enter after an arrow move is blocked by the 0.4s engine cooldown (consistent with existing keyboard-layer gating; tests sleep 0.6s before Enter).

**Testing:** `/tmp/opencode/osk_test.py` (23 checks: editor→field→A→OSK open/nav-keyboard/focus-first-key, type 'h', close→nav restore, reopen+shift→'A', view-switch hides OSK, QTest arrows move cursor, Enter types, Esc closes). Smoke suite extended to 25/25. Repro `/tmp/opencode/dash_nav_repro.py` now passes (live nav_list after cached re-present).

### Session 2026-07-31 (OSK bugfix round)

**Grid nav instead of nearest-in-direction (`input_engine._move_selection_keyboard`):**
- Old position-score search jumped to corner keys. Now reads `osk.rows` (list-of-lists, stable across ABC/sym since row lengths are identical): left/right wraps within the row (`(cc ± 1) % len(row)`), up/down moves to the adjacent row picking the key with min `|Δx|` from the current key's center. Locates the current key by identity (`b is cur`), returns `widgets.index(nb)`.
- Verified: h→right j; h→down b; up j; left stays in-row (h,g,f,d,s,a); no corner jumps.

**X (close) / Enter-on-QLineEdit restored nav mode:**
- `_on_key` "close" and `_enter()`'s QLineEdit branch called `self.close()` (hide + clear target) but left `_nav_mode == "keyboard"` and nav_list full of hidden OSK buttons → dead nav. Both now route through `_close_via_engine()` → `engine.close_keyboard()` (hides, rescans, restores `_nav_index_before_osk`, refocuses field).

**'&' label invisible:**
- Qt treats `&` in `setText` as a mnemonic marker (renders nothing). `_relabel` now escapes `text.replace("&", "&&")` for display; `b.char` keeps the real `'&'` so insertion types a literal `&`. (`&&` renders as one `&`.)

**Library-search crash (`wrapped QLineEdit has been deleted` → SIGABRT):**
- Each keystroke rebuilds the library (`_rebuild()` → new `_search`), so the OSK's cached `_last_target` pointed at a `deleteLater`-pending dead box; next key raised RuntimeError in the slot.
- Fixes (all in `views/library.py` + `on_screen_keyboard.py` + `input_engine.py`):
  - `_on_search_changed`: new `osk_targeting` check (`osk._last_target is self._search`) refocuses the rebuilt search box even when the field never had keyboard focus (OSK keeps focus on the key). When `osk_targeting and not had_focus`, cursor restored to `len(search.text())` (end) — otherwise cursor sat at 0 and backspace/insert acted at the wrong end.
  - `_on_focus_changed` (engine): while OSK open, editable gaining focus refreshes `osk._last_target` (covers the deferred refocus path).
  - `_focus_target` liveness probe: `t.winId()` wrapped in try/except RuntimeError → clears dead `_last_target`, returns None (keystroke dropped instead of crashing).
  - `_safe_call(t, func)` wraps every insert/backspace/cursor op in try/except RuntimeError → clears stale target on failure.
- **Key-dispatch is `sender()`-free:** `_build` connects `b.clicked.connect(lambda checked=False, k=b: self._on_key(k))` and `_on_key(b)` takes the button — `self.sender()` was flaky (once typed '1' when the 'h' key was pressed). Deterministic captured binding.
- Note: `open_keyboard` DOES move focus to the first key (reverted the field-focus experiment) — QLineEdit claims ShortcutOverride for arrows/Enter, so the keyboard layer would never see them if focus stayed in the field. Field rebuilds are handled by the `osk_targeting` refocus protocol instead.

**Testing:** `/tmp/opencode/osk_fix_test.py` (19 checks: X restores nav, Enter-on-line restores nav, `&` label `'&&'`, search h→backspace→e survives rebuilds with live cursor). All suites re-run 3×, stable: osk_test 23/23, osk_fix_test 19/19, smoke 25/25. Grid-nav verified via `/tmp/opencode/nav_test.py`. NOTE: never `pkill -f` with a pattern that appears in your own command line — it kills the shell.

### Session 2026-07-31 (Dashboard DETAILS as overlay)

**`DetailsOverlay(QFrame)` in `views/dashboard.py`:**
- Replaces the inline collapsible DETAILS frame. Full-view dimmed backdrop (`rgba(0,0,0,160)`, `WA_StyledBackground`) with a centered panel (max 620px): DETAILS header + close (✕) button + Exe/Prefix/Proton/Store/Launch Count rows. Created as a child of the dashboard (NOT in the layout) — geometry synced in `resizeEvent`, z-raised on open, deleted on `_rebuild`.
- **Discard paths:** (1) back action — `app.handle_back` checks `details_overlay_open` first and calls `view._close_details()` (covers controller B and Esc); (2) click/tap outside — `mousePressEvent` on the backdrop closes; (3) close button. `_AbsorbFilter(QObject)` event filter on the panel consumes mouse/touch so inside-clicks don't dismiss (QLabel ignores → propagates to panel → filter absorbs).
- **Nav confinement:** `_open_details` disables every dashboard `QPushButton` (`_set_nav_enabled(False)`, skipping the overlay subtree) so `rescan` yields `nav_list == [close_btn]`; `_close_details` re-enables and `rescan(priority_widget=self._details_btn)`. Because dashboard buttons are disabled while open, the X (list→editor) and Y (dashboard→browse_artwork) shortcuts are gated via `engine._details_open()` (new helper), and `_kb_details` gates too.
- Fade-in 150ms OutCubic via `QGraphicsOpacityEffect` (same pattern as confirm modal); `_close_details` stops the anim + clears the effect before hide.
- DETAILS button label changed to `▸` (opens a panel, not an expand).

**Testing:** `/tmp/opencode/overlay_test.py` 29/29 (open→buttons disabled→nav confined to close btn, back closes+stays on dashboard, backdrop click closes, close btn closes, inside-panel click keeps open, Esc closes, fresh hidden overlay after re-present). `/tmp/opencode/smoke2.py` 12/12 nav/back/sidebar regression. NOTE: `QTest.mouseClick(widget, ...)` delivers to the *passed widget*, not hit-tested — test inside-panel clicks by targeting a child QLabel directly; and `handle_back` from global_settings calls `show_library(sidebar=True)`, so sidebar toggle tests must force a known initial state.

**Dashboard button row (handheld fit):**
- Generate Art / Remove Artwork merged INTO the `btn_row` (Browse Artwork, Game Settings, fav) — the old separate `art_actions` row sat below the fold on small screens (handheld, no external monitor). One centered row now.
- Compacted: padding 6px/4px, font 10-11px, spacing 8, fav 34×32. Measured row ≈482px → fits even at 560px-wide content area (measured via `/tmp/opencode/btnwidth2.py`).

**Sidebar-toggle nav break (stale widgets):**
- Root cause: `_sidebar_anim_done` called `engine.rescan()` synchronously right after `view._rebuild()`. `_rebuild` uses `deleteLater`, so the widget tree still held the old (visible) buttons → `nav_list` filled with 6 stale + 6 new widgets; after the deferred deletion flushed, half the nav targets were dead C++ objects → nav stuck until a mouse-click rescan.
- Fix: `_sidebar_anim_done` now defers via `QTimer.singleShot(0, self.engine.rescan)` — same pattern as `_present_view`. Verified: 6 unique alive widgets, no dupes, full nav walk after ON→OFF toggle.
- NOTE: `_move_selection` list mode wraps through `nav_list` via `_is_valid` (checks `isVisible()` — clipped-but-shown widgets still count as valid).

**Dashboard adaptive art (content fits small screens + sidebar-growth fix):**
- `_stable_avail()`: art is sized from the STABLE content-area height (`content_area.height() - 36` bottom bar), NOT `self.height()` — the sidebar-slide transient-height race previously rebuilt art from a momentary height spike (746), and bigger art made the layout min force the window taller → runaway growth on every ON/OFF toggle.
- `_fit_content()` overflow cap: reads the real DETAILS button bottom; if it exceeds `self.height() - 12`, shrinks art via `_rebuild(art_override=...)`. Kills the window-growth loop and fixes long-notes overflow (content never exceeds the view); converges in one step (`desired = min(heuristic, used - over)`), rebuild threshold 12px.
- `_build(art_override=None)` + `_rebuild(art_override=None)`: default art from `_art_height_for_avail(_stable_avail())` (avail>200 else 400); override threads the capped value through.
- `_art_height_for_avail`: notes `clamp(200, avail - 345, 480)`, no-notes `clamp(260, avail - 235, 480)` (width = 0.75×). `_reflow_on_resize = True` (skips pointless `_sidebar_anim_done` rebuild). Verified: repeated ON/OFF toggles keep art/view size constant (no growth).
- Offscreen caveat: the QStackedWidget refuses to shrink below its sizeHint (766) — standalone fixed-size DashboardView tests overflow the layout and SCRAMBLE geometry (overlapping widgets, bogus `details_bottom`), so only trust real-app measurements for fit. `_fit_content` relies on small deficits being absorbed by spacing compression (sane positions).

### Session 2026-07-31 (handheld fit: dashboard art + sidebar EXIT)

**Dashboard art now adapts to real content (replaces the pure heuristic):**
- The old `_fit_content` bottom-check alone never fired on short screens — the layout silently compresses (spacing→0, label shrink), so art stayed 480 and buttons got squished/hidden. Fix: `_fit_content` also caps `desired` by `max_art = (h - 12) - non_art` where `non_art = layout.sizeHint().height() - used` (sizeHint is a stable natural-content measure; `heightForWidth` is NOT width-aware). This is absolute (not relative to current art), so it CANNOT oscillate: after a shrink the same cap reproduces `used`, delta 0. Guarded by `self._art_widget is not None` (no-art views skip the cap; negative math would otherwise emit a bogus art).
- Verified (`/tmp/opencode/fixed_harness.py`, real-app stack + 36px bottom bar): 800-tall → art 480 (no-notes) / 335 (notes), 700 → 385/235, 620 → 305/155, DETAILS bottom always ≤ stack height. No rebuild loop (second `_fit_content` call sees `sizeHint == h - 12`).

**Sidebar EXIT no longer clipped on short screens (`app.py`):**
- Sidebar min height was 579 (logo fixed 160 + title + 5 nav btns + exit); at window ≤ 620 the sidebar overflowed the content area (win_h − 50) and EXIT fell off-screen. Measured: non-logo min = 419; compact styles (font 13px, padding 8px, margin 3px) bring full min to 289.
- `_fit_sidebar()` (called from `_create_sidebar` and new `LauncherWindow.resizeEvent`): `avail = self.height() - 50`; `logo_h = clamp(40, avail - non_logo, 160)` — logo 160 preserved down to ~630-tall windows, shrinks continuously below. When `avail < 460` flips `_sidebar_compact`, which restyles title/exit/nav buttons via compact-aware templates (`_sb_style_vars`, `_sb_title_style`, `_sb_btn_style`, `_sb_exit_style`) and re-runs `_update_sidebar_active` (keeps `_nav_base_style` + focus ring in sync).
- Verified (`/tmp/opencode/sidebar_exit.py` at 800/700/620/560/520/480/440): EXIT fully visible at every height, no OFFSCREEN, sidebar_h == win_h − 50 always.

### Session 2026-08-01 (re-present growth + editor nav scroll)

**Re-present window-growth bug (dashboard↔library round-trip):**
- Symptom: every back-and-forth to the dashboard grew the window (772→844→916→983) until art pinned at 480. Root cause: `_present_view` calls `refresh()`→`_rebuild()`→`_build(art_override=None)` while the view is ALREADY in the stack, and `_build` reset `_art_height_used` to the heuristic — discarding the previously fitted value. The fit cap then landed exactly 12px under the heuristic every time (blocked by the 12px rebuild threshold), the layout's real sizeHint materialized in the event loop, and Qt never shrank the window back. This growth also pushed the sidebar EXIT off physical-screen in windowed mode.
- Fix: `_build` now caps the heuristic against the **stored non-art height**: `self._non_art_height` (measured in `_fit_content`, `max(0, sizeHint - used)`, hidden-art → `sizeHint`) → `art = min(heur, avail - 12 - non_art)`. First build (view not yet in stack) uses the heuristic and the build-time `_fit_content` shrink still works; re-presents cap from the stored measure so the layout never exceeds avail and the window can't grow. Also: `_reveal_widgets(layout)` shows all non-art widgets at the end of `_build` (skips `GameImage` attrs) so the layout sizeHint measures correctly during re-builds (freshly built widgets are `isHidden` → `QWidgetItem.sizeHint()==0` until the event loop shows them; `layout.activate()` does NOT fix it).
- Verified (`/tmp/opencode/growth_repro.py` 6 cycles + sidebar toggles): win_h constant 700, art constant 185. `growth_verify.py`: 800→art 435/285, 700→335/185, all stable after 2 more cycles. `exit_repro.py`: EXIT visible within the window at 560→800. Note: a notes game on a window shorter than the content floor still grows ONCE to the true minimum (e.g. 560→635) — a hard floor, not an oscillation; in fullscreen the window clips but the sidebar (win_h−50) still shows EXIT.

**Editor SAVE/DELETE reachable at small screens (`input_engine.py`):**
- Symptom: on short windows (editor content taller than the viewport) controller/keyboard nav landed on the SAVE/DELETE row but the buttons stayed off-screen — programmatic `setFocus()` does NOT auto-scroll a `QScrollArea`, so focus silently hit invisible buttons.
- Fix: `_ensure_scrolled(widget)` walks parent chain and calls `ensureWidgetVisible(widget, 8, 8)` on the first `QScrollArea` ancestor; invoked from `sync_visuals` before `setFocus`, skipped for `grid`/`file_browser` modes (library grid has its animated `scroll_to_library_item`, browser has `scroll_to_selected`). Mouse-hover path covered too (goes through `sync_visuals`).
- Verified: `/tmp/opencode/editor_nav_test.py` (nav to SAVE at 560-tall window → visible in viewport). Regressions green: overlay_test 29/29, smoke2 12/12, repro_navbreak2 walk 0, sidebar_bug + growth_repro stable.

### Session 2026-08-04 (M3: dashboard landscape hero + floating card)

**Prerequisite milestones (this port):** M1 shell (header/tabs/full-bleed/no sidebar/tab-first nav, `m1_test.py` 32/32) and M2 (Home recents carousel + A-Z Library + add-game modal, `m2_test.py` 21/21) shipped before M3. `launcher_pyqt/` is the active PyQt6 codebase; `colors.py` retokenized with role tokens; themes Deep Blue / Amber Glow / Synthwave.

**`art_land` (landscape backdrop) data layer:**
- `utils.py`: new `generate_placeholder_art_land(game_id, name, accent, bg, out_dir)` → 1280×720 themed placeholder (gradient + glow + arcs + title at ~0.26h so it clears the card) and `derive_landscape(game_id, name, accent, bg, out_dir, art_path=None)` → cover-crops the portrait art into 1280×720 with a bottom scrim, falls back to the landscape placeholder when no art. QFont usage requires a live QGuiApplication (offscreen tests must construct `QApplication` first — otherwise `QFontDatabase` access blocks).
- `config.py._migrate`: adds `art_land` default `""`.
- `ArtworkManager` (`artwork.py`): `select`/`remove` take a `key` param (`"art"` or `"art_land"`); `art_land` dest is `{game_id}_land{ext}`; `clear_all` clears both keys. `__init__` coerces dir to `pathlib.Path` (accepts str).
- Wired into `add_game_modal._finish`, `app.add_new_game`, `app.open_add_game` (add flow derives landscape from the fresh portrait), dashboard `_browse_artwork` (sets BOTH art + art_land to the picked file), `_generate_art` (regenerates portrait + derives landscape), `_remove_artwork` (clears both).

**Dashboard redesign (`views/dashboard.py`):**
- `ArtworkWidget` removed. New `HeroBackdrop(QWidget)`: paints `art_land` (falling back to portrait `art`) cover-scaled, or a themed accent gradient + arc motif when no art, always with a bottom scrim (`QLinearGradient` → rgba(0,0,0,160)) for card readability. `sizePolicy(Expanding, Fixed)`, height set to the computed hero height. Static only (no GameImage/webp animation — backdrop is decorative; grid posters keep animated covers).
- Floating card is a `QFrame` (`BG_PANEL` + `BORDER` + radius 14) containing name/meta/PLAY/btn_row (Browse Artwork, Game Settings, fav, Generate Art, Remove Artwork). Width `_card_width()` = `clamp(340, min(680, content_w * 0.72))`.
- **Layout trick (clipping-safe overlap):** children clip at their parent's bounds, and negative `setSpacing` is clamped by Qt — so instead of overlapping across widgets, the card lives INSIDE the hero container via a `QGridLayout` cell: `grid.addWidget(backdrop, 0, 0)` then `grid.addWidget(card, 0, 0, AlignHCenter|AlignBottom)`. Same-cell widgets stack with last-added on top; cell height = max(backdrop fixed height, card height); card bottom-aligned so it floats over the backdrop's bottom scrim region. Hero is full-bleed (main layout margins 0, spacing 0); notes + DETAILS button live in a `bottom` QWidget with (30,20,30,24) margins below the hero.
- **Fit math (replaces `_art_*`):** `_hero_height_used` / `_hero_floor` / `_non_hero_height` / `_hero_height_for_avail` (`clamp(220, avail-260, 430)` no-notes, `clamp(200, avail-300, 400)` notes). `_fit_content` caps desired by `(avail-12) - non_hero`, then floors it at `card_h + 60` (`_hero_floor`) so the floor can never oscillate against a too-small cap (delta 0 → no rebuild). `final_h = max(hero, card_h + 60)`.
- `_reveal_widgets` now recurses into child widgets' layouts (so hero/card/backdrop sizeHints are measured even before show). Nav: card buttons are plain QPushButtons in the tree → `_scan_widget_tree` finds them; first content nav widget is PLAY (nice default). `play_btn` contract preserved (`app.play_btn`).
- `DetailsOverlay` untouched; `_set_nav_enabled` still disables all dashboard QPushButtons (now including card ones) on open.

**Library/Home fallback:** `PosterWidget` and `HomePoster` use `data.get("art") or data.get("art_land")`; both `_data_sig` refresh signatures include `art_land`.

**Testing:** `/tmp/opencode/m3_test.py` 42/42 (hero/card structure, clipping containment, backdrop fills hero, `hero >= card+60`, card buttons in nav, Game Settings→editor, fit convergence, gen/rm art both keys, add-modal art_land, ArtworkManager key ops, migrate default, library+home poster fallback, back→library). Regressions: `m1_test.py` 32/32, `m2_test.py` 21/21. Renders verified by pixel probe (`/tmp/opencode/dash_art.png` / `dash_noart.png`): hero accent art at top, card panel distinct from backdrop at the same row, scrim darkens the bottom edge, gradient fallback when no art. NOTE: the model can't view images — verify renders by sampling `QImage.pixelColor` at known coordinates, not by eye.

### Session 2026-08-04 (M6: global default_proton + per-game "Use Default")

**Model (replaces the fixed "Default (UMU Internal)" per-game value):**
- New global `settings.default_proton` (migrated to `""` in `config.py._migrate` via `settings.setdefault` before the game loop).
- Per-game `proton` semantics: `""` = "Use Default" (falls back to the global default); `"Default (UMU Internal)"` = explicit override to UMU internal; any scanned proton name = explicit override. Resolution lives in `GameProcessManager._resolve_proton(data)`: `data.get('proton') or settings.default_proton or ""` — called in BOTH `try_launch` (guard: bogus path aborts launch) and `_run_process` (env `PROTONPATH`/`UMU_PROTON`), so the stored per-game value never needs to be rewritten.
- `editor.py` proton combo: new first item `"Use Default"` (stored `""` on save); then `"Default (UMU Internal)"`; then scanned proton names. Fixes a pre-existing bug where `proton_paths.keys()` (which already contains `"Default (UMU Internal)"`) added a duplicate — the scan loop now skips that key. Current selection: `data.get("proton", "")` — `""` stays on index 0.
- `global_settings.py`: new DEFAULT PROTON card (combo + "SAVE DEFAULT PROTON" button, `_save_proton` writes `""` for UMU internal and shows a toast; theme card's `_save` untouched). No "Default (UMU Internal)" duplicate there either.
- `dashboard.py` DETAILS overlay Proton row now shows the EFFECTIVE value: explicit proton if set, else `"Use Default (<global> or 'UMU Internal')"`.

**Testing:** `/tmp/opencode/m6_test.py` 26/26 (migration adds/keeps default, `_resolve_proton` precedence incl. missing-key, editor combo structure + no-duplicates + Use Default selection + save-stores-`""`, global settings save round-trip, DETAILS overlay effective display, try_launch aborts on bogus per-game AND bogus global default, launch resolution via patched `_run_process`). Regressions: `m1_test.py` 32/32, `m2_test.py` 21/21, `m3_test.py` 42/42. Total 121 checks green. NOTE: patching `_run_process` for launch tests must be a closure (the launch thread calls `self._run_process()` with no args — a plain method-typed stub raises TypeError).

### Session 2026-08-04 (M4: X quick-settings sheet)

**`launcher_pyqt/quick_settings.py` (`QuickSettingsOverlay`):**
- Child of `app._content_area` (like OSK); full-bleed dimmed backdrop `QFrame` (`rgba(0,0,0,160)`) whose `mousePressEvent` → `app.close_quick_settings()`, centered panel `QFrame` (max-width 560, BG_PANEL + BORDER + radius 12) with `_AbsorbFilter` so inside-clicks never dismiss. Fade-in 150ms OutCubic via `QGraphicsOpacityEffect`.
- Rows: QUICK SETTINGS header + ✕ close btn; game name; GAMESCOPE toggle; RESOLUTION cycle btn (`RES_PRESETS = ["1280x720","1920x1080","1600x900","1024x576"]`, unknown → index -1 → first preset); MANGO HUD toggle; LIVESPLIT toggle; PROTON combo (`Use Default` → saves `""`, `Default (UMU Internal)`, then `proton_paths.keys()` minus the duplicate); info line `N launches • last played <relative_time>`.
- Every change applies immediately via `config_manager.save_data(config_data)` (`_after_change` → `_refresh_widgets`). Toggling GS ON forces `livesplit=False`; LIVESPLIT button disabled when `app.runningOnGamescope` OR `gs_on` (disabled style stripped of hover). `_refresh_widgets` restores combo selection with `blockSignals` guard (no spurious save on open).
- `open(gid)` captures `engine.nav_index` + `_focused_game_id()` for close-restore; `show()`/`raise_()` then `engine.rescan(priority_widget=self.gs_btn)`. `close()` hides, `engine.rescan()`, then restores focus by game_id match else clamped stored index.

**Wiring (`app.py`):**
- Instance created in `__init__` AFTER `_content_area` (line 68) and alongside OSK: `self.quick_settings = QuickSettingsOverlay(self)`. App-level `open_quick_settings(gid)`/`close_quick_settings()` + `quick_settings_open` property (getattr + `isVisible()` in try/except RuntimeError). `handle_back` checks `quick_settings_open` FIRST (before view back) — one branch, covers controller B and Esc.
- `_present_view` closes the sheet (like OSK) on any view switch. `_kb_back` closes sheet after OSK check, before editable-focus guard. `_kb_tab` blocked while sheet open. `_kb_activate` needs no changes (Enter on focused sheet button routes via QPushButton/QCheckBox/QComboBox branches or `press_current`).
- `_kb_details` (Space) rewritten: opens the sheet via `engine.trigger_input` on home/library/dashboard (no more X→details/dashboard→editor); gated on OSK visible, quick_settings_open, modal, both cooldowns, and `details_overlay_open`.
- HINT_DEFS: home/library `X Quick-Set`, dashboard `X Quick-Set` (was X Details/Settings).

**Input engine (`input_engine.py`):**
- `_determine_mode` returns `("quick_settings", qs)` when `app.quick_settings.isVisible()` (checked after modal, before view_state); `rescan` scans the sheet subtree in that mode; no tabs prepended (tabs only in grid/list). `sync_visuals`' existing stale-focus clearing handles the underlying view's focus ring when nav_list changes (sheet open/close).
- Button dispatch: B (rising 1) → `close_quick_settings` in quick_settings mode; X (rising 2) rewritten → opens the sheet on home/library/dashboard (`vs in (...)` + `not self._details_open()` + `gid = _focused_game_id() or current_game_id`), no-op when already open; Y (rising 3) and Start (rising 7) no-op while the sheet is open. A (rising 0) → `press_current` works unchanged (toggles sheet buttons, cycles proton combo).

**Editor refresh (`views/editor.py`):**
- New `refresh()` re-syncs gs/hud/ls toggles + gs_w/gs_h + proton combo from `config_data` (quick-settings changes otherwise stale until Y/Save clobbered them). Called automatically by `_present_view` for cached views. Deliberately does NOT touch notes/prefix/umu/name (unsaved-editor-edits-preserved guarantee).

**Testing:** `/tmp/opencode/m4_smoke.py` 29/29 (structure, open-from-library/dashboard/home, nav confined to sheet + underlying poster excluded, toggle round-trips incl. gs-forces-livesplit + ls-disabled, res cycle, proton save incl. `""` for Use Default, disk persistence, close/backdrop-click/handle_back paths, nav restore, editor refresh, **controller dispatch via fake `Joystick` into `engine.update()`** — X opens/A toggles/B closes, keyboard Space/Esc via direct `_kb_details`/`_kb_back` calls). FakeJoystick note: `refresh_hardware` only rescans when `joysticks` empty, so `eng.stop(); eng.joysticks=[fake]` then manual `eng.update()`; cooldowns bypassed by zeroing `last_input`/`_last_input_button` between presses. QShortcuts DON'T fire offscreen (window never active) — prior tests call handlers directly. Regressions: m1 32/32, m2 21/21, m3 42/42, m6 26/26 → **150 total green**.

### Session 2026-08-04 (M7: home animation + dashboard art independence + A-open + MENU-launch)

**Home carousel animation (`views/home.py`):**
- HomePoster/BrowsePoster now animate on focus like library posters: shared `_zoom_mixin_setup`/`_zoom_prop`/`_animate_zoom`/`_stop_animations`, `_ZOOM_OFF=0.92`/`_ZOOM_ON=1.0`, `zoom` pyqtProperty, 180ms OutCubic `QPropertyAnimation`. `paintEvent` scales the draw rect by `_zoom` (radius `12*z`, ACCENT ring `max(1, int(3*z))`).
- `GameImage` created for webp/gif art only (posters with png/other art get `game_image=None`); engine shows/raises/starts it on focus.
- Running badge `"▶ RUNNING"` (c.SUCCESS, top-right, `\u25b6` glyph) painted when `is_running`. `HomeView._update_running_badges()` reads `game_process_manager.current_running_game_id`; `hideEvent` calls `stop_animations()` on all posters.
- BrowsePoster ("ALL GAMES" tile) zooms too but has no game/running state.

**Dashboard art independence (`views/dashboard.py` + `utils.py`):**
- Card button row: "Portrait" → `_browse_artwork("art")` (tooltip "Portrait art used in the library"), "Landscape" → `_browse_artwork("art_land")` (tooltip "Landscape hero art shown on this dashboard"), then Game Settings/fav/Generate/Remove.
- `_browse_artwork(key="art_land")`: portrait pick auto-derives the hero via `utils.derive_landscape` ONLY when `art_land` is unset (never clobbers an existing landscape); landscape pick never touches the portrait. `_remove_artwork` clears BOTH keys; `_generate_art` sets portrait + derived landscape.
- DETAILS overlay now has Portrait/Landscape rows showing `set`/`none`.
- NOTE: `_browse_artwork` local-imports `ControllerFileBrowser` — harnesses must patch `launcher_pyqt.controller_file_browser.ControllerFileBrowser` (the source module), NOT `views.dashboard`'s name.

**Library/home A → dashboard; MENU/Start → quick launch:**
- `press_current` game_id branch → `app.show_dashboard(gid)` (was `try_launch_game`). Library poster `clicked` also → `show_dashboard` (old `_quick_launch` removed).
- Start `rising(7)`: resolves `_focused_game_id() or current_game_id`, sets `current_game_id`, `trigger_input(try_launch_game)`, "launch" sound. No-op in quick_settings mode.
- `HINT_DEFS` home/library: `[("A","Open"), ("MENU","Launch"), ("X","Quick-Set"), ("Y","Fav"), ("LB/RB","Tabs"), ("View","Hold-Quit")]`.

**Keyboard parity (app.py):**
- `R` = Start/MENU (`_kb_start`): quick-launch focused/current gid. `F` = Y (`_kb_favorite`): settings→`save_game`, dashboard→`browse_artwork` (gated on details overlay closed), home/library→`toggle_favorite_for(focused gid)`. Both gated on editable focus, quick_settings_open, active modal, both cooldowns.
- Engine focus skip guard in `_apply_focus_style` is now plain `hasattr(widget, 'game_image')` (posters rely on their own paint/GameImage focus, not QSS rings).

**Testing:** `/tmp/opencode/m7_test.py` 40/40 (hints, home zoom/GameImage/badge/hideEvent, A→dashboard from home AND library, MENU quick-launch via fake joystick `press(7)`, keyboard R/F dispatch, art independence incl. auto-derive/no-clobber/landscape-independent/generate/remove, DETAILS rows). Harness gotchas: webp fixture must be a REAL webp (QImage.save with "WEBP") — invalid bytes hang QMovie offscreen; top-10 recents require high `last_played`; `QImage(...).fill(...).save(...)` chain breaks (fill returns None); `show_editor()` takes no arg; DETAILS row labels have trailing `:`. Regressions: m1 32/32, m2 21/21, m3 43/43 (nav labels updated to Portrait/Landscape), m4_smoke 29/29, m6 26/26 → **191 total green**.

### Session 2026-08-04 (M8: QS keyboard parity + controller-reachable library header + browse-only add modal + dashboard declutter/animated hero)

**1. Quick-settings keyboard parity (`app.py` + `quick_settings.py`):**
- `X`/`Space` (`_kb_details`) opens the quick-settings sheet on home/library/dashboard (gated on OSK, sheet open, active modal, both cooldowns, art/details overlays). `Esc` (`_kb_back`) closes the sheet BEFORE the editable-focus guard (reordered). `Enter` cycles the proton combo / toggles sheet buttons via `_kb_activate` → `press_current` (sheet buttons are plain QPushButton/QCheckBox/QComboBox). Q1 test drives these through direct handler calls (QShortcuts don't fire offscreen).

**2. Library Add New Game + search controller-reachable (`input_engine.py` grid/header nav + `views/library.py`):**
- `LibraryView._header_nav = [self._search, add_btn]` — grid mode `rescan` prepends header widgets (search box + green `+`), so controller Up from grid row 0 → search → up again → active tab; left/right wrap within the header row.
- **Default view-entry position skips the header** (`rescan` view_changed branch): `nav_index = tabs + len(header)` → lands on the FIRST POSTER, NOT the search box — otherwise the search box auto-focus blocks ALL keyboard shortcuts (`_kb_focus_is_text()` true → arrows/Q/E dead on entry). Header only gets focus when the user navigates up to it.
- Search focus: `sync_visuals` keeps line-edit focus in grid mode (pass-list: QLineEdit/QTextEdit/QPlainTextEdit — QComboBox only in `quick_settings` mode, so the global_settings combo still steals focus for keyboard nav). Enter on the search opens the OSK (`press_current` field branch).
- `scroll_to_letter` (A-Z jump) nav index is now `tabs + len(header) + card_idx` (was `tabs + i` — header shifted the grid).
- Grid left-from-col0 wraps within the row; up from col0 → search box (header_count), up from header → active tab. m1_test grid expectations updated for the header row.

**3. Add-game modal: browse buttons, no path fields (`add_game_modal.py` rewrite):**
- Non-blocking: `app.open_add_game` stores `self._add_game_modal` (None in `__init__`), `modal.open()` + `finished` → `_on_add_game_done` (stores game, saves config, `show_editor()`). Engine `_determine_mode` returns `("modal", agm)` when it's visible — no `exec()` so the controller/launcher never freezes.
- Fields: NAME line edit + EXECUTABLE/PREFIX **browse buttons** (`_BrowseCapture` wrapper: `app.browse` calls `setText(path)` on it → records `_exe_path`/`_prefix_path` on the modal and elides the button label; no QLineEdit for paths). Cancel/Add row. B cancels, name required on Add.
- `_finish` generates placeholder portrait + derived landscape (`art_land`) like `add_new_game`.

**4. Dashboard declutter + animated hero (`views/dashboard.py`):**
- Card button row collapsed to PLAY + **Settings** + **Artwork** + fav (Portrait/Landscape/Generate/Remove moved into a new `ArtOverlay` opened by the Artwork button — backdrop-dismissing panel like DetailsOverlay, `_set_nav_enabled` handles both overlays). `ArtOverlay` holds Portrait browse (`key="art"`), Landscape browse (`key="art_land"`), Generate (both), Remove (both; disabled when no art).
- `HeroBackdrop` (was static `ArtworkWidget`) now animates webp/gif via `QMovie` (`CacheNone`, `frameChanged→update`, NO `finished→start` reconnect — QMovie loops automatically and a spurious `finished` on a stalled movie would spin an infinite loop). Movie `start()` in `showEvent` AND in `_build` when `self.isVisible()` (rebuild-created backdrops never get a showEvent).
- Nav-label collision: the card "Settings" button and the "Settings" TAB both read "Settings" — list-mode tests must disambiguate (pick the one inside `_hero_card`).

**Testing:** `/tmp/opencode/q1_test.py` 15/15 (library header nav incl. A-on-search→OSK, sheet open/mode, combo not stolen in QS, Enter cycles combo, toggle gs, Esc closes), `/tmp/opencode/q2_test.py` 13/13 (non-blocking open, modal mode, browse picked exe/prefix via `_exe_path`/`_prefix_path`, B cancel, add saves + editor, reopen from library `+`, cancel-return), `/tmp/opencode/q4_test.py` 15/15 (card buttons, no Portrait/Landscape/Generate/Remove on card, Artwork opens overlay, overlay nav confined, back closes, Remove disabled w/o art, hero QMovie starts on show + stops on hide + restarts on re-show). Combined runner `/tmp/opencode/m8_test.py` 3/3. Regressions: m1 33/33, m2 21/21, m3 41/41, m4_smoke 29/29, m6 26/26, m7 40/40 → **233 total green**. NOTE: offscreen QMovie starts fine with `CacheNone` (standalone probe verified `MovieState.Running`); dashboard backdrop must also handle the rebuild-without-showEvent path.

### Session 2026-08-04 (M9: add-modal polish + dashboard Settings chooser + home featured/centered)

**Add-game modal (`launcher_pyqt/add_game_modal.py` rewrite):**
- **Auto-fill name from exe** (`_suggest_name`): on exe Browse, if NAME is empty (or `_name_auto` flag) suggest from path — basename stem → exe dirname → dirname-parent; reuse the full string if the stem is already in `_GENERIC_STEMS` (main/setup/game/launcher…). `_prettify` splits non-alnum runs, title-cases. Never clobbers a manually-typed name.
- **Prefix row = Browse + Create buttons.** Browse records `_prefix_path` (via `_BrowseCapture`, elides label). **Create** opens page 2 (`QStackedWidget`): deps card with `DEP_NAMES` checkboxes (`vcrun2022`, `dotnet48`, `corefonts`, `d3dx9`, `faudio`, `xna40`, `physx`), Back / Create Prefix. Create Prefix: pfx path = `<exe_dir>/<title>_pfx` (fallback `~/Games`), sets `_prefix_path`, disables buttons ("Creating…"), returns to page 1, spawns daemon thread → `create_wine_prefix(prefix, deps, log)` → `pfx_done_signal(bool, prefix)` (queued to main thread) re-enables + toast "Prefix created: …". Deps state preserved across page flips.
- `create_wine_prefix(prefix, deps, log=None)` extracted module-level in `pfx_creator.py`: `wineboot --init` under `WINEPREFIX`/`WINEARCH=win64`, then `winetricks <deps>` if any.
- **Add → dashboard + quick settings (not editor):** `app._on_add_game_done` → `show_dashboard(g_id)` then `QTimer.singleShot(200, lambda: self.open_quick_settings(g_id))` (delay lets the dashboard's deferred rescan settle). `q2_test` line 82 check updated to `view_state == "dashboard"`.

**Dashboard Settings chooser (`views/dashboard.py` `SettingsOverlay`):**
- Card "Settings" button opens a panel (same pattern as DetailsOverlay/ArtOverlay: dimmed backdrop QFrame + centered `_AbsorbFilter` panel, fade-in 150ms) with **⚡ Quick Settings** (`app.open_quick_settings(gid)`) and **⚙ Advanced Settings** (`show_editor`), close ✕. `_settings_overlay`/`_settings_btn`/`_open_settings`/`_close_settings`/`_act_settings` + `settings_overlay_open` property; `_set_nav_enabled` covers it; `handle_back`/`_kb_details`/`_kb_start`/engine `_details_open` gate on it. M8 note: "Settings" text collides with the Settings TAB — tests must disambiguate via `_hero_card`.

**Home featured + centering (`views/home.py`):**
- `FeaturedPoster` (QPushButton, same `_zoom_mixin_setup`/`_animate_zoom`/`_stop_animations`/pyqtProperty pattern): first carousel entry = most-recently-played game, wide Steam-style banner (`fw = int(ch * 2.6)`), paints `art_land`-or-art cover-scaled (`KeepAspectRatioByExpanding`), bottom scrim + bold name, RUNNING badge, ACCENT focus ring, `GameImage` for webp/gif. Fallback branch paints accent gradient + glow disc (float args to `QPainter.drawEllipse` CRASH — must `int()` them).
- Rest of recents are `HomePoster`, BrowsePoster "ALL GAMES" tile still last. `hideEvent` + `_update_running_badges` cover FeaturedPoster too.
- **Carousel centering:** `_center_carousel()` (deferred singleShot 0 + `resizeEvent`) → `_carousel_inner.setFixedWidth(max(total, avail))` with `avail = content_area.width() - 56`; `_carousel_total` tracks row width incl. spacing, so a short row centers and a long one scrolls.

**Robustness fix (`app.py._focused_game_id`):** wrap the focused-widget `hasattr` in `try/except RuntimeError` — after a view switch the deferred `rescan` hasn't flushed `deleteLater` yet, so `nav_list[nav_index]` can be a destroyed wrapper (crashed `_kb_start` in m7).

**Testing:** `/tmp/opencode/m9_test.py` 35/35 (suggestion chooser buttons created + click fills name + no-clobber + hidden-after-typing + fresh-modal create-disabled, page-2 create flow incl. `_prefix_path` + selected deps + back + toast via `len(w.toast.toasts)` — `ToastManager` is not a widget, assert `toasts[0].text()`; add→dashboard→QS + qs-close-back, SettingsOverlay Quick→QS / Advanced→editor + back + nav reset, featured = latest played + wide + in nav, centering `inner==max(total,avail)`). m3/m7 fixture updates: most-recent game is now FeaturedPoster, so m2 counts `len(HomePoster)+len(FeaturedPoster)==10`, m3 searches `findChildren((HomePoster, FeaturedPoster))`, m7 webp test targets `feat[0]` and HomePoster count is 9. Regressions: m1 33/33, m2 21/21, m3 42/42, m4_smoke 29/29, m6 26/26, m7 41/41, q1 15/15, q2 13/13, q4 15/15 → **266 total green**.

### Session 2026-08-04 (add-modal polish, UI refresh, hero backdrop crash fix)

**Bug fix — `HeroBackdrop` crash on re-enter (`views/dashboard.py`):**
- Root cause: `QMovie(art_path)` created without a parent (orphan QObject). When the dashboard was re-presented, `_rebuild()` → `_clear_layout` → `deleteLater()` destroyed the `HeroBackdrop` C++ object, but the orphan movie kept running; its `frameChanged` connection fired into the deleted widget → `RuntimeError: wrapped C/C++ object has been deleted`.
- Fix: `QMovie(art_path, parent=self)` — parent the movie to the widget so it dies with it (same lifetime guarantee `QLabel.setMovie()` provides in `GameImage`). Also replaced the lambda with a guarded method `_on_movie_frame` wrapping `self.update()` in `try/except RuntimeError`.
- Also added `_settings_overlay` to the `_rebuild` delete list (was missing — leaked across re-presents, stale nav confinement).

**Add-game modal — suggestion chooser (`launcher_pyqt/add_game_modal.py`):**
- `_suggest_candidates(exe_path)` returns up to 3 `(label, name)` tuples (exe stem, dir name, parent name) with dedup and generic-stem filtering.
- After exe Browse when NAME is empty: a `QFrame` suggestion row appears with "Did you mean:" hint + clickable pill buttons for each candidate. Clicking fills the name and hides the row. Typing manually hides the row.
- `_on_name_changed(text)` hides suggestions as soon as the user types anything (text non-empty).
- `spin()` between `bc.setText()` and button queries in the test harness to flush `deleteLater()` deferred deletions (old buttons must be gone before `findChildren`).

**BrowsePoster hover visibility (`views/home.py`):**
- `BrowsePoster.paintEvent` now paints `SURFACE_HOVER` background when `_focused` (was always `SURFACE`), and "ALL GAMES" text uses `TXT_MAIN` when focused (was always `TXT_DIM`). The accent squares, focus ring, and zoom animation were already working; the fix makes the hover state visually distinct from idle.

**Tabs premium styling (`launcher_pyqt/ui.py`):**
- Tab labels changed to uppercase (`HOME`, `LIBRARY`, `TOOLS`, `SETTINGS`) for a cleaner look.
- Active tab: transparent background + bold `TXT_MAIN` text + `2px solid ACCENT` bottom border (was a filled ACCENT pill). Inactive tab: transparent bg + `TXT_DIM` + `2px solid transparent` bottom border; hover shows `BORDER` underline + `TXT_MAIN` text. Narrower padding (`6px 16px`, `border-radius: 4px`) for a tighter, more modern feel.

**Battery/time header pill (`app.py._create_header`):**
- Wrapped battery, controller battery, and clock labels in a `QFrame` pill (`BG_INPUT` bg, `BORDER` border, `border-radius: 14px`, 10px horizontal padding). Labels are now children of `_header_right`, not `_header`. m1 test updated to check `_lbl_clock.parent() is w._header_right`.

**LiveSplit compact (`views/livesplit_view.py`):**
- Reduced root margins (30/12), spacing (10), card padding (10px). Title shortened to "LIVESPLIT" (was "LIVESPLIT MANAGEMENT"), font 18px. Status/conn labels in a horizontal row instead of stacked. Launch button shorter (fixedHeight 34). STOP button restyled to transparent+colored-border (matching dashboard DELETE style). Hotkey action labels fixed-width 90px, key-btn font 11px, min-width 70px.

**Testing:** m9_test 35/35, m1 updated (`_header_right`), full regression 270 total green (m1 33, m2 21, m3 42, m4_smoke 29, m6 26, m7 41, q1 15, q2 13, q4 15, m9 35).

**Post-sweep touches:**
- **BrowsePoster (`views/home.py`):** when focused (controller hover), the tile paints solid `ACCENT` with no grid icon, no "ALL GAMES" text — just a clean accent-colored block with a white `ON_ACCENT` focus ring. Unfocused state unchanged (SURFACE bg + icon + label).
- **Dashboard Y (`app.py._kb_favorite`):** opens the `ArtOverlay` panel (`view._open_art`) instead of `browse_artwork` directly, matching the new artwork wrapper pattern. Guarded against `art_overlay_open` to prevent double-open. m7 test updated: checks `view.art_overlay_open` instead of mocking `browse_artwork`.

**Testing:** full regression 271 total green (m7 updated for Y→overlay). AGENTS.md M9 notes updated.

### Session 2026-08-04 (post-M9 polish)

**BrowsePoster simplification (`views/home.py`):**
- Replaced custom grid-icon paint with a static image (`resources/HOME_ALLGAMES.png`) via `_load_browse_pixmap()` singleton. Same zoom/ring/badge behavior as HomePoster; fallback to "ALL GAMES" text when image missing.

**Startup view:**
- Changed initial view from `show_library()` to `show_home()` (`app.py`).

**README.md:**
- Updated project structure to reflect current files: added `home.py`, `add_game_modal.py`, `quick_settings.py`, `ui.py`; updated view descriptions.

**AGENTS.md cleanup:**
- Architecture section updated: CustomTkinter/CTkFrame/pygame references replaced with PyQt6 equivalents. Key Patterns cleaned of stale CTk* widget notes. Legacy `launcher/` directory noted as unused.

**NOTE:** Headless test harnesses in `/tmp/opencode/` (`m1_test.py`, `m2_test.py`, etc.) were written during the CustomTkinter era and assume library as startup view + grid-mode nav. They need rewriting to match the current Home-startup + list-mode-first architecture if tests are desired again.

### Session 2026-08-09 (Home carousel fill + ambient backdrop + smooth scroll)

**Carousel fills the view height (`views/home.py`):**
- Poster size is now height-driven, not width-only. `_carousel_sizes()` = `ch = clamp(220, avail*0.55, 430)` where `avail = _avail_carousel_h()` (existing carousel height, else `view.height()-155`; 155 = title 32 + label 15 + A-Z 32 + margins 40 + spacing 36, verified constant); `cw = min(ch/1.4, content_w//5)`, re-`ch = cw*1.4` when width-capped (keeps ~1.4 aspect). Handheld 800×800 → 160×224, external 1920×1040 → 307×430 (was capped 180×252 → dead space).
- `_build_carousel(cw, ch)` extracted from `_build`; `_build` nulls stale `_carousel_area/_inner/_ch_used` after `_clear_layout` (deleteLater safety).
- **Reflow on resize**: `resizeEvent` → `QTimer.singleShot(0, _reflow_carousel)`; skips when `|new_ch - _ch_used| <= 8` (no oscillation); preserves focused game via `engine.rescan(priority_widget=<same-game_id new poster>)`.
- **Vertical centering**: `_center_carousel` sets `inner.setFixedHeight(_avail_carousel_h())` (stable measure, not transient viewport) + `AlignVCenter` on `row.addWidget`; plus a `QScrollArea` resize **event filter** (`eventFilter`, `QEvent.Type.Resize`) keeps inner height synced to viewport.
- **Steam-style ambient backdrop (`HomeBackdrop`)**: full-view blurred art of the focused game behind the whole Home tab. `WA_TransparentForMouseEvents`, created once in `__init__` (persists across rebuilds/round-trips), `lower()` + geometry in `_build`/`resizeEvent`. Blur = cheap downscale-to-220px upsample (no QGraphicsBlurEffect), cached per `game_id` on the instance. `fade` pyqtProperty + 180ms OutCubic paint-driven crossfade (no opacity-effect buffer); art at `fade*0.5` brightness + `BG_MAIN` alpha-175 scrim for readability. Source `art_land` or `art`; missing file / BrowsePoster / tabs → fade to plain `BG_MAIN`. `stop_animations` on `hideEvent`.
- **Smooth horizontal scroll**: `_scroll_to_poster` (mirrors library `scroll_to_item` on the horizontal scrollbar, margin 28) + `_animate_h_scroll` (180ms OutCubic on `horizontalScrollBar().value`).

**Focus hook (`input_engine.py` + `app.py`):**
- `sync_visuals` calls `app._on_nav_focus(target)` (getattr-guarded) after target resolution — fires for controller nav, mouse hover, AND rescan (so backdrop initializes on view entry).
- `app._on_nav_focus` forwards to `current_view()._on_nav_focus(widget)` if present (library/others no-op).
- `HomeView._on_nav_focus` → backdrop update + `_scroll_to_poster`. `_ensure_scrolled` special-cases `view_state == "home"` + `hasattr(game_id)` → routes to `view._scroll_to_poster` (animated) instead of instant `ensureWidgetVisible`; all other views unchanged.

**Testing:** `/tmp/opencode/homefill_probe.py` (sizes/reflow/focus-preserve/idempotency), `/tmp/opencode/home_backdrop_probe.py` (backdrop attr/geo, focus flow, blur-cache reuse, BrowsePoster clears, vertical centering, animated h-scroll fully-visible end state, hideEvent, resize geo) — all PASS. Regression probe: rescan-driven backdrop, home↔library↔home round-trip keeps same view+backdrop instance, library grid nav intact (15), reflow idempotent (ch stable, 10 posters), engine-driven focus swaps art. Empty-library path unaffected. NOTE: offscreen top-level resize delivery is flaky — when a probe needs settled geometry, call `_center_carousel()`/`_reflow_carousel()` explicitly and re-collect widgets after any reflow (rebuilt rows delete old posters/inner).

**Lag + sharp-corner fixes:**
- **Lag cause**: backdrop re-scaled the 220px blur to full-view size with smooth upsampling on EVERY paint frame during a crossfade (~11 frames per nav), and restarted the fade even when the focused game hadn't changed (mouse hover / rescan re-entry). Fix: `_scaled_for()` caches the view-size scaled pixmap keyed by the **viewport size that produced it** (`_scaled_vw == (w, h)` — NOT the pixmap dims, which never equal the viewport because KeepAspectRatioByExpanding crops: 1920×942 viewport → 1920×1073 pixmap). `set_game` no-ops when `target is self._art` (no fade restart on repeated sync_visuals); `invalidate_cache()` clears on resizeEvent; `WA_OpaquePaintEvent` skips Qt's pre-paint erase (paint fills every pixel: BG_MAIN + scrim).
- **Sharp bottom corners (FeaturedPoster pre-existing, HomePoster copied it)**: scrim + name were drawn AFTER `p.setClipping(False)`, so the square-bottom scrim fillRect painted over the rounded corners. Fix: keep the clip active through scrim + title, move `p.setClipping(False)` to after the name block (badge/focus-ring stay unclipped, drawn on top). Same in BrowsePoster (no scrim there, unchanged).
- **Probe gotcha**: `paintEvent(None)`/direct `grab()` on unshown widgets paints nothing offscreen — render via `QWidget.render(QPainter(pixmap))`. And an unfocused poster (zoom 0.92) only paints the centered 92% rect, so corner samples land in transparent margins — set `p._zoom = 1.0` before pixel-probing corners. Scrim verification: corners alpha < 60 (transparent), center-bottom + top > 100 (scrim + art).
- **Verified**: `/tmp/opencode/corner_check.py` (both posters clip scrim; corners 0, center 255), `/tmp/opencode/backdrop_cache.py` (scaled cache hit on repeat paint, invalidate clears, re-scale correct, missing art stays plain), plus full regressions: home_backdrop_probe, homefill_probe, all PASS.

### Session 2026-08-09 (launch UX: deleted-exe guard, launching phase, cancel, grace-window minimize)

**Deleted-exe / no-exe / missing-proton guards (`launcher_pyqt/game_process.py` `try_launch`):**
- All pre-checks now run synchronously BEFORE mutating state (`is_playing`/`launching`/PLAY→STOP). Script games (`data['script']`) bypass the exe check (base_scripts provide the exe). Missing `exe` → toast "No executable is set for this game."; non-existent exe file → toast "Executable not found:\n<path>"; bogus proton (non-empty, not `Default (UMU Internal)`, not in `proton_paths`) → toast "Proton not found: <name>". Previously the missing exe only surfaced after launch as a silent insta-exit with a confusing STOP button.

**Launching phase + cancel:**
- State machine: `is_playing` (broad) + new `launching` (during spawn/grace). `launching=True` → dashboard `play_btn` = amber `LAUNCHING…`. New `LaunchStatusOverlay` (`launcher_pyqt/launch_status.py`, child of `app._content_area`, dim backdrop, centered panel, game name, indeterminate QProgressBar spinner, 12px status msg, amber "Press again to cancel" hint) — decorative (`WA_TransparentForMouseEvents`), shown before the spawn thread via `app.launch_status`. First-run (prefix missing `drive_c`) shows "First run detected — creating prefix. This can take a few minutes…". Pressing play while `launching` → `cancel_launch()`: sets `_cancel_event`, terminates via the grace loop, toast "Launch cancelled" (worker skips the duplicate failure toast on cancel).

**Grace-window minimize (deferred, spawn-health-gated):**
- Old code `QTimer.singleShot(500, app.showMinimized)` fired regardless of spawn health. New: after `Popen`, grace loop polls the child — normal launch waits until alive for `_GRACE_SECONDS=2.0` (re-check `poll()` every 0.25s); first-run waits up to `_FIRST_RUN_CAP=120.0s`, breaking early when `prefix/drive_c` appears; failure or cancel → NO minimize. Only on success: PLAY→STOP, hide overlay, `showMinimized()`.

**CRITICAL Qt threading fix — `QTimer.singleShot` from a plain `threading.Thread` NEVER fires:**
- Root cause of the "minimize never happened" symptom: `_run_process` runs in a daemon thread with no Qt event loop, so `QTimer.singleShot(0, ...)` posted there is created with the worker thread's affinity and is never delivered (launch probe showed `launching=False` in the worker yet minimized/overlay/button all stuck). `GameProcessManager` is now a `QObject` with three `pyqtSignal`s — `launch_ready`, `launch_failed(str)`, `launch_finished` — emitted from the worker and self-connected to main-thread handlers (`_on_launch_ready` → stop btn + hide overlay + `showMinimized`; `_on_launch_failed` → toast; `launch_finished` → `_reset_ui`). Queued cross-thread signals ARE delivered by `processEvents()`; singleShot from the worker is not. Same pattern as the pfx_creator pyqtSignal fix.

**Testing:** `/tmp/opencode/launch_probe.py` 6 tests PASS (deleted-exe toast+no-state, no-exe toast, launching overlay+button, grace→minimize+STOP, stop→PLAY, spawn-fail→error toast+no-minimize, cancel→terminate+PLAY, first-run drive_c early-break+minimize). Regressions green: `/tmp/opencode/homefill_probe.py` + `/tmp/opencode/home_backdrop_probe.py` (run with W H args). Probe gotchas: patch `gpmod.subprocess.Popen` AFTER `LauncherWindow()` (SoundManager's `subprocess.run` needs a real Popen during construction); fake must support `poll/terminate/kill/wait`; `try_launch` honors the 2s `launch_lock` cooldown — clear `gpm.launch_lock = False` between launches or wait 2.2s; `_reset_ui` rebuilds the dashboard on natural-exit/failure (`rgid == current_game_id`) so re-fetch `w.play_btn` after async completion instead of caching it (cached ref = deleted C++ object).

**Bug fix — toasts never displayed (`launcher_pyqt/toast.py`):**
- Root cause: `ToastManager.show` created `QLabel(message, parent)` but never called `show()` — a parented widget starts hidden and `raise_()` only reorders siblings, so every toast (incl. the new exe/proton guards, "Launch cancelled", pfx_creator, etc.) silently never rendered. Fix: `toast.show()` after `raise_()`. Verified via `/tmp/opencode/toast_probe.py` (visible, opacity→1.0, non-transparent pixel at toast bounds). Toast messages for missing/bogus exe now include the game name + "Update it in Game Settings" hint (not just the bare path).

### Session 2026-08-28 (system tray on launch, controller exclusive to game)

**Problem:** the launcher minimized (not hid) on game launch, and `QWidget.isVisible()` returns True for a minimized window — so `UmuInputEngineQt.update()` kept polling `/dev/input/js*` and navigating the launcher while the game was running, fighting the game for controller input.

**System tray (`app.py`):**
- `_setup_tray()` (called in `__init__`): `QSystemTrayIcon` with the `resources/logo.png` pixmap, tray context menu with "Show Launcher" (→ `restore_from_tray`) + "Quit" (→ `close`), and single-click activation (Trigger) restores. Guarded by `QSystemTrayIcon.isSystemTrayAvailable()` — offscreen/test and trays-less WMs get `self._tray = None` and the app just falls back to hide/show.
- `hide_to_tray()`: `self.hide()` + `self.engine.stop()` + `self._tray.show()`. Hiding (not minimizing) makes `isVisible()` → False, so the input engine's `update()` short-circuits at its `isVisible()` guard; additionally stopping the QTimer guarantees the controller never drives the launcher while a game runs.
- `restore_from_tray()`: hide tray icon, `engine.start()` (no-op if already running — safe for failed-launch paths), then `showNormal()` + `raise_()` + `activateWindow()`.

**Wiring (`game_process.py`):** `_on_launch_ready` → `app.hide_to_tray()` (was `showMinimized`); `_reset_ui` end → `app.restore_from_tray()` (was `showNormal`+`raise_`+`activateWindow`). Both wrapped in try/except RuntimeError.

**Testing:** `tests/tray_probe.py` (offscreen): fake Popen → launch leaves window hidden + engine stopped + `is_playing`; fake process death → window restored + engine running + `is_playing` False. NOTE: offscreen `isSystemTrayAvailable()` is False, so the tray icon itself isn't exercised offscreen — only the hide/restore + engine controller-exclusivity mechanics (assert `not w.engine._timer.isActive()` while hidden). Tray icon only verifiable on real hardware.

## Test harnesses (`tests/`)

- Probe harnesses live in `tests/` (run offscreen: `QT_QPA_PLATFORM=offscreen python tests/<probe>.py`). See `tests/README.md` for conventions.
- Only `tests/tray_probe.py` is currently maintained/migrated here; the many older probes referenced in the session notes below (`/tmp/opencode/*.py` — `m1_test`–`m9_test`, `q1/q2/q4`, `smoke`, `osk*`, `homefill_probe`, `home_backdrop_probe`, `launch_probe`, `toast_probe`, overlay/sidebar/growth/editor tests, etc.) were **transient harnesses written during feature work and were not migrated** — those `/tmp/opencode/` file references are historical records, not live files, and the CustomTkinter-era ones (per the note at line ~513) also assume a pre-Home-startup architecture.
