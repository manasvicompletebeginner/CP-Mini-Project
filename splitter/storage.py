"""
storage.py - JSON persistence and CSV export.

UNIT IV (File Handling + Exceptions):
  * open() in read / write mode, json.load / json.dump.
  * try / except / finally: the file is always closed in `finally`,
    even if json.load() fails halfway.
  * Writes go to a temporary file first, then os.replace() swaps it in,
    so a crash mid-write never corrupts rooms_data.json.
  * csv.DictWriter writes the past-expenses export.
"""
import copy
import csv
import json
import os

from .exceptions import StorageError

EMPTY_DATA = {"rooms": {}, "users": {}}

CSV_FIELDS = ("code", "name", "activity", "date", "role", "owner",
              "my_share", "total_amount", "total_people", "split_type", "closed_at")


class JSONStorage:
    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            self.save(copy.deepcopy(EMPTY_DATA))

    def load(self):
        file = None
        try:
            file = open(self.path, "r", encoding="utf-8")
            data = json.load(file)
        except FileNotFoundError:
            data = copy.deepcopy(EMPTY_DATA)
        except json.JSONDecodeError as error:
            raise StorageError(f"{os.path.basename(self.path)} is not valid JSON: {error}") from error
        finally:
            if file is not None:
                file.close()

        data.setdefault("rooms", {})
        data.setdefault("users", {})
        return data

    def save(self, data):
        temp_path = self.path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.path)
        except OSError as error:
            raise StorageError(f"Could not save data: {error}") from error


def export_expenses_csv(rows, path, fields=CSV_FIELDS):
    """Write one CSV row per past room. Returns the number of rows written."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
    except OSError as error:
        raise StorageError(f"Could not write CSV: {error}") from error
    return len(rows)
