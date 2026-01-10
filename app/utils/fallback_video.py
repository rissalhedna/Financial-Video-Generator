"""Generate guaranteed-relevant fallback visuals when retrieval fails.

We use ffmpeg to create a simple vertical "topic card" clip.
This prevents unrelated footage (storms/food/shoes) from ever leaking into output.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, Tuple


def create_text_card(
    output_path: Path,
    primary_text: str,
    secondary_text: Optional[str] = None,
    duration_seconds: float = 5.0,
    resolution: Tuple[int, int] = (720, 1280),
    fps: int = 30,
) -> Optional[Path]:
    """
    Create a simple color background video with centered text.

    If drawtext fails (missing fontconfig/drawtext), falls back to a plain color clip.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    w, h = resolution
    dur = max(float(duration_seconds), 1.0)

    # Write text to file to avoid escaping issues in drawtext.
    text_file = output_path.with_suffix(".txt")
    text_lines = [primary_text.strip()]
    if secondary_text and secondary_text.strip():
        text_lines.append(secondary_text.strip())
    text_file.write_text("\n".join(text_lines)[:400], encoding="utf-8")

    base = f"color=c=#0b1020:s={w}x{h}:d={dur}"

    # Try drawtext; if it fails, we fall back below.
    draw = (
        f"drawtext=textfile={text_file}:reload=1:"
        f"fontcolor=white:fontsize={max(int(h * 0.05), 32)}:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"line_spacing={max(int(h * 0.01), 10)}"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        base,
        "-vf",
        draw,
        "-r",
        str(fps),
        "-t",
        str(dur),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "veryfast",
        str(output_path),
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode == 0 and output_path.exists():
            return output_path
    except Exception:
        pass

    # Fallback: plain color clip (no text).
    cmd2 = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        base,
        "-r",
        str(fps),
        "-t",
        str(dur),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "veryfast",
        str(output_path),
    ]
    try:
        res2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
        if res2.returncode == 0 and output_path.exists():
            return output_path
    except Exception:
        return None

    return None

