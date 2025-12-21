from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .uploader_base import UploadResult, UploaderBase


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


@dataclass
class YouTubeConfig:
    credentials_json: Path
    token_json: Path
    privacy_status: str
    category_id: str | None


class YouTubeUploader(UploaderBase):
    def __init__(self, config: YouTubeConfig) -> None:
        self.config = config
        self.client = self._build_client()

    def _build_client(self):
        creds = None
        if self.config.token_json.exists():
            creds = Credentials.from_authorized_user_file(
                str(self.config.token_json), SCOPES
            )
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.config.credentials_json), SCOPES
                )
                creds = flow.run_local_server(port=0)
            self.config.token_json.parent.mkdir(parents=True, exist_ok=True)
            self.config.token_json.write_text(creds.to_json(), encoding="utf-8")
        return build("youtube", "v3", credentials=creds)

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str] | None,
        privacy_status: str,
        category_id: str | None,
    ) -> UploadResult:
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": category_id or self.config.category_id or "10",
            },
            "status": {"privacyStatus": privacy_status or self.config.privacy_status},
        }
        if tags:
            body["snippet"]["tags"] = tags
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        request = self.client.videos().insert(
            part="snippet,status", body=body, media_body=media
        )
        response = None
        while response is None:
            _, response = request.next_chunk()
        return UploadResult(video_id=response.get("id"), raw_response=response)

    def set_thumbnail(self, video_id: str, thumbnail_path: Path) -> None:
        suffix = thumbnail_path.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            mimetype = "image/jpeg"
        else:
            mimetype = "image/png"
        media = MediaFileUpload(str(thumbnail_path), mimetype=mimetype, resumable=False)
        request = self.client.thumbnails().set(videoId=video_id, media_body=media)
        request.execute()
