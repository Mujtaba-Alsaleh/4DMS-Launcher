import os
import pathlib
import shutil


class ArtworkManager:
    def __init__(self, artwork_dir):
        self.artwork_dir = artwork_dir

    def select(self, game_id, file_path, games, save_fn):
        """Opens file dialog, copies image, deletes old version, and updates JSON."""
        if not game_id or not file_path:
            return

        old_art_path = games[game_id].get("art")
        if old_art_path and os.path.exists(old_art_path):
            try:
                os.remove(old_art_path)
            except Exception as e:
                print(f"Cleanup failed: {e}")

        ext = pathlib.Path(file_path).suffix
        local_filename = f"{game_id}{ext}"
        dest_path = self.artwork_dir / local_filename

        shutil.copy2(file_path, dest_path)
        games[game_id]["art"] = str(dest_path)
        save_fn(games)

    def remove(self, game_id, games, save_fn):
        """Deletes art, and updates JSON."""
        if not game_id:
            return

        art_path = games[game_id].get("art")
        if art_path and os.path.exists(art_path):
            try:
                os.remove(art_path)
            except Exception as e:
                print(f"Cleanup failed: {e}")

        games[game_id]["art"] = ""
        save_fn(games)

    def clear_all(self, games, save_fn):
        """Deletes every image in the Artwork folder and resets JSON entries."""
        if self.artwork_dir.exists():
            for file in self.artwork_dir.iterdir():
                if file.is_file():
                    try:
                        file.unlink()
                    except Exception as e:
                        print(f"Error deleting {file}: {e}")

        for g_id in games:
            if isinstance(games[g_id], dict) and "art" in games[g_id]:
                games[g_id]["art"] = ""

        save_fn(games)
        print("Storage Cleared: All artwork deleted.")
