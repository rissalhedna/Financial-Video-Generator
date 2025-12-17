"""
Improved caching system for video files.

Features:
- Metadata manifest tracking (query, source, quality, timestamp)
- Content-based deduplication
- Backward compatible with old cache files
- Cache statistics
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .download import is_video_valid


@dataclass
class CacheEntry:
    """Metadata for a cached video file."""
    file_path: str
    tags: List[str]
    query: str
    source: str  # pexels, pixabay, freepik
    url: str
    width: int
    height: int
    duration_seconds: float
    file_size: int
    created_at: str  # ISO timestamp
    content_hash: Optional[str] = None  # For deduplication


class VideoCache:
    """
    Improved video cache with metadata tracking.
    
    Maintains backward compatibility with existing cache files
    while adding metadata tracking for new downloads.
    """
    
    MANIFEST_FILE = "cache_manifest.json"
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = cache_dir / self.MANIFEST_FILE
        self._manifest: Dict[str, CacheEntry] = {}
        self._load_manifest()
    
    def _load_manifest(self) -> None:
        """Load manifest from disk."""
        if self.manifest_path.exists():
            try:
                data = json.loads(self.manifest_path.read_text())
                for key, entry_dict in data.items():
                    self._manifest[key] = CacheEntry(**entry_dict)
            except (json.JSONDecodeError, TypeError):
                self._manifest = {}
    
    def _save_manifest(self) -> None:
        """Save manifest to disk."""
        data = {k: asdict(v) for k, v in self._manifest.items()}
        self.manifest_path.write_text(json.dumps(data, indent=2))
    
    def _compute_content_hash(self, file_path: Path) -> str:
        """Compute hash of file content for deduplication."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:16]
    
    def get_cache_key(self, segment_id: int, clip_idx: int, tags: List[str]) -> str:
        """Generate cache key from segment info and tags."""
        tag_hash = tags_hash(tags) if tags else "default"
        if clip_idx > 0:
            return f"seg{segment_id:02d}_clip{clip_idx:02d}_{tag_hash}"
        return f"seg{segment_id:02d}_{tag_hash}"
    
    def get_path(self, segment_id: int, clip_idx: int, tags: List[str]) -> Path:
        """Get file path for a cache entry (backward compatible)."""
        key = self.get_cache_key(segment_id, clip_idx, tags)
        return self.cache_dir / f"{key}.mp4"
    
    def is_cached(self, segment_id: int, clip_idx: int, tags: List[str]) -> bool:
        """Check if a valid cached file exists."""
        path = self.get_path(segment_id, clip_idx, tags)
        return path.exists() and path.stat().st_size > 0 and is_video_valid(path)
    
    def get_entry(self, segment_id: int, clip_idx: int, tags: List[str]) -> Optional[CacheEntry]:
        """Get metadata for a cached entry."""
        key = self.get_cache_key(segment_id, clip_idx, tags)
        return self._manifest.get(key)
    
    def add_entry(
        self,
        segment_id: int,
        clip_idx: int,
        tags: List[str],
        query: str,
        source: str,
        url: str,
        width: int,
        height: int,
        duration_seconds: float,
        file_path: Optional[Path] = None,  # Allow override for migration
    ) -> None:
        """Add or update a cache entry with metadata."""
        key = self.get_cache_key(segment_id, clip_idx, tags)
        path = file_path or self.get_path(segment_id, clip_idx, tags)
        
        if not path.exists():
            return
        
        # Compute content hash for deduplication
        content_hash = self._compute_content_hash(path)
        
        entry = CacheEntry(
            file_path=str(path),
            tags=tags,
            query=query,
            source=source,
            url=url,
            width=width,
            height=height,
            duration_seconds=duration_seconds,
            file_size=path.stat().st_size,
            created_at=datetime.now().isoformat(),
            content_hash=content_hash,
        )
        
        self._manifest[key] = entry
        self._save_manifest()
    
    def add_entry_by_path(
        self,
        file_path: Path,
        tags: List[str],
        query: str,
        source: str,
        url: str,
        width: int,
        height: int,
        duration_seconds: float,
    ) -> None:
        """Add entry using actual file path (for migration)."""
        if not file_path.exists():
            return
        
        key = file_path.stem  # Use filename without extension as key
        content_hash = self._compute_content_hash(file_path)
        
        entry = CacheEntry(
            file_path=str(file_path),
            tags=tags,
            query=query,
            source=source,
            url=url,
            width=width,
            height=height,
            duration_seconds=duration_seconds,
            file_size=file_path.stat().st_size,
            created_at=datetime.now().isoformat(),
            content_hash=content_hash,
        )
        
        self._manifest[key] = entry
        self._save_manifest()
    
    def find_duplicate(self, content_hash: str) -> Optional[CacheEntry]:
        """Find existing entry with same content hash."""
        for entry in self._manifest.values():
            if entry.content_hash == content_hash:
                return entry
        return None
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total_entries = len(self._manifest)
        total_size = sum(e.file_size for e in self._manifest.values())
        sources = {}
        for e in self._manifest.values():
            sources[e.source] = sources.get(e.source, 0) + 1
        
        # Count orphaned files (in directory but not in manifest)
        all_mp4s = list(self.cache_dir.glob("*.mp4"))
        manifest_files = {Path(e.file_path).name for e in self._manifest.values()}
        orphaned = [f for f in all_mp4s if f.name not in manifest_files]
        
        return {
            "total_entries": total_entries,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "sources": sources,
            "orphaned_files": len(orphaned),
        }
    
    def cleanup_invalid(self) -> int:
        """Remove invalid cache entries and return count removed."""
        removed = 0
        keys_to_remove = []
        
        for key, entry in self._manifest.items():
            path = Path(entry.file_path)
            if not path.exists() or not is_video_valid(path):
                keys_to_remove.append(key)
                if path.exists():
                    try:
                        path.unlink()
                    except Exception:
                        pass
                removed += 1
        
        for key in keys_to_remove:
            del self._manifest[key]
        
        if removed > 0:
            self._save_manifest()
        
        return removed


# ============================================================
# Backward compatible functions (used by existing code)
# ============================================================

def tags_hash(tags: List[str]) -> str:
    """Generate a short hash from tags for cache key."""
    tags_str = "|".join(sorted(t.lower().strip() for t in tags))
    return hashlib.md5(tags_str.encode()).hexdigest()[:8]


def get_cache_path(cache_dir: Path, segment_id: int, clip_idx: int, tags: List[str]) -> Path:
    """Get the cache file path for a video clip (backward compatible)."""
    tag_hash = tags_hash(tags) if tags else "default"
    if clip_idx > 0:
        filename = f"seg{segment_id:02d}_clip{clip_idx:02d}_{tag_hash}.mp4"
    else:
        filename = f"seg{segment_id:02d}_{tag_hash}.mp4"
    return cache_dir / filename


def is_cached(path: Path) -> bool:
    """Check if a valid cached file exists (backward compatible)."""
    return path.exists() and path.stat().st_size > 0 and is_video_valid(path)
