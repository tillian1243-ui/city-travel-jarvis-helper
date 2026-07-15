from copy import deepcopy
from typing import Any
from app.storage.base import Storage

class MemoryStorage(Storage):
    def __init__(self, seed: dict[str, list[dict[str, Any]]] | None = None): self.data = deepcopy(seed or {}); self.files: dict[str, bytes] = {}
    def read_rows(self, sheet: str) -> list[dict[str, Any]]: return deepcopy(self.data.get(sheet, []))
    def append_rows(self, sheet: str, rows: list[dict[str, Any]]) -> int: self.data.setdefault(sheet, []).extend(deepcopy(rows)); return len(rows)
    def append_many(self, batches: dict[str, list[dict[str, Any]]]) -> dict[str, int]: return {k:self.append_rows(k,v) for k,v in batches.items() if v}
    def replace_rows(self, sheet: str, rows: list[dict[str, Any]]) -> int: self.data[sheet] = deepcopy(rows); return len(rows)
    def update_matching_rows(self, sheet: str, key: str, value: object, updates: dict[str, object]) -> int:
        count=0
        for row in self.data.setdefault(sheet, []):
            if str(row.get(key, "")) == str(value): row.update(deepcopy(updates)); count += 1
        return count
    def upload_file(self, name: str, mime_type: str, content: bytes) -> str: self.files[name] = bytes(content); return f"memory://{name}"
    def drive_ready(self) -> bool: return True
