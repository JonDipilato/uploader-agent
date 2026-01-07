#!/usr/bin/env python3
"""
Demo script: Generate 3 thumbnail text overlay style variations.

Style characteristics:
- Font: Montserrat ExtraBold
- All capitalized
- Letter spacing (spaced characters like "H Y P E R F O C U S E D")
- Centered horizontally
- Spans left to right
"""

import subprocess
import tempfile
from pathlib import Path


def add_letter_spacing(text: str, spacing: int = 1) -> str:
    """Add spaces between each character for letter-spacing effect."""
    spaced = (" " * spacing).join(text.upper())
    return spaced


def escape_drawtext(value: str) -> str:
    """Escape special characters for ffmpeg drawtext filter."""
    # Escape backslash first, then other special chars
    value = value.replace("\\", "\\\\")
    value = value.replace(":", "\\:")
    value = value.replace("'", "\\'")
    return value


def render_style_1(
    input_path: Path,
    output_path: Path,
    text: str,
    fontfile: Path,
) -> None:
    """
    Style 1: Clean minimal - white text, thin black border, centered.
    """
    spaced_text = add_letter_spacing(text, spacing=2)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(spaced_text)
        textfile = Path(f.name)

    try:
        filter_str = (
            f"drawtext="
            f"textfile='{escape_drawtext(textfile.as_posix())}':"
            f"fontfile='{escape_drawtext(fontfile.as_posix())}':"
            f"fontcolor=white:"
            f"fontsize=72:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2:"
            f"bordercolor=black:"
            f"borderw=2"
        )

        args = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", filter_str,
            "-frames:v", "1",
            str(output_path),
        ]
        subprocess.run(args, check=True, capture_output=True)
        print(f"Style 1 saved: {output_path}")
    finally:
        textfile.unlink(missing_ok=True)


def render_style_2(
    input_path: Path,
    output_path: Path,
    text: str,
    fontfile: Path,
) -> None:
    """
    Style 2: Bold shadow - white text, strong drop shadow, larger font.
    """
    spaced_text = add_letter_spacing(text, spacing=2)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(spaced_text)
        textfile = Path(f.name)

    try:
        filter_str = (
            f"drawtext="
            f"textfile='{escape_drawtext(textfile.as_posix())}':"
            f"fontfile='{escape_drawtext(fontfile.as_posix())}':"
            f"fontcolor=white:"
            f"fontsize=80:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2:"
            f"shadowcolor=black@0.8:"
            f"shadowx=4:"
            f"shadowy=4"
        )

        args = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", filter_str,
            "-frames:v", "1",
            str(output_path),
        ]
        subprocess.run(args, check=True, capture_output=True)
        print(f"Style 2 saved: {output_path}")
    finally:
        textfile.unlink(missing_ok=True)


def render_style_3(
    input_path: Path,
    output_path: Path,
    text: str,
    fontfile: Path,
) -> None:
    """
    Style 3: Premium glow - white text, border + shadow combo, positioned lower.
    """
    spaced_text = add_letter_spacing(text, spacing=2)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(spaced_text)
        textfile = Path(f.name)

    try:
        filter_str = (
            f"drawtext="
            f"textfile='{escape_drawtext(textfile.as_posix())}':"
            f"fontfile='{escape_drawtext(fontfile.as_posix())}':"
            f"fontcolor=white:"
            f"fontsize=68:"
            f"x=(w-text_w)/2:"
            f"y=h-text_h-100:"  # Positioned near bottom
            f"bordercolor=black@0.6:"
            f"borderw=3:"
            f"shadowcolor=black@0.5:"
            f"shadowx=2:"
            f"shadowy=2"
        )

        args = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", filter_str,
            "-frames:v", "1",
            str(output_path),
        ]
        subprocess.run(args, check=True, capture_output=True)
        print(f"Style 3 saved: {output_path}")
    finally:
        textfile.unlink(missing_ok=True)


