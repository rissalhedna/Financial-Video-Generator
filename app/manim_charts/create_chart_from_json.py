import json
from .chart_renderer import render_line_chart, render_pie_chart, render_bar_chart

def load_chart_json(path: str) -> dict:
    """Read a JSON file from the given path and return the parsed Python dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def render_chart_from_data(data: dict) -> str:
    """
    Dispatch to the appropriate chart rendering function based on `chart_type`.
    Supported types: 'line', 'pie', 'bar'. Raises ValueError for unknown types.
    """
    chart_type = data.get("chart_type")

    if chart_type == "line":
        return render_line_chart(
            labels=data["labels"],
            values=data["values"],
            title=data.get("title", "Line Chart"),
            x_axis_label=data.get("x_axis_label"),
            y_axis_label=data.get("y_axis_label"),
        )
    elif chart_type == "pie":
        return render_pie_chart(
            labels=data["labels"],
            values=data["values"],
            title=data.get("title", "Pie Chart"),
        )
    elif chart_type == "bar":
        return render_bar_chart(
            labels=data["labels"],
            values=data["values"],
            title=data.get("title", "Bar Chart"),
            x_axis_label=data.get("x_axis_label"),
            y_axis_label=data.get("y_axis_label"),
        )
    else:
        raise ValueError(f"Unknown chart_type: {chart_type}")


def render_chart_from_json_file(path: str) -> str:
    """Load JSON from `path` and render the corresponding chart.

    This function can be called by an external pipeline by passing a string
    that contains the path to the JSON file to render.

    Returns:
        str: Path to the generated video file (videopath)
    """
    data = load_chart_json(path)
    videopath = render_chart_from_data(data)
    return videopath


if __name__ == "__main__":
    # Specify the path to the JSON file to render.
    json_path = "apple_stock_2014_2025.json" #line
    #json_path = "apple_services_revenue_2018_2024.json" #bar
    #json_path = "apple_revenue_by_product.json" #pie

    videopath = render_chart_from_json_file(json_path)
    print("Video path:")
    print(videopath)

