#!/usr/bin/env python3
"""
Cache Migration Script

Indexes existing cached video files into the new manifest system.
This maintains backward compatibility while enabling new features.

Usage:
    python scripts/migrate_cache.py [--cache-dir tmp/videos]
"""
import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.cache import VideoCache, tags_hash


def get_video_info(path: Path) -> dict:
    """Get video metadata using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-show_entries", "format=duration,size",
            "-of", "json",
            str(path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        stream = data.get("streams", [{}])[0]
        fmt = data.get("format", {})
        
        return {
            "width": stream.get("width", 0),
            "height": stream.get("height", 0),
            "duration": float(fmt.get("duration", stream.get("duration", 0))),
            "size": int(fmt.get("size", 0)),
        }
    except Exception as e:
        print(f"  Warning: Could not probe {path.name}: {e}")
        return {"width": 0, "height": 0, "duration": 0, "size": 0}


def parse_filename(filename: str) -> dict:
    """Parse segment info from old-style filename."""
    # Pattern: seg01_clip00_abc12345.mp4 or seg01_abc12345.mp4
    pattern = r"seg(\d+)(?:_clip(\d+))?_([a-f0-9]+)\.mp4"
    match = re.match(pattern, filename)
    
    if match:
        return {
            "segment_id": int(match.group(1)),
            "clip_idx": int(match.group(2)) if match.group(2) else 0,
            "tag_hash": match.group(3),
        }
    return None


def migrate_cache(cache_dir: Path, dry_run: bool = False) -> dict:
    """
    Migrate existing cache files to new manifest system.
    
    Returns:
        Dict with migration statistics
    """
    print(f"Migrating cache: {cache_dir}")
    print()
    
    if not cache_dir.exists():
        print("Cache directory does not exist.")
        return {"migrated": 0, "skipped": 0, "errors": 0}
    
    # Initialize cache (will create manifest if not exists)
    cache = VideoCache(cache_dir)
    
    # Get existing stats
    existing_stats = cache.get_stats()
    print(f"Existing manifest entries: {existing_stats['total_entries']}")
    print(f"Orphaned files: {existing_stats['orphaned_files']}")
    print()
    
    # Find all MP4 files
    mp4_files = list(cache_dir.glob("*.mp4"))
    print(f"Found {len(mp4_files)} video files")
    print()
    
    migrated = 0
    skipped = 0
    errors = 0
    
    for mp4 in mp4_files:
        # Check if already in manifest
        key = mp4.stem
        if key in cache._manifest:
            skipped += 1
            continue
        
        # Parse filename to get segment info
        parsed = parse_filename(mp4.name)
        if not parsed:
            print(f"  Skipping unrecognized file: {mp4.name}")
            errors += 1
            continue
        
        # Get video metadata
        info = get_video_info(mp4)
        
        if dry_run:
            print(f"  Would migrate: {mp4.name}")
            print(f"    Segment: {parsed['segment_id']}, Clip: {parsed['clip_idx']}")
            print(f"    Size: {info['width']}x{info['height']}, Duration: {info['duration']:.1f}s")
            migrated += 1
            continue
        
        # Add to manifest using actual file path
        cache.add_entry_by_path(
            file_path=mp4,
            tags=[f"migrated_{parsed['tag_hash']}"],  # Placeholder
            query="(migrated from legacy cache)",
            source="unknown",
            url="",
            width=info["width"],
            height=info["height"],
            duration_seconds=info["duration"],
        )
        
        print(f"  Migrated: {mp4.name}")
        migrated += 1
    
    print()
    print("=" * 50)
    print(f"Migration complete!")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped (already indexed): {skipped}")
    print(f"  Errors: {errors}")
    
    # Show final stats
    if not dry_run:
        final_stats = cache.get_stats()
        print()
        print("Cache Statistics:")
        print(f"  Total entries: {final_stats['total_entries']}")
        print(f"  Total size: {final_stats['total_size_mb']} MB")
        print(f"  Sources: {final_stats['sources']}")
    
    return {"migrated": migrated, "skipped": skipped, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description="Migrate video cache to new manifest system")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("tmp/videos"),
        help="Cache directory path (default: tmp/videos)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    
    args = parser.parse_args()
    
    migrate_cache(args.cache_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

