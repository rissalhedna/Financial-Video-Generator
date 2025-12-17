"""Pixabay video source provider.

API Documentation: https://pixabay.com/api/docs/#api_search_videos

Parameters:
- q: Search term (max 100 chars, URL encoded)
- video_type: all, film, animation
- category: backgrounds, fashion, nature, science, education, feelings, health, 
            people, religion, places, animals, industry, computer, food, sports,
            transportation, travel, buildings, business, music
- min_width, min_height: Minimum dimensions
- editors_choice: true for curated high-quality
- safesearch: true/false
- order: popular, latest
"""
from __future__ import annotations

from typing import List, Optional

import httpx

from ..config import get_settings
from .base import VideoSource, VideoResult


# Map keywords to Pixabay categories
KEYWORD_TO_CATEGORY = {
    # Technology
    "technology": "computer", "tech": "computer", "software": "computer",
    "computer": "computer", "laptop": "computer", "smartphone": "computer",
    "phone": "computer", "device": "computer", "digital": "computer",
    "code": "computer", "programming": "computer", "data": "computer",
    
    # Business
    "business": "business", "office": "business", "meeting": "business",
    "corporate": "business", "finance": "business", "money": "business",
    "stock": "business", "market": "business", "trading": "business",
    "growth": "business", "success": "business", "company": "business",
    
    # People
    "person": "people", "people": "people", "man": "people", "woman": "people",
    "team": "people", "group": "people", "family": "people", "crowd": "people",
    
    # Nature
    "nature": "nature", "forest": "nature", "tree": "nature", "sky": "nature",
    "ocean": "nature", "mountain": "nature", "landscape": "nature",
    
    # Places
    "city": "places", "street": "places", "building": "buildings",
    "architecture": "buildings", "house": "buildings", "home": "buildings",
    
    # Transportation
    "car": "transportation", "vehicle": "transportation", "airplane": "transportation",
    "train": "transportation", "travel": "travel", "airport": "travel",
    
    # Industry
    "factory": "industry", "manufacturing": "industry", "industrial": "industry",
    "warehouse": "industry", "production": "industry",
    
    # Education
    "education": "education", "school": "education", "learning": "education",
    "student": "education", "classroom": "education", "university": "education",
    
    # Health
    "health": "health", "medical": "health", "hospital": "health",
    "doctor": "health", "fitness": "health", "gym": "sports",
    
    # Food
    "food": "food", "restaurant": "food", "cooking": "food", "kitchen": "food",
    
    # Music/Entertainment
    "music": "music", "entertainment": "music", "concert": "music",
}


class PixabaySource(VideoSource):
    """Pixabay video search provider with category matching."""
    
    name = "pixabay"
    API_URL = "https://pixabay.com/api/videos/"
    
    def __init__(self):
        self.settings = get_settings()
        self._rate_limited = False
    
    def is_available(self) -> bool:
        return bool(self.settings.pixabay_api_key) and not self._rate_limited
    
    def _detect_category(self, query: str) -> Optional[str]:
        """Detect best Pixabay category from search query."""
        query_lower = query.lower()
        for keyword, category in KEYWORD_TO_CATEGORY.items():
            if keyword in query_lower:
                return category
        return None
    
    def search(
        self, 
        query: str, 
        limit: int = 5,
        category: Optional[str] = None,
        editors_choice: bool = False,
        min_width: int = 1280,
        min_height: int = 720,
    ) -> List[VideoResult]:
        """
        Search for videos with category and quality filtering.
        
        Args:
            query: Search keywords
            limit: Max results
            category: Pixabay category (auto-detected if None)
            editors_choice: Only return curated high-quality videos
            min_width, min_height: Minimum dimensions
        """
        if not self.is_available():
            return []
        
        # Auto-detect category from query
        if category is None:
            category = self._detect_category(query)
        
        params = {
            "key": self.settings.pixabay_api_key,
            "q": (query or "business technology")[:100],  # Max 100 chars
            "per_page": min(limit * 2, 50),  # Get extra for filtering
            "video_type": "film",  # Prefer real footage over animation
            "safesearch": "true",
            "lang": "en",
            "min_width": min_width,
            "min_height": min_height,
            "order": "popular",  # Popular videos tend to be higher quality
        }
        
        # Add category if detected
        if category:
            params["category"] = category
        
        # Editors choice for premium quality
        if editors_choice:
            params["editors_choice"] = "true"
        
        try:
            with httpx.Client(timeout=20) as client:
                resp = client.get(self.API_URL, params=params)
                
                if resp.status_code == 429:
                    self._rate_limited = True
                    return []
                
                resp.raise_for_status()
                data = resp.json()
                
                results = []
                for hit in data.get("hits", []):
                    videos = hit.get("videos", {})
                    duration = hit.get("duration", 0)
                    
                    # Skip very short clips
                    if duration < 3:
                        continue
                    
                    # Prefer large > medium > small
                    best = None
                    for key in ("large", "medium", "small"):
                        if key in videos and videos[key].get("url"):
                            v = videos[key]
                            # Check minimum dimensions
                            if v.get("width", 0) >= min_width * 0.8:  # Allow 80% tolerance
                                best = v
                                break
                    
                    if not best:
                        # Fallback to any available
                        for key in ("large", "medium", "small"):
                            if key in videos and videos[key].get("url"):
                                best = videos[key]
                                break
                    
                    if not best:
                        continue
                    
                    results.append(VideoResult(
                        id=str(hit.get("id")),
                        title=hit.get("tags", ""),
                        download_url=best["url"],
                        width=int(best.get("width", 1280)),
                        height=int(best.get("height", 720)),
                        duration_seconds=duration,
                        source=self.name
                    ))
                    
                    if len(results) >= limit:
                        break
                
                return results
                
        except Exception as e:
            print(f"Pixabay search error: {e}")
            return []
    
    def search_by_tags(self, tags: List[str], limit: int = 5) -> List[VideoResult]:
        """Search using tags with category detection."""
        # Try with all tags first
        query = " ".join(tags[:3])
        
        # Try editors choice first for best quality
        results = self.search(query, limit, editors_choice=True)
        
        if len(results) >= limit:
            return results
        
        # Fallback to regular search
        if len(results) < limit:
            more = self.search(query, limit - len(results), editors_choice=False)
            results.extend(more)
        
        return results[:limit]
