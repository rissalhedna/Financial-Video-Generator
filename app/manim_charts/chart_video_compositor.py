import subprocess
import random
from pathlib import Path


def compose_with_background(background_mp4: str, chart_mov: str) -> str:
    """
    Overlays a (transparent) chart .mov on top of a background .mp4 and returns the output .mp4 path.
    Assumes portrait 1080x1920 output.
    """
    bg = Path(background_mp4)
    fg = Path(chart_mov)

    if not bg.exists():
        raise FileNotFoundError(f"Background video not found: {bg}")
    if not fg.exists():
        raise FileNotFoundError(f"Chart video not found: {fg}")

    out_mp4 = fg.with_name(f"{fg.stem}_with_bg.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(bg),
        "-i", str(fg),
        "-filter_complex",
        # scale+crop background to 9:16, then overlay chart at 0:0 (chart is already 1080x1920)
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];"
        "[bg][1:v]overlay=0:0:format=auto[v]",
        "-map", "[v]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "veryfast",
        str(out_mp4),
    ]

    subprocess.run(cmd, check=True)
    return str(out_mp4)


def pick_background_video(background_dir: str, default_background: str) -> str:
    bg_dir = Path(background_dir)

    if not bg_dir.exists() or not bg_dir.is_dir():
        return default_background

    videos = sorted([*bg_dir.glob("*.mp4"), *bg_dir.glob("*.mov")])
    if not videos:
        return default_background

    return str(random.choice(videos))