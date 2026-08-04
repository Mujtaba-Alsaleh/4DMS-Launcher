import os
import pathlib
import shutil


class ArtworkManager:
    def __init__(self, artwork_dir):
        self.artwork_dir = pathlib.Path(artwork_dir)

    @staticmethod
    def _key_art_key(key):
        return "art_land" if key == "art_land" else "art"

    def _dest_path(self, game_id, file_path, key):
        ext = pathlib.Path(file_path).suffix or ".png"
        suffix = "_land" if key == "art_land" else ""
        return self.artwork_dir / f"{game_id}{suffix}{ext}"

    def select(self, game_id, file_path, games, save_fn, key="art"):
        if not game_id or not file_path:
            return
        art_key = self._key_art_key(key)
        old_art_path = games[game_id].get(art_key)
        if old_art_path and os.path.exists(old_art_path):
            try:
                os.remove(old_art_path)
            except Exception as e:
                print(f"Cleanup failed: {e}")
        dest_path = self._dest_path(game_id, file_path, art_key)
        shutil.copy2(file_path, dest_path)
        games[game_id][art_key] = str(dest_path)
        save_fn(games)

    def remove(self, game_id, games, save_fn, key="art"):
        if not game_id:
            return
        art_key = self._key_art_key(key)
        art_path = games[game_id].get(art_key)
        if art_path and os.path.exists(art_path):
            try:
                os.remove(art_path)
            except Exception as e:
                print(f"Cleanup failed: {e}")
        games[game_id][art_key] = ""
        save_fn(games)

    def clear_all(self, games, save_fn):
        if self.artwork_dir.exists():
            for file in self.artwork_dir.iterdir():
                if file.is_file():
                    try:
                        file.unlink()
                    except Exception as e:
                        print(f"Error deleting {file}: {e}")
        for g_id in games:
            if isinstance(games[g_id], dict):
                for k in ("art", "art_land"):
                    if k in games[g_id]:
                        games[g_id][k] = ""
        save_fn(games)
