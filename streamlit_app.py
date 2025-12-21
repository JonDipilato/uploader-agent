from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Any

import streamlit as st
import yaml


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.yaml"
EXAMPLE_CONFIG_PATH = ROOT / "config.example.yaml"
SECRETS_DIR = ROOT / "secrets"
ASSETS_DIR = ROOT / "assets"


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    if EXAMPLE_CONFIG_PATH.exists():
        return yaml.safe_load(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return {}


def save_config(config: dict[str, Any]) -> None:
    text = yaml.safe_dump(config, sort_keys=False)
    CONFIG_PATH.write_text(text, encoding="utf-8")


def cfg(config: dict[str, Any], section: str, key: str, default: Any) -> Any:
    return config.get(section, {}).get(key, default)


def path_for_config(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def save_uploaded_file(upload, dest_path: Path) -> str:
    if upload is None:
        return ""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(upload.getvalue())
    return path_for_config(dest_path)


def split_tags(text: str) -> list[str]:
    return [tag.strip() for tag in text.split(",") if tag.strip()]


def main() -> None:
    st.set_page_config(
        page_title="Video Creator Agent",
        page_icon=":movie_camera:",
        layout="centered",
    )
    st.title("Video Creator Agent")
    st.caption("Fill out the settings, save config, then run or schedule.")
    demo_mode = st.sidebar.checkbox(
        "Demo mode (preview only)",
        value=os.getenv("DEMO_MODE") == "1",
    )
    if demo_mode:
        st.sidebar.info("Saving is disabled in demo mode.")

    if "config" not in st.session_state:
        st.session_state.config = load_config()

    config = st.session_state.config

    with st.form("config_form"):
        st.subheader("Project")
        project_name = st.text_input(
            "Project name",
            cfg(config, "project", "name", "daily_chill_mix"),
        )
        output_dir = st.text_input(
            "Output folder",
            cfg(config, "project", "output_dir", "runs"),
        )

        st.subheader("Audio")
        drive_folder_id = st.text_input(
            "Google Drive folder ID (MP3s)",
            cfg(config, "audio", "drive_folder_id", ""),
        )
        ordering = st.selectbox(
            "Ordering",
            ["name", "modifiedTime"],
            index=0 if cfg(config, "audio", "ordering", "name") == "name" else 1,
        )
        target_hours_min = st.number_input(
            "Target hours minimum",
            min_value=0,
            max_value=24,
            value=int(cfg(config, "audio", "target_hours_min", 8)),
        )
        target_hours_max = st.number_input(
            "Target hours maximum",
            min_value=0,
            max_value=24,
            value=int(cfg(config, "audio", "target_hours_max", 9)),
        )
        concat_quality = st.number_input(
            "MP3 quality (0 best - 9 worst)",
            min_value=0,
            max_value=9,
            value=int(cfg(config, "audio", "concat_quality", 2)),
        )
        concat_bitrate = st.text_input(
            "MP3 bitrate (optional, e.g. 192k)",
            cfg(config, "audio", "concat_bitrate", "") or "",
        )

        st.subheader("Drive")
        use_service_account = st.checkbox(
            "Use service account",
            value=bool(cfg(config, "drive", "use_service_account", True)),
        )
        if use_service_account:
            service_account_path = st.text_input(
                "Service account JSON path",
                cfg(config, "drive", "service_account_json", "secrets/drive_service_account.json"),
            )
            upload_sa = st.file_uploader("Upload service account JSON", type=["json"])
        else:
            service_account_path = ""
            upload_sa = None
            oauth_client_path = st.text_input(
                "Drive OAuth client JSON path",
                cfg(config, "drive", "oauth_client_json", "secrets/drive_oauth_client.json"),
            )
            upload_oauth = st.file_uploader("Upload Drive OAuth client JSON", type=["json"])
            drive_token_path = st.text_input(
                "Drive token JSON path (created on first auth)",
                cfg(config, "drive", "token_json", "secrets/drive_token.json"),
            )

        st.subheader("Visuals")
        image_path = st.text_input(
            "Existing image path (leave blank to generate)",
            cfg(config, "visuals", "image_path", "") or "",
        )
        upload_image = st.file_uploader("Upload image (optional)", type=["png", "jpg", "jpeg"])
        if not image_path:
            image_prompt = st.text_input(
                "Whisk image prompt",
                cfg(
                    config,
                    "visuals",
                    "image_prompt",
                    "cozy fireplace on a rainy night, warm glow, cinematic, high detail",
                ),
            )
        else:
            image_prompt = cfg(config, "visuals", "image_prompt", "")
        st.caption("Tip: leave empty space for overlay text if you plan to add it.")

        loop_video_path = st.text_input(
            "Existing loop video path (leave blank to generate)",
            cfg(config, "visuals", "loop_video_path", "") or "",
        )
        upload_loop = st.file_uploader("Upload loop video (optional)", type=["mp4", "mov"])
        if not loop_video_path:
            video_prompt = st.text_input(
                "Grok video prompt",
                cfg(
                    config,
                    "visuals",
                    "video_prompt",
                    "subtle fire animation, gentle embers drifting, loopable, 5s",
                ),
            )
        else:
            video_prompt = cfg(config, "visuals", "video_prompt", "")

        loop_duration = st.number_input(
            "Loop duration (seconds)",
            min_value=1,
            max_value=30,
            value=int(cfg(config, "visuals", "loop_duration_seconds", 5)),
        )
        fps = st.number_input(
            "FPS",
            min_value=1,
            max_value=60,
            value=int(cfg(config, "visuals", "fps", cfg(config, "video", "fps", 30))),
        )

        st.subheader("Text Overlay + Thumbnail")
        overlay_text = st.text_area(
            "Overlay text (leave blank to disable)",
            cfg(config, "text_overlay", "text", "") or "",
        )
        overlay_apply_to_video = st.checkbox(
            "Burn text into video",
            value=bool(cfg(config, "text_overlay", "apply_to_video", True)),
        )
        overlay_create_thumbnail = st.checkbox(
            "Create thumbnail image with text",
            value=bool(cfg(config, "text_overlay", "create_thumbnail", True)),
        )
        overlay_upload_thumbnail = st.checkbox(
            "Upload thumbnail to YouTube",
            value=bool(cfg(config, "text_overlay", "upload_thumbnail", False)),
        )
        overlay_font_path = st.text_input(
            "Font file path (optional)",
            cfg(config, "text_overlay", "fontfile", "") or "",
        )
        upload_overlay_font = st.file_uploader(
            "Upload font file (TTF/OTF)",
            type=["ttf", "otf"],
        )
        overlay_font_name = st.text_input(
            "Font family name (optional)",
            cfg(config, "text_overlay", "font", "") or "",
        )
        overlay_font_size = st.number_input(
            "Font size",
            min_value=10,
            max_value=400,
            value=int(cfg(config, "text_overlay", "font_size", 96)),
        )
        overlay_font_color = st.text_input(
            "Font color",
            cfg(config, "text_overlay", "font_color", "white"),
        )
        overlay_outline_color = st.text_input(
            "Outline color",
            cfg(config, "text_overlay", "outline_color", "black"),
        )
        overlay_outline_width = st.number_input(
            "Outline width",
            min_value=0,
            max_value=20,
            value=int(cfg(config, "text_overlay", "outline_width", 4)),
        )
        position_options = {
            "center": ("(w-text_w)/2", "(h-text_h)/2"),
            "lower third": ("(w-text_w)/2", "(h-text_h)*0.75"),
            "top": ("(w-text_w)/2", "(h-text_h)*0.15"),
        }
        current_x = cfg(config, "text_overlay", "x", "(w-text_w)/2")
        current_y = cfg(config, "text_overlay", "y", "(h-text_h)/2")
        position_default = "custom"
        for label, (x_value, y_value) in position_options.items():
            if current_x == x_value and current_y == y_value:
                position_default = label
                break
        position_choice = st.selectbox(
            "Text position",
            ["center", "lower third", "top", "custom"],
            index=["center", "lower third", "top", "custom"].index(position_default),
        )
        if position_choice == "custom":
            overlay_x = st.text_input("X position expression", current_x)
            overlay_y = st.text_input("Y position expression", current_y)
        else:
            overlay_x, overlay_y = position_options[position_choice]

        st.subheader("Video")
        resolution = st.text_input(
            "Resolution",
            cfg(config, "video", "resolution", "1920x1080"),
        )
        video_bitrate = st.text_input(
            "Video bitrate",
            cfg(config, "video", "video_bitrate", "4500k"),
        )
        audio_bitrate = st.text_input(
            "Audio bitrate",
            cfg(config, "video", "audio_bitrate", "192k"),
        )

        st.subheader("Upload")
        upload_enabled = st.checkbox(
            "Enable upload",
            value=bool(cfg(config, "upload", "enabled", True)),
        )
        youtube_client_path = st.text_input(
            "YouTube OAuth client JSON path",
            cfg(config, "upload", "credentials_json", "secrets/youtube_client.json"),
        )
        upload_youtube_client = st.file_uploader("Upload YouTube OAuth client JSON", type=["json"])
        youtube_token_path = st.text_input(
            "YouTube token JSON path (created on first auth)",
            cfg(config, "upload", "token_json", "secrets/youtube_token.json"),
        )
        privacy_status = st.selectbox(
            "Privacy status",
            ["public", "unlisted", "private"],
            index=["public", "unlisted", "private"].index(
                cfg(config, "upload", "privacy_status", "public")
            ),
        )
        category_id = st.text_input(
            "YouTube category ID",
            cfg(config, "upload", "category_id", "10"),
        )
        title_template = st.text_input(
            "Title template",
            cfg(config, "upload", "title_template", "Daily Chill Mix - {date}"),
        )
        description_template = st.text_area(
            "Description template",
            cfg(config, "upload", "description_template", "Longform ambient mix. Generated daily."),
        )
        tags_text = st.text_input(
            "Tags (comma-separated)",
            ", ".join(cfg(config, "upload", "tags", ["ambient", "chill", "fireplace"])),
        )

        st.subheader("Schedule")
        schedule_enabled = st.checkbox(
            "Enable daily schedule",
            value=bool(cfg(config, "schedule", "enabled", True)),
        )
        daily_time = st.text_input(
            "Daily time (HH:MM, 24h)",
            cfg(config, "schedule", "daily_time", "03:00"),
        )

        with st.expander("Advanced: Whisk/Grok command templates"):
            whisk_command = st.text_area(
                "Whisk command template (YAML list)",
                yaml.safe_dump(
                    cfg(
                        config,
                        "visuals",
                        "whisk_command",
                        [
                            "whisk",
                            "image",
                            "--prompt",
                            "{prompt}",
                            "--out",
                            "{output_path}",
                        ],
                    ),
                    sort_keys=False,
                ).strip(),
            )
            grok_command = st.text_area(
                "Grok command template (YAML list)",
                yaml.safe_dump(
                    cfg(
                        config,
                        "visuals",
                        "grok_command",
                        [
                            "grok",
                            "video",
                            "--image",
                            "{image_path}",
                            "--prompt",
                            "{prompt}",
                            "--duration",
                            "{duration}",
                            "--fps",
                            "{fps}",
                            "--out",
                            "{output_path}",
                        ],
                    ),
                    sort_keys=False,
                ).strip(),
            )

        submitted = st.form_submit_button("Save config", disabled=demo_mode)

    if submitted:
        saved_service_account_path = service_account_path
        saved_oauth_path = ""
        saved_drive_token = ""
        if use_service_account:
            if upload_sa is not None:
                saved_service_account_path = save_uploaded_file(
                    upload_sa, SECRETS_DIR / "drive_service_account.json"
                )
            saved_oauth_path = ""
            saved_drive_token = ""
        else:
            if upload_oauth is not None:
                saved_oauth_path = save_uploaded_file(
                    upload_oauth, SECRETS_DIR / "drive_oauth_client.json"
                )
            else:
                saved_oauth_path = oauth_client_path
            saved_drive_token = drive_token_path

        saved_image_path = image_path
        if upload_image is not None:
            saved_image_path = save_uploaded_file(upload_image, ASSETS_DIR / "image.png")

        saved_loop_path = loop_video_path
        if upload_loop is not None:
            saved_loop_path = save_uploaded_file(upload_loop, ASSETS_DIR / "loop.mp4")

        saved_overlay_font_path = overlay_font_path
        if upload_overlay_font is not None:
            suffix = Path(upload_overlay_font.name).suffix or ".ttf"
            saved_overlay_font_path = save_uploaded_file(
                upload_overlay_font, ASSETS_DIR / f"overlay_font{suffix}"
            )

        saved_youtube_client = youtube_client_path
        if upload_youtube_client is not None:
            saved_youtube_client = save_uploaded_file(
                upload_youtube_client, SECRETS_DIR / "youtube_client.json"
            )

        try:
            parsed_whisk_command = yaml.safe_load(whisk_command) or []
            parsed_grok_command = yaml.safe_load(grok_command) or []
        except yaml.YAMLError:
            st.error("Invalid YAML in command templates.")
            return

        config_out = {
            "project": {
                "name": project_name,
                "output_dir": output_dir,
            },
            "audio": {
                "drive_folder_id": drive_folder_id,
                "ordering": ordering,
                "target_hours_min": int(target_hours_min),
                "target_hours_max": int(target_hours_max),
                "concat_codec": "libmp3lame",
                "concat_quality": int(concat_quality),
                "concat_bitrate": concat_bitrate or None,
            },
            "drive": {
                "use_service_account": use_service_account,
                "service_account_json": saved_service_account_path or None,
                "oauth_client_json": saved_oauth_path or None,
                "token_json": saved_drive_token or None,
            },
            "visuals": {
                "image_prompt": image_prompt,
                "video_prompt": video_prompt,
                "loop_duration_seconds": int(loop_duration),
                "fps": int(fps),
                "image_path": saved_image_path or None,
                "loop_video_path": saved_loop_path or None,
                "whisk_mode": "command",
                "whisk_command": parsed_whisk_command,
                "whisk_api_key_env": cfg(config, "visuals", "whisk_api_key_env", "WHISK_API_KEY"),
                "whisk_model": cfg(config, "visuals", "whisk_model", None),
                "grok_mode": "command",
                "grok_command": parsed_grok_command,
                "grok_api_key_env": cfg(config, "visuals", "grok_api_key_env", "GROK_API_KEY"),
                "grok_model": cfg(config, "visuals", "grok_model", None),
            },
            "text_overlay": {
                "text": overlay_text or None,
                "fontfile": saved_overlay_font_path or None,
                "font": overlay_font_name or None,
                "font_size": int(overlay_font_size),
                "font_color": overlay_font_color,
                "outline_color": overlay_outline_color,
                "outline_width": int(overlay_outline_width),
                "box_color": cfg(config, "text_overlay", "box_color", None),
                "box_borderw": cfg(config, "text_overlay", "box_borderw", None),
                "shadow_color": cfg(config, "text_overlay", "shadow_color", None),
                "shadow_x": cfg(config, "text_overlay", "shadow_x", None),
                "shadow_y": cfg(config, "text_overlay", "shadow_y", None),
                "x": overlay_x,
                "y": overlay_y,
                "apply_to_video": overlay_apply_to_video,
                "create_thumbnail": overlay_create_thumbnail,
                "upload_thumbnail": overlay_upload_thumbnail,
            },
            "video": {
                "resolution": resolution,
                "fps": int(fps),
                "video_bitrate": video_bitrate,
                "audio_bitrate": audio_bitrate,
            },
            "upload": {
                "enabled": upload_enabled,
                "provider": "youtube",
                "credentials_json": saved_youtube_client,
                "token_json": youtube_token_path,
                "privacy_status": privacy_status,
                "category_id": category_id,
                "title_template": title_template,
                "description_template": description_template,
                "tags": split_tags(tags_text),
            },
            "schedule": {
                "enabled": schedule_enabled,
                "daily_time": daily_time,
            },
        }

        save_config(config_out)
        st.success(f"Saved config at {CONFIG_PATH}")

    st.divider()
    st.subheader("Next steps")
    st.write(
        "1) Set WHISK_API_KEY and GROK_API_KEY in your environment. "
        "2) Run the agent once or schedule it."
    )
    st.code(
        ".\\run-once.ps1\n"
        ".\\schedule-task.ps1\n"
        ".\\schedule-task.ps1 -Remove",
        language="powershell",
    )
    st.caption(f"Today: {dt.date.today().isoformat()}")


if __name__ == "__main__":
    main()
