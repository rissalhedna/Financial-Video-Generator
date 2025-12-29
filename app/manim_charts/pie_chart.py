from manim import *

# ---- Colors ----
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
# Manim scene for pie chart
# ============================================================
class PieChartScene(Scene):
    def __init__(self, labels, values, title="Pie Chart", **kwargs):
        self.labels = labels
        self.values = values
        self.chart_title = title
        super().__init__(**kwargs)

    def construct(self):

        # --- Data ---
        values = np.array([0.4, 0.3, 0.15, 0.10, 0.05])
        labels_text = ["iPhone", "Services", "Mac", "iPad", "Wearables"]

        # convert values to angles
        angles = 360 * DEGREES * values
        # Starting angle for the individual sectors on the circle
        # Using the cumulative sum for the starting positions on the circle
        rotate_angles = 360 * DEGREES * np.cumsum([0, 0.3, 0.15, 0.10, 0.05])
        colors = [CUSTOM_BLUE_0, CUSTOM_BLUE_1, CUSTOM_BLUE_2, CUSTOM_BLUE_3, CUSTOM_ORANGE_1]

        # --- Sectors ---
        sectors = [
            Sector(radius=3, color=c, angle=a, start_angle=-r)  #Sectors
            for a, c, r in zip(angles, colors, rotate_angles)
        ]

        # --- Labels ---
        # Radius for labels
        label_circle = Circle(radius=1.75)
        # Middle of each sector
        label_angles = rotate_angles - (angles / 2)
        labels = [
            Text(f"{w:.0%}", font="Montserrat", font_size=30, color=CUSTOM_GREY_1)
            .move_to(label_circle.point_at_angle(-la))
            for w, s, la in zip(values, sectors, label_angles)
        ]

        pie_chart_group = VGroup(*sectors, *labels).shift(DOWN * 0.8)

        # --- Title ---
        title = Text(
            "Pie Chart",
            font="Montserrat",
            weight=BOLD,
            font_size=48,
            color=CUSTOM_BLUE_1
        ).to_edge(UP)

        # --- legend ---
        legend_items = VGroup()
        for color, label in zip(colors, labels_text):
            sq = Square(0.3).set_fill(color, 1).set_stroke(CUSTOM_GREY_1, 1)
            tx = Text(label, font="Montserrat", font_size=26, color=CUSTOM_GREY_1)
            legend_items.add(VGroup(sq, tx).arrange(RIGHT, buff=0.25))
        legend = legend_items.arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        legend.next_to(pie_chart_group, RIGHT, buff=1.0).shift(UP * 0.5)

        self.camera.background_color = WHITE

        # ---Animation---
        self.play(Write(title), run_time=1.0)

        # Sectors
        self.play(
            LaggedStart(
                *[GrowFromCenter(s) for s in sectors],
                lag_ratio=0.5
            ),
            run_time=4.0,
            rate_func=smooth
        )
        # Keep permanently in the scene graph after appearance
        self.add(*sectors)

        # Labels
        self.play(
            LaggedStart(*[FadeIn(l, scale=0.85) for l in labels], lag_ratio=0.12),
            run_time=0.8, rate_func=smooth
        )
        # Keep permanently in the scene graph after appearance
        self.add(*labels)

        # Legend
        self.play(FadeIn(legend, shift=LEFT * 0.2), run_time=0.6, rate_func=smooth)

        self.wait(0.5)
