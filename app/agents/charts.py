"""
Charts agent - generates the data segment and chart visuals using real CDN data.

This agent handles both:
1. Script generation (narration about data)
2. Chart generation using real stock data from CDN
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
    blur_background: bool = False  # If True, composite over blurred stock video
    # CDN data source info
    symbol: Optional[str] = None  # e.g., "AAPL.US"
    chart_range: Optional[str] = None  # e.g., "Y1" for 1 year
    
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
    Generates the charts/data section (~10 seconds) using real CDN data.
    
    This agent is responsible for:
    1. Writing narration about data/trends
    2. Fetching real chart data from CDN
    3. Generating chart visuals with Manim
    """
    
    name = "charts"
    target_duration_seconds = 10
    
    # Symbol to use for CDN data (set by pipeline)
    stock_symbol: Optional[str] = None
    
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

NOTE: Chart data will be fetched from real stock data sources. Just write compelling narration.

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
      "needs_chart": true
    }
  ]
}"""
    
    def run(self, context: AgentContext) -> AgentOutput:
        """Run the agent and fetch real chart data from CDN."""
        user_prompt = self.build_user_prompt(context)
        data = self._call_llm(self.system_prompt, user_prompt)
        
        # Try to get real chart data from CDN
        cdn_chart_data = self._fetch_cdn_chart_data(context.topic)
        
        segments = []
        chart_used = False
        
        for seg in data.get("segments", []):
            chart_data = None
            
            # Use CDN data for the first segment that needs a chart
            if seg.get("needs_chart", False) and cdn_chart_data and not chart_used:
                chart_data = cdn_chart_data
                chart_used = True
            
            segment = ChartSegmentOutput(
                text=seg.get("text", ""),
                duration_estimate_seconds=seg.get("duration_estimate_seconds", 5.0),
                on_screen_text=seg.get("on_screen_text"),
                is_chart_placeholder=True if chart_data else False,
                chart_data=chart_data,
            )
            segments.append(segment)
        
        return AgentOutput(segments=segments)
    
    def _fetch_cdn_chart_data(self, topic: str) -> Optional[ChartData]:
        """
        Fetch real chart data from CDN based on topic.
        
        Args:
            topic: The video topic (e.g., "Apple Inc stock")
            
        Returns:
            ChartData with real stock data, or None if CDN is unavailable
        """
        try:
            from ..CDN import extract_symbol_from_topic, build_chart_data, ChartRange
            from ..config import get_settings
            
            settings = get_settings()
            
            # Check if CDN is configured
            if not settings.cdn_api_url or not settings.cdn_api_key:
                print("⚠️ CDN not configured, skipping real chart data")
                return None
            
            # Extract symbol from topic
            symbol = self.stock_symbol or extract_symbol_from_topic(topic)
            if not symbol:
                print(f"⚠️ Could not extract stock symbol from topic: {topic}")
                return None
            
            print(f"📊 Fetching chart data for {symbol} from CDN...")
            
            # Build chart data (fetches from CDN and creates JSON)
            json_path = build_chart_data(symbol, ChartRange.Y1)  # Default to 1 year
            
            # Load the generated JSON
            import json
            chart_json = json.loads(json_path.read_text())
            
            # Convert to ChartData
            return ChartData(
                chart_type=chart_json.get("chart_type", "line"),
                title=chart_json.get("title", "Stock Price"),
                labels=chart_json.get("labels", []),
                values=chart_json.get("values", []),
                x_axis_label=chart_json.get("x_axis_label", "Date"),
                y_axis_label=chart_json.get("y_axis_label", "Price (USD)"),
                blur_background=True,  # Default to blurred background
                symbol=symbol,
                chart_range="Y1",
            )
            
        except Exception as e:
            print(f"⚠️ Failed to fetch CDN chart data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_chart(
        self, 
        chart_data: ChartData, 
        output_path: Path,
        background_video: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Generate an animated chart video using manim.
        
        Args:
            chart_data: ChartData with type, labels, values, etc.
            output_path: Where to save the generated video
            background_video: Optional stock video to use as blurred background
        
        Returns:
            Path to the generated chart video, or None on failure
        """
        try:
            from ..manim_charts.create_chart_from_json import render_chart_from_data, get_default_background
            from ..manim_charts.chart_video_compositor import compose_with_background
            import shutil
            
            # Convert to dict format expected by manim renderer
            data = chart_data.to_dict()
            
            # Render the chart with transparency for compositing
            use_transparency = chart_data.blur_background
            video_path = render_chart_from_data(data, transparent=use_transparency)
            
            if not video_path or not Path(video_path).exists():
                return None
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If blur_background is enabled, composite over background
            if chart_data.blur_background:
                try:
                    # Use provided background or default
                    if background_video and background_video.exists():
                        bg_path = str(background_video)
                    else:
                        bg_path = str(get_default_background())
                    
                    result = compose_with_background(bg_path, video_path)
                    # Copy result to output path
                    shutil.copy(result, output_path)
                    return output_path
                except Exception as e:
                    print(f"⚠️ Compositing failed, using plain chart: {e}")
                    shutil.copy(video_path, output_path)
                    return output_path
            else:
                # Just copy the chart video
                shutil.copy(video_path, output_path)
                return output_path
            
        except Exception as e:
            print(f"Warning: Chart generation failed: {e}")
            import traceback
            traceback.print_exc()
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
