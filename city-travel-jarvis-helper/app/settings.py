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

    # Sheets can continue using the service account. Drive exports can use either
    # a Shared Drive via the service account or a human user's OAuth refresh token.
    google_drive_auth_mode: str = os.getenv("GOOGLE_DRIVE_AUTH_MODE", "service_account").strip().lower()
    google_drive_oauth_client_id: str = os.getenv("GOOGLE_DRIVE_OAUTH_CLIENT_ID", "").strip()
    google_drive_oauth_client_secret: str = os.getenv("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET", "").strip()
    google_drive_oauth_refresh_token: str = os.getenv("GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN", "").strip()
    google_drive_oauth_token_uri: str = os.getenv(
        "GOOGLE_DRIVE_OAUTH_TOKEN_URI", "https://oauth2.googleapis.com/token"
    ).strip()

    app_timezone: str = os.getenv("APP_TIMEZONE", "Europe/Moscow")
    home_city: str = os.getenv("HOME_CITY", "Москва")
    default_map_provider: str = os.getenv("DEFAULT_MAP_PROVIDER", "yandex")
    preview_ttl_seconds: int = int(os.getenv("PREVIEW_TTL_SECONDS", "1800"))
    max_candidates: int = int(os.getenv("MAX_PLACE_CANDIDATES", "30"))
    max_route_points: int = int(os.getenv("MAX_ROUTE_POINTS", "150"))
    auto_promote_maturity: bool = _bool("AUTO_PROMOTE_MATURITY", False)


settings = Settings()
