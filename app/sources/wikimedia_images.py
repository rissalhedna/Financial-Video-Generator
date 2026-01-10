"""Wikimedia Commons image source for A-roll with Ken Burns effect."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import httpx

from .base import VideoSource, VideoResult


@dataclass
class ImageResult:
    """An image search result from Wikimedia Commons."""
    id: str
    title: str
    download_url: str
    width: int
    height: int
    source: str = "wikimedia_image"


class WikimediaImageSource(VideoSource):
    """
    Search Wikimedia Commons for images (much more content than videos).
    
    Images are converted to video with Ken Burns effect in the footage fetcher.
    """

    name = "wikimedia_image"
    API_URL = "https://commons.wikimedia.org/w/api.php"
    USER_AGENT = "FiindoVideoGenerator/1.0 (+https://github.com/Financial-Video-Generator)"

    def is_available(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> List[VideoResult]:
        """Search for images, return as VideoResult for compatibility."""
        images = self.search_images(query, limit)
        
        # Convert to VideoResult format (will be processed by Ken Burns)
        results = []
        for img in images:
            results.append(VideoResult(
                id=img.id,
                title=img.title,
                download_url=img.download_url,
                width=img.width,
                height=img.height,
                duration_seconds=5.0,  # Ken Burns will create 5s video
                source=self.name,
            ))
        return results

    def search_images(self, query: str, limit: int = 5) -> List[ImageResult]:
        """Search Wikimedia Commons for images."""
        terms = self._build_search_terms(query)
        
        for term in terms:
            results = self._query_api(term, limit)
            if results:
                return results
        
        return []

    def _query_api(self, search_term: str, limit: int) -> List[ImageResult]:
        """Query Commons API for images."""
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": search_term,
            "gsrlimit": limit * 2,  # Get extra to filter
            "gsrnamespace": 6,  # Files only
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
        }

        try:
            resp = httpx.get(
                self.API_URL,
                params=params,
                timeout=30.0,
                headers={"User-Agent": self.USER_AGENT},
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            return []

        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        results: List[ImageResult] = []

        for page in pages.values():
            imageinfo = page.get("imageinfo")
            if not imageinfo:
                continue
            
            info = imageinfo[0]
            mime = info.get("mime", "")
            
            # Only accept images (not video, audio, etc.)
            if not mime.startswith("image"):
                continue
            
            # Skip SVGs (don't work well with Ken Burns)
            if "svg" in mime.lower():
                continue
            
            width = info.get("width") or 1280
            height = info.get("height") or 720
            
            # Skip tiny images (< 500px)
            if width < 500 or height < 400:
                continue
            
            url = info.get("url", "")
            if not url:
                continue

            results.append(ImageResult(
                id=str(page.get("pageid", "")),
                title=page.get("title", "Wikimedia Image"),
                download_url=url,
                width=int(width),
                height=int(height),
            ))

        # Sort by resolution (prefer higher quality)
        results.sort(key=lambda r: r.width * r.height, reverse=True)
        return results[:limit]

    def _build_search_terms(self, query: str) -> List[str]:
        """Build search terms with progressive simplification."""
        cleaned = query.strip()
        if not cleaned:
            return []

        terms = []
        
        # Try full query first
        terms.append(cleaned)
        
        # Try with common suffixes removed
        words = cleaned.split()
        
        # Try first 3 words, then 2, then 1
        if len(words) > 3:
            terms.append(" ".join(words[:3]))
        if len(words) > 2:
            terms.append(" ".join(words[:2]))
        if len(words) > 1:
            terms.append(words[0])

        return terms

