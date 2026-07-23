import os
import csv
import difflib
from launcher.utils import normalize, resource_path


class UMUDatabase:
    def __init__(self):
        self.db = {}
        self.load()

    def load(self):
        csv_path = resource_path("resources/umu-database.csv")
        if not os.path.exists(csv_path):
            print("UMU Database not found!")
            return

        try:
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    norm_title = normalize(row['TITLE'])
                    norm_store = normalize(row['STORE'])
                    umu_id = row['UMU_ID']

                    self.db[f"{norm_title}|{norm_store}"] = umu_id

                    if norm_title not in self.db:
                        self.db[norm_title] = umu_id
        except Exception as e:
            print(f"Error parsing UMU CSV: {e}")

    def lookup(self, title, store="none"):
        """Search for a UMU ID based on title and store."""
        if not self.db:
            return "0"

        n_title = normalize(title)
        n_store = normalize(store)

        match = self.db.get(f"{n_title}|{n_store}")
        if match:
            return match

        match = self.db.get(n_title)
        if match:
            return match

        all_titles = [k for k in self.db.keys() if '|' not in k]
        closest = difflib.get_close_matches(n_title, all_titles, n=1, cutoff=0.7)

        if closest:
            return self.db[closest[0]]

        return "0"
