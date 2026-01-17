from __future__ import annotations
from typing import List, Tuple
from .chart_ranges import ChartRange
from datetime import datetime
from collections import OrderedDict


def _parse_date(d: str) -> datetime:
    # API liefert ISO "YYYY-MM-DD"
    return datetime.strptime(d, "%Y-%m-%d")


def extract_series(
    chart_json: dict,
    range_: ChartRange,
    price_key: str = "adjusted_close",
) -> Tuple[List[str], List[float]]:
    key = range_.value
    if key not in chart_json:
        raise ValueError(f"Expected key '{key}' not found in chart.json")

    series = chart_json[key]
    if not isinstance(series, list) or not series:
        raise ValueError(f"Chart series '{key}' is empty or invalid")

    labels: List[str] = []
    values: List[float] = []

    for row in series:
        date = row.get("date")
        price = row.get(price_key)
        if date and price is not None:
            labels.append(str(date))
            values.append(float(price))

    if not labels:
        raise ValueError("No usable datapoints found")

    return labels, values


def _bucket_last_value(
    labels: List[str],
    values: List[float],
    bucket_fn,
    label_fn,
) -> Tuple[List[str], List[float]]:
    # nimmt pro Bucket immer den letzten Wert (chronologisch)
    pairs = sorted(zip(labels, values), key=lambda x: x[0])
    buckets = OrderedDict()
    for d, v in pairs:
        dt = _parse_date(d)
        b = bucket_fn(dt)
        buckets[b] = (label_fn(dt), v)
    out_labels = [lv[0] for lv in buckets.values()]
    out_values = [lv[1] for lv in buckets.values()]
    return out_labels, out_values


def format_x_axis_labels(date_labels: List[str], range_: ChartRange) -> List[str]:
    """
    Returns a labels-list with SAME length as date_labels, but most entries are "".
    Non-empty entries mark the desired X-axis tick labels depending on the range.
    """
    dts = [_parse_date(d) for d in date_labels]
    out = [""] * len(dts)

    def mark_on_bucket_change(bucket_fn, label_fn):
        last_bucket = None
        for i, dt in enumerate(dts):
            b = bucket_fn(dt)
            if b != last_bucket:
                out[i] = label_fn(dt)
                last_bucket = b
    # 1 Month: weekly labels
    if range_ == ChartRange.M1:
        STEP_DAYS = 5 # weekly labels

        for i, dt in enumerate(dts):
            if i % STEP_DAYS == 0:
                out[i] = dt.strftime("%d.%m.%y")  # e.g.. "05.10"

    # 6 Months, YTD, 1 Year
    elif range_ in {ChartRange.M6, ChartRange.YTD, ChartRange.Y1}:
        # monthly labels and ticks (fallback to weekly date labels if only a single month is present)
        unique_months = {(dt.year, dt.month) for dt in dts}

        if len(unique_months) <= 1:
            # Fallback: behave like M1 (weekly-ish date labels)
            STEP_DAYS = 5
            for i, dt in enumerate(dts):
                if i % STEP_DAYS == 0:
                    out[i] = dt.strftime("%d.%m.%y")  # e.g. "05.01.26"
        else:
            def month_label(dt: datetime) -> str:
                # include year on January (or first tick) to avoid ambiguity across years
                if dt.month == 1:
                    return dt.strftime("%b\n%Y")  # e.g. "Jan\n2026"
                return dt.strftime("%b")  # "Feb", "Mar", ...

            mark_on_bucket_change(
                bucket_fn=lambda dt: (dt.year, dt.month),
                label_fn=month_label,
            )
    # 3 Years: quarterly ticks
    elif range_ == ChartRange.Y3:
        # quarterly ticks
        def quarter(dt: datetime) -> int:
            return (dt.month - 1) // 3 + 1
        mark_on_bucket_change(
            bucket_fn=lambda dt: (dt.year, quarter(dt)),
            label_fn=lambda dt: f"Q{quarter(dt)}\n{dt.year}",
        )

    else:
        # 5 Years, 10 Years: yearly ticks
        mark_on_bucket_change(
            bucket_fn=lambda dt: dt.year,
            label_fn=lambda dt: f"{dt.year}",
        )

    return out



def build_stock_price_chart_json(
    chart_id: str,
    title: str,
    labels: List[str],
    values: List[float],
):

    return {
        "chart_id": chart_id,
        "chart_type": "line",
        "title": title,
        "labels": labels,
        "values": values,
        "x_axis_label": "Date",
        "y_axis_label": "Price (USD)",
    }
