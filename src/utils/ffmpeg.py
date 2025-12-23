from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Iterable


def run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()}")


def run_ffprobe(args: list[str]) -> str:
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    return result.stdout.strip()


def probe_duration_seconds(path: Path) -> float:
    output = run_ffprobe(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    return float(output)


def write_concat_list(files: Iterable[Path], list_path: Path) -> None:
    lines = []
    for file_path in files:
        safe_path = file_path.as_posix().replace("'", r"'\''")
        lines.append(f"file '{safe_path}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ffmetadata_chapters(
    playlist: Iterable[Path],
    duration_map: dict[Path, float],
    output_path: Path,
) -> None:
    lines = [";FFMETADATA1"]
    start_ms = 0
    for path in playlist:
        duration = duration_map.get(path)
        if duration is None:
            continue
        duration_ms = max(int(round(duration * 1000.0)), 1)
        end_ms = start_ms + duration_ms
        title = _escape_ffmetadata(path.stem)
        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start_ms}",
                f"END={end_ms}",
                f"title={title}",
            ]
        )
        start_ms = end_ms
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def concat_audio(
    list_path: Path,
    output_path: Path,
    codec: str = "libmp3lame",
    quality: int | None = 2,
    bitrate: str | None = None,
) -> None:
    args = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c:a",
        codec,
    ]
    if codec == "libmp3lame" and quality is not None:
        args += ["-q:a", str(quality)]
    if bitrate:
        args += ["-b:a", bitrate]
    args.append(str(output_path))
    run_ffmpeg(args)


def trim_audio(
    input_path: Path,
    output_path: Path,
    max_seconds: float,
    codec: str = "libmp3lame",
    quality: int | None = 2,
    bitrate: str | None = None,
) -> None:
    args = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-t",
        f"{max_seconds:.3f}",
        "-c:a",
        codec,
    ]
    if codec == "libmp3lame" and quality is not None:
        args += ["-q:a", str(quality)]
    if bitrate:
        args += ["-b:a", bitrate]
    args.append(str(output_path))
    run_ffmpeg(args)


def mux_chapters(
    input_video_path: Path,
    metadata_path: Path,
    output_path: Path,
) -> None:
    args = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video_path),
        "-f",
        "ffmetadata",
        "-i",
        str(metadata_path),
        "-map",
        "0",
        "-map_metadata",
        "1",
        "-codec",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run_ffmpeg(args)


def _escape_drawtext_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _escape_ffmetadata(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("=", "\\=")
        .replace(";", "\\;")
    )


def build_drawtext_filter(
    textfile: Path,
    fontfile: Path | None = None,
    font: str | None = None,
    font_size: int = 64,
    font_color: str = "white",
    x: str = "(w-text_w)/2",
    y: str = "(h-text_h)/2",
    border_color: str | None = "black",
    border_width: int | None = 4,
    box_color: str | None = None,
    box_borderw: int | None = None,
    shadow_color: str | None = None,
    shadow_x: int | None = None,
    shadow_y: int | None = None,
) -> str:
    args = []
    textfile_value = _escape_drawtext_value(textfile.as_posix())
    args.append(f"textfile={textfile_value}")
    if fontfile:
        fontfile_value = _escape_drawtext_value(fontfile.as_posix())
        args.append(f"fontfile={fontfile_value}")
    elif font:
        args.append(f"font={_escape_drawtext_value(font)}")
    args.append(f"fontcolor={font_color}")
    args.append(f"fontsize={int(font_size)}")
    args.append(f"x={x}")
    args.append(f"y={y}")
    if border_color and border_width:
        args.append(f"bordercolor={border_color}")
        args.append(f"borderw={int(border_width)}")
    if box_color and box_borderw:
        args.append("box=1")
        args.append(f"boxcolor={box_color}")
        args.append(f"boxborderw={int(box_borderw)}")
    if shadow_color and shadow_x is not None and shadow_y is not None:
        args.append(f"shadowcolor={shadow_color}")
        args.append(f"shadowx={int(shadow_x)}")
        args.append(f"shadowy={int(shadow_y)}")
    return "drawtext=" + ":".join(args)


def render_image_with_text(
    input_path: Path,
    output_path: Path,
    drawtext_filter: str,
) -> None:
    args = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        drawtext_filter,
        "-frames:v",
        "1",
        str(output_path),
    ]
    run_ffmpeg(args)


