from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, NonNegativeInt, PositiveInt, validator


class InputData(BaseModel):
    topic: str
    facts: List[str] = Field(default_factory=list)
    news: List[str] = Field(default_factory=list)
    target_seconds: PositiveInt = 45
    mood: str = "excited"
    voice_id: Optional[str] = None
    force_cache_refresh: bool = Field(default=False, description="If True, ignores existing cached video files and redownloads them.")
    voice_speed: str = Field(default="medium", pattern="^(slow|medium|fast)$", description="Overall talking speed: slow (0.9x), medium (1.0x), fast (1.1x)")
    emotion_intensity: float = Field(default=1.0, ge=0.0, le=2.0, description="Scale factor for emotion expressiveness (0.0=neutral, 1.0=normal, 2.0=exaggerated)")


class VisualClip(BaseModel):
    """A single visual clip within a segment. Allows multiple clips per segment for variety."""
    tags: List[str] = Field(default_factory=list)
    duration_pct: float = Field(default=100.0, ge=0, le=100, description="Percentage of segment duration for this clip")
    trigger: Optional[str] = Field(default=None, description="Word/phrase that triggers this clip (for word-sync)")


class Segment(BaseModel):
    id: PositiveInt
    start_ms: NonNegativeInt
    end_ms: PositiveInt
    narration: str
    on_screen_text: Optional[str] = None
    visual_tags: List[str] = Field(default_factory=list)  # Legacy: single set of tags
    visual_clips: Optional[List[VisualClip]] = None  # New: multiple clips with specific tags
    emotion: Optional[str] = None
    sfx: List[str] = Field(default_factory=list)
    bgm_mood: Optional[str] = None
    emphasis_words: Optional[List[str]] = None  # Used for SSML <emphasis> tags
    pause_after_ms: Optional[int] = None  # AI-suggested pause duration after segment (works with <break> tag)
    chart_video: Optional[str] = None  # Pre-generated chart video path (skips stock video fetch)

    @validator("end_ms")
    def validate_duration(cls, v: int, values: dict) -> int:
        start = values.get("start_ms", 0)
        if v <= start:
            raise ValueError("end_ms must be greater than start_ms")
        return v

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


class Script(BaseModel):
    title: str
    target_seconds: PositiveInt
    segments: List[Segment]
    disclaimer: str
    # We could carry emotion_intensity here if needed, but it's cleaner to pass it as a param

    @property
    def total_duration_ms(self) -> int:
        if not self.segments:
            return 0
        return self.segments[-1].end_ms


class VisualAsset(BaseModel):
    segment_id: PositiveInt
    source_url: str  # Changed from HttpUrl to str to allow "cached" or file paths
    file_path: str
    width: PositiveInt
    height: PositiveInt
    duration_ms: PositiveInt
    trim_start_ms: NonNegativeInt = 0
    trim_end_ms: Optional[NonNegativeInt] = None


class TTSResult(BaseModel):
    segment_id: PositiveInt
    audio_path: str
    duration_ms: PositiveInt
    words: Optional[List[dict]] = None  # word-level timestamps if available


class RenderSegment(BaseModel):
    segment_id: PositiveInt
    video_path: str
    audio_path: str
    start_ms: NonNegativeInt
    end_ms: PositiveInt
    scale_to: str = "720x1280"
    center_crop: bool = True
    fade_frames: int = 5
    # Multi-clip support
    clip_index: int = 0  # Which clip within the segment (0-indexed)
    total_clips: int = 1  # Total clips in this segment
    clip_duration_ms: Optional[PositiveInt] = None  # Duration for this specific clip


class RenderPlan(BaseModel):
    resolution: str = "720x1280"
    fps: PositiveInt = 30
    total_ms: PositiveInt
    segments: List[RenderSegment]
    output_path: str
    bgm_path: Optional[str] = None
    srt_path: Optional[str] = None  # Optional path to SRT file to burn into the video
