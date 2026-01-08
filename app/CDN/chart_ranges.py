from enum import Enum

class ChartRange(str, Enum):
    M1  = "chart_1m"
    M6  = "chart_6m"
    YTD = "chart_ytd"
    Y1  = "chart_1j"
    Y3  = "chart_3j"
    Y5  = "chart_5j"
    Y10 = "chart_10j"
