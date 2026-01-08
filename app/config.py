from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError


class Settings(BaseModel):
    # API keys
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    google_api_key: str = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    freepik_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("FREEPIK_API_KEY", ""))
    pixabay_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("PIXABAY_API_KEY"))
    pexels_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("PEXELS_API_KEY"))
    # CDN settings
    cdn_api_url: Optional[str] = Field(default_factory=lambda: os.getenv("CDN_API_URL"))
    cdn_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("CDN_API_KEY"))

    # Defaults
    aspect_ratio: str = Field(default_factory=lambda: os.getenv("ASPECT", "9:16"))
    resolution: str = Field(default_factory=lambda: os.getenv("RESOLUTION", "720x1280"))
    fps: int = Field(default_factory=lambda: int(os.getenv("FPS", "30")))
    default_voice_name: Optional[str] = Field(default_factory=lambda: os.getenv("DEFAULT_VOICE_NAME", "en-US-Journey-D"))
    output_dir: str = Field(default_factory=lambda: os.getenv("OUTPUT_DIR", "out"))
    tmp_dir: str = Field(default_factory=lambda: os.getenv("TMP_DIR", "tmp"))
    timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("HTTP_TIMEOUT", "20")))

    # Model
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    
    # TTS settings
    use_ai_speech_control: bool = Field(default_factory=lambda: os.getenv("USE_AI_SPEECH_CONTROL", "false").lower() == "true")
    
    # Chart settings
    chart_blur_background: bool = Field(default_factory=lambda: os.getenv("CHART_BLUR_BACKGROUND", "true").lower() == "true")

    def ensure_valid(self) -> None:
        missing = []
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.google_api_key:
            missing.append("GOOGLE_API_KEY")
        # Freepik is no longer strictly required if we have Pexels/Pixabay
        # but we should check at least one is present
        if not any([self.freepik_api_key, self.pixabay_api_key, self.pexels_api_key]):
            missing.append("ONE OF: FREEPIK_API_KEY, PIXABAY_API_KEY, PEXELS_API_KEY")
        # validate cdn
        if not self.cdn_api_url:
            missing.append("CDN_API_URL")
        if not self.cdn_api_key:
            missing.append("CDN_API_KEY")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Create a .env file based on .env.example."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Load .env only once
    load_dotenv(override=False)
    try:
        settings = Settings()
    except ValidationError as exc:
        raise RuntimeError(f"Invalid configuration: {exc}") from exc
    return settings
