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
    drive_folder_id = prompt("Google Drive folder ID (MP3s)", required=True)
    target_min_hours = prompt_int("Target hours minimum", 8)
    target_max_hours = prompt_int("Target hours maximum", 9)

    use_service_account = prompt_bool("Use Drive service account?", default=True)
    service_account_path = ""
    oauth_client_path = ""
    drive_token_path = ""
    if use_service_account:
        service_account_path = prompt_path(
            "Path to Drive service account JSON",
            "secrets/drive_service_account.json",
        )
        sa_src = normalize_path(service_account_path)
        sa_dest = ROOT / "secrets" / "drive_service_account.json"
        service_account_path = path_for_config(maybe_copy_file("Drive service account", sa_src, sa_dest))
        oauth_client_path = "secrets/drive_oauth_client.json"
        drive_token_path = "secrets/drive_token.json"
    else:
        oauth_client_path = prompt_path(
            "Path to Drive OAuth client JSON",
            "secrets/drive_oauth_client.json",
        )
        oauth_src = normalize_path(oauth_client_path)
        oauth_dest = ROOT / "secrets" / "drive_oauth_client.json"
        oauth_client_path = path_for_config(maybe_copy_file("Drive OAuth client", oauth_src, oauth_dest))
        drive_token_path = prompt_path(
            "Path to Drive OAuth token JSON (will be created)",
            "secrets/drive_token.json",
        )

    image_path = prompt_path("Existing image path (leave blank to generate)", "")
    image_prompt = ""
    if not image_path:
        image_prompt = prompt(
            "Whisk image prompt",
            "cozy fireplace on a rainy night, warm glow, cinematic, high detail",
        )

    loop_video_path = prompt_path("Existing loop video path (leave blank to generate)", "")
    video_prompt = ""
    if not loop_video_path:
        video_prompt = prompt(
            "Grok video prompt",
            "subtle fire animation, gentle embers drifting, loopable, 5s",
        )

    loop_duration = prompt_int("Loop duration seconds", 5)
    fps = prompt_int("FPS", 30)

    overlay_text = prompt("Overlay text (blank for none)", "")
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
  drive_folder_id: {yaml_quote(drive_folder_id)}
  ordering: "name"
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
"""

    config_path = ROOT / "config.yaml"
    config_path.write_text(config_text, encoding="utf-8")
    print(f"Wrote {config_path}")


if __name__ == "__main__":
    main()
