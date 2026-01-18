"""
Footage search module with intelligent multi-source video fetching.

Optimized for speed with:
- Parallel source searching
- Lazy validation (only validate on actual use)
- Increased concurrent downloads
- Smarter caching
"""
from __future__ import annotations

import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from tqdm import tqdm

from .config import get_settings
from .models import Script, VisualAsset
from .sources import PexelsSource, FreepikSource, PixabaySource, VideoSource, VideoResult
from .utils import download_file, get_cache_path, is_cached
from .utils.cache import VideoCache
from .utils.keywords import extract_keywords, build_search_query, get_fallback_queries


class VideoFetcher:
    """Fetches videos from multiple sources with intelligent fallback and ranking."""
    
    def __init__(self, cache: Optional[VideoCache] = None):
        self.settings = get_settings()
        self.cache = cache
        # Order by speed: Pexels is fastest, then Pixabay, Freepik is slowest (ZIPs)
        self.sources: List[VideoSource] = [
            PexelsSource(),   # Fast downloads, good quality
            PixabaySource(),  # Good variety
            FreepikSource(),  # Premium but slow (ZIP downloads) - last resort
        ]
        self._last_result: Optional[VideoResult] = None
    
    def search(self, query: str, limit: int = 5) -> List[VideoResult]:
        """Search all available sources for videos."""
        for source in self.sources:
            if source.is_available():
                results = source.search(query, limit)
                if results:
                    return results
        return []

    def search_parallel(self, query: str, limit: int = 5) -> List[VideoResult]:
        """
        Search multiple sources in parallel for faster results.
        
        Returns results from the first source that responds with matches.
        """
        available_sources = [s for s in self.sources if s.is_available()]
        
        if not available_sources:
            return []
        
        # Use only the first 2 sources (fastest) for parallel search
        sources_to_try = available_sources[:2]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_to_source = {
                executor.submit(s.search, query, limit): s 
                for s in sources_to_try
            }
            
            # Return results from first successful source
            for future in concurrent.futures.as_completed(future_to_source):
                try:
                    results = future.result(timeout=10)
                    if results:
                        # Cancel other pending searches
                        for f in future_to_source:
                            if f != future and not f.done():
                                f.cancel()
                        return results
                except Exception:
                    continue
        
        # Fallback to sequential search if parallel fails
        return self.search(query, limit)

    def search_with_fallbacks(
        self, 
        query: str, 
        fallbacks: List[str],
        limit: int = 5
    ) -> List[VideoResult]:
        """
        Search with automatic fallback to broader queries.
        
        Tries the primary query first, then progressively broader fallbacks.
        Uses parallel search for speed.
        """
        # Try primary query with parallel search
        results = self.search_parallel(query, limit)
        if results:
            return results
        
        # Try fallback queries (sequential to avoid rate limiting)
        for fallback in fallbacks:
            results = self.search(fallback, limit)
            if results:
                return results
        
        return []

    def _rank_results(
        self, 
        results: List[VideoResult], 
        target_duration_ms: int = 5000
    ) -> List[VideoResult]:
        """Rank video results by quality, duration fit, and aspect ratio."""
        target_res = self.settings.resolution
        target_w, target_h = map(int, target_res.split("x"))
        target_duration_s = target_duration_ms / 1000
        is_portrait = target_h > target_w
        
        def score(r: VideoResult) -> float:
            # Resolution score (max 35 points)
            res_ratio = min(r.width / target_w, r.height / target_h)
            res_score = min(res_ratio, 1.5) * 25
            
            # Duration score (max 35 points)
            if r.duration_seconds >= target_duration_s:
                dur_score = 35
            elif r.duration_seconds >= target_duration_s * 0.5:
                dur_score = 20
            else:
                dur_score = (r.duration_seconds / target_duration_s) * 15
            
            # Aspect ratio score (max 30 points)
            video_portrait = r.height > r.width
            if is_portrait == video_portrait:
                aspect_score = 30
            elif r.width == r.height:
                aspect_score = 20
            else:
                aspect_score = 5
            
            return res_score + dur_score + aspect_score
        
        return sorted(results, key=score, reverse=True)
    
    def fetch_video(
        self, 
        tags: List[str], 
        narration: str, 
        dest: Path,
        target_duration_ms: int = 5000
    ) -> Optional[Tuple[str, int, int]]:
        """
        Fetch a video matching tags/narration.
        
        Uses smart search with fallbacks and ranking.
        
        Returns:
            (path, width, height) or None
        """
        # Check cache first (fast path - skip expensive validation)
        if dest.exists() and dest.stat().st_size > 10000:  # Min 10KB for valid video
            from .utils.download import get_video_info
            info = get_video_info(dest)
            if info:
                return str(dest), info[0], info[1]
        
        # Build search query from narration and tags
        keywords = extract_keywords(narration, tags)
        primary_query = " ".join(keywords[:3])
        fallbacks = get_fallback_queries(primary_query)
        
        # Search with fallbacks
        results = self.search_with_fallbacks(primary_query, fallbacks, limit=8)
        
        if not results:
            return None
        
        # Rank by quality and fit
        ranked = self._rank_results(results, target_duration_ms)
        
        # Try downloading top candidates
        for candidate in ranked[:3]:
            try:
                download_file(candidate.download_url, dest)
                self._last_result = candidate
                return str(dest), candidate.width, candidate.height
            except Exception:
                continue
        
        return None
    
    def get_last_download_info(self) -> Optional[VideoResult]:
        """Get info about the last successfully downloaded video."""
        return self._last_result


