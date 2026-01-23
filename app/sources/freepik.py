"""Freepik video source provider."""
from __future__ import annotations

import concurrent.futures
from typing import List, Optional, Tuple

import httpx

from ..config import get_settings
from .base import VideoSource, VideoResult


class FreepikSource(VideoSource):
    """Freepik video search provider."""
    
    name = "freepik"
    SEARCH_URL = "https://api.freepik.com/v1/videos"
    _rate_limited = False  # Class variable to persist across instances
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
    
    def is_available(self) -> bool:
        return bool(self.settings.freepik_api_key) and not self._rate_limited
    
    def _get_download_url(self, resource_id: int, client: httpx.Client) -> Optional[str]:
        """Get download URL for a specific video resource."""
        url = f"https://api.freepik.com/v1/videos/{resource_id}/download"
        
        try:
            resp = client.get(url)
            if resp.status_code == 405:
                resp = client.post(url)
            
            if resp.status_code == 429:
                FreepikSource._rate_limited = True
                return None
            
            resp.raise_for_status()
            data = resp.json()
            
            if "data" in data and isinstance(data["data"], dict):
                return data["data"].get("url")
            return data.get("url")
        except Exception:
            return None
    
    def _fetch_video_with_url(
        self, 
        video: dict, 
        client: httpx.Client
    ) -> Optional[VideoResult]:
        """Fetch download URL and create VideoResult for a single video."""
        video_id = video.get("id")
        if not video_id:
            return None
        
        download_url = self._get_download_url(video_id, client)
        if not download_url:
            return None
        
        try:
            width = int(video.get("width", 1920))
            height = int(video.get("height", 1080))
            duration = float(video.get("duration", 10))
        except (ValueError, TypeError):
            width, height, duration = 1920, 1080, 10.0
        
        return VideoResult(
            id=str(video_id),
            title=video.get("name") or video.get("title") or "",
            download_url=download_url,
            width=width,
            height=height,
            duration_seconds=duration,
            source=self.name
        )
    
    def search(self, query: str, limit: int = 5) -> List[VideoResult]:
        if not self.is_available():
            return []
        
        headers = {"x-freepik-api-key": self.settings.freepik_api_key}
        params = {
            "term": query or "business",
            "limit": min(limit, 3),  # Limit API calls
            "locale": "en-US",
        }
        
        try:
            with httpx.Client(headers=headers, timeout=10) as client:
                resp = client.get(self.SEARCH_URL, params=params)
                
                if resp.status_code == 429:
                    FreepikSource._rate_limited = True
                    print("⚠️  Freepik rate limited")
                    return []
                
                resp.raise_for_status()
                data = resp.json()
                
                videos = data.get("data", []) if isinstance(data, dict) else data
                videos = videos[:limit]
                
                if not videos:
                    return []
                
                # Fetch download URLs in parallel
                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    futures = {
                        executor.submit(self._fetch_video_with_url, v, client): v 
                        for v in videos
                    }
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            result = future.result()
                            if result:
                                results.append(result)
                        except Exception:
                            pass
                
                return results
                
        except Exception as e:
            if "429" in str(e):
                FreepikSource._rate_limited = True
                print("⚠️  Freepik rate limited")
            return []
