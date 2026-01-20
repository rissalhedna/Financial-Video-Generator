"""File download and validation utilities."""
from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import httpx


def is_video_valid(path: Path) -> bool:
    """Check if a video file is valid and can be decoded by ffmpeg."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,pix_fmt",
            "-of", "json",
            str(path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return False
        
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams:
            return False
        
        # Check for valid pixel format
        stream = streams[0]
        pix_fmt = stream.get("pix_fmt")
        if pix_fmt is None or pix_fmt == "none":
            return False
        
        return True
    except Exception:
        return False


def get_video_info(path: Path) -> tuple[int, int] | None:
    """Get video width and height. Returns (width, height) or None."""
    try:
        import ffmpeg
        probe = ffmpeg.probe(str(path))
        video_stream = next(
            (s for s in probe['streams'] if s['codec_type'] == 'video'), 
            None
        )
        if video_stream:
            return int(video_stream['width']), int(video_stream['height'])
    except Exception:
        pass
    return None


def download_file(url: str, dest: Path, max_retries: int = 2, skip_validation: bool = False) -> Path:
    """
    Download a file from URL to destination path.
    
    Args:
        url: URL to download from
        dest: Destination path
        max_retries: Number of retry attempts
        skip_validation: If True, skip expensive ffprobe validation (faster)
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Quick cache check: skip expensive validation if file looks valid
    if dest.exists() and dest.stat().st_size > 10000:  # Min 10KB
        if skip_validation:
            return dest
        if is_video_valid(dest):
            return dest
    
    # Delete invalid cached file
    if dest.exists():
        try:
            dest.unlink()
        except Exception:
            pass
    
    # Download with retry logic
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
            with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=65536):
                        f.write(chunk)
            break
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                import time
                time.sleep(1)
                continue
            raise last_error
    
    # Handle ZIP files (common with Freepik)
    if zipfile.is_zipfile(dest):
        _extract_video_from_zip(dest)
    
    # Validate final file (skip if requested for speed)
    if not skip_validation and not is_video_valid(dest):
        try:
            dest.unlink()
        except Exception:
            pass
        raise ValueError(f"Downloaded file is invalid: {dest}")
    
    return dest


def _extract_video_from_zip(zip_path: Path) -> None:
    """Extract video from ZIP file, replacing the ZIP with the video."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Prefer MP4 over MOV
            mp4_files = [f for f in zip_ref.namelist() if f.lower().endswith('.mp4')]
            mov_files = [f for f in zip_ref.namelist() if f.lower().endswith('.mov')]
            
            video_files = mp4_files if mp4_files else mov_files
            if not video_files:
                return
            
            # Sort by size, pick largest
            video_files.sort(key=lambda x: zip_ref.getinfo(x).file_size, reverse=True)
            best_file = video_files[0]
            
            # Extract to temp location
            extract_path = zip_path.parent / f"temp_extract_{zip_path.stem}"
            if extract_path.exists():
                shutil.rmtree(extract_path)
            extract_path.mkdir(exist_ok=True)
            
            zip_ref.extract(best_file, extract_path)
            
            # Replace ZIP with extracted video
            extracted = extract_path / best_file
            if zip_path.exists():
                zip_path.unlink()
            shutil.move(str(extracted), str(zip_path))
            shutil.rmtree(extract_path)
            
    except Exception as e:
        print(f"Warning: Failed to extract ZIP {zip_path}: {e}")
