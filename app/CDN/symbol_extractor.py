"""
Symbol Extractor - Extracts stock symbols from topic strings.

This module provides utilities to identify stock symbols from natural language
topics like "Apple Inc stock" -> "AAPL.US"
"""
from __future__ import annotations

import re
from typing import Optional, Dict

# Common company name to symbol mappings
COMPANY_SYMBOLS: Dict[str, str] = {
    # Tech giants
    "apple": "AAPL.US",
    "microsoft": "MSFT.US",
    "google": "GOOG.US",
    "alphabet": "GOOG.US",
    "amazon": "AMZN.US",
    "meta": "META.US",
    "facebook": "META.US",
    "nvidia": "NVDA.US",
    "tesla": "TSLA.US",
    "netflix": "NFLX.US",
    
    # Finance
    "jpmorgan": "JPM.US",
    "jp morgan": "JPM.US",
    "goldman sachs": "GS.US",
    "goldman": "GS.US",
    "bank of america": "BAC.US",
    "wells fargo": "WFC.US",
    "visa": "V.US",
    "mastercard": "MA.US",
    "paypal": "PYPL.US",
    "berkshire": "BRK-A.US",
    "berkshire hathaway": "BRK-A.US",
    
    # Healthcare
    "johnson & johnson": "JNJ.US",
    "johnson and johnson": "JNJ.US",
    "pfizer": "PFE.US",
    "unitedhealth": "UNH.US",
    "abbvie": "ABBV.US",
    "merck": "MRK.US",
    "eli lilly": "LLY.US",
    "lilly": "LLY.US",
    
    # Consumer
    "walmart": "WMT.US",
    "costco": "COST.US",
    "coca-cola": "KO.US",
    "coca cola": "KO.US",
    "coke": "KO.US",
    "pepsi": "PEP.US",
    "pepsico": "PEP.US",
    "nike": "NKE.US",
    "starbucks": "SBUX.US",
    "mcdonalds": "MCD.US",
    "mcdonald's": "MCD.US",
    "disney": "DIS.US",
    "walt disney": "DIS.US",
    
    # Industrial / Energy
    "exxon": "XOM.US",
    "exxonmobil": "XOM.US",
    "chevron": "CVX.US",
    "boeing": "BA.US",
    "caterpillar": "CAT.US",
    "3m": "MMM.US",
    "general electric": "GE.US",
    "ge": "GE.US",
    "honeywell": "HON.US",
    
    # Semiconductors
    "amd": "AMD.US",
    "intel": "INTC.US",
    "qualcomm": "QCOM.US",
    "broadcom": "AVGO.US",
    "tsmc": "TSM.US",
    "taiwan semiconductor": "TSM.US",
    
    # Telecom
    "at&t": "T.US",
    "verizon": "VZ.US",
    "t-mobile": "TMUS.US",
    
    # Other notable
    "salesforce": "CRM.US",
    "adobe": "ADBE.US",
    "oracle": "ORCL.US",
    "ibm": "IBM.US",
    "cisco": "CSCO.US",
    "uber": "UBER.US",
    "airbnb": "ABNB.US",
    "spotify": "SPOT.US",
    "zoom": "ZM.US",
    "shopify": "SHOP.US",
    "square": "SQ.US",
    "block": "SQ.US",
    "palantir": "PLTR.US",
    "snowflake": "SNOW.US",
    "crowdstrike": "CRWD.US",
    "coinbase": "COIN.US",
}


def extract_symbol_from_topic(topic: str) -> Optional[str]:
    """
    Extract a stock symbol from a topic string.
    
    Args:
        topic: Natural language topic like "Apple Inc stock analysis"
        
    Returns:
        Stock symbol like "AAPL.US" or None if not found
    """
    topic_lower = topic.lower()
    
    # First, check if topic contains a direct symbol (e.g., "AAPL stock")
    # Pattern: 1-5 uppercase letters optionally followed by .XX
    symbol_pattern = r'\b([A-Z]{1,5})(?:\.([A-Z]{2}))?\b'
    matches = re.findall(symbol_pattern, topic)
    for match in matches:
        symbol = match[0]
        suffix = match[1] if match[1] else "US"
        full_symbol = f"{symbol}.{suffix}"
        # Validate it's a known format (not just random uppercase words)
        if len(symbol) <= 5 and symbol.isalpha():
            return full_symbol
    
    # Check against known company names (longest match first)
    sorted_companies = sorted(COMPANY_SYMBOLS.keys(), key=len, reverse=True)
    for company in sorted_companies:
        if company in topic_lower:
            return COMPANY_SYMBOLS[company]
    
    return None


def get_symbol_company_name(symbol: str) -> str:
    """
    Get the common company name for a symbol.
    
    Args:
        symbol: Stock symbol like "AAPL.US"
        
    Returns:
        Company name like "Apple" or the symbol if not found
    """
    # Reverse lookup
    symbol_upper = symbol.upper()
    for company, sym in COMPANY_SYMBOLS.items():
        if sym == symbol_upper:
            return company.title()
    
    # Return symbol without suffix as fallback
    return symbol.split(".")[0]


if __name__ == "__main__":
    # Test cases
    test_topics = [
        "Apple Inc stock",
        "Tesla stock analysis",
        "AAPL stock price",
        "Microsoft quarterly earnings",
        "Nvidia GPU market",
        "What is happening with Amazon?",
        "TSLA.US performance",
        "Random topic without stocks",
    ]
    
    for topic in test_topics:
        symbol = extract_symbol_from_topic(topic)
        print(f"{topic!r} -> {symbol}")

