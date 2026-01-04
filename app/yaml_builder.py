"""
YAML Builder - Converts agent output to VideoSpec YAML format.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .agents.visual_mapper import VisualSegmentOutput


def build_yaml_spec(
    title: str,
    segments: List[VisualSegmentOutput],
    voice_id: str = "en-US-Studio-O",
    voice_speed: str = "fast",
    music: str = "inspirational",
    output_dir: str = "out/generated",
) -> Dict[str, Any]:
    """
    Convert visual segments to VideoSpec dictionary.
    
    Args:
        title: Video title
        segments: List of annotated segments from VisualMapperAgent
        voice_id: Google TTS voice ID
        voice_speed: slow/medium/fast
        music: Background music mood
        output_dir: Output directory for the video
    
    Returns:
        Dictionary ready for YAML serialization
    """
    spec_segments = []
    
    for seg in segments:
        segment_dict: Dict[str, Any] = {
            "text": seg.text,
            "emotion": seg.emotion,
        }
        
        # Add on_screen_text for chart placeholders
        if seg.on_screen_text:
            segment_dict["on_screen_text"] = seg.on_screen_text
        
        # If we have a pre-generated chart video, use it directly
        if seg.chart_video_path:
            segment_dict["chart_video"] = seg.chart_video_path
        # Add visual clips or simple visuals
        elif seg.clips:
            if len(seg.clips) == 1 and not seg.clips[0].trigger:
                # Single clip without trigger - use simple visuals format
                segment_dict["visuals"] = seg.clips[0].tags
            else:
                # Multiple clips or clips with triggers
                segment_dict["clips"] = [
                    {
                        "tags": clip.tags,
                        **({"trigger": clip.trigger} if clip.trigger else {}),
                    }
                    for clip in seg.clips
                ]
        
        spec_segments.append(segment_dict)
    
    return {
        "title": title,
        "voice_id": voice_id,
        "voice_speed": voice_speed,
        "music": music,
        "output_dir": output_dir,
        "segments": spec_segments,
    }


def save_yaml_spec(
    spec: Dict[str, Any],
    path: Path,
) -> Path:
    """
    Save VideoSpec to a YAML file.
    
    Args:
        spec: VideoSpec dictionary
        path: Output path for YAML file
    
    Returns:
        Path to the saved file
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Custom representer for multi-line strings
    def str_representer(dumper, data):
        if '\n' in data or len(data) > 80:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='>')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    
    yaml.add_representer(str, str_representer)
    
    with open(path, 'w') as f:
        yaml.dump(spec, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    return path

