"""Base class for video source providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class VideoResult:
    """A video search result from any source."""
    id: str
    title: str
    download_url: str
    width: int
    height: int
    duration_seconds: float
    source: str  # "pexels", "freepik", "pixabay"
    
    def __repr__(self) -> str:
        return f"VideoResult({self.source}:{self.id}, {self.width}x{self.height})"


class VideoSource(ABC):
    """Abstract base class for video source providers."""
    
    name: str = "base"
    
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[VideoResult]:
        """Search for videos matching the query."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this source is available (API key configured, not rate limited)."""
        pass
    
    def search_by_tags(self, tags: List[str], limit: int = 5) -> List[VideoResult]:
        """Search using a list of tags."""
        query = " ".join(tags)
        return self.search(query, limit)

