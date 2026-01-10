"""
Script Pipeline - Orchestrates all agents to generate a complete video script.

This module provides separate functions for:
- generate_script_only(): Just the AI script (no charts)
- generate_charts(): Render chart animations from a spec
- generate_script(): Full pipeline (script + charts) - legacy
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm

from .agents import (
    AgentContext,
    IntroductionAgent,
    DevelopmentAgent,
    ChartsAgent,
    ConclusionAgent,
    RevisionAgent,
    VisualMapperAgent,
    VisualSegmentOutput,
)
from .agents.charts import ChartSegmentOutput
from .models import InputData
from .yaml_builder import build_yaml_spec, save_yaml_spec


from typing import Callable

# Type for progress callback: (step_num, step_name, status)
ProgressCallback = Callable[[int, str, str], None]


def generate_script_only(
    input_data: InputData,
    output_path: Optional[Path] = None,
    voice_id: str = "en-US-Studio-O",
    voice_speed: str = "fast",
    music: str = "inspirational",
    on_progress: Optional[ProgressCallback] = None,
) -> Tuple[Dict[str, Any], List[ChartSegmentOutput]]:
    """
    Generate ONLY the script using AI agents - NO chart rendering.
    
    This runs the 6 AI agents to create the narrative but does NOT
    render any Manim chart animations. Use generate_charts() separately.
    
    Args:
        input_data: Input data with topic, facts, news, etc.
        output_path: Optional path to save YAML file
        voice_id: Google TTS voice ID
        voice_speed: slow/medium/fast
        music: Background music mood
    
    Returns:
        Tuple of (VideoSpec dict, list of chart segments needing rendering)
    """
    context = AgentContext(
        topic=input_data.topic,
        facts=input_data.facts,
        news=input_data.news,
        target_seconds=input_data.target_seconds,
        mood=input_data.mood,
        previous_segments=[],
    )
    
    # Calculate duration targets
    total_target = input_data.target_seconds
    intro_target = max(10, total_target * 0.25)
    dev_target = max(10, total_target * 0.30)
    charts_target = max(8, total_target * 0.15)
    conclusion_target = max(10, total_target * 0.30)
    
    # Initialize agents
    intro_agent = IntroductionAgent()
    intro_agent.target_duration_seconds = int(intro_target)
    
    dev_agent = DevelopmentAgent()
    dev_agent.target_duration_seconds = int(dev_target)
    
    charts_agent = ChartsAgent()
    charts_agent.target_duration_seconds = int(charts_target)
    
    conclusion_agent = ConclusionAgent()
    conclusion_agent.target_duration_seconds = int(conclusion_target)
    
    revision_agent = RevisionAgent()
    visual_mapper = VisualMapperAgent()
    
    topic_slug = input_data.topic.lower().replace(" ", "_").replace(".", "")[:30]
    
    print(f"🎬 Generating script for: {input_data.topic}")
    print(f"📊 Target duration: {total_target}s")
    
    # Collect chart segments for later rendering
    chart_segments: List[ChartSegmentOutput] = []
    
    def notify(step: int, name: str, status: str):
        if on_progress:
            on_progress(step, name, status)
    
    with tqdm(total=6, desc="Script Generation", unit="step") as pbar:
        # Step 1: Introduction
        pbar.set_description("Introduction")
        notify(1, "Introduction", "running")
        intro_output = intro_agent.run(context)
        context.previous_segments.extend(intro_output.to_dicts())
        notify(1, "Introduction", "done")
        pbar.update(1)
        
        # Step 2: Development
        pbar.set_description("Development")
        notify(2, "Development", "running")
        dev_output = dev_agent.run(context)
        context.previous_segments.extend(dev_output.to_dicts())
        notify(2, "Development", "done")
        pbar.update(1)
        
        # Step 3: Charts (AI only - no rendering)
        pbar.set_description("Charts (AI)")
        notify(3, "Charts", "running")
        charts_output = charts_agent.run(context)
        
        # Save chart segments for later rendering
        for seg in charts_output.segments:
            if isinstance(seg, ChartSegmentOutput) and seg.chart_data:
                chart_segments.append(seg)
        
        context.previous_segments.extend(charts_output.to_dicts())
        notify(3, "Charts", "done")
        pbar.update(1)
        
        # Step 4: Conclusion
        pbar.set_description("Conclusion")
        notify(4, "Conclusion", "running")
        conclusion_output = conclusion_agent.run(context)
        context.previous_segments.extend(conclusion_output.to_dicts())
        notify(4, "Conclusion", "done")
        pbar.update(1)
        
        # Step 5: Revision
        pbar.set_description("Revision")
        notify(5, "Revision", "running")
        revised_output = revision_agent.run(context)
        revised_segments = revised_output.to_dicts()
        notify(5, "Revision", "done")
        pbar.update(1)
        
        # Step 6: Visual Mapping
        pbar.set_description("Visual Mapping")
        notify(6, "Visual Mapping", "running")
        visual_segments = visual_mapper.run(revised_segments, input_data.topic)
        notify(6, "Visual Mapping", "done")
        pbar.update(1)
    
    # Build YAML spec (without chart video paths yet)
    title = f"{input_data.topic} Explainer"
    output_dir = f"out/{topic_slug}"
    
    spec = build_yaml_spec(
        title=title,
        segments=visual_segments,
        voice_id=voice_id,
        voice_speed=voice_speed,
        music=music,
        output_dir=output_dir,
    )
    
    if output_path:
        save_yaml_spec(spec, output_path)
        print(f"✅ Script saved to: {output_path}")
    
    print(f"📊 Found {len(chart_segments)} chart(s) to render")
    
    return spec, chart_segments


def generate_charts(
    spec: Dict[str, Any],
    chart_segments: List[ChartSegmentOutput],
) -> Dict[str, Any]:
    """
    Render chart animations using Manim and update the spec.
    
    Args:
        spec: The video spec dict (from generate_script_only)
        chart_segments: List of chart segments to render
    
    Returns:
        Updated spec with chart_video paths
    """
    if not chart_segments:
        print("📊 No charts to render")
        return spec
    
    from .config import get_settings
    import glob
    
    settings = get_settings()
    use_blur_bg = settings.chart_blur_background
    
    # Extract topic slug from output_dir
    output_dir = spec.get("output_dir", "out/generated")
    chart_output_dir = Path(output_dir) / "charts"
    chart_output_dir.mkdir(parents=True, exist_ok=True)
    
    charts_agent = ChartsAgent()
    chart_video_paths: List[str] = []
    
    print(f"📊 Rendering {len(chart_segments)} chart animation(s)...")
    
    for i, seg in enumerate(tqdm(chart_segments, desc="Charts", unit="chart")):
        chart_path = chart_output_dir / f"chart_{hash(seg.text) % 100000}.mp4"
        
        if use_blur_bg:
            seg.chart_data.blur_background = True
            stock_videos = glob.glob("tmp/videos/*.mp4")
            bg_video = Path(stock_videos[0]) if stock_videos else None
        else:
            bg_video = None
        
        result = charts_agent.generate_chart(seg.chart_data, chart_path, background_video=bg_video)
        if result:
            chart_video_paths.append(str(result))
            bg_info = " (with blurred bg)" if use_blur_bg and bg_video else ""
            print(f"📊 Generated chart {i+1}: {result.name}{bg_info}")
    
    # Update spec segments with chart video paths
    chart_idx = 0
    for segment in spec.get("segments", []):
        # Check if this segment is a chart placeholder
        if segment.get("chart_video") is None and chart_idx < len(chart_video_paths):
            # Simple heuristic: if segment has chart data markers
            if any(kw in segment.get("text", "").lower() for kw in ["percent", "%", "billion", "million", "grew", "growth"]):
                segment["chart_video"] = chart_video_paths[chart_idx]
                chart_idx += 1
    
    # Also try matching by is_chart_placeholder if present
    chart_idx = 0
    for segment in spec.get("segments", []):
        if segment.get("is_chart_placeholder") and chart_idx < len(chart_video_paths):
            segment["chart_video"] = chart_video_paths[chart_idx]
            chart_idx += 1
    
    return spec


def generate_script(
    input_data: InputData,
    output_path: Optional[Path] = None,
    voice_id: str = "en-US-Studio-O",
    voice_speed: str = "fast",
    music: str = "inspirational",
    skip_charts: bool = False,
) -> Dict[str, Any]:
    """
    Generate a complete video script using the agentic pipeline.
    
    This is the legacy all-in-one function that runs both script
    generation and chart rendering. For more control, use:
    - generate_script_only() for just the script
    - generate_charts() to render charts separately
    
    Args:
        input_data: Input data with topic, facts, news, etc.
        output_path: Optional path to save YAML file
        voice_id: Google TTS voice ID
        voice_speed: slow/medium/fast
        music: Background music mood
        skip_charts: If True, skip chart rendering (just AI script)
    
    Returns:
        VideoSpec dictionary
    """
    # Generate script (AI only)
    spec, chart_segments = generate_script_only(
        input_data=input_data,
        output_path=None,  # Save after charts
        voice_id=voice_id,
        voice_speed=voice_speed,
        music=music,
    )
    
    # Render charts unless skipped
    if not skip_charts and chart_segments:
        spec = generate_charts(spec, chart_segments)
    
    # Save final spec
    if output_path:
        save_yaml_spec(spec, output_path)
        print(f"✅ Script saved to: {output_path}")
    
    return spec


def generate_and_create_video(
    input_data: InputData,
    yaml_path: Optional[Path] = None,
    force_refresh: bool = False,
    burn_subtitles: bool = True,
) -> Path:
    """
    Generate script and create video in one step.
    
    Args:
        input_data: Input data with topic, facts, news
        yaml_path: Optional path to save intermediate YAML
        force_refresh: Force re-download of video assets
    
    Returns:
        Path to the generated video
    """
    from .video_spec import create_video
    
    # Generate the script
    voice_id = input_data.voice_id or "en-US-Studio-O"
    spec = generate_script(
        input_data,
        output_path=yaml_path,
        voice_id=voice_id,
        voice_speed=input_data.voice_speed,
    )
    
    # Create the video
    return create_video(spec, force_refresh=force_refresh, burn_subtitles=burn_subtitles)

