from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"


def prompt(text: str, default: str | None = None, required: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"{text}{suffix}: ").strip()
        if not value and default is not None:
            return default
        if value:
            return value
        if not required:
            return ""
        print("Value required.")


def prompt_bool(text: str, default: bool = True) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        value = input(f"{text}{suffix}: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Enter y or n.")


def prompt_int(text: str, default: int) -> int:
    while True:
        value = prompt(text, str(default))
        try:
            return int(value)
        except ValueError:
            print("Enter a whole number.")


def prompt_float(text: str, default: float) -> float:
    while True:
        value = prompt(text, str(default))
        try:
            return float(value)
        except ValueError:
            print("Enter a number.")


def prompt_path(text: str, default: str | None = None) -> str:
    return prompt(text, default=default, required=False)


def normalize_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path


def path_for_config(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def maybe_copy_file(label: str, src_path: Path, default_dest: Path) -> Path:
    if not src_path.exists():
        print(f"Warning: {label} file not found at {src_path}")
        return src_path
    if default_dest.exists() and default_dest.samefile(src_path):
        return default_dest
    if src_path.resolve() == default_dest.resolve():
        return default_dest
    if prompt_bool(f"Copy {label} into {default_dest}?", default=True):
        default_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, default_dest)
        return default_dest
    return src_path


def yaml_quote(value: str | None) -> str:
    if value is None or value == "":
        return "null"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_list(values: list[str]) -> str:
    lines = []
    for item in values:
        lines.append(f"  - {yaml_quote(item)}")
    return "\n".join(lines) if lines else "  - \"\""


