import math
from manim import *

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

# ============================================================
# Manim scene for bar chart
# ============================================================
class BarChartScene(Scene):
    def __init__(self, labels, values, title, x_axis_label=None, y_axis_label=None, transparent=False, **kwargs):
        self.labels = labels
        self.values = values
        self.chart_title = title
        self.x_axis_label_text = x_axis_label
        self.y_axis_label_text = y_axis_label
        self.transparent_bg = transparent
        config.transparent = transparent
        super().__init__(**kwargs)


    @staticmethod
    def optimize_y_axis_steps(data_max: float, target_ticks: int = 6, pad_ratio: float = 0.08):
        if data_max <= 0:
            return 1.0, 1.0

        padded_max = data_max * (1.0 + pad_ratio)
        rough_step = padded_max / target_ticks

        nice = [1, 2, 2.5, 5, 10]

        exp = math.floor(math.log10(rough_step))
        base = 10 ** exp
        frac = rough_step / base

        step_mult = next(m for m in nice if frac <= m)
        y_step = step_mult * base

        y_max = y_step * math.ceil(padded_max / y_step)
        return y_step, y_max


    def construct(self):
        labels = self.labels
        values = self.values
        n = len(labels)

        assert len(values) == n, "labels and values must have the same length"

        data_min = 0
        data_max = max(values)

        y_step, y_max = self.optimize_y_axis_steps(data_max, pad_ratio=0.10)
        y_min = 0

        # ---------------- Axes ----------------
        ax = Axes(
            x_range=[0, n, 1],
            y_range=[y_min, y_max, y_step],
            x_length=10,
            y_length=4.8,
            axis_config={
                "include_tip": False,
                "stroke_width": 6,
                "color": WHITE
            },
            x_axis_config={
                "include_ticks": False,
            },
            y_axis_config={
                "include_ticks": True,
            }
        ).to_edge(DOWN).shift(UP * 0.6)


        # ---------------- Horizontal helper lines ----------------
        y_ticks = [y_min + k * y_step for k in range(int(round((y_max - y_min) / y_step)) + 1)]

        grid_lines = VGroup(*[
            Line(ax.c2p(0, y), ax.c2p(n, y), stroke_width=2, color=CUSTOM_GREY_2)
            for y in y_ticks
        ]).set_z_index(1)

        # sinnvolles Format automatisch (0.00, 0.0, 0)
        decimals = max(0, -int(math.floor(math.log10(y_step)))) if y_step < 1 else 0
        fmt = f"{{:.{min(decimals, 2)}f}}"  # cap bei 2 Nachkommastellen

        grid_lines.set_z_index(1)
        ax.set_z_index(2)


        # ---------------- Y-axis numbers matching the ticks ----------------
        ylabels = VGroup(*[
            Text(fmt.format(y), weight=BOLD).scale(0.33).set_color(WHITE)
                         .next_to(ax.c2p(0, y), LEFT, buff=0.2)
            for y in y_ticks
        ])


        # ---------------- Bars ----------------
        bars = VGroup()
        bar_width = 0.6
        for i, v in enumerate(values):
            x_center = i + 0.5
            bar = Rectangle(
                width=bar_width,
                height=ax.c2p(0, v)[1] - ax.c2p(0, 0)[1],
                fill_color=CUSTOM_BLUE_1,
                fill_opacity=1.0,
                stroke_color=CUSTOM_BLUE_1,
                stroke_width=0,
            )
            bar.move_to(ax.c2p(x_center, v / 2))
            bars.add(bar)
            bars.set_z_index(3)

        # ---------------- X-labels ----------------
        xlabels = VGroup(
            *[
                Text(lbl, color=WHITE, weight=BOLD).scale(0.35).next_to(
                    ax.c2p(i + 0.5, y_min), DOWN, buff=0.25
                )
                for i, lbl in enumerate(labels)
            ]
        )

        # ---------------- Axes titles ----------------
        extra_labels = VGroup()
        if self.x_axis_label_text:
            x_title = (
                Text(self.x_axis_label_text, weight=BOLD)
                .scale(0.4)
                .set_color(WHITE)
            )
            x_title.next_to(ax, DOWN, buff=0.8)
            extra_labels.add(x_title)

        if self.y_axis_label_text:
            y_title = (
                Text(self.y_axis_label_text, weight=BOLD)
                .scale(0.4)
                .set_color(WHITE)
            )
            # place the label above the Y axis
            y_title.next_to(ax.y_axis, UP, buff=0.3)
            y_title.shift(LEFT * 0.3)
            extra_labels.add(y_title)

        # ---------------- Title ----------------
        title = Text(
            self.chart_title,
            weight=BOLD,
            font_size=42,
            color=CUSTOM_BLUE_1,
        ).to_edge(UP)

        if not self.transparent_bg:
            self.camera.background_color = WHITE

        # ---------------- Animation ----------------
        self.play(
            Write(title),
            run_time=0.6
        )

        self.play(
            Create(ax),
            FadeIn(xlabels),
            FadeIn(ylabels),
            FadeIn(extra_labels),
            run_time=1.0
        )

        self.play(
            FadeIn(grid_lines),
            run_time=0.5,
        )
        self.play(
            LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in bars], lag_ratio=0.1),
            run_time=1.8,
        )

        self.wait(3.0)
