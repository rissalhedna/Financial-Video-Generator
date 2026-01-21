from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from cdn import CdnSource
from dividend_data_parser import parse_and_aggregate_dividends_per_year, build_dividend_bar_chart_json

def build_dividend_chart_data(symbol: str) -> Optional[str]:
    """
    Builds dividend chart data JSON for the given stock symbol,
    writes it to a .JSON file, and returns the path to the file or None if no dividend data is available.
    Args:
        symbol (str): Stock symbol (e.g., "AAPL.US").
    Returns:
        Optional[str]: Path to the generated JSON file, or None if no dividend data is available
    """
    # fetch raw data and metadata from CDN
    cdn = CdnSource()
    raw_data = cdn.fetch_dividend_calendar_json(symbol)
    company_metadata = cdn.fetch_company_metadata(symbol)

    series = parse_and_aggregate_dividends_per_year(
        raw_data,
        date_field="payment_date",
        value_field="value",
    )

    # return None if stock has no dividends
    if series is None:
        return None

    labels, values = series

    # determine company name and chart range for chart title
    if company_metadata and "company_name" in company_metadata:
        company_name = company_metadata["company_name"]
    else:
        company_name = symbol

    # build unique chart ID and title
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_id = f"{symbol.lower().replace('.', '_')}_DIV_{dt}"
    title = f"{company_name} - Annual Dividends"

    # build final dividend chart JSON which can be used to create manim charts
    chart_json = build_dividend_bar_chart_json(
        chart_id=chart_id,
        title=title,
        labels=labels,
        values=values,
    )

    # write JSON file
    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / "chart_data"
    out_dir.mkdir(exist_ok=True)

    out_path = out_dir / f"{chart_id}.json"
    out_path.write_text(json.dumps(chart_json, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(out_path)
