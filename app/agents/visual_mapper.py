"""
Visual Mapper agent - adds emotions, visual tags, and triggers.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import ScriptAgent, AgentContext, AgentOutput, SegmentOutput, get_settings
from openai import OpenAI


@dataclass
class VisualClipOutput:
    """A visual clip with tags and trigger."""
    tags: List[str] = field(default_factory=list)
    trigger: Optional[str] = None


@dataclass
class VisualSegmentOutput:
    """A segment with visual annotations."""
    text: str
    emotion: str = "informative"
    duration_estimate_seconds: float = 5.0
    on_screen_text: Optional[str] = None
    is_chart_placeholder: bool = False
    clips: List[VisualClipOutput] = field(default_factory=list)


class VisualMapperAgent:
    """Adds visual annotations (emotions, tags, triggers) to the script."""
    
    name = "visual_mapper"
    
    @property
    def system_prompt(self) -> str:
        return """You are a visual director for short-form financial videos. Your job is to add visual annotations to a script.

For each segment, you must add:
1. emotion: One of [curious, serious, informative, dramatic, impactful]
2. clips: Array of visual descriptions for stock footage

EMOTION GUIDE:
- curious: Questions, mysteries, "what if" moments
- serious: Important facts, warnings, transitions
- informative: Explanations, context, background
- dramatic: Big reveals, surprising data, climaxes
- impactful: Conclusions, key takeaways, memorable moments

VISUAL TAGS RULES:
- Use GENERIC terms (no brand names) - "smartphone" not "iPhone"
- Use concrete, searchable terms for stock footage
- Format: 3-4 descriptive words per clip
- Examples: "garage workshop vintage", "stock chart rising green", "smartphone modern technology"

TRIGGERS:
- Pick a word from the narration that should trigger a clip change
- Use this for precise visual synchronization
- Choose words that match the visual concept

MULTI-CLIP SEGMENTS:
- If a segment mentions multiple distinct concepts, create multiple clips
- Each clip should have a trigger word

Example output for a segment:
{
  "text": "This is Apple. Started in a garage. Now worth three trillion.",
  "emotion": "serious",
  "clips": [
    {"tags": ["garage workshop vintage technology"], "trigger": "garage"},
    {"tags": ["skyscraper corporate modern city"], "trigger": "trillion"}
  ]
}

CHART PLACEHOLDER SEGMENTS:
- For segments with is_chart_placeholder=true, use generic data visualization tags
- Example: ["chart graph data visualization", "stock market screen trading"]

Return the complete script with visual annotations."""

    def run(self, segments: List[Dict[str, Any]], topic: str) -> List[VisualSegmentOutput]:
        """Add visual annotations to segments."""
        settings = get_settings()
        client = OpenAI(api_key=settings.openai_api_key, timeout=60.0)
        
        segments_json = json.dumps(segments, indent=2)
        
        user_prompt = f"""TOPIC: {topic}

SCRIPT TO ANNOTATE:
{segments_json}

Add visual annotations (emotion, clips with tags and triggers) to each segment.

Return JSON:
{{
  "segments": [
    {{
      "text": "...",
      "emotion": "curious",
      "duration_estimate_seconds": 5,
      "on_screen_text": null,
      "is_chart_placeholder": false,
      "clips": [
        {{"tags": ["word1 word2 word3"], "trigger": "keyword"}}
      ]
    }}
  ]
}}"""
        
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        
        result = []
        for seg in data.get("segments", []):
            clips = [
                VisualClipOutput(
                    tags=clip.get("tags", []),
                    trigger=clip.get("trigger"),
                )
                for clip in seg.get("clips", [])
            ]
            
            result.append(VisualSegmentOutput(
                text=seg.get("text", ""),
                emotion=seg.get("emotion", "informative"),
                duration_estimate_seconds=seg.get("duration_estimate_seconds", 5.0),
                on_screen_text=seg.get("on_screen_text"),
                is_chart_placeholder=seg.get("is_chart_placeholder", False),
                clips=clips,
            ))
        
        return result

