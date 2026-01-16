from pathlib import Path
from datetime import datetime
import json

from app.CDN.cdn import CdnSource
from app.CDN.chart_ranges import ChartRange
from app.CDN.stock_data_parser import extract_series, build_stock_price_chart_json, format_x_axis_labels

def range_to_str(range_: ChartRange) -> str:
    """
       Maps a ChartRange to a human-readable title suffix.
    """
    mapping = {
        ChartRange.M1: "Last Month",
        ChartRange.M6: "Last 6 Months",
        ChartRange.YTD: "Year to Date",
        ChartRange.Y1: "Last Year",
        ChartRange.Y3: "Last 3 Years",
        ChartRange.Y5: "Last 5 Years",
        ChartRange.Y10: "Last 10 Years",
    }
    return mapping.get(range_, "Unknown Range")

def build_chart_data(symbol: str, range_: ChartRange) -> Path:
    """
    Builds chart data JSON for the given stock symbol and chart range,
    writes it to a .JSON file, and returns the path to the file.
    Args:
        symbol (str): Stock symbol (e.g., "AAPL.US").
        range_ (ChartRange): Chart range enum value (e.g. Y1).
    Returns:
        Path: Path to the generated JSON file.
    """
    # fetch raw data and metadata from CDN
    cdn = CdnSource()
    raw_data = cdn.fetch_chart_json(symbol)
    company_metadata = cdn.fetch_company_metadata(symbol)

    # determine company name and chart range for chart title
    if company_metadata and "company_name" in company_metadata:
        company_name = company_metadata["company_name"]
    else:
        company_name = symbol

    range_str = range_to_str(range_)

    # extract labels and values for the specified range
    labels, values = extract_series(raw_data, range_=range_)
    labels = format_x_axis_labels(labels, range_)

    # build unique chart ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_id = f"{symbol.lower().replace('.', '_')}_{range_.name}_{timestamp}"

    # build final chart JSON which can be used to create manim charts
    chart_data = build_stock_price_chart_json(
        chart_id=chart_id,
        title=f"{company_name} Stock Price - {range_str}",
        labels=labels,
        values=values,
    )

    # write JSON file
    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / "chart_data"
    out_dir.mkdir(exist_ok=True)

    out_path = out_dir / f"{chart_id}.json"
    out_path.write_text(
        json.dumps(chart_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return out_path