def main() -> None:
    print("Video Creator Agent setup wizard")
    print("Press Enter to accept defaults.")

    project_name = prompt("Project name", "daily_chill_mix")
    audio_source = prompt("Audio source (local/drive)", "local").strip().lower()
    if audio_source not in {"local", "drive"}:
        audio_source = "local"
    local_folder = ""
    drive_folder_id = ""
    if audio_source == "local":
        local_folder = prompt("Local folder path (MP3s)", "C:\\Users\\USERNAME\\Music")
    else:
        drive_folder_id = prompt("Google Drive folder ID (MP3s)", required=True)
    repeat_playlist = prompt_bool("Repeat playlist to reach target hours?", default=True)
    recursive = prompt_bool("Scan subfolders for MP3s?", default=False)
    target_min_hours = prompt_int("Target hours minimum", 8)
    target_max_hours = prompt_int("Target hours maximum", 9)

    use_service_account = True
    service_account_path = "secrets/drive_service_account.json"
    oauth_client_path = "secrets/drive_oauth_client.json"
    drive_token_path = "secrets/drive_token.json"
    if audio_source == "drive":
        use_service_account = prompt_bool("Use Drive service account?", default=True)
        if use_service_account:
            service_account_path = prompt_path(
                "Path to Drive service account JSON",
                "secrets/drive_service_account.json",
            )
            sa_src = normalize_path(service_account_path)
            sa_dest = ROOT / "secrets" / "drive_service_account.json"
            service_account_path = path_for_config(
                maybe_copy_file("Drive service account", sa_src, sa_dest)
            )
        else:
            oauth_client_path = prompt_path(
                "Path to Drive OAuth client JSON",
                "secrets/drive_oauth_client.json",
            )
            oauth_src = normalize_path(oauth_client_path)
            oauth_dest = ROOT / "secrets" / "drive_oauth_client.json"
            oauth_client_path = path_for_config(
                maybe_copy_file("Drive OAuth client", oauth_src, oauth_dest)
            )
            drive_token_path = prompt_path(
                "Path to Drive OAuth token JSON (will be created)",
                "secrets/drive_token.json",
            )

    image_path = prompt_path("Existing image path (leave blank to generate)", "")
    image_prompt = ""
    auto_background = False
    image_provider = "whisk"
    openai_api_key_env = "OPENAI_API_KEY"
    openai_model = "gpt-image-1"
    openai_size = "1792x1024"
    openai_quality = ""
    openai_style = ""
    openai_base_url = "https://api.openai.com/v1/images/generations"
    if not image_path:
        auto_background = prompt_bool("Auto-generate background (no Whisk)?", default=False)
    if not image_path and not auto_background:
        image_provider = prompt("Image provider (whisk/openai)", "openai").strip().lower()
        if image_provider not in {"whisk", "openai"}:
            image_provider = "openai"
        image_prompt = prompt(
            "Image prompt",
            "cozy coffee shop interior, warm light, cinematic, empty space for title text \"{overlay_text}\", high detail",
        )
        if image_provider == "openai":
            openai_api_key_env = prompt("OpenAI API key env var", "OPENAI_API_KEY")
            openai_model = prompt("OpenAI image model", "gpt-image-1")
            openai_size = prompt("OpenAI image size", "1792x1024")
            openai_quality = prompt("OpenAI quality (optional)", "")
            openai_style = prompt("OpenAI style (optional)", "")

    loop_video_path = prompt_path("Existing loop video path (leave blank to generate)", "")
    loop_provider = prompt("Loop generator (ffmpeg/grok)", "ffmpeg").strip().lower()
    if loop_provider not in {"ffmpeg", "grok"}:
        loop_provider = "ffmpeg"
    video_prompt = ""
    if not loop_video_path and loop_provider == "grok":
        video_prompt = prompt(
            "Grok video prompt",
            "subtle fire animation, gentle embers drifting, loopable, 5s",
        )

    loop_duration = prompt_int("Loop duration seconds", 5)
    fps = prompt_int("FPS", 30)
    loop_zoom_amount = 0.02
    loop_pan_amount = 0.15
    loop_motion_style = "cinematic"
    loop_effects: list[str] = []
    loop_sway_degrees = 0.35
    loop_flicker_amount = 0.015
    loop_hue_degrees = 0.0
    loop_vignette_angle = 0.63
    loop_steam_opacity = 0.08
    loop_steam_blur = 10.0
    loop_steam_noise = 12
    loop_steam_drift_x = 0.02
    loop_steam_drift_y = 0.05
    if loop_provider == "ffmpeg":
        loop_zoom_amount = prompt_float("Loop zoom amount (subtle motion)", 0.02)
        loop_pan_amount = prompt_float("Loop pan amount (0 = no pan)", 0.15)
        loop_motion_style = prompt("Motion style (smooth/cinematic/orbit)", "cinematic").strip().lower()
        if loop_motion_style not in {"smooth", "cinematic", "orbit"}:
            loop_motion_style = "cinematic"
        if prompt_bool("Add coffee steam drift?", default=False):
            loop_effects.append("steam")
            loop_steam_opacity = prompt_float("Steam opacity", 0.08)
            loop_steam_blur = prompt_float("Steam blur", 10.0)
            loop_steam_noise = prompt_int("Steam noise", 12)
            loop_steam_drift_x = prompt_float("Steam drift X", 0.02)
            loop_steam_drift_y = prompt_float("Steam drift Y", 0.05)
        if prompt_bool("Add extra loop effects (flicker/vignette)?", default=True):
            loop_effects.extend(["flicker", "vignette"])
            loop_flicker_amount = prompt_float("Flicker amount", 0.015)
            loop_vignette_angle = prompt_float("Vignette angle (lower = stronger)", 0.63)
            if prompt_bool("Add gentle sway rotation?", default=False):
                loop_effects.append("sway")
                loop_sway_degrees = prompt_float("Sway degrees (rotation)", 0.35)
            if prompt_bool("Add subtle color drift?", default=False):
                loop_effects.append("color_drift")
                loop_hue_degrees = prompt_float("Color drift degrees", 1.5)

    overlay_text = prompt("Overlay text (blank for none)", "")
    overlay_auto_texts: list[str] = []
    overlay_auto_mode = "daily"
    if not overlay_text and prompt_bool("Rotate auto overlay text each day?", default=False):
        raw_auto_texts = prompt(
            "Auto overlay texts (comma-separated)",
            "LOCK IN, HYPER FOCUS, SLOW DOWN",
        )
        overlay_auto_texts = [item.strip() for item in raw_auto_texts.split(",") if item.strip()]
        overlay_auto_mode = prompt("Auto text mode (daily/random)", "daily").strip().lower()
        if overlay_auto_mode not in {"daily", "random"}:
            overlay_auto_mode = "daily"
    overlay_apply_to_video = True
    overlay_create_thumbnail = True
    overlay_upload_thumbnail = False
    overlay_font_path = ""
    overlay_font_size = 96
    overlay_font_color = "white"
    overlay_outline_color = "black"
    overlay_outline_width = 4
    overlay_x = "(w-text_w)/2"
    overlay_y = "(h-text_h)/2"
    if overlay_text:
        overlay_apply_to_video = prompt_bool("Apply overlay to video?", default=True)
        overlay_create_thumbnail = prompt_bool("Create thumbnail with overlay?", default=True)
        overlay_upload_thumbnail = prompt_bool("Upload thumbnail to YouTube?", default=False)
        overlay_font_path = prompt_path("Overlay font file path (optional)", "")
        if overlay_font_path:
            font_src = normalize_path(overlay_font_path)
            font_dest = ASSETS_DIR / "overlay_font.ttf"
            overlay_font_path = path_for_config(
                maybe_copy_file("Overlay font", font_src, font_dest)
            )
        overlay_font_size = prompt_int("Overlay font size", 96)
        overlay_font_color = prompt("Overlay font color", "white")
        overlay_outline_color = prompt("Outline color", "black")
        overlay_outline_width = prompt_int("Outline width", 4)
        position = prompt("Position (center/lower/top)", "center").strip().lower()
        if position == "lower":
            overlay_x = "(w-text_w)/2"
            overlay_y = "(h-text_h)*0.75"
        elif position == "top":
            overlay_x = "(w-text_w)/2"
            overlay_y = "(h-text_h)*0.15"

    youtube_client_path = prompt_path(
        "Path to YouTube OAuth client JSON",
        "secrets/youtube_client.json",
    )
    yt_src = normalize_path(youtube_client_path)
    yt_dest = ROOT / "secrets" / "youtube_client.json"
    youtube_client_path = path_for_config(maybe_copy_file("YouTube OAuth client", yt_src, yt_dest))
    youtube_token_path = prompt_path(
        "Path to YouTube OAuth token JSON (will be created)",
        "secrets/youtube_token.json",
    )

    privacy_status = prompt("YouTube privacy status", "public")
    category_id = prompt("YouTube category ID", "10")
    title_template = prompt("Title template", "Daily Chill Mix - {date}")
    description_template = prompt(
        "Description template",
        "Longform ambient mix. Generated daily.",
    )
    tags_raw = prompt("Tags (comma-separated)", "ambient, chill, fireplace")
    tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]

    daily_time = prompt("Daily publish time (HH:MM, 24h)", "03:00")

    tracklist_enabled = prompt_bool("Generate tracklist timestamps?", default=True)
    tracklist_append = prompt_bool("Append tracklist to description?", default=True)
    tracklist_embed = prompt_bool("Embed chapters into MP4?", default=True)
    tracklist_filename = prompt("Tracklist filename", "tracklist.txt")

    test_enabled = prompt_bool("Enable test mode (no upload, no repeat)?", default=False)
    test_max_minutes = prompt_int("Test max minutes (0 = full length)", 0)

    whisk_command = [
        "whisk",
        "image",
        "--prompt",
        "{prompt}",
        "--out",
        "{output_path}",
    ]
    grok_command = [
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
    ]

    config_text = f"""project:
  name: {yaml_quote(project_name)}
  output_dir: "runs"

audio:
  source: {yaml_quote(audio_source)}
  drive_folder_id: {yaml_quote(drive_folder_id)}
  local_folder: {yaml_quote(local_folder) if local_folder else "null"}
  ordering: "name"
  repeat_playlist: {"true" if repeat_playlist else "false"}
  recursive: {"true" if recursive else "false"}
  target_hours_min: {target_min_hours}
  target_hours_max: {target_max_hours}
  concat_codec: "libmp3lame"
  concat_quality: 2
  concat_bitrate: null

drive:
  use_service_account: {"true" if use_service_account else "false"}
  service_account_json: {yaml_quote(service_account_path) if use_service_account else "null"}
  oauth_client_json: {yaml_quote(oauth_client_path) if not use_service_account else "null"}
  token_json: {yaml_quote(drive_token_path) if not use_service_account else "null"}

visuals:
  image_prompt: {yaml_quote(image_prompt)}
  video_prompt: {yaml_quote(video_prompt)}
  loop_duration_seconds: {loop_duration}
  fps: {fps}
  image_path: {yaml_quote(path_for_config(normalize_path(image_path))) if image_path else "null"}
  loop_video_path: {yaml_quote(path_for_config(normalize_path(loop_video_path))) if loop_video_path else "null"}
  image_provider: {yaml_quote(image_provider)}
  openai_api_key_env: {yaml_quote(openai_api_key_env)}
  openai_model: {yaml_quote(openai_model)}
  openai_size: {yaml_quote(openai_size)}
  openai_quality: {yaml_quote(openai_quality) if openai_quality else "null"}
  openai_style: {yaml_quote(openai_style) if openai_style else "null"}
  openai_base_url: {yaml_quote(openai_base_url)}
  loop_provider: {yaml_quote(loop_provider)}
  loop_zoom_amount: {loop_zoom_amount}
  loop_pan_amount: {loop_pan_amount}
  loop_motion_style: {yaml_quote(loop_motion_style)}
  loop_effects:
{yaml_list(loop_effects)}
  loop_sway_degrees: {loop_sway_degrees}
  loop_flicker_amount: {loop_flicker_amount}
  loop_hue_degrees: {loop_hue_degrees}
  loop_vignette_angle: {loop_vignette_angle}
  loop_steam_opacity: {loop_steam_opacity}
  loop_steam_blur: {loop_steam_blur}
  loop_steam_noise: {loop_steam_noise}
  loop_steam_drift_x: {loop_steam_drift_x}
  loop_steam_drift_y: {loop_steam_drift_y}
  auto_background: {"true" if auto_background else "false"}
  background_color: "black"
  whisk_mode: "command"
  whisk_command:
{yaml_list(whisk_command)}
  whisk_api_key_env: "WHISK_API_KEY"
  whisk_model: null
  grok_mode: "command"
  grok_command:
{yaml_list(grok_command)}
  grok_api_key_env: "GROK_API_KEY"
  grok_model: null

text_overlay:
  text: {yaml_quote(overlay_text) if overlay_text else "null"}
  auto_texts:
{yaml_list(overlay_auto_texts)}
  auto_mode: {yaml_quote(overlay_auto_mode)}
  fontfile: {yaml_quote(overlay_font_path) if overlay_font_path else "null"}
  font: null
  font_size: {overlay_font_size}
  font_color: {yaml_quote(overlay_font_color)}
  outline_color: {yaml_quote(overlay_outline_color)}
  outline_width: {overlay_outline_width}
  box_color: null
  box_borderw: null
  shadow_color: null
  shadow_x: null
  shadow_y: null
  x: {yaml_quote(overlay_x)}
  y: {yaml_quote(overlay_y)}
  apply_to_video: {"true" if overlay_apply_to_video else "false"}
  create_thumbnail: {"true" if overlay_create_thumbnail else "false"}
  upload_thumbnail: {"true" if overlay_upload_thumbnail else "false"}

video:
  resolution: "1920x1080"
  fps: {fps}
  video_bitrate: "4500k"
  audio_bitrate: "192k"

upload:
  enabled: true
  provider: "youtube"
  credentials_json: {yaml_quote(youtube_client_path)}
  token_json: {yaml_quote(youtube_token_path)}
  privacy_status: {yaml_quote(privacy_status)}
  category_id: {yaml_quote(category_id)}
  title_template: {yaml_quote(title_template)}
  description_template: {yaml_quote(description_template)}
  tags:
{yaml_list(tags)}

schedule:
  enabled: true
  daily_time: {yaml_quote(daily_time)}

tracklist:
  enabled: {"true" if tracklist_enabled else "false"}
  filename: {yaml_quote(tracklist_filename)}
  append_to_description: {"true" if tracklist_append else "false"}
  embed_chapters: {"true" if tracklist_embed else "false"}

test:
  enabled: {"true" if test_enabled else "false"}
  max_minutes: {test_max_minutes if test_max_minutes else "null"}
  disable_upload: true
  repeat_playlist: false
"""

    config_path = ROOT / "config.yaml"
    config_path.write_text(config_text, encoding="utf-8")
    print(f"Wrote {config_path}")


if __name__ == "__main__":
    main()
