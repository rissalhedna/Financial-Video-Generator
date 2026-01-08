from __future__ import annotations
from typing import Optional, List, Tuple
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


def thin_series_for_range(
    labels: List[str],
    values: List[float],
    range_: ChartRange,
) -> Tuple[List[str], List[float]]:

    if range_ in {ChartRange.Y3, ChartRange.Y5, ChartRange.Y10}:
        # jährliche Punkte: letzter Handelstag pro Jahr
        return _bucket_last_value(
            labels, values,
            bucket_fn=lambda dt: dt.year,
            label_fn=lambda dt: f"{dt.year}",
        )

    if range_ in {ChartRange.M6, ChartRange.YTD, ChartRange.Y1}:
        # monatliche Punkte: letzter Handelstag pro Monat
        return _bucket_last_value(
            labels, values,
            bucket_fn=lambda dt: (dt.year, dt.month),
            label_fn=lambda dt: dt.strftime("%b"),  # "Jan", "Feb", ...
        )

    if range_ == ChartRange.M1:
        # wöchentlich: letzter Handelstag pro Kalenderwoche
        return _bucket_last_value(
            labels, values,
            bucket_fn=lambda dt: (dt.isocalendar().year, dt.isocalendar().week),
            label_fn=lambda dt: f"KW{dt.isocalendar().week:02d}",
        )

    # fallback: keine Verdichtung
    return labels, values


def build_stock_price_chart_json(
    symbol: str,
    labels: List[str],
    values: List[float],
    range_: ChartRange,
    title: Optional[str] = None,
    chart_id: Optional[str] = None,
):
    if title is None:
        title = f"{symbol} (Last {range_.name} Years)"

    if chart_id is None:
        chart_id = f"{symbol.lower().replace('.', '_')}_{range_.value}"

    return {
        "chart_id": chart_id,
        "chart_type": "line",
        "title": title,
        "labels": labels,
        "values": values,
        "x_axis_label": "Date",
        "y_axis_label": "Price (USD)",
    }
