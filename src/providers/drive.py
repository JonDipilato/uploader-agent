from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


@dataclass
class DriveConfig:
    folder_id: str
    use_service_account: bool
    service_account_json: Path | None
    oauth_client_json: Path | None
    token_json: Path | None


class DriveClient:
    def __init__(self, config: DriveConfig) -> None:
        self.config = config
        self.service = self._build_service()

    def _build_service(self):
        if self.config.use_service_account:
            if not self.config.service_account_json:
                raise ValueError("service_account_json is required for service account auth")
            creds = service_account.Credentials.from_service_account_file(
                str(self.config.service_account_json),
                scopes=SCOPES,
            )
        else:
            creds = None
            if self.config.token_json and self.config.token_json.exists():
                creds = Credentials.from_authorized_user_file(
                    str(self.config.token_json), SCOPES
                )
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not self.config.oauth_client_json:
                        raise ValueError("oauth_client_json is required for OAuth auth")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.config.oauth_client_json),
                        SCOPES,
                    )
                    creds = flow.run_local_server(port=0)
                if self.config.token_json:
                    self.config.token_json.parent.mkdir(parents=True, exist_ok=True)
                    self.config.token_json.write_text(creds.to_json(), encoding="utf-8")
        return build("drive", "v3", credentials=creds)

    def list_mp3_files(self, ordering: str = "name") -> list[dict]:
        if ordering not in {"name", "modifiedTime"}:
            ordering = "name"
        query = (
            f"'{self.config.folder_id}' in parents "
            "and mimeType='audio/mpeg' "
            "and trashed=false"
        )
        files: list[dict] = []
        page_token = None
        while True:
            response = (
                self.service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, size, modifiedTime)",
                    orderBy=ordering,
                    pageToken=page_token,
                )
                .execute()
            )
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return files

    def download_file(self, file_id: str, dest_path: Path) -> None:
        request = self.service.files().get_media(fileId=file_id)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with dest_path.open("wb") as handle:
            downloader = MediaIoBaseDownload(handle, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

    def download_many(self, files: Iterable[dict], dest_dir: Path) -> list[Path]:
        downloaded: list[Path] = []
        for index, file_info in enumerate(files, start=1):
            safe_name = file_info["name"].replace("/", "_")
            dest_path = dest_dir / f"{index:03d}_{safe_name}"
            self.download_file(file_info["id"], dest_path)
            downloaded.append(dest_path)
        return downloaded
