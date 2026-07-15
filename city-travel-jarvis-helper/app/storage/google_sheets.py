import base64
import io
import json
from typing import Any

from app.settings import settings
from app.storage.base import Storage

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_MIME = "application/vnd.google-apps.folder"


def col(index: int) -> str:
    value = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        value = chr(65 + rem) + value
    return value


def find_header(values: list[list[Any]]) -> int:
    for i, row in enumerate(values[:12]):
        if len([x for x in row if x not in (None, "")]) >= 2:
            return i
    raise RuntimeError("Sheet has no table header row in the first 12 rows")


def _http_error_detail(exc: Exception) -> str:
    content = getattr(exc, "content", b"")
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    try:
        payload = json.loads(content or "{}")
        return str(payload.get("error", {}).get("message") or exc)
    except Exception:
        return str(exc)


class GoogleSheetsStorage(Storage):
    def __init__(self):
        from google.oauth2.service_account import Credentials as ServiceAccountCredentials
        from googleapiclient.discovery import build

        if not settings.google_spreadsheet_id:
            raise RuntimeError("GOOGLE_SPREADSHEET_ID is required")

        raw = settings.google_service_account_json or (
            base64.b64decode(settings.google_service_account_json_b64).decode()
            if settings.google_service_account_json_b64
            else ""
        )
        if not raw:
            raise RuntimeError("Google service account JSON is required")

        service_account_info = json.loads(raw)
        sheets_creds = ServiceAccountCredentials.from_service_account_info(
            service_account_info, scopes=SHEETS_SCOPES
        )
        self.sheets = build("sheets", "v4", credentials=sheets_creds, cache_discovery=False)

        self.drive_auth_mode = settings.google_drive_auth_mode
        if self.drive_auth_mode in {"user_oauth", "oauth", "user"}:
            from google.oauth2.credentials import Credentials as UserCredentials

            required = {
                "GOOGLE_DRIVE_OAUTH_CLIENT_ID": settings.google_drive_oauth_client_id,
                "GOOGLE_DRIVE_OAUTH_CLIENT_SECRET": settings.google_drive_oauth_client_secret,
                "GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN": settings.google_drive_oauth_refresh_token,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise RuntimeError("Missing Drive OAuth variables: " + ", ".join(missing))

            drive_creds = UserCredentials(
                token=None,
                refresh_token=settings.google_drive_oauth_refresh_token,
                token_uri=settings.google_drive_oauth_token_uri,
                client_id=settings.google_drive_oauth_client_id,
                client_secret=settings.google_drive_oauth_client_secret,
                scopes=DRIVE_SCOPES,
            )
            self.drive_auth_mode = "user_oauth"
        else:
            drive_creds = ServiceAccountCredentials.from_service_account_info(
                service_account_info, scopes=DRIVE_SCOPES
            )
            self.drive_auth_mode = "service_account"

        self.drive = build("drive", "v3", credentials=drive_creds, cache_discovery=False)
        self.id = settings.google_spreadsheet_id
        self.folder = settings.google_drive_folder_id

    def vals(self, range_name: str) -> list[list[Any]]:
        return (
            self.sheets.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.id,
                range=range_name,
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="FORMATTED_STRING",
            )
            .execute()
            .get("values", [])
        )

    def _table(self, sheet: str):
        values = self.vals(f"'{sheet}'")
        if not values:
            raise RuntimeError(f"Sheet {sheet} is empty")
        i = find_header(values)
        return values, i, [str(x) for x in values[i]]

    def header_info(self, sheet: str):
        values = self.vals(f"'{sheet}'!1:12")
        if not values:
            raise RuntimeError(f"Sheet {sheet} has no rows")
        i = find_header(values)
        return [str(x) for x in values[i]], i + 1

    def read_rows(self, sheet: str):
        values, i, headers = self._table(sheet)
        out = []
        for row in values[i + 1 :]:
            padded = row + [None] * (len(headers) - len(row))
            if any(x not in (None, "") for x in padded):
                out.append(dict(zip(headers, padded)))
        return out

    def append_rows(self, sheet: str, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        headers, _ = self.header_info(sheet)
        vals = [[r.get(h, "") for h in headers] for r in rows]
        (
            self.sheets.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.id,
                range=f"'{sheet}'!A1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": vals},
            )
            .execute()
        )
        return len(rows)

    def append_many(self, batches: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
        data = []
        counts = {}
        for sheet, rows in batches.items():
            if not rows:
                continue
            current = self.vals(f"'{sheet}'")
            i = find_header(current)
            headers = [str(x) for x in current[i]]
            start = len(current) + 1
            end = start + len(rows) - 1
            data.append(
                {
                    "range": f"'{sheet}'!A{start}:{col(len(headers) - 1)}{end}",
                    "values": [[r.get(h, "") for h in headers] for r in rows],
                }
            )
            counts[sheet] = len(rows)
        if data:
            (
                self.sheets.spreadsheets()
                .values()
                .batchUpdate(
                    spreadsheetId=self.id,
                    body={"valueInputOption": "USER_ENTERED", "data": data},
                )
                .execute()
            )
        return counts

    def replace_rows(self, sheet: str, rows: list[dict[str, Any]]) -> int:
        headers, header_row = self.header_info(sheet)
        first = header_row + 1
        (
            self.sheets.spreadsheets()
            .values()
            .clear(spreadsheetId=self.id, range=f"'{sheet}'!A{first}:ZZ", body={})
            .execute()
        )
        if rows:
            (
                self.sheets.spreadsheets()
                .values()
                .update(
                    spreadsheetId=self.id,
                    range=f"'{sheet}'!A{first}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [[r.get(h, "") for h in headers] for r in rows]},
                )
                .execute()
            )
        return len(rows)

    def update_matching_rows(
        self, sheet: str, key: str, value: object, updates: dict[str, object]
    ) -> int:
        values, i, headers = self._table(sheet)
        if key not in headers:
            return 0
        key_index = headers.index(key)
        requests = []
        count = 0
        for row_num, row in enumerate(values[i + 1 :], i + 2):
            current = row[key_index] if key_index < len(row) else ""
            if str(current) != str(value):
                continue
            for field, new_value in updates.items():
                if field in headers:
                    requests.append(
                        {
                            "range": f"'{sheet}'!{col(headers.index(field))}{row_num}",
                            "values": [[new_value]],
                        }
                    )
            count += 1
        if requests:
            (
                self.sheets.spreadsheets()
                .values()
                .batchUpdate(
                    spreadsheetId=self.id,
                    body={"valueInputOption": "USER_ENTERED", "data": requests},
                )
                .execute()
            )
        return count

    def drive_status(self) -> dict[str, Any]:
        if not self.folder:
            return {
                "ready": False,
                "auth_mode": self.drive_auth_mode,
                "code": "DRIVE_FOLDER_ID_MISSING",
                "detail": "GOOGLE_DRIVE_FOLDER_ID is required for exports",
            }

        try:
            folder = (
                self.drive.files()
                .get(
                    fileId=self.folder,
                    fields="id,name,mimeType,driveId,capabilities(canAddChildren)",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:
            return {
                "ready": False,
                "auth_mode": self.drive_auth_mode,
                "code": "DRIVE_FOLDER_UNAVAILABLE",
                "detail": _http_error_detail(exc),
            }

        if folder.get("mimeType") != FOLDER_MIME:
            return {
                "ready": False,
                "auth_mode": self.drive_auth_mode,
                "code": "DRIVE_TARGET_NOT_FOLDER",
                "detail": "GOOGLE_DRIVE_FOLDER_ID does not point to a folder",
                "folder": folder,
            }

        if not folder.get("capabilities", {}).get("canAddChildren", False):
            return {
                "ready": False,
                "auth_mode": self.drive_auth_mode,
                "code": "DRIVE_FOLDER_NOT_WRITABLE",
                "detail": "Configured identity cannot create files in the target folder",
                "folder": folder,
            }

        # A service account can upload into a Shared Drive, but cannot own files
        # in a human user's My Drive because service accounts have no quota.
        if self.drive_auth_mode == "service_account" and not folder.get("driveId"):
            return {
                "ready": False,
                "auth_mode": self.drive_auth_mode,
                "code": "DRIVE_SERVICE_ACCOUNT_MY_DRIVE_UNSUPPORTED",
                "detail": (
                    "The folder is in My Drive. Configure user_oauth for Drive exports "
                    "or move the folder to a Shared Drive."
                ),
                "folder": folder,
            }

        return {
            "ready": True,
            "auth_mode": self.drive_auth_mode,
            "code": "OK",
            "detail": "Drive export folder is accessible and writable",
            "folder": folder,
        }

    def upload_file(self, name: str, mime_type: str, content: bytes) -> str:
        status = self.drive_status()
        if not status.get("ready"):
            raise RuntimeError(f"{status.get('code')}: {status.get('detail')}")

        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
        obj = (
            self.drive.files()
            .create(
                body={"name": name, "parents": [self.folder]},
                media_body=media,
                fields="id,webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )
        return obj.get("webViewLink") or f"https://drive.google.com/file/d/{obj['id']}/view"
