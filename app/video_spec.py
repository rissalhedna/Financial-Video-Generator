"""
Video specification module - declarative video creation from YAML/dict config.

Usage:
    from app.video_spec import create_video
    
    # From YAML file
    video_path = create_video("my_video.yaml")
    
    # From dict
    spec = {
        "title": "My Video",
        "segments": [
            {"text": "Hello world", "emotion": "excited", "visuals": ["hello", "world"]}
        ]
    }
    video_path = create_video(spec)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

import yaml
from tqdm import tqdm

from .config import get_settings
from .models import Script, Segment, VisualClip


@dataclass
class SegmentSpec:
    """Specification for a single video segment."""
    text: str
    emotion: str = "neutral"
    visuals: List[str] = field(default_factory=list)
    clips: Optional[List[Dict[str, Any]]] = None  # Multi-clip support
    duration_seconds: Optional[float] = None  # Auto-calculated if not specified
    chart_video: Optional[str] = None  # Pre-generated chart video path
    
    def to_segment(self, segment_id: int, start_ms: int) -> Segment:
        """Convert to internal Segment model."""
        # Estimate duration from text length if not specified
        if self.duration_seconds:
            duration_ms = int(self.duration_seconds * 1000)
        else:
            # Rough estimate: 150 words per minute, average 5 chars per word
            words = len(self.text.split())
            duration_ms = int((words / 150) * 60 * 1000)
            duration_ms = max(duration_ms, 2000)  # Minimum 2 seconds
        
        # Convert clips if specified
        visual_clips = None
        if self.clips:
            visual_clips = [
                VisualClip(
                    tags=clip.get("tags", []),
                    duration_pct=clip.get("duration_pct", 100 / len(self.clips)),
                    trigger=clip.get("trigger"),
                )
                for clip in self.clips
            ]
        
        return Segment(
            id=segment_id,
            start_ms=start_ms,
            end_ms=start_ms + duration_ms,
            narration=self.text,
            visual_tags=self.visuals,
            visual_clips=visual_clips,
            emotion=self.emotion,
            chart_video=self.chart_video,
        )


@dataclass
class VideoSpec:
    """Complete specification for a video."""
    title: str
    segments: List[SegmentSpec]
    voice_id: str = "en-US-Studio-O"
    voice_speed: str = "fast"
    music: str = "inspirational"
    output_dir: str = "out/generated"
    disclaimer: str = "Educational content only. Not financial advice."
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoSpec":
        """Create VideoSpec from dictionary."""
        segments = [
            SegmentSpec(
                text=s["text"],
                emotion=s.get("emotion", "neutral"),
                visuals=s.get("visuals", []),
                clips=s.get("clips"),
                duration_seconds=s.get("duration"),
                chart_video=s.get("chart_video"),
            )
            for s in data.get("segments", [])
        ]
        
        return cls(
            title=data.get("title", "Untitled Video"),
            segments=segments,
            voice_id=data.get("voice_id", "en-US-Studio-O"),
            voice_speed=data.get("voice_speed", "fast"),
            music=data.get("music", "inspirational"),
            output_dir=data.get("output_dir", "out/generated"),
            disclaimer=data.get("disclaimer", "Educational content only."),
        )
    
    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "VideoSpec":
        """Load VideoSpec from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    def to_script(self) -> Script:
        """Convert to internal Script model."""
        internal_segments = []
        current_ms = 0
        
        for i, seg_spec in enumerate(self.segments, start=1):
            segment = seg_spec.to_segment(i, current_ms)
            internal_segments.append(segment)
            current_ms = segment.end_ms
        
        return Script(
            title=self.title,
            target_seconds=current_ms // 1000,
            segments=internal_segments,
            disclaimer=self.disclaimer,
        )


def create_video(
    spec: Union[str, Path, Dict[str, Any], VideoSpec],
    force_refresh: bool = False
) -> Path:
    """
    Create a video from a specification.
    
    Args:
        spec: Can be:
            - Path to YAML file (str or Path)
            - Dictionary with video specification
            - VideoSpec object
        force_refresh: If True, ignore cache and re-download videos
    
    Returns:
        Path to the generated video file
    
    Example:
        # From YAML
        video = create_video("videos/my_video.yaml")
        
        # From dict
        video = create_video({
            "title": "Hello World",
            "segments": [
                {"text": "Welcome to my video!", "emotion": "excited"}
            ]
        })
    """
    # Parse spec
    if isinstance(spec, (str, Path)):
        path = Path(spec)
        if path.suffix in ('.yaml', '.yml'):
            video_spec = VideoSpec.from_yaml(path)
        elif path.suffix == '.json':
            with open(path) as f:
                video_spec = VideoSpec.from_dict(json.load(f))
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")
    elif isinstance(spec, dict):
        video_spec = VideoSpec.from_dict(spec)
    elif isinstance(spec, VideoSpec):
        video_spec = spec
    else:
        raise TypeError(f"Invalid spec type: {type(spec)}")
    
    # Setup directories
    settings = get_settings()
    settings.ensure_valid()
    
    output_dir = Path(video_spec.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    tmp_dir = Path(settings.tmp_dir)
    (tmp_dir / "videos").mkdir(parents=True, exist_ok=True)
    (tmp_dir / "audio").mkdir(parents=True, exist_ok=True)
    
    # Convert to internal script
    script = video_spec.to_script()
    
    print(f"🎬 Creating video: {video_spec.title}")
    print(f"📊 Duration: ~{script.total_duration_ms / 1000:.1f}s")
    print(f"📝 Segments: {len(script.segments)}")
    
    # Import here to avoid circular imports
    from .footage_search import fetch_visuals_for_script, search_music, download_music
    from .tts import synthesize_segments
    from .arranger import build_render_plan
    from .renderer import render
    from .subtitles import write_srt
    
    with tqdm(total=4, desc="Pipeline", unit="step") as pbar:
        # 1. Fetch visuals
        pbar.set_description("Fetching footage")
        visuals = fetch_visuals_for_script(script, tmp_dir / "videos", force_refresh)
        pbar.update(1)
        
        # 2. Generate TTS
        pbar.set_description("Synthesizing audio")
        tts = synthesize_segments(
            script,
            tmp_dir / "audio",
            voice_id=video_spec.voice_id,
            voice_speed=video_spec.voice_speed,
        )
        pbar.update(1)
        
        # 3. Fetch music
        pbar.set_description("Fetching music")
        bgm_path = None
        try:
            tracks = search_music(video_spec.music)
            if tracks:
                bgm_dest = tmp_dir / "audio" / f"bgm_{video_spec.music}.mp3"
                bgm_path = str(download_music(tracks[0]["url"], bgm_dest))
        except Exception as e:
            print(f"Warning: Music failed: {e}")
        pbar.update(1)
        
        # 4. Render
        pbar.set_description("Rendering video")
        out_path = output_dir / "video.mp4"
        plan = build_render_plan(script, visuals, tts, out_path)
        if bgm_path:
            plan.bgm_path = bgm_path
        
        result_path = render(plan)
        
        # Write subtitles
        write_srt(script, tts, output_dir / "subtitles.srt")
        pbar.update(1)
    
    # Write manifest
    manifest = {
        "title": script.title,
        "duration_seconds": script.total_duration_ms / 1000,
        "segments": len(script.segments),
        "output": str(result_path),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    
    print(f"✅ Video created: {result_path}")
    return result_path