def generate_loop_video_from_image(
    image_path: Path,
    output_path: Path,
    duration_seconds: int = 5,
    fps: int = 30,
    resolution: str = "1920x1080",
    zoom_amount: float = 0.02,
    pan_amount: float = 0.0,
    effects: Iterable[str] | None = None,
    sway_degrees: float = 0.0,
    flicker_amount: float = 0.0,
    hue_degrees: float = 0.0,
    vignette_angle: str | float | None = None,
    motion_style: str = "smooth",
    steam_opacity: float = 0.08,
    steam_blur: float = 10.0,
    steam_noise: int = 12,
    steam_drift_x: float = 0.02,
    steam_drift_y: float = 0.05,
) -> None:
    frames = max(int(duration_seconds * fps), 1)
    cycle = max(frames - 1, 1)
    phase = f"(2*PI*on/{cycle})"
    phase2 = f"(4*PI*on/{cycle})"
    style = motion_style.strip().lower() if motion_style else "smooth"
    if style == "cinematic":
        zoom_mix = f"(0.7*sin({phase})+0.3*sin({phase2}+PI/3))"
        pan_x_mix = f"(0.8*sin({phase}+PI/6)+0.2*sin({phase2}))"
        pan_y_mix = f"(0.8*cos({phase}+PI/3)+0.2*cos({phase2}+PI/4))"
    elif style == "orbit":
        zoom_mix = f"sin({phase})"
        pan_x_mix = f"sin({phase})"
        pan_y_mix = f"sin({phase}+PI/2)"
    else:
        zoom_mix = f"sin({phase})"
        pan_x_mix = f"sin({phase})"
        pan_y_mix = f"cos({phase})"
    zoom_base = 1.0 + zoom_amount
    zoom_expr = f"{zoom_base}+{zoom_amount}*{zoom_mix}"
    pan_x_expr = f"((iw-iw/zoom)/2)*{pan_amount}*{pan_x_mix}"
    pan_y_expr = f"((ih-ih/zoom)/2)*{pan_amount}*{pan_y_mix}"
    base_filters = [
        f"scale={resolution}",
        (
            "zoompan="
            f"z='{zoom_expr}':"
            f"x='(iw-iw/zoom)/2+{pan_x_expr}':"
            f"y='(ih-ih/zoom)/2+{pan_y_expr}':"
            "d=1:"
            f"s={resolution}:"
            f"fps={fps}"
        ),
    ]
    effect_set = {item.strip().lower() for item in (effects or []) if item}
    period = max(float(duration_seconds), 0.1)
    post_filters = []
    if "sway" in effect_set and sway_degrees > 0:
        sway_radians = math.radians(sway_degrees)
        rotate_expr = f"{sway_radians}*sin(2*PI*t/{period})"
        post_filters.append(f"rotate='{rotate_expr}':c=black@0:ow=iw:oh=ih")
    if "flicker" in effect_set and flicker_amount > 0:
        post_filters.append(f"eq=brightness='{flicker_amount}*sin(2*PI*t/{period})'")
    if ("color_drift" in effect_set or "hue" in effect_set) and hue_degrees > 0:
        post_filters.append(f"hue=h='{hue_degrees}*sin(2*PI*t/{period})'")
    if "vignette" in effect_set:
        vignette_expr = _format_vignette_angle(vignette_angle)
        post_filters.append(f"vignette=angle={vignette_expr}")
    if "steam" in effect_set:
        steam_opacity = max(0.0, min(float(steam_opacity), 1.0))
        steam_blur = max(float(steam_blur), 0.0)
        steam_noise = max(int(steam_noise), 0)
        steam_drift_x = max(float(steam_drift_x), 0.0)
        steam_drift_y = max(float(steam_drift_y), 0.0)
        steam_filters = (
            "crop=w=iw*0.45:h=ih*0.6:x=iw*0.275:y=ih*0.32,"
            f"gblur=sigma={steam_blur}:steps=2,"
            f"noise=alls={steam_noise}:allf=t+u,"
            "eq=brightness=0.04,"
            f"colorchannelmixer=aa={steam_opacity}"
        )
        overlay_x = f"(W-w)/2 + (W*{steam_drift_x})*sin(2*PI*t/{period})"
        overlay_y = f"(H*0.5) - (H*{steam_drift_y})*sin(2*PI*t/{period}+PI/3)"
        overlay_chain = (
            f"[base][steam2]overlay=x='{overlay_x}':y='{overlay_y}'"
        )
        if post_filters:
            overlay_chain = overlay_chain + "," + ",".join(post_filters)
        filter_value = (
            f"{','.join(base_filters)},format=rgba,split=2[base][steam];"
            f"[steam]{steam_filters}[steam2];"
            f"{overlay_chain}"
        )
    else:
        filter_value = ",".join(base_filters + post_filters)
    args = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-t",
        str(duration_seconds),
        "-vf",
        filter_value,
        "-r",
        str(fps),
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    run_ffmpeg(args)


def _format_vignette_angle(value: str | float | None) -> str:
    if value is None:
        return "PI/5"
    if isinstance(value, (int, float)):
        return f"{float(value):.4f}"
    value = str(value).strip()
    return value or "PI/5"


def generate_color_image(
    output_path: Path,
    resolution: str = "1920x1080",
    color: str = "black",
) -> None:
    args = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s={resolution}",
        "-frames:v",
        "1",
        str(output_path),
    ]
    run_ffmpeg(args)

def render_video(
    loop_video_path: Path,
    audio_path: Path,
    output_path: Path,
    resolution: str = "1920x1080",
    fps: int = 30,
    video_bitrate: str = "4500k",
    audio_bitrate: str = "192k",
    duration_seconds: float | None = None,
    drawtext_filter: str | None = None,
) -> None:
    filters = [f"scale={resolution}"]
    if drawtext_filter:
        filters.append(drawtext_filter)
    filter_value = ",".join(filters)
    args = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(loop_video_path),
        "-i",
        str(audio_path),
        "-vf",
        filter_value,
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-b:v",
        video_bitrate,
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-shortest",
    ]
    if duration_seconds is not None:
        args += ["-t", f"{duration_seconds:.3f}"]
    args.append(str(output_path))
    run_ffmpeg(args)
