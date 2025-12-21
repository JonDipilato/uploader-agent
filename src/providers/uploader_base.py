from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class UploadResult:
    video_id: str | None
    raw_response: Any | None


class UploaderBase:
    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str] | None,
        privacy_status: str,
        category_id: str | None,
    ) -> UploadResult:
        raise NotImplementedError

    def set_thumbnail(self, video_id: str, thumbnail_path: Path) -> None:
        raise NotImplementedError
