from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .providers.drive import DriveClient, DriveConfig
from .providers.grok import GrokClient, GrokConfig
from .providers.openai_images import OpenAIImageClient, OpenAIImageConfig
from .providers.uploader_base import UploaderBase
from .providers.whisk import WhiskClient, WhiskConfig
from .providers.youtube_uploader import YouTubeConfig, YouTubeUploader
from .utils.ffmpeg import (
    build_drawtext_filter,
    concat_audio,
    generate_color_image,
    generate_loop_video_from_image,
    mux_chapters,
    probe_duration_seconds,
    render_image_with_text,
    render_video,
    trim_audio,
    write_ffmetadata_chapters,
    write_concat_list,
)


@dataclass
class RunArtifacts:
    run_dir: Path
    audio_path: Path
    image_path: Path
    loop_video_path: Path
    thumbnail_path: Path | None
    tracklist_path: Path | None
    output_video_path: Path


class VideoCreatorAgent:
    def __init__(self, config: dict) -> None:
        self.config = config

    def run_once(self, test_minutes: float | None = None, test_mode: bool = False) -> RunArtifacts:
        run_dir = self._create_run_dir()
        audio_dir = run_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        test_cfg = self.config.get("test", {})
        test_enabled = test_mode or bool(test_cfg.get("enabled")) or test_minutes is not None
        if test_minutes is None and test_enabled:
            test_minutes = test_cfg.get("max_minutes")
        repeat_playlist = (
            test_cfg.get("repeat_playlist", False)
            if test_enabled
            else self._cfg("audio", "repeat_playlist", default=True)
        )
        disable_upload = test_cfg.get("disable_upload", True) if test_enabled else False

        audio_files = self._collect_audio_files(audio_dir)
        if not audio_files:
            raise RuntimeError("No MP3 files found for the selected audio source")

        duration_map = self._probe_durations(audio_files)
        target_min = self._target_min_seconds() if repeat_playlist else 0.0
        playlist, total_seconds = self._build_playlist(audio_files, target_min, duration_map)
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
        if test_enabled:
            if test_minutes:
                max_seconds = float(test_minutes) * 60.0
            elif not repeat_playlist:
                max_seconds = None
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

        overlay_text = self._resolve_overlay_text()
        image_path = self._ensure_image(run_dir, overlay_text)
        loop_video_path = self._ensure_loop_video(run_dir, image_path)
        overlay = self._build_text_overlay(run_dir, overlay_text)
        tracklist_path = self._write_tracklist(
            run_dir,
            playlist,
            duration_map,
            enabled=self._cfg("tracklist", "enabled", default=True),
            filename=self._cfg("tracklist", "filename", default="tracklist.txt"),
        )
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

        if tracklist_path and self._cfg("tracklist", "embed_chapters", default=True):
            metadata_path = run_dir / "chapters.ffmetadata"
            write_ffmetadata_chapters(playlist, duration_map, metadata_path)
            chapters_output = run_dir / f"{output_video_path.stem}_chapters{output_video_path.suffix}"
            mux_chapters(output_video_path, metadata_path, chapters_output)
            output_video_path.unlink(missing_ok=True)
            chapters_output.replace(output_video_path)

        if self._cfg("upload", "enabled", default=True) and not disable_upload:
            uploader = self._build_uploader()
            title = self._render_template(self._cfg("upload", "title_template", default=""))
            description = self._render_template(
                self._cfg("upload", "description_template", default="")
            )
            if tracklist_path and self._cfg(
                "tracklist", "append_to_description", default=True
            ):
                description = self._append_tracklist(description, tracklist_path)
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
            tracklist_path=tracklist_path,
            output_video_path=output_video_path,
        )

    def _create_run_dir(self) -> Path:
        base_dir = Path(self._cfg("project", "output_dir", default="runs"))
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = base_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _collect_audio_files(self, audio_dir: Path) -> list[Path]:
        source = self._cfg("audio", "source", default="drive")
        ordering = self._cfg("audio", "ordering", default="name")
        if source == "local":
            folder = Path(self._cfg("audio", "local_folder", required=True))
            files = self._list_local_audio_files(folder, ordering)
            return [path.resolve() for path in files]
        if source != "drive":
            raise ValueError(f"Unsupported audio source: {source}")

        drive_cfg = self._build_drive_config()
        drive_client = DriveClient(drive_cfg)
        audio_files = drive_client.list_mp3_files(ordering=ordering)
        if not audio_files:
            return []
        downloaded = drive_client.download_many(audio_files, audio_dir)
        return [path.resolve() for path in downloaded]

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

    def _list_local_audio_files(self, folder: Path, ordering: str) -> list[Path]:
        if not folder.exists():
            raise RuntimeError(f"Audio folder not found: {folder}")
        recursive = bool(self._cfg("audio", "recursive", default=False))
        candidates = folder.rglob("*") if recursive else folder.iterdir()
        files = [path for path in candidates if path.is_file() and path.suffix.lower() == ".mp3"]
        if ordering == "modifiedTime":
            files.sort(key=lambda path: path.stat().st_mtime)
        else:
            files.sort(key=lambda path: path.name.lower())
        return files

    def _probe_durations(self, files: list[Path]) -> dict[Path, float]:
        return {path: probe_duration_seconds(path) for path in files}

    def _build_playlist(
        self,
        files: list[Path],
        target_min: float,
        duration_map: dict[Path, float] | None = None,
    ) -> tuple[list[Path], float]:
        if duration_map is None:
            duration_map = self._probe_durations(files)
        durations = [duration_map[path] for path in files]
        if target_min <= 0:
            return files, sum(durations)
        playlist: list[Path] = []
        total = 0.0
        index = 0
        while total < target_min:
            path = files[index % len(files)]
            duration = durations[index % len(durations)]
            playlist.append(path)
            total += duration
            index += 1
        return playlist, total

    def _ensure_image(self, run_dir: Path, overlay_text: str | None = None) -> Path:
        image_path = self._cfg("visuals", "image_path", default=None)
        if image_path:
            resolved = Path(image_path)
            if not resolved.exists():
                raise RuntimeError(f"Image not found: {resolved}")
            return resolved

        prompt = self._cfg("visuals", "image_prompt", default=None) or self._cfg(
            "visuals", "prompt", default=None
        )
        if prompt:
            prompt = self._render_prompt_template(prompt, overlay_text)
            output_path = run_dir / "visual.png"
            provider = self._cfg("visuals", "image_provider", default="whisk")
            if provider == "openai":
                openai = OpenAIImageClient(
                    OpenAIImageConfig(
                        api_key_env=self._cfg(
                            "visuals", "openai_api_key_env", default="OPENAI_API_KEY"
                        ),
                        model=self._cfg("visuals", "openai_model", default="gpt-image-1"),
                        size=self._cfg("visuals", "openai_size", default="1792x1024"),
                        quality=self._cfg("visuals", "openai_quality", default=None),
                        style=self._cfg("visuals", "openai_style", default=None),
                        base_url=self._cfg(
                            "visuals",
                            "openai_base_url",
                            default="https://api.openai.com/v1/images/generations",
                        ),
                    )
                )
                openai.generate_image(prompt, output_path)
            elif provider == "whisk":
                whisk = WhiskClient(
                    WhiskConfig(
                        mode=self._cfg("visuals", "whisk_mode", default="command"),
                        command=self._cfg("visuals", "whisk_command", default=None),
                        api_key_env=self._cfg("visuals", "whisk_api_key_env", default=None),
                        model=self._cfg("visuals", "whisk_model", default=None),
                    )
                )
                whisk.generate_image(prompt, output_path)
            else:
                raise ValueError(f"Unsupported image provider: {provider}")
            return output_path

        if self._cfg("visuals", "auto_background", default=False):
            output_path = run_dir / "visual.png"
            generate_color_image(
                output_path,
                resolution=self._cfg("video", "resolution", default="1920x1080"),
                color=self._cfg("visuals", "background_color", default="black"),
            )
            return output_path

        raise RuntimeError(
            "Provide visuals.image_path, visuals.image_prompt, or enable visuals.auto_background"
        )

    def _ensure_loop_video(self, run_dir: Path, image_path: Path) -> Path:
        loop_path = self._cfg("visuals", "loop_video_path", default=None)
        if loop_path:
            resolved = Path(loop_path)
            if not resolved.exists():
                raise RuntimeError(f"Loop video not found: {resolved}")
            return resolved

        provider = self._cfg("visuals", "loop_provider", default=None)
        if not provider:
            provider = "grok" if self._cfg("visuals", "grok_command", default=None) else "ffmpeg"

        output_path = run_dir / "loop.mp4"
        duration_seconds = self._cfg("visuals", "loop_duration_seconds", default=5)
        fps = self._cfg("visuals", "fps", default=None) or self._cfg("video", "fps", default=30)

        if provider == "grok":
            prompt = self._cfg("visuals", "video_prompt", default=None) or self._cfg(
                "visuals", "prompt", default=None
            )
            if not prompt:
                raise RuntimeError("visuals.video_prompt is required to generate loop video")
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
                duration_seconds=duration_seconds,
                fps=fps,
            )
            return output_path

        if provider == "ffmpeg":
            effects = self._cfg("visuals", "loop_effects", default=[])
            if isinstance(effects, str):
                effects = [item.strip() for item in effects.split(",") if item.strip()]
            generate_loop_video_from_image(
                image_path=image_path,
                output_path=output_path,
                duration_seconds=duration_seconds,
                fps=fps,
                resolution=self._cfg("video", "resolution", default="1920x1080"),
                zoom_amount=self._cfg("visuals", "loop_zoom_amount", default=0.02),
                pan_amount=self._cfg("visuals", "loop_pan_amount", default=0.0),
                effects=effects,
                sway_degrees=self._cfg("visuals", "loop_sway_degrees", default=0.35),
                flicker_amount=self._cfg("visuals", "loop_flicker_amount", default=0.015),
                hue_degrees=self._cfg("visuals", "loop_hue_degrees", default=0.0),
                vignette_angle=self._cfg("visuals", "loop_vignette_angle", default=None),
                motion_style=self._cfg("visuals", "loop_motion_style", default="smooth"),
                steam_opacity=self._cfg("visuals", "loop_steam_opacity", default=0.08),
                steam_blur=self._cfg("visuals", "loop_steam_blur", default=10.0),
                steam_noise=self._cfg("visuals", "loop_steam_noise", default=12),
                steam_drift_x=self._cfg("visuals", "loop_steam_drift_x", default=0.02),
                steam_drift_y=self._cfg("visuals", "loop_steam_drift_y", default=0.05),
            )
            return output_path

        raise ValueError(f"Unsupported loop provider: {provider}")

    def _target_min_seconds(self) -> float:
        # Check for minutes first (more granular control)
        min_minutes = self._cfg("audio", "target_minutes_min", default=None)
        if min_minutes is not None:
            return float(min_minutes) * 60.0
        # Fall back to hours
        min_hours = self._cfg("audio", "target_hours_min", default=8)
        if not min_hours:
            return 0.0
        return float(min_hours) * 3600.0

    def _target_max_seconds(self) -> float | None:
        # Check for minutes first (more granular control)
        max_minutes = self._cfg("audio", "target_minutes_max", default=None)
        if max_minutes is not None:
            return float(max_minutes) * 60.0
        # Fall back to hours
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

    def _build_text_overlay(
        self,
        run_dir: Path,
        overlay_text: str | None = None,
    ) -> dict | None:
        overlay_cfg = self.config.get("text_overlay", {})
        text = overlay_text if overlay_text is not None else self._resolve_overlay_text()
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

    def _resolve_overlay_text(self) -> str:
        overlay_cfg = self.config.get("text_overlay", {})
        text = overlay_cfg.get("text") or ""
        if not text:
            auto_texts = overlay_cfg.get("auto_texts", [])
            if isinstance(auto_texts, str):
                parts: list[str] = []
                for line in auto_texts.splitlines():
                    parts.extend(line.split(","))
                auto_texts = parts
            auto_texts = [item.strip() for item in auto_texts if str(item).strip()]
            if auto_texts:
                mode = str(overlay_cfg.get("auto_mode", "daily")).strip().lower()
                if mode == "random":
                    text = random.choice(auto_texts)
                else:
                    idx = dt.date.today().toordinal() % len(auto_texts)
                    text = auto_texts[idx]
        return str(text).strip()

    def _render_prompt_template(self, template: str, overlay_text: str | None) -> str:
        class _SafeDict(dict):
            def __missing__(self, key: str) -> str:
                return "{" + key + "}"

        replacements = {
            "date": dt.date.today().isoformat(),
            "overlay_text": overlay_text or "",
        }
        return template.format_map(_SafeDict(replacements))

    def _write_tracklist(
        self,
        run_dir: Path,
        playlist: list[Path],
        duration_map: dict[Path, float],
        enabled: bool,
        filename: str,
    ) -> Path | None:
        if not enabled:
            return None
        entries: list[str] = []
        current = 0.0
        for path in playlist:
            title = path.stem
            entries.append(f"{self._format_timestamp(current)} {title}")
            current += duration_map.get(path, 0.0)
        tracklist_path = run_dir / filename
        tracklist_path.write_text("\n".join(entries) + "\n", encoding="utf-8")
        return tracklist_path

    def _append_tracklist(self, description: str, tracklist_path: Path) -> str:
        tracklist_text = tracklist_path.read_text(encoding="utf-8").strip()
        if not tracklist_text:
            return description
        if description:
            return f"{description}\n\nTracklist:\n{tracklist_text}"
        return f"Tracklist:\n{tracklist_text}"

    def _format_timestamp(self, seconds: float) -> str:
        total = int(round(seconds))
        hours = total // 3600
        minutes = (total % 3600) // 60
        secs = total % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