def render_style_4(
    input_path: Path,
    output_path: Path,
    text: str,
    fontfile: Path,
) -> None:
    """
    Style 4: Premium top-left - large text spanning screen width, positioned top-left.
    """
    spaced_text = add_letter_spacing(text, spacing=2)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(spaced_text)
        textfile = Path(f.name)

    try:
        filter_str = (
            f"drawtext="
            f"textfile='{escape_drawtext(textfile.as_posix())}':"
            f"fontfile='{escape_drawtext(fontfile.as_posix())}':"
            f"fontcolor=white:"
            f"fontsize=115:"  # Larger to span screen
            f"x=60:"  # Left margin
            f"y=60:"  # Top margin
            f"bordercolor=black@0.6:"
            f"borderw=3:"
            f"shadowcolor=black@0.5:"
            f"shadowx=3:"
            f"shadowy=3"
        )

        args = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", filter_str,
            "-frames:v", "1",
            str(output_path),
        ]
        subprocess.run(args, check=True, capture_output=True)
        print(f"Style 4 saved: {output_path}")
    finally:
        textfile.unlink(missing_ok=True)


def render_style_with_subtitle(
    input_path: Path,
    output_path: Path,
    main_text: str,
    subtitle: str,
    fontfile: Path,
    main_spacing: int = 2,
    subtitle_spacing: int = 1,
    main_size: int = 115,
    subtitle_size: int = 32,
) -> None:
    """
    Premium style with main text + subtitle underneath.
    """
    spaced_main = add_letter_spacing(main_text, spacing=main_spacing)
    spaced_sub = add_letter_spacing(subtitle, spacing=subtitle_spacing)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f1:
        f1.write(spaced_main)
        main_textfile = Path(f1.name)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f2:
        f2.write(spaced_sub)
        sub_textfile = Path(f2.name)

    try:
        # Two drawtext filters: main text + subtitle
        filter_str = (
            f"drawtext="
            f"textfile='{escape_drawtext(main_textfile.as_posix())}':"
            f"fontfile='{escape_drawtext(fontfile.as_posix())}':"
            f"fontcolor=white:"
            f"fontsize={main_size}:"
            f"x=60:"
            f"y=60:"
            f"bordercolor=black@0.6:"
            f"borderw=3:"
            f"shadowcolor=black@0.5:"
            f"shadowx=3:"
            f"shadowy=3,"
            f"drawtext="
            f"textfile='{escape_drawtext(sub_textfile.as_posix())}':"
            f"fontfile='{escape_drawtext(fontfile.as_posix())}':"
            f"fontcolor=white@0.85:"
            f"fontsize={subtitle_size}:"
            f"x=65:"
            f"y=60+{main_size}+20:"  # Below main text with gap
            f"shadowcolor=black@0.4:"
            f"shadowx=2:"
            f"shadowy=2"
        )

        args = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", filter_str,
            "-frames:v", "1",
            str(output_path),
        ]
        subprocess.run(args, check=True, capture_output=True)
        print(f"Saved: {output_path}")
    finally:
        main_textfile.unlink(missing_ok=True)
        sub_textfile.unlink(missing_ok=True)


