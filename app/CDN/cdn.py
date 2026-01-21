from __future__ import annotations

from typing import Optional, Dict, Any
import httpx

from ..config import get_settings

class CdnSource:
    """CDN provider."""

    name = "cdn"

    def __init__(self):
        self.settings = get_settings()
        self._rate_limited = False

    def is_available(self) -> bool:
        return (
                bool(self.settings.cdn_api_key)
                and bool(self.settings.cdn_api_url)
                and not self._rate_limited
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.cdn_api_key}",
            "Accept": "application/json",
        }

    def fetch_chart_json(self, symbol: str) -> dict:
        """
        GET {CDN_API_URL}/symbols/{SYMBOL}/chart.json
        Example symbol: "AAPL.US"
        """
        if not self.is_available():
            raise RuntimeError("CDN API not configured (missing CDN_API_URL or CDN_API_KEY)")

        base_url = self.settings.cdn_api_url.rstrip("/")  # prevents // in the URL
        url = f"{base_url}/symbols/{symbol}/chart.json"

        with httpx.Client(timeout=self.settings.timeout_seconds) as client:
            resp = client.get(url, headers=self._headers())

            if resp.status_code == 429:
                self._rate_limited = True
                raise RuntimeError("CDN API rate-limited (429)")

            resp.raise_for_status()
            return resp.json()


    def fetch_company_metadata(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        GET {CDN_API_URL}/symbols/{SYMBOL}/meta.json
        Example symbol: "AAPL.US"
        """
        if not self.is_available():
            raise RuntimeError("CDN API not configured (missing CDN_API_URL or CDN_API_KEY)")

        base_url = self.settings.cdn_api_url.rstrip("/")  # prevents // in the URL
        url = f"{base_url}/symbols/{symbol}/short_overview.json"

        with httpx.Client(timeout=self.settings.timeout_seconds) as client:
            resp = client.get(url, headers=self._headers())

            if resp.status_code == 429:
                self._rate_limited = True
                raise RuntimeError("CDN API rate-limited (429)")

            if resp.status_code == 404:
                return None  # metadata not found

            resp.raise_for_status()
            return resp.json()


    def fetch_dividend_calendar_json(self, symbol: str) -> dict:
        """
        GET {CDN_API_URL}/symbols/{SYMBOL}/dividend_calendar.json
        Example symbol: "AAPL.US"
        """
        if not self.is_available():
            raise RuntimeError("CDN API not configured (missing CDN_API_URL or CDN_API_KEY)")

        base_url = self.settings.cdn_api_url.rstrip("/")  # prevents // in the URL
        url = f"{base_url}/symbols/{symbol}/dividend_calendar.json"

        with httpx.Client(timeout=self.settings.timeout_seconds) as client:
            resp = client.get(url, headers=self._headers())

            if resp.status_code == 429:
                self._rate_limited = True
                raise RuntimeError("CDN API rate-limited (429)")

            resp.raise_for_status()
            return resp.json()