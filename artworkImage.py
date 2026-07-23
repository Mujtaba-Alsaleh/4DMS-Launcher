import customtkinter as ctk
from PIL import Image, ImageSequence, ImageTk
import os
import gc

class GameImage(ctk.CTkCanvas):
    """
    A single-threaded CustomTkinter widget that compresses and loops heavy WebPs.
    Hardened against RAM leaks and destruction conflicts without breaking Tkinter internals.
    """
    def __init__(self, master, file_path, width=250, height=350, quality=45, **kwargs):
        bg = "#2B2B2B"
        if "bg" not in kwargs:
            try:
                val = master.cget("fg_color")
                if val and val != "transparent":
                    bg = val
            except Exception:
                pass
        kwargs.setdefault("bg", bg)
        super().__init__(
            master,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            **kwargs
        )

        self.original_path = file_path
        self.width = width
        self.height = height
        self.quality = quality

        base, ext = os.path.splitext(file_path)
        self.optimized_path = f"{base}_lowram{ext}"

        self.is_playing = False
        self._canvas_img_id = None
        self._current_photo = None
        self._loop_id = None
        self._img_stream = None
        self._img_stream = None

        # Bind the destruction handle
        self.bind("<Destroy>", self._on_destroy)

        if not os.path.exists(self.optimized_path):
            self.after(10, self._compress_asset)

    def _compress_asset(self):
        try:
            with Image.open(self.original_path) as img:
                frames = []
                durations = []
                for i, frame in enumerate(ImageSequence.Iterator(img)):
                    if i % 2 == 0:
                        resized_frame = frame.copy().resize(
                            (self.width, self.height),
                            Image.Resampling.BILINEAR
                        )
                        frames.append(resized_frame)
                        durations.append(frame.info.get('duration', 100) * 2)

                if frames:
                    frames[0].save(
                        self.optimized_path,
                        save_all=True,
                        append_images=frames[1:],
                        duration=durations,
                        loop=img.info.get('loop', 0),
                        optimize=True,
                        quality=self.quality,
                        lossless=False
                    )
            self.start()
        except Exception as e:
            print(f"Compression error: {e}")

    def start(self):
        if not self.is_playing and os.path.exists(self.optimized_path):
            self.is_playing = True
            try:
                self._resize_to_parent()
                self._img_stream = Image.open(self.optimized_path)
                self._frame_idx = 0
                self._animate_next_frame()
            except Exception as e:
                print(f"Failed to start streaming context: {e}")

    def _resize_to_parent(self):
        try:
            pw = self.master.winfo_width()
            ph = self.master.winfo_height()
            if pw > 1 and ph > 1:
                self.width = pw
                self.height = ph
                self.configure(width=pw, height=ph)
        except Exception:
            pass

    def _animate_next_frame(self):
        if not self.is_playing or not self.winfo_exists():
            self.stop()
            return

        try:
            self._img_stream.seek(self._frame_idx)
            duration = self._img_stream.info.get('duration', 100)

            frame = self._img_stream.copy()
            if frame.size != (self.width, self.height):
                frame = frame.resize((self.width, self.height), Image.Resampling.BILINEAR)
            photo = ImageTk.PhotoImage(frame)

            self._draw_frame(photo)
            self._frame_idx += 1

            self._loop_id = self.after(duration, self._animate_next_frame)

        except EOFError:
            if self.is_playing and self._img_stream:
                loop = self._img_stream.info.get('loop', 0)
                if loop == 0:
                    self._frame_idx = 0
                    self._loop_id = self.after(1, self._animate_next_frame)
                else:
                    self.stop()
        except Exception:
            self.stop()

    def _draw_frame(self, new_photo):
        if not self.winfo_exists():
            return

        old_img_id = self._canvas_img_id
        self._canvas_img_id = self.create_image(0, 0, anchor="nw", image=new_photo)

        self._current_photo = new_photo

        if old_img_id is not None:
            self.delete(old_img_id)

    def stop(self):
        """Forcefully breaks loop binds and breaks memory hooks clean."""
        self.is_playing = False

        if getattr(self, '_loop_id', None) is not None:
            try:
                self.after_cancel(self._loop_id)
            except Exception:
                pass
            self._loop_id = None

        if getattr(self, '_img_stream', None) is not None:
            try:
                self._img_stream.close()
            except Exception:
                pass
            self._img_stream = None

        self._current_photo = None
        self._canvas_img_id = None

        if self.winfo_exists():
            try:
                self.delete("all")
            except Exception:
                pass

    def destroy(self):
        """Intercepts CustomTkinter internal component manual code-destructions."""
        self.stop()
        super().destroy()

    def lift_widget(self):
        self.tk.call('raise', self._w)

    def lower_widget(self):
        self.tk.call('lower', self._w)

    def _on_destroy(self, event):
        """Fires when Tkinter framework tears away layout slots."""
        if event.widget == self:
            self.stop()

            # SAFE LEAK PLUG: Explicitly target and delete only the large memory references
            # rather than wiping the structural Tkinter properties (_name, master, etc.)
            if hasattr(self, '_current_photo'): del self._current_photo
            if hasattr(self, '_img_stream'): del self._img_stream

            # Force immediate recovery of orphaned memory arrays
            gc.collect()
