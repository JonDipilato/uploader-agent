from __future__ import annotations

import datetime as dt
import hmac
import random
import os
from pathlib import Path
from typing import Any

import streamlit as st
import yaml
from src.utils.ffmpeg import (
    build_drawtext_filter,
    generate_color_image,
    render_image_with_text,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.yaml"
EXAMPLE_CONFIG_PATH = ROOT / "config.example.yaml"
SECRETS_DIR = ROOT / "secrets"
ASSETS_DIR = ROOT / "assets"

def get_app_password() -> str:
    if "app_password" in st.secrets:
        return str(st.secrets["app_password"]).strip()
    return os.getenv("APP_PASSWORD", "").strip()

def require_password() -> bool:
    app_password = get_app_password()
    if not app_password:
        return True
    if st.session_state.get("password_ok"):
        return True

    def password_entered() -> None:
        entered = st.session_state.get("password", "")
        if hmac.compare_digest(entered, app_password):
            st.session_state["password_ok"] = True
            st.session_state["password"] = ""
        else:
            st.session_state["password_ok"] = False

    st.text_input(
        "App password",
        type="password",
        on_change=password_entered,
        key="password",
    )
    if st.session_state.get("password_ok") is False:
        st.error("Incorrect password.")
    return st.session_state.get("password_ok", False)


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

def split_text_lines(text: str) -> list[str]:
    if not text:
        return []
    entries: list[str] = []
    for line in text.splitlines():
        entries.extend(line.split(","))
    return [item.strip() for item in entries if item.strip()]

def select_overlay_text(overlay_text: str, auto_texts: list[str], mode: str) -> str:
    if overlay_text.strip():
        return overlay_text.strip()
    if not auto_texts:
        return ""
    mode = mode.strip().lower()
    if mode == "random":
        return random.choice(auto_texts)
    idx = dt.date.today().toordinal() % len(auto_texts)
    return auto_texts[idx]

def resolve_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path

def apply_preset(config: dict[str, Any], preset: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for section, values in preset.items():
        section_map = config.setdefault(section, {})
        section_map.update(values)
    return config

PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "Cafe Steam": {
        "visuals": {
            "image_provider": "openai",
            "image_prompt": (
                "cozy coffee shop interior, warm light, soft steam, cinematic, "
                "empty center space for title text \"{overlay_text}\", high detail"
            ),
            "openai_model": "gpt-image-1",
            "openai_size": "1792x1024",
            "loop_motion_style": "cinematic",
            "loop_zoom_amount": 0.015,
            "loop_pan_amount": 0.08,
            "loop_effects": ["steam", "flicker", "vignette"],
            "loop_flicker_amount": 0.01,
            "loop_vignette_angle": "PI/5",
            "loop_steam_opacity": 0.08,
            "loop_steam_blur": 10.0,
            "loop_steam_noise": 12,
            "loop_steam_drift_x": 0.02,
            "loop_steam_drift_y": 0.05,
        },
        "text_overlay": {
            "text": "LOCK IN",
            "auto_texts": ["LOCK IN", "HYPER FOCUS", "SLOW DOWN"],
            "auto_mode": "daily",
            "apply_to_video": False,
            "create_thumbnail": True,
            "upload_thumbnail": True,
            "font_size": 96,
            "x": "(w-text_w)/2",
            "y": "(h-text_h)/2",
        },
        "upload": {
            "title_template": "Cafe Steam Chill Mix - Cozy Coffee Shop Ambience - {date}",
            "description_template": (
                "Relaxing cafe ambience with gentle steam drift visuals.\n"
                "Perfect for study, focus, reading, and sleep.\n\n"
                "New mix daily."
            ),
            "tags": [
                "cafe ambience",
                "coffee shop ambience",
                "study music",
                "focus music",
                "relaxing mix",
                "lofi",
                "chill beats",
                "background music",
                "sleep music",
            ],
            "category_id": "10",
        },
    },
}


def main() -> None:
    st.set_page_config(
        page_title="Video Creator Agent",
        page_icon=":movie_camera:",
        layout="centered",
    )
    st.title("Video Creator Agent")
    if not require_password():
        st.stop()
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
    st.subheader("Quick presets")
    preset_choice = st.selectbox(
        "Preset",
        ["None"] + sorted(PRESETS.keys()),
    )
    if st.button("Apply preset"):
        if preset_choice == "None":
            st.info("Select a preset to apply.")
        else:
            st.session_state.config = apply_preset(
                st.session_state.config,
                PRESETS[preset_choice],
            )
            st.success("Preset applied. You can tweak fields below.")

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
        audio_source_label = st.selectbox(
            "Audio source",
            ["Local folder", "Google Drive"],
            index=0 if cfg(config, "audio", "source", "drive") == "local" else 1,
        )
        st.caption("YouTube audio downloads are not supported. Use local files or Drive.")
        audio_source = "local" if audio_source_label == "Local folder" else "drive"
        drive_folder_id = cfg(config, "audio", "drive_folder_id", "")
        local_folder = cfg(config, "audio", "local_folder", "")
        recursive = bool(cfg(config, "audio", "recursive", False))
        if audio_source == "local":
            local_folder = st.text_input(
                "Local folder path (MP3s)",
                local_folder or "C:\\Users\\USERNAME\\Music",
            )
            recursive = st.checkbox("Scan subfolders", value=recursive)
        else:
            drive_folder_id = st.text_input(
                "Google Drive folder ID (MP3s)",
                drive_folder_id,
            )
        ordering = st.selectbox(
            "Ordering",
            ["name", "modifiedTime"],
            index=0 if cfg(config, "audio", "ordering", "name") == "name" else 1,
        )
        repeat_playlist = st.checkbox(
            "Repeat playlist to hit target hours",
            value=bool(cfg(config, "audio", "repeat_playlist", True)),
        )
        target_hours_min = st.number_input(
            "Target hours minimum",
            min_value=0,
            max_value=24,
            value=int(cfg(config, "audio", "target_hours_min", 8)),
            disabled=not repeat_playlist,
        )
        target_hours_max = st.number_input(
            "Target hours maximum",
            min_value=0,
            max_value=24,
            value=int(cfg(config, "audio", "target_hours_max", 9)),
            disabled=not repeat_playlist,
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

        use_service_account = bool(cfg(config, "drive", "use_service_account", True))
        service_account_path = cfg(
            config,
            "drive",
            "service_account_json",
            "secrets/drive_service_account.json",
        )
        oauth_client_path = cfg(
            config,
            "drive",
            "oauth_client_json",
            "secrets/drive_oauth_client.json",
        )
        drive_token_path = cfg(
            config,
            "drive",
            "token_json",
            "secrets/drive_token.json",
        )
        upload_sa = None
        upload_oauth = None
        if audio_source == "drive":
            st.subheader("Drive")
            use_service_account = st.checkbox(
                "Use service account",
                value=use_service_account,
            )
            if use_service_account:
                service_account_path = st.text_input(
                    "Service account JSON path",
                    service_account_path,
                )
                upload_sa = st.file_uploader("Upload service account JSON", type=["json"])
            else:
                oauth_client_path = st.text_input(
                    "Drive OAuth client JSON path",
                    oauth_client_path,
                )
                upload_oauth = st.file_uploader(
                    "Upload Drive OAuth client JSON",
                    type=["json"],
                )
                drive_token_path = st.text_input(
                    "Drive token JSON path (created on first auth)",
                    drive_token_path,
                )

        st.subheader("Visuals")
        auto_background = st.checkbox(
            "Auto-generate background (no Whisk needed)",
            value=bool(cfg(config, "visuals", "auto_background", False)),
        )
        background_color = cfg(config, "visuals", "background_color", "black")
        if auto_background:
            background_color = st.text_input("Background color", background_color)
        image_provider = cfg(config, "visuals", "image_provider", "whisk")
        image_provider = st.selectbox(
            "Image generator (if no image path is provided)",
            ["whisk", "openai"],
            index=0 if image_provider == "whisk" else 1,
        )
        openai_api_key_env = cfg(config, "visuals", "openai_api_key_env", "OPENAI_API_KEY")
        openai_model = cfg(config, "visuals", "openai_model", "gpt-image-1")
        openai_size = cfg(config, "visuals", "openai_size", "1792x1024")
        openai_quality = cfg(config, "visuals", "openai_quality", "")
        openai_style = cfg(config, "visuals", "openai_style", "")
        openai_base_url = cfg(
            config,
            "visuals",
            "openai_base_url",
            "https://api.openai.com/v1/images/generations",
        )
        if image_provider == "openai":
            openai_api_key_env = st.text_input("OpenAI API key env var", openai_api_key_env)
            openai_model = st.text_input("OpenAI image model", openai_model)
            openai_size = st.selectbox(
                "OpenAI image size",
                ["1792x1024", "1024x1024", "1024x1792"],
                index=["1792x1024", "1024x1024", "1024x1792"].index(
                    openai_size if openai_size in {"1792x1024", "1024x1024", "1024x1792"} else "1792x1024"
                ),
            )
            openai_quality = st.text_input(
                "OpenAI quality (optional)",
                openai_quality or "",
            )
            openai_style = st.text_input(
                "OpenAI style (optional)",
                openai_style or "",
            )
            openai_base_url = st.text_input(
                "OpenAI base URL (optional)",
                openai_base_url,
            )
        image_path = st.text_input(
            "Existing image path (leave blank to generate)",
            cfg(config, "visuals", "image_path", "") or "",
        )
        upload_image = st.file_uploader("Upload image (optional)", type=["png", "jpg", "jpeg"])
        if not image_path and not auto_background:
            image_prompt = st.text_input(
                "Image prompt",
                cfg(
                    config,
                    "visuals",
                    "image_prompt",
                    "cozy coffee shop interior, warm light, cinematic, empty space for text, high detail",
                ),
            )
        else:
            image_prompt = cfg(config, "visuals", "image_prompt", "")
        st.caption("Tip: leave empty space for overlay text. You can use {overlay_text} and {date}.")

        loop_video_path = st.text_input(
            "Existing loop video path (leave blank to generate)",
            cfg(config, "visuals", "loop_video_path", "") or "",
        )
        upload_loop = st.file_uploader("Upload loop video (optional)", type=["mp4", "mov"])
        loop_provider = st.selectbox(
            "Loop generator (if no loop video is provided)",
            ["ffmpeg", "grok"],
            index=0 if cfg(config, "visuals", "loop_provider", "ffmpeg") == "ffmpeg" else 1,
        )
        loop_zoom_amount = float(cfg(config, "visuals", "loop_zoom_amount", 0.02))
        loop_pan_amount = float(cfg(config, "visuals", "loop_pan_amount", 0.15))
        loop_motion_style = cfg(config, "visuals", "loop_motion_style", "cinematic")
        if not loop_video_path and loop_provider == "grok":
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
        if loop_provider == "ffmpeg":
            loop_zoom_amount = st.number_input(
                "Loop zoom amount (subtle motion)",
                min_value=0.0,
                max_value=0.2,
                value=float(loop_zoom_amount),
                step=0.005,
            )
            loop_pan_amount = st.number_input(
                "Loop pan amount (0 = no pan)",
                min_value=0.0,
                max_value=1.0,
                value=float(loop_pan_amount),
                step=0.05,
            )
            loop_motion_style = st.selectbox(
                "Motion style",
                ["smooth", "cinematic", "orbit"],
                index=["smooth", "cinematic", "orbit"].index(
                    loop_motion_style if loop_motion_style in {"smooth", "cinematic", "orbit"} else "cinematic"
                ),
            )
            effect_options = ["steam", "sway", "flicker", "color_drift", "vignette"]
            effect_labels = {
                "steam": "Steam drift",
                "sway": "Sway (rotation)",
                "flicker": "Flicker (brightness)",
                "color_drift": "Color drift (hue)",
                "vignette": "Vignette (edge darken)",
            }
            default_effects = cfg(
                config,
                "visuals",
                "loop_effects",
                ["flicker", "vignette"],
            )
            if isinstance(default_effects, str):
                default_effects = [
                    item.strip() for item in default_effects.split(",") if item.strip()
                ]
            loop_effects = st.multiselect(
                "Extra loop effects",
                options=effect_options,
                default=[effect for effect in default_effects if effect in effect_options],
                format_func=lambda key: effect_labels.get(key, key),
            )
            loop_sway_degrees = float(cfg(config, "visuals", "loop_sway_degrees", 0.35))
            loop_flicker_amount = float(
                cfg(config, "visuals", "loop_flicker_amount", 0.015)
            )
            loop_hue_degrees = float(cfg(config, "visuals", "loop_hue_degrees", 0.0))
            loop_steam_opacity = float(cfg(config, "visuals", "loop_steam_opacity", 0.08))
            loop_steam_blur = float(cfg(config, "visuals", "loop_steam_blur", 10.0))
            loop_steam_noise = int(cfg(config, "visuals", "loop_steam_noise", 12))
            loop_steam_drift_x = float(cfg(config, "visuals", "loop_steam_drift_x", 0.02))
            loop_steam_drift_y = float(cfg(config, "visuals", "loop_steam_drift_y", 0.05))
            vignette_default = cfg(config, "visuals", "loop_vignette_angle", 0.63)
            try:
                loop_vignette_angle = float(vignette_default)
            except (TypeError, ValueError):
                loop_vignette_angle = 0.63
            if "steam" in loop_effects:
                loop_steam_opacity = st.number_input(
                    "Steam opacity",
                    min_value=0.0,
                    max_value=0.2,
                    value=float(loop_steam_opacity),
                    step=0.01,
                )
                loop_steam_blur = st.number_input(
                    "Steam blur",
                    min_value=0.0,
                    max_value=30.0,
                    value=float(loop_steam_blur),
                    step=1.0,
                )
                loop_steam_noise = st.number_input(
                    "Steam noise",
                    min_value=0,
                    max_value=40,
                    value=int(loop_steam_noise),
                    step=1,
                )
                loop_steam_drift_x = st.number_input(
                    "Steam drift X",
                    min_value=0.0,
                    max_value=0.1,
                    value=float(loop_steam_drift_x),
                    step=0.005,
                )
                loop_steam_drift_y = st.number_input(
                    "Steam drift Y",
                    min_value=0.0,
                    max_value=0.2,
                    value=float(loop_steam_drift_y),
                    step=0.01,
                )
            if "sway" in loop_effects:
                loop_sway_degrees = st.number_input(
                    "Sway degrees (rotation)",
                    min_value=0.0,
                    max_value=2.0,
                    value=float(loop_sway_degrees),
                    step=0.05,
                )
            if "flicker" in loop_effects:
                loop_flicker_amount = st.number_input(
                    "Flicker amount",
                    min_value=0.0,
                    max_value=0.05,
                    value=float(loop_flicker_amount),
                    step=0.005,
                )
            if "color_drift" in loop_effects:
                loop_hue_degrees = st.number_input(
                    "Color drift degrees",
                    min_value=0.0,
                    max_value=6.0,
                    value=float(loop_hue_degrees),
                    step=0.25,
                )
            if "vignette" in loop_effects:
                loop_vignette_angle = st.number_input(
                    "Vignette angle (lower = stronger)",
                    min_value=0.2,
                    max_value=1.5,
                    value=float(loop_vignette_angle),
                    step=0.05,
                )
        else:
            loop_effects = cfg(config, "visuals", "loop_effects", [])
            loop_sway_degrees = float(cfg(config, "visuals", "loop_sway_degrees", 0.35))
            loop_flicker_amount = float(
                cfg(config, "visuals", "loop_flicker_amount", 0.015)
            )
            loop_hue_degrees = float(cfg(config, "visuals", "loop_hue_degrees", 0.0))
            loop_vignette_angle = cfg(config, "visuals", "loop_vignette_angle", 0.63)
            loop_steam_opacity = float(cfg(config, "visuals", "loop_steam_opacity", 0.08))
            loop_steam_blur = float(cfg(config, "visuals", "loop_steam_blur", 10.0))
            loop_steam_noise = int(cfg(config, "visuals", "loop_steam_noise", 12))
            loop_steam_drift_x = float(cfg(config, "visuals", "loop_steam_drift_x", 0.02))
            loop_steam_drift_y = float(cfg(config, "visuals", "loop_steam_drift_y", 0.05))
            loop_motion_style = cfg(config, "visuals", "loop_motion_style", "cinematic")

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
        overlay_auto_texts_input = st.text_area(
            "Auto overlay texts (one per line, used only if overlay text is blank)",
            "\n".join(cfg(config, "text_overlay", "auto_texts", [])),
        )
        overlay_auto_mode = st.selectbox(
            "Auto text mode",
            ["daily", "random"],
            index=0 if cfg(config, "text_overlay", "auto_mode", "daily") == "daily" else 1,
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

        st.subheader("Tracklist")
        tracklist_enabled = st.checkbox(
            "Generate timestamps",
            value=bool(cfg(config, "tracklist", "enabled", True)),
        )
        tracklist_append = st.checkbox(
            "Append tracklist to description",
            value=bool(cfg(config, "tracklist", "append_to_description", True)),
        )
        tracklist_embed = st.checkbox(
            "Embed chapters into MP4",
            value=bool(cfg(config, "tracklist", "embed_chapters", True)),
        )
        tracklist_filename = st.text_input(
            "Tracklist filename",
            cfg(config, "tracklist", "filename", "tracklist.txt"),
        )

        st.subheader("Test mode")
        test_enabled = st.checkbox(
            "Enable test mode (no upload, no repeat)",
            value=bool(cfg(config, "test", "enabled", False)),
        )
        test_max_minutes_value = cfg(config, "test", "max_minutes", None) or 0
        test_max_minutes = st.number_input(
            "Max minutes (0 = full length)",
            min_value=0,
            max_value=720,
            value=int(test_max_minutes_value),
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

        preview_submitted = st.form_submit_button("Preview thumbnail overlay")
        submitted = st.form_submit_button("Save config", disabled=demo_mode)

    if preview_submitted:
        auto_texts = split_text_lines(overlay_auto_texts_input)
        selected_text = select_overlay_text(
            overlay_text,
            auto_texts,
            overlay_auto_mode,
        )
        if not selected_text:
            st.warning("Add overlay text or auto texts to generate a preview.")
        else:
            preview_dir = ROOT / "runs" / "_preview"
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_text_path = preview_dir / "preview_overlay.txt"
            preview_text_path.write_text(selected_text, encoding="utf-8")

            preview_image_path = None
            if upload_image is not None:
                suffix = Path(upload_image.name).suffix or ".png"
                preview_image_path = preview_dir / f"preview_base{suffix}"
                preview_image_path.write_bytes(upload_image.getvalue())
            elif image_path:
                resolved_image = resolve_path(image_path)
                if resolved_image.exists():
                    preview_image_path = resolved_image
                else:
                    st.error(f"Image not found: {resolved_image}")
            elif auto_background:
                preview_image_path = preview_dir / "preview_base.png"
                generate_color_image(
                    preview_image_path,
                    resolution=resolution,
                    color=background_color,
                )
            else:
                st.warning("Provide an image or enable auto background to preview.")

            if preview_image_path:
                preview_font_path = None
                if upload_overlay_font is not None:
                    suffix = Path(upload_overlay_font.name).suffix or ".ttf"
                    preview_font_path = preview_dir / f"preview_font{suffix}"
                    preview_font_path.write_bytes(upload_overlay_font.getvalue())
                elif overlay_font_path:
                    resolved_font = resolve_path(overlay_font_path)
                    if resolved_font.exists():
                        preview_font_path = resolved_font

                drawtext_filter = build_drawtext_filter(
                    textfile=preview_text_path,
                    fontfile=preview_font_path,
                    font=overlay_font_name or None,
                    font_size=int(overlay_font_size),
                    font_color=overlay_font_color,
                    x=overlay_x,
                    y=overlay_y,
                    border_color=overlay_outline_color,
                    border_width=int(overlay_outline_width),
                    box_color=cfg(config, "text_overlay", "box_color", None),
                    box_borderw=cfg(config, "text_overlay", "box_borderw", None),
                    shadow_color=cfg(config, "text_overlay", "shadow_color", None),
                    shadow_x=cfg(config, "text_overlay", "shadow_x", None),
                    shadow_y=cfg(config, "text_overlay", "shadow_y", None),
                )
                preview_output = preview_dir / "thumbnail_preview.png"
                try:
                    render_image_with_text(
                        preview_image_path,
                        preview_output,
                        drawtext_filter,
                    )
                    st.session_state.preview_path = str(preview_output)
                    st.success(f"Preview generated with: {selected_text}")
                except RuntimeError as exc:
                    st.error(f"Preview failed: {exc}")

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
        if isinstance(loop_effects, str):
            loop_effects = [item.strip() for item in loop_effects.split(",") if item.strip()]

        config_out = {
            "project": {
                "name": project_name,
                "output_dir": output_dir,
            },
            "audio": {
                "source": audio_source,
                "drive_folder_id": drive_folder_id,
                "local_folder": local_folder or None,
                "ordering": ordering,
                "repeat_playlist": repeat_playlist,
                "recursive": recursive,
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
                "image_provider": image_provider,
                "openai_api_key_env": openai_api_key_env,
                "openai_model": openai_model,
                "openai_size": openai_size,
                "openai_quality": openai_quality or None,
                "openai_style": openai_style or None,
                "openai_base_url": openai_base_url or None,
                "loop_provider": loop_provider,
                "loop_zoom_amount": float(loop_zoom_amount),
                "loop_pan_amount": float(loop_pan_amount),
                "loop_motion_style": loop_motion_style,
                "loop_effects": loop_effects or [],
                "loop_sway_degrees": float(loop_sway_degrees),
                "loop_flicker_amount": float(loop_flicker_amount),
                "loop_hue_degrees": float(loop_hue_degrees),
                "loop_vignette_angle": loop_vignette_angle,
                "loop_steam_opacity": float(loop_steam_opacity),
                "loop_steam_blur": float(loop_steam_blur),
                "loop_steam_noise": int(loop_steam_noise),
                "loop_steam_drift_x": float(loop_steam_drift_x),
                "loop_steam_drift_y": float(loop_steam_drift_y),
                "auto_background": auto_background,
                "background_color": background_color,
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
                "auto_texts": split_text_lines(overlay_auto_texts_input),
                "auto_mode": overlay_auto_mode,
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
            "tracklist": {
                "enabled": tracklist_enabled,
                "filename": tracklist_filename or "tracklist.txt",
                "append_to_description": tracklist_append,
                "embed_chapters": tracklist_embed,
            },
            "test": {
                "enabled": test_enabled,
                "max_minutes": int(test_max_minutes) if test_max_minutes else None,
                "disable_upload": True,
                "repeat_playlist": False,
            },
            "schedule": {
                "enabled": schedule_enabled,
                "daily_time": daily_time,
            },
        }

        save_config(config_out)
        st.success(f"Saved config at {CONFIG_PATH}")

    preview_path = st.session_state.get("preview_path")
    if preview_path and Path(preview_path).exists():
        st.subheader("Thumbnail preview")
        st.image(preview_path, use_column_width=True)

    st.divider()
    st.subheader("Next steps")
    st.write(
        "1) Set WHISK_API_KEY and GROK_API_KEY in your environment. "
        "2) Run the agent once or schedule it."
    )
    st.code(
        ".\\run-once.ps1\n"
        ".\\run-test.ps1 -Minutes 10\n"
        ".\\schedule-task.ps1\n"
        ".\\schedule-task.ps1 -Remove",
        language="powershell",
    )
    st.caption(f"Today: {dt.date.today().isoformat()}")


if __name__ == "__main__":
    main()
