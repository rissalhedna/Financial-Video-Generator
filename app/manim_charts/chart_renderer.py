from pathlib import Path
from .line_chart import LineChartScene
from .pie_chart import PieChartScene
from .bar_chart import BarChartScene


def render_line_chart(labels, values, title="Line Chart", x_axis_label=None, y_axis_label=None) -> str:
    """Wrapper function: creates the Manim Line Chart scene and renders it."""

    scene = LineChartScene(
        labels=labels,
        values=values,
        title=title,
        x_axis_label=x_axis_label,
        y_axis_label=y_axis_label,
    )
    return _render_and_get_path(scene)


def render_pie_chart(labels, values, title) -> str:
    """Wrapper function: creates the Manim Pie Chart scene and renders it."""

    scene = PieChartScene(labels=labels, values=values, title=title)
    return _render_and_get_path(scene)


def render_bar_chart(labels, values, title, x_axis_label=None, y_axis_label=None) -> str:
    """Wrapper function: creates the Manim Bar Chart scene and renders it."""

    scene = BarChartScene(
        labels=labels,
        values=values,
        title=title,
        x_axis_label=x_axis_label,
        y_axis_label=y_axis_label,
    )
    return _render_and_get_path(scene)

def _render_and_get_path(scene) -> str:
    scene.render(preview=False)
    return str(Path(scene.renderer.file_writer.movie_file_path))