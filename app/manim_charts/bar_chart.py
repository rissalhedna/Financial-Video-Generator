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

    def construct(self):
        labels = self.labels
        values = self.values
        n = len(labels)

        y_min = 0
        y_max = max(values) * 1.15

        # ---------------- Axes ----------------
        ax = Axes(
            x_range=[0, n, 1],
            y_range=[y_min, y_max, y_max / 5],
            x_length=10,
            y_length=4.8,
            axis_config={"include_tip": False, "stroke_width": 2, "color": CUSTOM_GREY_1},
        ).to_edge(DOWN).shift(UP * 0.6)

        # ---------------- Bars ----------------
        bars = VGroup()
        bar_width = 0.6
        for i, v in enumerate(values):
            x_center = i + 0.5
            bar = Rectangle(
                width=bar_width,
                height=ax.c2p(0, v)[1] - ax.c2p(0, 0)[1],
                fill_color=CUSTOM_BLUE_1,
                fill_opacity=0.9,
                stroke_color=CUSTOM_BLUE_1,
                stroke_width=0,
            )
            bar.move_to(ax.c2p(x_center, v / 2))
            bars.add(bar)

        # ---------------- X-labels ----------------
        xlabels = VGroup(
            *[
                Text(lbl, color=CUSTOM_GREY_1).scale(0.35).next_to(
                    ax.c2p(i + 0.5, y_min), DOWN, buff=0.25
                )
                for i, lbl in enumerate(labels)
            ]
        )

        # ---------------- Axes titles ----------------
        extra_labels = VGroup()
        if self.x_axis_label_text:
            x_title = Text(self.x_axis_label_text, color=CUSTOM_GREY_1).scale(0.4)
            x_title.next_to(ax, DOWN, buff=0.8)
            extra_labels.add(x_title)

        if self.y_axis_label_text:
            y_title = (
                Text(self.y_axis_label_text, color=CUSTOM_GREY_1)
                .scale(0.4)
                .rotate(PI / 2)
            )
            y_title.next_to(ax, LEFT, buff=0.8)
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
        self.play(Write(title), run_time=0.6)
        self.play(Create(ax), FadeIn(xlabels), FadeIn(extra_labels), run_time=1.0)

        self.play(
            LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in bars], lag_ratio=0.1),
            run_time=1.8,
        )

        self.wait(3.0)
