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
    chart_video_path: Optional[str] = None  # Pre-generated chart video


class VisualMapperAgent:
    """Adds visual annotations (emotions, tags, triggers) to the script."""
    
    name = "visual_mapper"
    
    @property
    def system_prompt(self) -> str:
        return """You are a visual director for PROFESSIONAL financial/business videos. Choose stock footage that SUPPORTS THE STORY, not literally illustrates every word.

CRITICAL MINDSET:
Think like a documentary editor. Ask: "What would Bloomberg or CNBC show here?"
This video is about a COMPANY/STOCK - every visual should relate to business, finance, or technology.

⚠️ DO NOT TAKE WORDS LITERALLY - UNDERSTAND CONTEXT:
| Phrase in script | ❌ WRONG (literal) | ✅ RIGHT (contextual) |
|------------------|-------------------|----------------------|
| "Fast forward to today" | fast cars, speed | modern city skyline, office building |
| "Apple's journey" | road trip, hiking | tech office, products on display |
| "Explosive growth" | explosion, fire | stock chart rising, busy trading floor |
| "Diving into financials" | scuba diving | documents, spreadsheets, analyst working |
| "Sky-rocketed" | rocket launch | green stock arrows, celebration |
| "What lies ahead?" | road, path | businessman thinking, meeting room |
| "Unstoppable rise" | stairs, elevator | trading floor, wealth imagery |
| "Let's dive in" | swimming pool | computer screen, research |
| "The story unfolds" | book opening | timeline graphics, historical footage |

THIS IS A BUSINESS VIDEO - USE BUSINESS VISUALS:
1. CORPORATE: office building, boardroom, handshake, executives, headquarters
2. TECHNOLOGY: smartphone closeup, laptop screen, server room, circuit board
3. FINANCE: stock ticker, trading screens, charts, money, calculator, wall street
4. GROWTH: city construction, expanding warehouse, team celebration
5. WORK: employees at desks, team meeting, presentation, typing
6. DATA: screens with numbers, analytics dashboard, documents

FORMAT: 3-4 concrete words that will find REAL footage on Pexels/Pixabay.
NO: Brand names, metaphors taken literally, abstract concepts, nature unless relevant.

EMOTION GUIDE:
- curious → person researching, thinking, question on screen
- dramatic → impressive buildings, stock celebration, big numbers
- informative → office work, documents, screens with data
- impactful → city panorama, success imagery, team applause

TRIGGERS: Choose the most MEANINGFUL business word, not transition phrases like "let's" or "now"."""

    def run(self, segments: List[Dict[str, Any]], topic: str) -> List[VisualSegmentOutput]:
        """Add visual annotations to segments."""
        settings = get_settings()
        client = OpenAI(api_key=settings.openai_api_key, timeout=60.0)
        
        segments_json = json.dumps(segments, indent=2)
        
        user_prompt = f"""TOPIC: {topic}

SCRIPT TO ANNOTATE:
{segments_json}

This is a BUSINESS/FINANCE video. Choose visuals like a professional documentary editor would.

⚠️ CRITICAL: Do NOT take phrases literally!
- "Fast forward" → show modern office, NOT fast cars
- "Journey" → show company growth, NOT hiking
- "Dive in" → show research/analysis, NOT swimming

GOOD EXAMPLE:
{{
  "text": "Fast forward to today, and it's now a trillion-dollar empire.",
  "emotion": "dramatic",
  "clips": [
    {{"tags": ["modern glass office building exterior"], "trigger": "today"}},
    {{"tags": ["stock market trading floor busy"], "trigger": "trillion"}}
  ]
}}

Return JSON with business-appropriate visuals:
{{
  "segments": [
    {{
      "text": "...",
      "emotion": "curious",
      "duration_estimate_seconds": 5,
      "on_screen_text": null,
      "is_chart_placeholder": false,
      "clips": [
        {{"tags": ["business finance technology terms"], "trigger": "keyword"}}
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