def _quick_cache_check(dest: Path) -> bool:
    """
    Fast cache validation without ffprobe.
    
    Only checks file existence and minimum size.
    Full validation happens later during rendering.
    """
    return dest.exists() and dest.stat().st_size > 10000  # Min 10KB


def fetch_visuals_for_script(
    script: Script, 
    cache_dir: Path, 
    force_refresh: bool = False
) -> Dict[int, List[VisualAsset]]:
    """
    Fetch videos for all segments in a script.
    
    Optimized with:
    - Quick cache checks (no ffprobe)
    - Parallel downloads (5 workers)
    - Pre-filtering of tasks
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize cache with metadata tracking
    video_cache = VideoCache(cache_dir)
    fetcher = VideoFetcher(cache=video_cache)
    
    # Build task list (skip segments with pre-generated chart videos)
    tasks = []
    chart_video_results: Dict[int, List[Tuple[int, VisualAsset]]] = {}
    
    for seg in script.segments:
        # If segment has a pre-generated chart video, use it directly
        if seg.chart_video and Path(seg.chart_video).exists():
            from .utils.download import get_video_info
            info = get_video_info(Path(seg.chart_video))
            w, h = info if info else (1080, 1920)
            asset = VisualAsset(
                segment_id=seg.id,
                source_url="chart",
                file_path=seg.chart_video,
                width=w,
                height=h,
                duration_ms=seg.duration_ms,
            )
            chart_video_results[seg.id] = [(0, asset)]
            continue
        
        if seg.visual_clips:
            for clip_idx, clip in enumerate(seg.visual_clips):
                dest = get_cache_path(cache_dir, seg.id, clip_idx, clip.tags)
                duration_ms = int(seg.duration_ms * (clip.duration_pct / 100.0))
                tasks.append({
                    "seg_id": seg.id,
                    "clip_idx": clip_idx,
                    "tags": clip.tags,
                    "narration": seg.narration,
                    "dest": dest,
                    "duration_ms": max(duration_ms, 500),
                })
        else:
            tags = extract_keywords(seg.narration, seg.visual_tags)
            dest = get_cache_path(cache_dir, seg.id, 0, tags)
            tasks.append({
                "seg_id": seg.id,
                "clip_idx": 0,
                "tags": tags,
                "narration": seg.narration,
                "dest": dest,
                "duration_ms": max(seg.duration_ms, 1000),
            })
    
    # Separate cached vs new (using quick check)
    cached_results: Dict[int, List[Tuple[int, VisualAsset]]] = {}
    tasks_to_fetch = []
    
    for task in tasks:
        if not force_refresh and _quick_cache_check(task["dest"]):
            # Use cached dimensions from manifest if available
            cached_entry = video_cache.get_entry(task["seg_id"], task["clip_idx"], task["tags"])
            if cached_entry:
                w, h = cached_entry.width, cached_entry.height
            else:
                # Fallback to ffprobe only if not in manifest
                from .utils.download import get_video_info
                info = get_video_info(task["dest"])
                w, h = info if info else (1080, 1920)
            
            asset = VisualAsset(
                segment_id=task["seg_id"],
                source_url=str(task["dest"]),
                file_path=str(task["dest"]),
                width=w,
                height=h,
                duration_ms=task["duration_ms"],
            )
            if task["seg_id"] not in cached_results:
                cached_results[task["seg_id"]] = []
            cached_results[task["seg_id"]].append((task["clip_idx"], asset))
        else:
            tasks_to_fetch.append(task)
    
    if cached_results:
        print(f"📦 {sum(len(v) for v in cached_results.values())} clips cached, {len(tasks_to_fetch)} to download")
    
    # Fetch new clips with more parallel workers
    if tasks_to_fetch:
        def fetch_task(task):
            result = fetcher.fetch_video(
                task["tags"], 
                task["narration"], 
                task["dest"],
                target_duration_ms=task["duration_ms"]
            )
            return task, result, fetcher.get_last_download_info()
        
        # Increase workers for faster parallel downloads
        max_workers = min(5, len(tasks_to_fetch))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_task, t): t for t in tasks_to_fetch}
            
            for future in tqdm(concurrent.futures.as_completed(futures), 
                              total=len(tasks_to_fetch), desc="Downloading", unit="clip"):
                try:
                    task, result, download_info = future.result()
                    if result:
                        path, w, h = result
                        asset = VisualAsset(
                            segment_id=task["seg_id"],
                            source_url=path,
                            file_path=path,
                            width=w,
                            height=h,
                            duration_ms=task["duration_ms"],
                        )
                        if task["seg_id"] not in cached_results:
                            cached_results[task["seg_id"]] = []
                        cached_results[task["seg_id"]].append((task["clip_idx"], asset))
                        
                        # Record metadata in cache manifest (skip expensive hash)
                        if download_info:
                            video_cache.add_entry(
                                segment_id=task["seg_id"],
                                clip_idx=task["clip_idx"],
                                tags=task["tags"],
                                query=" ".join(task["tags"][:3]),
                                source=download_info.source,
                                url=download_info.download_url,
                                width=w,
                                height=h,
                                duration_seconds=download_info.duration_seconds,
                            )
                except Exception as e:
                    task = futures[future]
                    print(f"Failed: segment {task['seg_id']}: {e}")
    
    # Merge chart video results with cached results
    for seg_id, clip_list in chart_video_results.items():
        cached_results[seg_id] = clip_list
    
    # Flush cache manifest (batch write)
    video_cache.flush()
    
    # Sort clips and convert to final format
    assets: Dict[int, List[VisualAsset]] = {}
    for seg_id, clip_list in cached_results.items():
        clip_list.sort(key=lambda x: x[0])
        assets[seg_id] = [asset for _, asset in clip_list]
                
    return assets


# Background music
MUSIC_TRACKS = [
    {
        "name": "Ambient Technology",
        "url": "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/ccCommunity/Kai_Engel/Satin/Kai_Engel_-_04_-_Sentinel.mp3",
    },
    {
        "name": "Cinematic Emotional",
        "url": "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/ccCommunity/Kai_Engel/Chapter_Two__Mild/Kai_Engel_-_08_-_Daemones.mp3",
    },
]


def search_music(query: str = "inspirational", limit: int = 1) -> List[dict]:
    """Get background music tracks."""
    return MUSIC_TRACKS[:limit]


def download_music(url: str, dest: Path) -> Path:
    """Download music file."""
    return download_file(url, dest)


# Backwards compatibility
plan_and_fetch_visuals = fetch_visuals_for_script
