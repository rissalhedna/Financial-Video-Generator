"""
Revision agent - checks for consistency and fixes issues.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from .base import ScriptAgent, AgentContext, AgentOutput, SegmentOutput


class RevisionAgent(ScriptAgent):
    """Revises the complete script for consistency and flow."""
    
    name = "revision"
    target_duration_seconds = 0  # Not applicable for revision
    
    @property
    def system_prompt(self) -> str:
        return """You are part of a financial video scriptwriters team. Your job is to REVISE an existing script for consistency, flow, and quality.

TASK: Review and improve the given script.

WHAT TO FIX:
1. Grammatical inconsistencies
2. Repetitive sentences or phrases - consolidate into one
3. Story flow holes - ensure smooth transitions
4. Awkward phrasing - make it sound natural
5. Sentences that are too long - break them up
6. Any listing of items (avoid "phones, tablets, watches...")

WHAT TO PRESERVE:
1. All data points (percentages, dates, numbers) - DO NOT remove these
2. The overall structure and message
3. The social media style tone
4. Segment boundaries (keep same number of segments)
5. on_screen_text fields if present
6. is_chart_placeholder flags if present

STRICT RULES:
- NO investment advice (no buy/sell/hold/targets)
- Educational tone only
- Keep the story flowing naturally
- Only make small, targeted improvements
- Do NOT add new content or segments

Return the revised segments in the same JSON format."""
    
    def build_user_prompt(self, context: AgentContext) -> str:
        """Build prompt with all segments to revise."""
        segments_json = json.dumps(context.previous_segments, indent=2)
        
        return f"""TOPIC: {context.topic}

SCRIPT TO REVISE:
{segments_json}

Review this script for:
- Repetitive phrases
- Grammatical issues
- Flow problems
- Awkward listing of items

Return the revised script in the same JSON format:
{{
  "segments": [
    {{"text": "...", "duration_estimate_seconds": 5, "on_screen_text": "...", "is_chart_placeholder": false}}
  ]
}}

Preserve all data points and segment count. Only make minimal necessary improvements."""
    
    def run(self, context: AgentContext) -> AgentOutput:
        """Run revision on the accumulated segments."""
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

