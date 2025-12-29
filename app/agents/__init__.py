"""
Agentic script generation pipeline.

This module provides specialized LLM agents for generating video scripts:
- IntroductionAgent: Creates compelling hooks
- DevelopmentAgent: Covers key facts
- ChartsAgent: Data segments with chart placeholders
- ConclusionAgent: Story close
- RevisionAgent: Consistency check
- VisualMapperAgent: Adds visual annotations
"""
from .base import AgentContext, AgentOutput, SegmentOutput, ScriptAgent
from .introduction import IntroductionAgent
from .development import DevelopmentAgent
from .charts import ChartsAgent, ChartData, ChartSegmentOutput
from .conclusion import ConclusionAgent
from .revision import RevisionAgent
from .visual_mapper import VisualMapperAgent, VisualSegmentOutput, VisualClipOutput

__all__ = [
    "AgentContext",
    "AgentOutput",
    "SegmentOutput",
    "ScriptAgent",
    "IntroductionAgent",
    "DevelopmentAgent",
    "ChartsAgent",
    "ChartData",
    "ChartSegmentOutput",
    "ConclusionAgent",
    "RevisionAgent",
    "VisualMapperAgent",
    "VisualSegmentOutput",
    "VisualClipOutput",
]

