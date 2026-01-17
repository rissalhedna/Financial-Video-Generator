from pathlib import Path
import subprocess
from manim import config
from .line_chart import LineChartScene
from .pie_chart import PieChartScene
from .bar_chart import BarChartScene


def render_line_chart(labels, values, title="Line Chart", x_axis_label=None, y_axis_label=None, transparent=False) -> str:
    """Wrapper function: creates the Manim Line Chart scene and renders it."""
    scene = LineChartScene(
        labels=labels,
        values=values,
        title=title,
        x_axis_label=x_axis_label,
        y_axis_label=y_axis_label,
        transparent=transparent,
    )
    return _render_and_get_path(scene, transparent=transparent)


def render_pie_chart(labels, values, title, transparent=False) -> str:
    """Wrapper function: creates the Manim Pie Chart scene and renders it."""
    scene = PieChartScene(labels=labels, values=values, title=title, transparent=transparent)
    return _render_and_get_path(scene, transparent=transparent)


def render_bar_chart(labels, values, title, x_axis_label=None, y_axis_label=None, transparent=False) -> str:
    """Wrapper function: creates the Manim Bar Chart scene and renders it."""
    scene = BarChartScene(
        labels=labels,
        values=values,
        title=title,
        x_axis_label=x_axis_label,
        y_axis_label=y_axis_label,
        transparent=transparent,
    )
    return _render_and_get_path(scene, transparent=transparent)


def _render_and_get_path(scene, transparent=False) -> str:
    """Render scene and return path to video."""
    if transparent:
        config.transparent = True
    else:
        config.transparent = False
    # set preview=True for manim chart video preview
    scene.render(preview=False)
    return str(Path(scene.renderer.file_writer.movie_file_path))


def composite_chart_over_blurred_video(
    chart_video: str,
    background_video: str,
    output_path: str,
    blur_strength: int = 20,
) -> str:
    """
    Composite a transparent chart video over a blurred background video.

    Args:
        chart_video: Path to chart video (with transparency or white bg)
        background_video: Path to stock video to use as blurred background
        output_path: Where to save the composited video
        blur_strength: Gaussian blur sigma (default 20)

    Returns:
        Path to the composited video
    """
    # FFmpeg command to:
    # 1. Take background video, blur it
    # 2. Overlay chart video on top
    # If chart has white background, we use colorkey to make it transparent
    cmd = [
        "ffmpeg", "-y",
        "-i", background_video,
        "-i", chart_video,
        "-filter_complex",
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur={blur_strength}:{blur_strength}[bg];"
        f"[1:v]colorkey=0xFFFFFF:0.1:0.2[fg];"
        f"[bg][fg]overlay=0:0:shortest=1[out]",
        "-map", "[out]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        output_path,
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to composite chart: {e.stderr.decode()}")
        return chart_video  # Fallback to original chart