import time, uuid
from typing import Any
from fastapi import HTTPException
from app.settings import settings

class PreviewStore:
    def __init__(self): self.data: dict[str, tuple[float, dict[str, Any]]] = {}; self.consumed: set[str] = set()
    def put(self, payload: dict[str, Any]) -> str:
        pid = "PRE-" + uuid.uuid4().hex[:14]; self.data[pid] = (time.time() + settings.preview_ttl_seconds, payload); return pid
    def get(self, pid: str) -> dict[str, Any]:
        if pid in self.consumed: raise HTTPException(409, "Preview already committed")
        item = self.data.get(pid)
        if not item or item[0] < time.time(): self.data.pop(pid, None); raise HTTPException(410, "Preview expired or service restarted")
        return item[1]
    def consume(self, pid: str) -> dict[str, Any]:
        payload = self.get(pid); self.data.pop(pid, None); self.consumed.add(pid); return payload
preview_store = PreviewStore()
