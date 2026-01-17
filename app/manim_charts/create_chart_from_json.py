import json
import subprocess

from chart_video_compositor import compose_with_background
from .chart_renderer import render_line_chart, render_pie_chart, render_bar_chart

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


def render_chart_from_json_file(path: str) -> str:
    """Load JSON from `path` and render the corresponding chart.

    This function can be called by an external pipeline by passing a string
    that contains the path to the JSON file to render.

    Returns:
        str: Path to the generated video file (final_path)
    """
    data = load_chart_json(path)
    chart_video_path = render_chart_from_data(data)

    background_mp4 = "../../assets/chart_backgrounds/chart_background_1.mp4"
    final_path = compose_with_background(background_mp4, chart_video_path)

    return final_path


if __name__ == "__main__":
    # Specify the path to the JSON file to render.
    #json_path = "apple_stock_2014_2025.json" #line
    #json_path = "apple_services_revenue_2018_2024.json" #bar
    #json_path = "apple_revenue_by_product.json" #pie
    #json_path = "../CDN/aapl_us_Y1_20260108_204225.json"

    json_path = "../CDN/chart_data/aapl_us_Y1_20260117_194824.json"

    videopath = render_chart_from_json_file(json_path)

    # open video
    subprocess.run(["open", videopath], check=False)
    # print video path
    print("Video path:")
    print(videopath)

