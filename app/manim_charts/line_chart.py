from manim import *
import math

# ---- COLORS ----
FIINDO_BLUE = "2fb9d1"
FIINDO_BLUE_DARK = "18313f"
FIINDO_YELLLOW = "f7a600"
FIINDO_BORDEAUX = "924165"
FIINDO_RED = "e94f35"
FIINDO_GREEN = "00965e"

WHITE           = "#ffffff"
CUSTOM_BLUE_0   = "#006f88"
CUSTOM_BLUE_1   = "#00a8cc"
CUSTOM_BLUE_2   = "#ade3ef"
CUSTOM_BLUE_3   = "#ecf9fb"
CUSTOM_GREY_1   = "#333333"
CUSTOM_GREY_2   = "#b5b5b5"
CUSTOM_ORANGE_1 = "#ff8000"
CUSTOM_YELLOW_1 = "#ff8000"

Text.set_default(font="Montserrat")

config.pixel_width = 1080
config.pixel_height = 1920
#config.background_color = "#cccccc"
#config.transparent = True

# ============================================================
# Manim scene for line chart
# ============================================================
class LineChartScene(MovingCameraScene):
    def __init__(
        self,
        labels,
        values,
        title="Apple Stock (2014–2025)",
        x_axis_label=None,
        y_axis_label=None,
        **kwargs,
    ):
        self.labels = labels
        self.values = values
        self.chart_title = title
        self.x_axis_label_text = x_axis_label
        self.y_axis_label_text = y_axis_label
        super().__init__(**kwargs)

    def construct(self):
        labels = self.labels
        values = self.values
        n = len(labels)

        assert len(values) == n, "labels and values must have the same length"

        # --------- Set Y-range ---------
        data_min = min(values)
        data_max = max(values)

        step = 50  # step size for Y-axis

        y_min = step * math.floor(data_min / step)
        y_max = step * math.ceil(data_max / step)

        # If all values are equal -> add some padding
        if y_min == y_max:
            y_min -= step
            y_max += step

        # ---------------- Axes ----------------
        ax = Axes(
            x_range=[0, n - 1, 1],
            y_range=[y_min, y_max, step],
            x_length=10,
            y_length=4.8,
            axis_config={
                "include_tip": False,
                "stroke_width": 2,
                "color": CUSTOM_GREY_1,
            },
        ).to_edge(DOWN).shift(UP * 0.6)

        # ---------------- Y-axis numbers matching the ticks ----------------
        y_number_labels = VGroup(
            *[
                Text(f"{int(y)}")
                .scale(0.33)
                .set_color(CUSTOM_GREY_1)
                .next_to(ax.c2p(0, y), LEFT, buff=0.2)
                for y in range(int(y_min), int(y_max) + 1, step)
            ]
        )

        # ---------------- X-labels ----------------
        xlabels = VGroup(
            *[
                Text(m)
                .scale(0.35)
                .set_color(CUSTOM_GREY_1)
                .next_to(ax.c2p(i, y_min), DOWN, buff=0.25)
                for i, m in enumerate(labels)
            ]
        )

        # ---------------- Axes titles ----------------
        extra_labels = VGroup()
        if self.x_axis_label_text:
            x_title = (
                Text(self.x_axis_label_text)
                .scale(0.4)
                .set_color(CUSTOM_GREY_1)
            )
            x_title.next_to(ax, DOWN, buff=0.8)
            extra_labels.add(x_title)

        if self.y_axis_label_text:
            y_title = (
                Text(self.y_axis_label_text)
                .scale(0.4)
                .set_color(CUSTOM_GREY_1)
            )
            # place the label above the Y axis
            y_title.next_to(ax.y_axis, UP, buff=0.3)
            y_title.shift(LEFT * 0.3)
            extra_labels.add(y_title)

        # ---------------- Graph and points ----------------
        pts = [ax.c2p(i, v) for i, v in enumerate(values)]

        line = VMobject().set_stroke(CUSTOM_BLUE_1, width=4)
        line.set_points_smoothly(pts)

        dots = VGroup(*[Dot(p, color=CUSTOM_BLUE_1) for p in pts])
        vals = VGroup(
            *[
                Text(f"{v:.0f}", weight=BOLD)
                .scale(0.33)
                .set_color(CUSTOM_GREY_1)
                .next_to(p, UP + 0.1 * RIGHT, buff=0.2)
                .shift(UP * 0.1)
                for p, v in zip(pts, values)
            ]
        )

        # ---------------- Title ----------------
        title = Text(
            self.chart_title,
            font="Montserrat",
            weight=BOLD,
            font_size=48,
            color=CUSTOM_BLUE_1,
        ).to_edge(UP)

        # ---------------- Scale scene ----------------
        chart_group = VGroup(ax, xlabels, y_number_labels, extra_labels, line, dots, vals)
        chart_group.scale(1.1)
        chart_group.shift(UP * 0.2)

        # ---------------- Animation ----------------
        self.camera.background_color = WHITE

        # PHASE 1: Title, axes, X/Y labels, axis titles
        self.play(Write(title), run_time=0.7)
        self.play(
            Create(ax),
            FadeIn(xlabels),
            FadeIn(y_number_labels),
            FadeIn(extra_labels),
            run_time=1.0,
        )

        # PHASE 2: draw line graph
        self.play(Create(line), run_time=2.0, rate_func=smooth)

        # add points + values sequentially
        pops = []
        for d, v in zip(dots, vals):
            pops.append(AnimationGroup(FadeIn(d, scale=0.8), FadeIn(v, scale=0.8)))
        self.play(LaggedStart(*pops, lag_ratio=0.08), run_time=2.0)

        # Hold final frame for 3 seconds so viewer can read the chart
        self.wait(3.0)
