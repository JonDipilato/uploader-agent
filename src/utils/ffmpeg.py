from __future__ import annotations

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


def _escape_drawtext_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


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
) -> None:
    frames = max(int(duration_seconds * fps), 1)
    cycle = max(frames - 1, 1)
    zoom_expr = f"1+{zoom_amount}*sin(2*PI*on/{cycle})"
    filter_value = (
        f"scale={resolution},"
        "zoompan="
        f"z='{zoom_expr}':"
        "x='(iw-iw/zoom)/2':"
        "y='(ih-ih/zoom)/2':"
        "d=1:"
        f"s={resolution}:"
        f"fps={fps}"
    )
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
