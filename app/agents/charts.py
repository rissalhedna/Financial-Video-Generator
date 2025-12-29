"""
Charts agent - generates the data segment and chart visuals.

This agent handles both:
1. Script generation (narration about data)
2. Chart generation (placeholder for now, ready for implementation)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import ScriptAgent, AgentContext, AgentOutput, SegmentOutput


@dataclass
class ChartData:
    """Data structure for chart generation."""
    chart_type: str = "line"  # line, bar, pie
    title: str = ""
    labels: List[str] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    color: str = "#00C853"  # Green by default
    duration_seconds: float = 5.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "title": self.title,
            "labels": self.labels,
            "values": self.values,
            "color": self.color,
            "duration_seconds": self.duration_seconds,
        }


@dataclass 
class ChartSegmentOutput(SegmentOutput):
    """Extended segment output with chart data."""
    chart_data: Optional[ChartData] = None


class ChartsAgent(ScriptAgent):
    """
    Generates the charts/data section (~10 seconds).
    
    This agent is responsible for:
    1. Writing narration about data/trends
    2. Extracting chart data from the content
    3. Generating chart visuals (placeholder for now)
    
    When chart generation is implemented, just fill in generate_chart().
    """
    
    name = "charts"
    target_duration_seconds = 10
    
    @property
    def system_prompt(self) -> str:
        return """You are part of a financial video scriptwriters team. Your job is to write the CHARTS section - a transition between development and conclusion where data will be shown on screen.

TASK: Produce a story-driven data segment (~10 seconds).

CRITICAL REQUIREMENTS:
1. Generate segments that add up to the target duration
2. The script must follow a social media style
3. Write narration as a FLOWING STORY - segments should connect naturally
4. Avoid starting every segment with "And" or "But" - vary your transitions
5. Include specific data that can be visualized (percentages, growth, dates)
6. Do NOT announce the chart ("look at this chart") - just tell the story with data

DATA PRESENTATION:
- Use specific numbers, dates, and percentages from the facts provided
- Example: "Between 2014 and 2024, the company grew 600%"
- Make the data part of the narrative, not a separate announcement
- One clear data point is better than many confusing ones

OUTPUT FORMAT:
Include chart_data with the key metrics for visualization.

STRICT RULES:
- NO investment advice (no buy/sell/hold/targets)
- Educational tone only
- Flow naturally from previous segments
- Focus on storytelling, not chart announcements

Return JSON with this format:
{
  "segments": [
    {
      "text": "Between 2014 and today, the stock jumped from $31 to over $227.",
      "duration_estimate_seconds": 5,
      "on_screen_text": "$31 → $227 (2014-2024)",
      "chart_data": {
        "chart_type": "line",
        "title": "Stock Price",
        "labels": ["2014", "2024"],
        "values": [31, 227]
      }
    }
  ]
}"""
    
    def run(self, context: AgentContext) -> AgentOutput:
        """Run the agent and process chart data."""
        user_prompt = self.build_user_prompt(context)
        data = self._call_llm(self.system_prompt, user_prompt)
        
        segments = []
        for seg in data.get("segments", []):
            # Parse chart data if present
            chart_data = None
            if seg.get("chart_data"):
                cd = seg["chart_data"]
                chart_data = ChartData(
                    chart_type=cd.get("chart_type", "line"),
                    title=cd.get("title", ""),
                    labels=cd.get("labels", []),
                    values=cd.get("values", []),
                    color=cd.get("color", "#00C853"),
                    duration_seconds=seg.get("duration_estimate_seconds", 5.0),
                )
            
            segment = ChartSegmentOutput(
                text=seg.get("text", ""),
                duration_estimate_seconds=seg.get("duration_estimate_seconds", 5.0),
                on_screen_text=seg.get("on_screen_text"),
                is_chart_placeholder=True,
                chart_data=chart_data,
            )
            segments.append(segment)
        
        return AgentOutput(segments=segments)
    
    # =========================================================================
    # CHART GENERATION - PLACEHOLDER
    # Fill in this method when ready to generate actual charts
    # =========================================================================
    
    def generate_chart(self, chart_data: ChartData, output_path: Path) -> Path:
        """
        Generate an animated chart video from data.
        
        TODO: Implement chart generation using matplotlib/plotly + moviepy
        
        Args:
            chart_data: ChartData with type, labels, values, etc.
            output_path: Where to save the generated video
        
        Returns:
            Path to the generated chart video
        
        Example implementation:
        ```python
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation
        
        fig, ax = plt.subplots()
        
        if chart_data.chart_type == "line":
            # Animate line drawing
            line, = ax.plot([], [], color=chart_data.color, linewidth=3)
            ax.set_xlim(0, len(chart_data.values))
            ax.set_ylim(0, max(chart_data.values) * 1.1)
            
            def animate(frame):
                line.set_data(range(frame+1), chart_data.values[:frame+1])
                return line,
            
            anim = FuncAnimation(fig, animate, frames=len(chart_data.values))
            anim.save(output_path, fps=30)
        
        return output_path
        ```
        """
        # PLACEHOLDER: Return None to signal "use stock video fallback"
        # When implemented, return the path to the generated chart video
        return None
    
    def get_chart_video(self, segment: ChartSegmentOutput, output_dir: Path) -> Optional[Path]:
        """
        Get chart video for a segment.
        
        Returns:
            Path to chart video if generated, None to use stock video fallback
        """
        if not segment.chart_data:
            return None
        
        chart_path = output_dir / f"chart_{hash(segment.text) % 10000}.mp4"
        
        # Try to generate chart
        result = self.generate_chart(segment.chart_data, chart_path)
        
        if result and result.exists():
            return result
        
        # Fallback: return None (will use stock video)
        return None