def main():
    # Source image - use latest thumbnail or visual
    source_candidates = [
        Path("/mnt/c/Users/jon-d/Downloads/Music/cafe.png"),
        Path("runs/_preview/grok_frame.png"),
        Path("runs/20251223_151729/thumbnail.png"),
        Path("runs/20251222_150526/visual.png"),
    ]

    source_image = None
    for candidate in source_candidates:
        if candidate.exists():
            source_image = candidate
            break

    if not source_image:
        print("No source image found. Creating a cozy cafe-style background...")
        # Create a warm dark cafe-style background gradient
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "color=c=0x2d1810:s=1920x1080:d=1",
            "-frames:v", "1",
            "test_bg.png"
        ], check=True, capture_output=True)
        source_image = Path("test_bg.png")

    print(f"Using source image: {source_image}")

    # Font file - Montserrat ExtraBold
    font_candidates = [
        Path("fonts/Montserrat-ExtraBold.ttf"),
        Path("fonts/montserrat/Montserrat-ExtraBold.ttf"),
        Path("/usr/share/fonts/truetype/montserrat/Montserrat-ExtraBold.ttf"),
        Path("C:/Windows/Fonts/Montserrat-ExtraBold.ttf"),
    ]

    fontfile = None
    for candidate in font_candidates:
        if candidate.exists():
            fontfile = candidate
            break

    if not fontfile:
        print("Montserrat ExtraBold not found. Please install it or update the font path.")
        print("Download from: https://fonts.google.com/specimen/Montserrat")
        print("\nAttempting with system default font...")
        # Create a minimal font reference for testing
        fontfile = Path("fonts/Montserrat-ExtraBold.ttf")
        if not fontfile.exists():
            print(f"Font not found at {fontfile}. Please add the font file.")
            return

    print(f"Using font: {fontfile}")

    # Output directory
    output_dir = Path("runs/_style_demos")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Text to render
    text = "HYPERFOCUSED"

    print(f"\nRendering text: '{text}' -> '{add_letter_spacing(text, 2)}'")
    print("-" * 60)

    # Generate all 3 styles
    render_style_1(
        source_image,
        output_dir / "style_1_minimal.png",
        text,
        fontfile,
    )

    render_style_2(
        source_image,
        output_dir / "style_2_shadow.png",
        text,
        fontfile,
    )

    render_style_3(
        source_image,
        output_dir / "style_3_premium.png",
        text,
        fontfile,
    )

    render_style_4(
        source_image,
        output_dir / "style_4_premium_top_left.png",
        text,
        fontfile,
    )

    # New variations with subtitles and different words
    print("\nGenerating subtitle variations...")

    # Variation A: HYPERFOCUSED + subtitle
    render_style_with_subtitle(
        source_image,
        output_dir / "style_5a_hyperfocused_subtitle.png",
        "HYPERFOCUSED",
        "DEEP WORK MODE",
        fontfile,
    )

    # Variation B: DEEP WORK as main
    render_style_with_subtitle(
        source_image,
        output_dir / "style_5b_deepwork.png",
        "DEEP WORK",
        "FLOW STATE ACTIVATED",
        fontfile,
        main_size=115,
    )

    # Variation C: FLOW STATE
    render_style_with_subtitle(
        source_image,
        output_dir / "style_5c_flowstate.png",
        "FLOW STATE",
        "ZERO DISTRACTIONS",
        fontfile,
        main_size=115,
    )

    # Variation D: FOCUSED (shorter word)
    render_style_with_subtitle(
        source_image,
        output_dir / "style_5d_focused.png",
        "FOCUSED",
        "STAY IN THE ZONE",
        fontfile,
        main_size=140,
    )

    # Variation E: CONCENTRATE
    render_style_with_subtitle(
        source_image,
        output_dir / "style_5e_concentrate.png",
        "CONCENTRATE",
        "PRODUCTIVITY UNLOCKED",
        fontfile,
        main_size=100,
    )

    print("-" * 60)
    print(f"\nAll styles saved to: {output_dir.absolute()}")
    print("\nStyle descriptions:")
    print("  1. Minimal: Clean white text, thin black border, centered")
    print("  2. Shadow: Bold drop shadow, larger font, centered")
    print("  3. Premium: Border + shadow combo, positioned near bottom")
    print("  4. Premium Top-Left: Large text spanning width, top-left position")
    print("\nSubtitle variations (5a-5e):")
    print("  5a. HYPERFOCUSED + 'DEEP WORK MODE'")
    print("  5b. DEEP WORK + 'FLOW STATE ACTIVATED'")
    print("  5c. FLOW STATE + 'ZERO DISTRACTIONS'")
    print("  5d. FOCUSED + 'STAY IN THE ZONE'")
    print("  5e. CONCENTRATE + 'PRODUCTIVITY UNLOCKED'")


if __name__ == "__main__":
    main()
