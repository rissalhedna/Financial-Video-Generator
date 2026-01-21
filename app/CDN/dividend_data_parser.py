from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional


def _parse_date(d: str) -> datetime:
    return datetime.strptime(d, "%Y-%m-%d")


def parse_and_aggregate_dividends_per_year(
    raw: Dict[str, Any],
    *,
    date_field: str = "payment_date",
    value_field: str = "value",
) -> Optional[Tuple[List[str], List[float]]]:
    items = raw.get("dividend_calendar")
    if not isinstance(items, list) or not items:
        return None  # return None if stock has no dividends

    # aggregate dividends by year
    yearly: Dict[int, float] = {}
    for item in items:
        d = item.get(date_field)
        v = item.get(value_field)
        if not d or v is None:
            continue  # skip incomplete rows

        year = _parse_date(d).year
        if year == datetime.now().year:
            continue
        yearly[year] = yearly.get(year, 0.0) + float(v)

    if not yearly:
        return None

    years_sorted = sorted(yearly.keys())
    labels = [str(y) for y in years_sorted]
    values = [round(yearly[y], 4) for y in years_sorted]

    return labels, values


def build_dividend_bar_chart_json(
    chart_id: str,
    title: str,
    labels: List[str],
    values: List[float],
) -> Dict[str, Any]:
    if len(labels) != len(values):
        raise ValueError("labels and values must have the same length")

    return {
        "chart_id": chart_id,
        "chart_type": "bar",
        "title": title,
        "labels": labels,
        "values": values,
        "x_axis_label": "Year",
        "y_axis_label": "Dividends (USD)",
    }

