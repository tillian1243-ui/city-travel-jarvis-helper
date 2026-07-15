import hashlib, json, math, re, uuid
from datetime import datetime, timezone
from typing import Any

def now_iso() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def new_id(prefix: str) -> str: return f"{prefix}-{uuid.uuid4().hex[:12]}"
def digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()
def norm(value: Any) -> str:
    text = str(value or "").lower().replace("ё", "е"); text = re.sub(r"[^a-zа-я0-9]+", " ", text, flags=re.I); return re.sub(r"\s+", " ", text).strip()
def num(value: Any, default: float = 0.0) -> float:
    try: return float(value)
    except (TypeError, ValueError): return default
def clamp(value: float, lo: float, hi: float) -> float: return max(lo, min(hi, value))
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r=6371.0; p1=math.radians(lat1); p2=math.radians(lat2); dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2; return 2*r*math.asin(math.sqrt(a))
