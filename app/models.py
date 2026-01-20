from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, NonNegativeInt, PositiveInt, validator


# Video style presets for different content formats
VIDEO_STYLES: Dict[str, Dict[str, any]] = {
    "social-media": {"default_seconds": 45, "segment_hint": "3-8 seconds each"},
    "documentary": {"default_seconds": 300, "segment_hint": "10-25 seconds each"},
}

# Video content types - what kind of story to tell
VIDEO_TYPES: Dict[str, Dict[str, str]] = {
    "stock-analysis": {
        "name": "Stock Analysis",
        "description": "Analyze recent price performance and market position",
        "prompt_hint": "Focus on recent price movements, key metrics, and what's driving the stock",
    },
    "company-story": {
        "name": "Company Story",
        "description": "Tell the company's journey and growth story",
        "prompt_hint": "Focus on the company's history, major milestones, and long-term growth trajectory",
    },
}

# Supported stocks with CDN data
SUPPORTED_STOCKS: Dict[str, str] = {
    # Tech giants
    "AAPL.US": "Apple",
    "MSFT.US": "Microsoft",
    "GOOGL.US": "Google (Alphabet)",
    "AMZN.US": "Amazon",
    "META.US": "Meta (Facebook)",
    "NVDA.US": "Nvidia",
    "TSLA.US": "Tesla",
    "NFLX.US": "Netflix",
    # Finance
    "JPM.US": "JPMorgan Chase",
    "GS.US": "Goldman Sachs",
    "BAC.US": "Bank of America",
    "WFC.US": "Wells Fargo",
    "V.US": "Visa",
    "MA.US": "Mastercard",
    "PYPL.US": "PayPal",
    "BRK-B.US": "Berkshire Hathaway",
    # Healthcare
    "JNJ.US": "Johnson & Johnson",
    "PFE.US": "Pfizer",
    "UNH.US": "UnitedHealth",
    "ABBV.US": "AbbVie",
    "MRK.US": "Merck",
    "LLY.US": "Eli Lilly",
    # Consumer
    "WMT.US": "Walmart",
    "COST.US": "Costco",
    "KO.US": "Coca-Cola",
    "PEP.US": "PepsiCo",
    "NKE.US": "Nike",
    "SBUX.US": "Starbucks",
    "MCD.US": "McDonald's",
    "DIS.US": "Disney",
    # Industrial / Energy
    "XOM.US": "ExxonMobil",
    "CVX.US": "Chevron",
    "BA.US": "Boeing",
    "CAT.US": "Caterpillar",
    "GE.US": "General Electric",
    "HON.US": "Honeywell",
    # Semiconductors
    "AMD.US": "AMD",
    "INTC.US": "Intel",
    "QCOM.US": "Qualcomm",
    "AVGO.US": "Broadcom",
    "TSM.US": "TSMC",
    # Telecom
    "T.US": "AT&T",
    "VZ.US": "Verizon",
    "TMUS.US": "T-Mobile",
    # Other notable
    "CRM.US": "Salesforce",
    "ADBE.US": "Adobe",
    "ORCL.US": "Oracle",
    "IBM.US": "IBM",
    "CSCO.US": "Cisco",
    "UBER.US": "Uber",
    "ABNB.US": "Airbnb",
    "SPOT.US": "Spotify",
    "ZM.US": "Zoom",
    "SHOP.US": "Shopify",
    "SQ.US": "Block (Square)",
    "PLTR.US": "Palantir",
    "SNOW.US": "Snowflake",
    "CRWD.US": "CrowdStrike",
    "COIN.US": "Coinbase",
}


class InputData(BaseModel):
    topic: str
    stock_symbol: Optional[str] = Field(default=None, description="Stock symbol (e.g., AAPL.US) for CDN data")
    video_type: str = Field(default="stock-analysis", pattern="^(stock-analysis|company-story)$", description="Type of video content")
    facts: List[str] = Field(default_factory=list)
    news: List[str] = Field(default_factory=list)
    target_seconds: PositiveInt = 45
    video_style: str = Field(default="social-media", pattern="^(social-media|documentary)$", description="Video format: social-media (short) or documentary (long)")
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
