import hmac
from fastapi import Header, HTTPException
from app.settings import settings

def require_api_key(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    if not hmac.compare_digest(authorization[7:].strip(), settings.action_api_key):
        raise HTTPException(401, "Invalid action API key")
