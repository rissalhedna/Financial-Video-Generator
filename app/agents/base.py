"""
Base agent class for the agentic script generation pipeline.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import get_settings


@dataclass
class AgentContext:
    """Shared context passed between agents."""
    topic: str
    facts: List[str] = field(default_factory=list)
    news: List[str] = field(default_factory=list)
    target_seconds: int = 60
    mood: str = "informative"
    previous_segments: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_previous_text(self) -> str:
        """Get all previous segment texts for context."""
        if not self.previous_segments:
            return ""
        texts = [seg.get("text", "") for seg in self.previous_segments]
        return "\n\n".join(texts)


@dataclass
class SegmentOutput:
    """A single segment output from an agent."""
    text: str
    duration_estimate_seconds: float = 5.0
    on_screen_text: Optional[str] = None
    is_chart_placeholder: bool = False


@dataclass
class AgentOutput:
    """Output from a script agent."""
    segments: List[SegmentOutput] = field(default_factory=list)
    
    def to_dicts(self) -> List[Dict[str, Any]]:
        """Convert segments to dictionaries."""
        return [
            {
                "text": seg.text,
                "duration_estimate_seconds": seg.duration_estimate_seconds,
                "on_screen_text": seg.on_screen_text,
                "is_chart_placeholder": seg.is_chart_placeholder,
            }
            for seg in self.segments
        ]


class ScriptAgent(ABC):
    """Base class for script generation agents."""
    
    name: str = "base"
    target_duration_seconds: int = 15
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for the LLM."""
        pass
    
    def build_user_prompt(self, context: AgentContext) -> str:
        """Build the user prompt from context."""
        facts_str = "\n- ".join(context.facts) if context.facts else "N/A"
        news_str = "\n- ".join(context.news) if context.news else "N/A"
        
        previous = context.get_previous_text()
        previous_section = f"\n\nPREVIOUS SEGMENTS (maintain story flow):\n{previous}" if previous else ""
        
        return f"""TOPIC: {context.topic}

FACTS:
- {facts_str}

NEWS:
- {news_str}

TARGET DURATION: {self.target_duration_seconds} seconds{previous_section}

Return ONLY valid JSON with this format:
{{
  "segments": [
    {{"text": "Your narration here", "duration_estimate_seconds": 5}}
  ]
}}"""
    
    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        retry=retry_if_exception_type(Exception),
    )
    def _call_llm(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call the LLM with retry logic."""
        settings = get_settings()
        client = OpenAI(api_key=settings.openai_api_key, timeout=60.0)
        
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
    
    def run(self, context: AgentContext) -> AgentOutput:
        """Run the agent and return structured output."""
        user_prompt = self.build_user_prompt(context)
        data = self._call_llm(self.system_prompt, user_prompt)
        
        segments = []
        for seg in data.get("segments", []):
            segments.append(SegmentOutput(
                text=seg.get("text", ""),
                duration_estimate_seconds=seg.get("duration_estimate_seconds", 5.0),
                on_screen_text=seg.get("on_screen_text"),
                is_chart_placeholder=seg.get("is_chart_placeholder", False),
            ))
        
        return AgentOutput(segments=segments)

