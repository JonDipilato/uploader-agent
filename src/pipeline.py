from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .providers.drive import DriveClient, DriveConfig
from .providers.grok import GrokClient, GrokConfig
from .providers.uploader_base import UploaderBase
from .providers.whisk import WhiskClient, WhiskConfig
from .providers.youtube_uploader import YouTubeConfig, YouTubeUploader
from .utils.ffmpeg import (
    build_drawtext_filter,
    concat_audio,
    probe_duration_seconds,
    render_image_with_text,
    render_video,
    trim_audio,
    write_concat_list,
)


@dataclass
class RunArtifacts:
    run_dir: Path
    audio_path: Path
    image_path: Path
    loop_video_path: Path
    thumbnail_path: Path | None
    output_video_path: Path


class VideoCreatorAgent:
    def __init__(self, config: dict) -> None:
        self.config = config

    def run_once(self) -> RunArtifacts:
        run_dir = self._create_run_dir()
        audio_dir = run_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        drive_cfg = self._build_drive_config()
        drive_client = DriveClient(drive_cfg)
        audio_files = drive_client.list_mp3_files(
            ordering=self._cfg("audio", "ordering", default="name")
        )
        if not audio_files:
            raise RuntimeError("No MP3 files found in the Drive folder")
        downloaded = drive_client.download_many(audio_files, audio_dir)

        playlist, total_seconds = self._build_playlist(downloaded)
        concat_list_path = run_dir / "concat.txt"
        write_concat_list(playlist, concat_list_path)

        audio_path = run_dir / "audio_full.mp3"
        concat_audio(
            concat_list_path,
            audio_path,
            codec=self._cfg("audio", "concat_codec", default="libmp3lame"),
            quality=self._cfg("audio", "concat_quality", default=2),
            bitrate=self._cfg("audio", "concat_bitrate", default=None),
        )
        total_seconds = probe_duration_seconds(audio_path)

        max_seconds = self._target_max_seconds()
        if max_seconds and total_seconds > max_seconds:
            trimmed_audio = run_dir / "audio_trimmed.mp3"
            trim_audio(
                audio_path,
                trimmed_audio,
                max_seconds=max_seconds,
                codec=self._cfg("audio", "concat_codec", default="libmp3lame"),
                quality=self._cfg("audio", "concat_quality", default=2),
                bitrate=self._cfg("audio", "concat_bitrate", default=None),
            )
            audio_path = trimmed_audio
            total_seconds = max_seconds

        image_path = self._ensure_image(run_dir)
        loop_video_path = self._ensure_loop_video(run_dir, image_path)
        overlay = self._build_text_overlay(run_dir)
        drawtext_filter = None
        thumbnail_path = None
        if overlay:
            drawtext_filter = build_drawtext_filter(
                textfile=overlay["textfile"],
                fontfile=overlay["fontfile"],
                font=overlay["font"],
                font_size=overlay["font_size"],
                font_color=overlay["font_color"],
                x=overlay["x"],
                y=overlay["y"],
                border_color=overlay["border_color"],
                border_width=overlay["border_width"],
                box_color=overlay["box_color"],
                box_borderw=overlay["box_borderw"],
                shadow_color=overlay["shadow_color"],
                shadow_x=overlay["shadow_x"],
                shadow_y=overlay["shadow_y"],
            )
            if overlay["create_thumbnail"]:
                thumbnail_path = run_dir / "thumbnail.png"
                render_image_with_text(image_path, thumbnail_path, drawtext_filter)

        output_video_path = run_dir / self._output_filename()
        render_video(
            loop_video_path,
            audio_path,
            output_video_path,
            resolution=self._cfg("video", "resolution", default="1920x1080"),
            fps=self._cfg("video", "fps", default=30),
            video_bitrate=self._cfg("video", "video_bitrate", default="4500k"),
            audio_bitrate=self._cfg("video", "audio_bitrate", default="192k"),
            duration_seconds=total_seconds,
            drawtext_filter=drawtext_filter if overlay and overlay["apply_to_video"] else None,
        )

        if self._cfg("upload", "enabled", default=True):
            uploader = self._build_uploader()
            title = self._render_template(self._cfg("upload", "title_template", default=""))
            description = self._render_template(
                self._cfg("upload", "description_template", default="")
            )
            tags = self._cfg("upload", "tags", default=None)
            upload_result = uploader.upload_video(
                output_video_path,
                title=title or output_video_path.stem,
                description=description,
                tags=tags,
                privacy_status=self._cfg("upload", "privacy_status", default="public"),
                category_id=self._cfg("upload", "category_id", default=None),
            )
            if (
                overlay
                and overlay["upload_thumbnail"]
                and thumbnail_path
                and upload_result.video_id
            ):
                try:
                    uploader.set_thumbnail(upload_result.video_id, thumbnail_path)
                except NotImplementedError:
                    pass

        return RunArtifacts(
            run_dir=run_dir,
            audio_path=audio_path,
            image_path=image_path,
            loop_video_path=loop_video_path,
            thumbnail_path=thumbnail_path,
            output_video_path=output_video_path,
        )

    def _create_run_dir(self) -> Path:
        base_dir = Path(self._cfg("project", "output_dir", default="runs"))
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = base_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _build_drive_config(self) -> DriveConfig:
        folder_id = self._cfg("audio", "drive_folder_id", required=True)
        return DriveConfig(
            folder_id=folder_id,
            use_service_account=self._cfg("drive", "use_service_account", default=True),
            service_account_json=self._path(self._cfg("drive", "service_account_json", default=None)),
            oauth_client_json=self._path(self._cfg("drive", "oauth_client_json", default=None)),
            token_json=self._path(self._cfg("drive", "token_json", default=None)),
        )

    def _build_uploader(self) -> UploaderBase:
        provider = self._cfg("upload", "provider", default="youtube")
        if provider != "youtube":
            raise ValueError(f"Unsupported upload provider: {provider}")
        return YouTubeUploader(
            YouTubeConfig(
                credentials_json=self._path(
                    self._cfg("upload", "credentials_json", required=True)
                ),
                token_json=self._path(self._cfg("upload", "token_json", required=True)),
                privacy_status=self._cfg("upload", "privacy_status", default="public"),
                category_id=self._cfg("upload", "category_id", default="10"),
            )
        )

    def _build_playlist(self, downloaded: list[Path]) -> tuple[list[Path], float]:
        durations = [probe_duration_seconds(path) for path in downloaded]
        target_min = self._target_min_seconds()
        if target_min <= 0:
            return downloaded, sum(durations)
        playlist: list[Path] = []
        total = 0.0
        index = 0
        while total < target_min:
            path = downloaded[index % len(downloaded)]
            duration = durations[index % len(durations)]
            playlist.append(path)
            total += duration
            index += 1
        return playlist, total

    def _ensure_image(self, run_dir: Path) -> Path:
        image_path = self._cfg("visuals", "image_path", default=None)
        if image_path:
            resolved = Path(image_path)
            if not resolved.exists():
                raise RuntimeError(f"Image not found: {resolved}")
            return resolved

        prompt = self._cfg("visuals", "image_prompt", default=None) or self._cfg(
            "visuals", "prompt", default=None
        )
        if not prompt:
            raise RuntimeError("visuals.image_prompt is required to generate an image")
        output_path = run_dir / "visual.png"
        whisk = WhiskClient(
            WhiskConfig(
                mode=self._cfg("visuals", "whisk_mode", default="command"),
                command=self._cfg("visuals", "whisk_command", default=None),
                api_key_env=self._cfg("visuals", "whisk_api_key_env", default=None),
                model=self._cfg("visuals", "whisk_model", default=None),
            )
        )
        whisk.generate_image(prompt, output_path)
        return output_path

    def _ensure_loop_video(self, run_dir: Path, image_path: Path) -> Path:
        loop_path = self._cfg("visuals", "loop_video_path", default=None)
        if loop_path:
            resolved = Path(loop_path)
            if not resolved.exists():
                raise RuntimeError(f"Loop video not found: {resolved}")
            return resolved

        prompt = self._cfg("visuals", "video_prompt", default=None) or self._cfg(
            "visuals", "prompt", default=None
        )
        if not prompt:
            raise RuntimeError("visuals.video_prompt is required to generate loop video")
        output_path = run_dir / "loop.mp4"
        grok = GrokClient(
            GrokConfig(
                mode=self._cfg("visuals", "grok_mode", default="command"),
                command=self._cfg("visuals", "grok_command", default=None),
                api_key_env=self._cfg("visuals", "grok_api_key_env", default=None),
                model=self._cfg("visuals", "grok_model", default=None),
            )
        )
        grok.generate_loop_video(
            image_path=image_path,
            output_path=output_path,
            prompt=prompt,
            duration_seconds=self._cfg("visuals", "loop_duration_seconds", default=5),
            fps=self._cfg("visuals", "fps", default=None)
            or self._cfg("video", "fps", default=30),
        )
        return output_path

    def _target_min_seconds(self) -> float:
        min_hours = self._cfg("audio", "target_hours_min", default=8)
        if not min_hours:
            return 0.0
        return float(min_hours) * 3600.0

    def _target_max_seconds(self) -> float | None:
        max_hours = self._cfg("audio", "target_hours_max", default=9)
        return float(max_hours) * 3600.0 if max_hours else None

    def _output_filename(self) -> str:
        base = self._cfg("project", "name", default="daily_mix")
        date_str = dt.date.today().isoformat()
        return f"{base}_{date_str}.mp4"

    def _render_template(self, template: str) -> str:
        date_str = dt.date.today().isoformat()
        return template.format(date=date_str)

    def _cfg(self, section: str, key: str, default=None, required: bool = False):
        value = self.config.get(section, {}).get(key, default)
        if required and value in (None, ""):
            raise ValueError(f"Missing config: {section}.{key}")
        return value

    def _path(self, value: str | None) -> Path | None:
        if not value:
            return None
        return Path(value)

    def _build_text_overlay(self, run_dir: Path) -> dict | None:
        overlay_cfg = self.config.get("text_overlay", {})
        text = overlay_cfg.get("text", "")
        if not text:
            return None
        textfile = run_dir / "overlay.txt"
        textfile.write_text(text, encoding="utf-8")
        return {
            "textfile": textfile,
            "fontfile": self._path(overlay_cfg.get("fontfile")),
            "font": overlay_cfg.get("font"),
            "font_size": int(overlay_cfg.get("font_size", 96)),
            "font_color": overlay_cfg.get("font_color", "white"),
            "border_color": overlay_cfg.get("outline_color", "black"),
            "border_width": int(overlay_cfg.get("outline_width", 4)),
            "box_color": overlay_cfg.get("box_color"),
            "box_borderw": int(overlay_cfg.get("box_borderw"))
            if overlay_cfg.get("box_borderw") is not None
            else None,
            "shadow_color": overlay_cfg.get("shadow_color"),
            "shadow_x": int(overlay_cfg.get("shadow_x"))
            if overlay_cfg.get("shadow_x") is not None
            else None,
            "shadow_y": int(overlay_cfg.get("shadow_y"))
            if overlay_cfg.get("shadow_y") is not None
            else None,
            "x": overlay_cfg.get("x", "(w-text_w)/2"),
            "y": overlay_cfg.get("y", "(h-text_h)/2"),
            "apply_to_video": overlay_cfg.get("apply_to_video", True),
            "create_thumbnail": overlay_cfg.get("create_thumbnail", True),
            "upload_thumbnail": overlay_cfg.get("upload_thumbnail", False),
        }
