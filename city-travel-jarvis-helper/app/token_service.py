import base64, hashlib, hmac, json, time
from typing import Any
from fastapi import HTTPException
from app.settings import settings

def create_token(payload: dict[str, Any], ttl: int | None = None) -> str:
    data = dict(payload); data["exp"] = int(time.time()) + (ttl or settings.preview_ttl_seconds)
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    body = base64.urlsafe_b64encode(raw).rstrip(b"=")
    sig = hmac.new(settings.preview_signing_secret.encode(), body, hashlib.sha256).digest()
    return body.decode() + "." + base64.urlsafe_b64encode(sig).rstrip(b"=").decode()

def read_token(token: str, action: str | None = None) -> dict[str, Any]:
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(settings.preview_signing_secret.encode(), body.encode(), hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))
        if not hmac.compare_digest(expected, actual): raise ValueError("signature")
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except Exception as exc:
        raise HTTPException(400, "Invalid commit token") from exc
    if payload.get("exp", 0) < time.time(): raise HTTPException(410, "Commit token expired")
    if action and payload.get("action") != action: raise HTTPException(400, "Commit token action mismatch")
    return payload
