import os
from dataclasses import dataclass

def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}

@dataclass(frozen=True)
class Settings:
    action_api_key: str = os.getenv("ACTION_API_KEY", "replace-with-a-long-random-secret")
    preview_signing_secret: str = os.getenv("PREVIEW_SIGNING_SECRET", "replace-with-another-long-random-secret")
    writes_enabled: bool = _bool("WRITES_ENABLED", False)
    storage_mode: str = os.getenv("STORAGE_MODE", "memory").strip().lower()
    google_spreadsheet_id: str = os.getenv("GOOGLE_SPREADSHEET_ID", "")
    google_drive_folder_id: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    google_service_account_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    google_service_account_json_b64: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64", "")
    app_timezone: str = os.getenv("APP_TIMEZONE", "Europe/Moscow")
    home_city: str = os.getenv("HOME_CITY", "Москва")
    default_map_provider: str = os.getenv("DEFAULT_MAP_PROVIDER", "yandex")
    preview_ttl_seconds: int = int(os.getenv("PREVIEW_TTL_SECONDS", "1800"))
    max_candidates: int = int(os.getenv("MAX_PLACE_CANDIDATES", "30"))
    max_route_points: int = int(os.getenv("MAX_ROUTE_POINTS", "150"))
    auto_promote_maturity: bool = _bool("AUTO_PROMOTE_MATURITY", False)
settings = Settings()
