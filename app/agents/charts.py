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
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "title": self.title,
            "labels": self.labels,
            "values": self.values,
            "x_axis_label": self.x_axis_label,
            "y_axis_label": self.y_axis_label,
        }


@dataclass 
class ChartSegmentOutput(SegmentOutput):
    """Extended segment output with chart data."""
    chart_data: Optional[ChartData] = None
    chart_video_path: Optional[str] = None


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

CHART TYPE GUIDE:
- "line": For time series, trends over time (e.g. stock price history, revenue growth)
- "bar": For comparing values across categories (e.g. revenue by year, earnings by quarter)
- "pie": For showing proportions/percentages (e.g. revenue breakdown by product)

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
        "labels": ["2014", "2018", "2022", "2024"],
        "values": [31, 45, 150, 227],
        "x_axis_label": "Year",
        "y_axis_label": "Price (USD)"
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
                    x_axis_label=cd.get("x_axis_label"),
                    y_axis_label=cd.get("y_axis_label"),
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
    
    def generate_chart(self, chart_data: ChartData, output_path: Path) -> Optional[Path]:
        """
        Generate an animated chart video using manim.
        
        Args:
            chart_data: ChartData with type, labels, values, etc.
            output_path: Where to save the generated video
        
        Returns:
            Path to the generated chart video, or None on failure
        """
        try:
            from ..manim_charts.create_chart_from_json import render_chart_from_data
            
            # Convert to dict format expected by manim renderer
            data = chart_data.to_dict()
            
            # Render the chart (returns path to generated video)
            video_path = render_chart_from_data(data)
            
            if video_path and Path(video_path).exists():
                # Copy to desired output path
                import shutil
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(video_path, output_path)
                return output_path
            
            return None
        except Exception as e:
            print(f"Warning: Chart generation failed: {e}")
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
