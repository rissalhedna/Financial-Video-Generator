"""Pexels video source provider.

API Documentation: https://www.pexels.com/api/documentation/#videos-search

Parameters:
- query: Search term
- orientation: landscape, portrait, square
- size: large (4K), medium (Full HD), small (HD)
- locale: Language for search (en-US, es-ES, etc.)
- page, per_page: Pagination
"""
from __future__ import annotations

from typing import List, Optional

import httpx

from ..config import get_settings
from .base import VideoSource, VideoResult


class PexelsSource(VideoSource):
    """Pexels video search provider with advanced filtering."""
    
    name = "pexels"
    API_URL = "https://api.pexels.com/videos/search"
    
    def __init__(self):
        self.settings = get_settings()
        self._rate_limited = False
    
    def is_available(self) -> bool:
        return bool(self.settings.pexels_api_key) and not self._rate_limited
    
    def search(
        self, 
        query: str, 
        limit: int = 5,
        orientation: Optional[str] = None,
        min_duration: int = 3,
        min_width: int = 1080,
    ) -> List[VideoResult]:
        """
        Search for videos with advanced filtering.
        
        Args:
            query: Search keywords
            limit: Max results
            orientation: 'landscape', 'portrait', or 'square'
            min_duration: Minimum video duration in seconds
            min_width: Minimum video width
        """
        if not self.is_available():
            return []
        
        headers = {"Authorization": self.settings.pexels_api_key}
        params = {
            "query": query or "business technology",
            "per_page": min(limit * 2, 30),  # Get extra for filtering
            "size": "large",  # Prefer 4K/high-res videos
        }
        
        # Only add orientation if explicitly specified (don't auto-filter)
        # This allows more results, and the ranking system handles aspect ratio preference
        if orientation:
            params["orientation"] = orientation
        
        try:
            with httpx.Client(headers=headers, timeout=20) as client:
                resp = client.get(self.API_URL, params=params)
                
                if resp.status_code == 429:
                    self._rate_limited = True
                    return []
                
                resp.raise_for_status()
                data = resp.json()
                
                results = []
                for video in data.get("videos", []):
                    duration = video.get("duration", 0)
                    
                    # Filter by minimum duration
                    if duration < min_duration:
                        continue
                    
                    # Find best MP4 file matching our requirements
                    mp4_files = [
                        f for f in video.get("video_files", []) 
                        if f.get("file_type") == "video/mp4" and f.get("width", 0) >= min_width
                    ]
                    
                    if not mp4_files:
                        # Fallback: any MP4
                        mp4_files = [
                            f for f in video.get("video_files", []) 
                            if f.get("file_type") == "video/mp4"
                        ]
                    
                    if not mp4_files:
                        continue
                    
                    # Sort by resolution (prefer higher)
                    mp4_files.sort(key=lambda f: f.get("width", 0) * f.get("height", 0), reverse=True)
                    best = mp4_files[0]
                    
                    # Extract tags from URL for better matching info
                    url_parts = video.get("url", "").split("/")
                    title = url_parts[-2] if len(url_parts) > 1 else ""
                    
                    results.append(VideoResult(
                        id=str(video.get("id")),
                        title=title,
                        download_url=best["link"],
                        width=best["width"],
                        height=best["height"],
                        duration_seconds=duration,
                        source=self.name
                    ))
                    
                    if len(results) >= limit:
                        break
                
                return results
                
        except Exception as e:
            print(f"Pexels search error: {e}")
            return []
    
    def search_by_tags(self, tags: List[str], limit: int = 5) -> List[VideoResult]:
        """Search using multiple tag strategies for better matching."""
        # Strategy 1: All tags together
        query = " ".join(tags[:3])
        results = self.search(query, limit)
        
        if len(results) >= limit:
            return results
        
        # Strategy 2: First tag only (most important)
        if tags and len(results) < limit:
            more = self.search(tags[0], limit - len(results))
            results.extend(more)
        
        return results[:limit]
