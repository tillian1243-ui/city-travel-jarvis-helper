"""Create a user OAuth refresh token and a dedicated Drive export folder.

This script is intentionally local-only. It opens Google's consent page in the
user's browser, creates a folder that is owned by the user, and writes Railway
variables to a local text file. It never uploads the OAuth client JSON anywhere.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_MIME = "application/vnd.google-apps.folder"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("client_secret_json", type=Path)
    parser.add_argument(
        "--folder-name",
        default="City Jarvis Files (OAuth)",
        help="Name of the dedicated folder that the app will create in My Drive.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(tempfile.gettempdir()) / "city-jarvis-drive-oauth.env",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.client_secret_json.is_file():
        raise SystemExit(f"OAuth client JSON not found: {args.client_secret_json}")

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise SystemExit(
            "Missing local OAuth packages. Run: "
            "python -m pip install --user google-auth-oauthlib google-api-python-client"
        ) from exc

    client_config = json.loads(args.client_secret_json.read_text(encoding="utf-8"))
    installed = client_config.get("installed") or client_config.get("web")
    if not installed:
        raise SystemExit("The JSON does not contain an installed or web OAuth client")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(args.client_secret_json), scopes=SCOPES
    )
    credentials = flow.run_local_server(
        port=0,
        open_browser=True,
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true",
        success_message="City Jarvis Drive access granted. You can close this tab.",
    )
    if not credentials.refresh_token:
        raise SystemExit(
            "Google did not return a refresh token. Revoke the app access and run "
            "the script again with consent, or create a new Desktop OAuth client."
        )

    drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
    folder = (
        drive.files()
        .create(
            body={"name": args.folder_name, "mimeType": FOLDER_MIME},
            fields="id,name,webViewLink",
        )
        .execute()
    )

    lines = [
        "GOOGLE_DRIVE_AUTH_MODE=user_oauth",
        f"GOOGLE_DRIVE_OAUTH_CLIENT_ID={installed['client_id']}",
        f"GOOGLE_DRIVE_OAUTH_CLIENT_SECRET={installed.get('client_secret', '')}",
        f"GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN={credentials.refresh_token}",
        f"GOOGLE_DRIVE_FOLDER_ID={folder['id']}",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(os.linesep.join(lines) + os.linesep, encoding="utf-8")

    print(f"Created Drive folder: {folder.get('name')} ({folder['id']})")
    print(f"Railway variables written to: {args.output}")
    print("Keep this file private and delete it after copying the variables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
