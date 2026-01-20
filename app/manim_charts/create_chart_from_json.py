"""
Create Chart from JSON - Renders Manim charts from JSON data files.
"""
from __future__ import annotations

import json
from pathlib import Path

from .chart_video_compositor import compose_with_background
from .chart_renderer import render_line_chart, render_pie_chart, render_bar_chart


# Get the assets directory (relative to project root)
ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
CHART_BACKGROUNDS_DIR = ASSETS_DIR / "chart_backgrounds"


def load_chart_json(path: str) -> dict:
    """Read a JSON file from the given path and return the parsed Python dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def render_chart_from_data(data: dict, transparent: bool = False) -> str:
    """
    Dispatch to the appropriate chart rendering function based on `chart_type`.
    Supported types: 'line', 'pie', 'bar'. Raises ValueError for unknown types.

    Args:
        data: Chart data dictionary
        transparent: If True, render with transparent background (for overlay on blurred video)
    """
    chart_type = data.get("chart_type")

    if chart_type == "line":
        return render_line_chart(
            labels=data["labels"],
            values=data["values"],
            title=data.get("title", "Line Chart"),
            x_axis_label=data.get("x_axis_label"),
            y_axis_label=data.get("y_axis_label"),
            transparent=transparent,
        )
    elif chart_type == "pie":
        return render_pie_chart(
            labels=data["labels"],
            values=data["values"],
            title=data.get("title", "Pie Chart"),
            transparent=transparent,
        )
    elif chart_type == "bar":
        return render_bar_chart(
            labels=data["labels"],
            values=data["values"],
            title=data.get("title", "Bar Chart"),
            x_axis_label=data.get("x_axis_label"),
            y_axis_label=data.get("y_axis_label"),
            transparent=transparent,
        )
    else:
        raise ValueError(f"Unknown chart_type: {chart_type}")


def get_default_background() -> Path:
    """Get the default chart background video path."""
    bg_path = CHART_BACKGROUNDS_DIR / "chart_background_1.mp4"
    if bg_path.exists():
        return bg_path
    # Fallback to second background
    bg_path2 = CHART_BACKGROUNDS_DIR / "chart_background_2.mp4"
    if bg_path2.exists():
        return bg_path2
    raise FileNotFoundError(f"No chart background found in {CHART_BACKGROUNDS_DIR}")


def render_chart_from_json_file(path: str, transparent: bool = False, background_video: str = None) -> str:
    """Load JSON from `path` and render the corresponding chart.

    This function can be called by an external pipeline by passing a string
    that contains the path to the JSON file to render.

    Args:
        path: Path to the JSON file containing chart data
        transparent: If True, render with transparent background for compositing
        background_video: Optional path to background video for compositing

    Returns:
        str: Path to the generated video file (final_path)
    """
    data = load_chart_json(path)
    chart_video_path = render_chart_from_data(data, transparent)
    
    if not transparent:
        return chart_video_path
    
    # If transparent, composite chart over background
    if background_video:
        bg_path = Path(background_video)
    else:
        bg_path = get_default_background()
    
    final_path = compose_with_background(str(bg_path), chart_video_path)
    return final_path


if __name__ == "__main__":
    # Test: render a chart from JSON
    import subprocess
    
    # Look for test JSON in CDN chart_data folder
    cdn_dir = Path(__file__).parent.parent / "CDN" / "chart_data"
    json_files = list(cdn_dir.glob("*.json")) if cdn_dir.exists() else []
    
    if json_files:
        json_path = str(json_files[0])
        print(f"Rendering chart from: {json_path}")
    videopath = render_chart_from_json_file(json_path, transparent=True)
    subprocess.run(["open", videopath], check=False)
        print(f"Video path: {videopath}")
    else:
        print(f"No JSON files found in {cdn_dir}")
