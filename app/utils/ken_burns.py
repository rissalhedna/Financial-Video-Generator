"""Ken Burns effect - convert static images to dynamic video with pan/zoom."""

from __future__ import annotations

import random
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def apply_ken_burns(
    image_path: Path,
    output_path: Path,
    duration: float = 5.0,
    target_resolution: Tuple[int, int] = (720, 1280),
    fps: int = 30,
) -> Optional[Path]:
    """
    Apply Ken Burns effect to an image, creating a video with pan/zoom.
    
    Properly handles aspect ratio by scaling and cropping first.
    """
    if not image_path.exists():
        return None
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target_w, target_h = target_resolution
    
    # Randomly choose effect type for variety
    effect = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up"])
    
    total_frames = int(duration * fps)
    
    # Scale image to be larger than target (for zoompan headroom), then crop to target aspect ratio
    # Use 1.5x the target size for zoom headroom
    scale_w = int(target_w * 1.5)
    scale_h = int(target_h * 1.5)
    
    # Build filter chain:
    # 1. Scale to cover target (maintaining aspect, then crop center)
    # 2. Apply zoompan on the prepared image
    scale_crop = f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,crop={scale_w}:{scale_h}"
    
    if effect == "zoom_in":
        zoom_expr = f"z='1+0.3*on/{total_frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    elif effect == "zoom_out":
        zoom_expr = f"z='1.3-0.3*on/{total_frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    elif effect == "pan_left":
        zoom_expr = f"z='1.15':x='(iw/zoom)-(iw/zoom)*on/{total_frames}':y='ih/2-(ih/zoom/2)'"
    elif effect == "pan_right":
        zoom_expr = f"z='1.15':x='(iw/zoom)*on/{total_frames}':y='ih/2-(ih/zoom/2)'"
    else:  # pan_up
        zoom_expr = f"z='1.15':x='iw/2-(iw/zoom/2)':y='(ih/zoom)-(ih/zoom)*on/{total_frames}'"
    
    zoompan = f"zoompan={zoom_expr}:d={total_frames}:s={target_w}x{target_h}:fps={fps}"
    
    # Combined filter: scale+crop, then zoompan
    vf = f"{scale_crop},{zoompan}"
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", vf,
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "fast",
        str(output_path),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode != 0:
            print(f"Ken Burns ffmpeg error: {result.stderr[:300]}")
            return None
        
        if output_path.exists():
            return output_path
        return None
        
    except subprocess.TimeoutExpired:
        print("Ken Burns effect timed out")
        return None
    except Exception as e:
        print(f"Ken Burns effect failed: {e}")
        return None


def image_to_video(
    image_path: Path,
    output_path: Path,
    duration: float = 5.0,
    target_resolution: Tuple[int, int] = (720, 1280),
) -> Optional[Path]:
    """
    Convert image to video with Ken Burns effect.
    """
    return apply_ken_burns(
        image_path=image_path,
        output_path=output_path,
        duration=duration,
        target_resolution=target_resolution,
    )
