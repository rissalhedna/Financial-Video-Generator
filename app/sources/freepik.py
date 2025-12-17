"""Freepik video source provider."""
from __future__ import annotations

from typing import List, Optional

import httpx

from ..config import get_settings
from .base import VideoSource, VideoResult


class FreepikSource(VideoSource):
    """Freepik video search provider."""
    
    name = "freepik"
    SEARCH_URL = "https://api.freepik.com/v1/videos"
    
    def __init__(self):
        self.settings = get_settings()
        self._rate_limited = False
    
    def is_available(self) -> bool:
        return bool(self.settings.freepik_api_key) and not self._rate_limited
    
    def _get_download_url(self, resource_id: int) -> Optional[str]:
        """Get download URL for a specific video resource."""
        url = f"https://api.freepik.com/v1/videos/{resource_id}/download"
        headers = {"x-freepik-api-key": self.settings.freepik_api_key}
        
        try:
            with httpx.Client(headers=headers, timeout=15) as client:
                resp = client.get(url)
                if resp.status_code == 405:
                    resp = client.post(url)
                
                if resp.status_code == 429:
                    self._rate_limited = True
                    return None
                
                resp.raise_for_status()
                data = resp.json()
                
                if "data" in data and isinstance(data["data"], dict):
                    return data["data"].get("url")
                return data.get("url")
        except Exception:
            return None
    
    def search(self, query: str, limit: int = 5) -> List[VideoResult]:
        if not self.is_available():
            return []
        
        headers = {"x-freepik-api-key": self.settings.freepik_api_key}
        params = {
            "term": query or "business",
            "limit": limit,
            "locale": "en-US",
        }
        
        try:
            with httpx.Client(headers=headers, timeout=15) as client:
                resp = client.get(self.SEARCH_URL, params=params)
                
                if resp.status_code == 429:
                    self._rate_limited = True
                    print("⚠️  Freepik rate limited")
                    return []
                
                resp.raise_for_status()
                data = resp.json()
                
                videos = data.get("data", []) if isinstance(data, dict) else data
                
                results = []
                for video in videos[:limit]:
                    video_id = video.get("id")
                    if not video_id:
                        continue
                    
                    download_url = self._get_download_url(video_id)
                    if not download_url:
                        continue
                    
                    results.append(VideoResult(
                        id=str(video_id),
                        title=video.get("name") or video.get("title") or "",
                        download_url=download_url,
                        width=video.get("width", 1920),
                        height=video.get("height", 1080),
                        duration_seconds=video.get("duration", 10),
                        source=self.name
                    ))
                
                return results
                
        except Exception as e:
            if "429" in str(e):
                self._rate_limited = True
                print("⚠️  Freepik rate limited")
            return []

