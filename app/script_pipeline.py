"""
Script Pipeline - Orchestrates all agents to generate a complete video script.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

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


def generate_script(
    input_data: InputData,
    output_path: Optional[Path] = None,
    voice_id: str = "en-US-Studio-O",
    voice_speed: str = "fast",
    music: str = "inspirational",
) -> Dict[str, Any]:
    """
    Generate a complete video script using the agentic pipeline.
    
    Args:
        input_data: Input data with topic, facts, news, etc.
        output_path: Optional path to save YAML file
        voice_id: Google TTS voice ID
        voice_speed: slow/medium/fast
        music: Background music mood
    
    Returns:
        VideoSpec dictionary
    """
    # Initialize context
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
    
    # Build topic slug early (needed for chart output dir)
    topic_slug = input_data.topic.lower().replace(" ", "_").replace(".", "")[:30]
    
    print(f"🎬 Generating script for: {input_data.topic}")
    print(f"📊 Target duration: {total_target}s")
    
    with tqdm(total=6, desc="Pipeline", unit="step") as pbar:
        # Step 1: Introduction
        pbar.set_description("Introduction")
        intro_output = intro_agent.run(context)
        context.previous_segments.extend(intro_output.to_dicts())
        pbar.update(1)
        
        # Step 2: Development
        pbar.set_description("Development")
        dev_output = dev_agent.run(context)
        context.previous_segments.extend(dev_output.to_dicts())
        pbar.update(1)
        
        # Step 3: Charts (includes chart video generation)
        pbar.set_description("Charts")
        charts_output = charts_agent.run(context)
        
        # Generate chart videos for segments with chart_data
        chart_video_paths: List[str] = []  # List of chart video paths (in order)
        chart_output_dir = Path(f"out/{topic_slug}/charts")
        chart_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if blur background is enabled
        from .config import get_settings
        settings = get_settings()
        use_blur_bg = settings.chart_blur_background
        
        for seg in charts_output.segments:
            if isinstance(seg, ChartSegmentOutput) and seg.chart_data:
                chart_path = chart_output_dir / f"chart_{hash(seg.text) % 100000}.mp4"
                
                # Enable blur background in chart data if setting is on
                if use_blur_bg:
                    seg.chart_data.blur_background = True
                    
                    # Try to find a stock video for background
                    import glob
                    stock_videos = glob.glob("tmp/videos/*.mp4")
                    bg_video = Path(stock_videos[0]) if stock_videos else None
                else:
                    bg_video = None
                
                result = charts_agent.generate_chart(seg.chart_data, chart_path, background_video=bg_video)
                if result:
                    chart_video_paths.append(str(result))
                    bg_info = " (with blurred bg)" if use_blur_bg and bg_video else ""
                    print(f"📊 Generated chart: {result.name}{bg_info}")
        
        context.previous_segments.extend(charts_output.to_dicts())
        pbar.update(1)
        
        # Step 4: Conclusion
        pbar.set_description("Conclusion")
        conclusion_output = conclusion_agent.run(context)
        context.previous_segments.extend(conclusion_output.to_dicts())
        pbar.update(1)
        
        # Step 5: Revision
        pbar.set_description("Revision")
        revised_output = revision_agent.run(context)
        revised_segments = revised_output.to_dicts()
        pbar.update(1)
        
        # Step 6: Visual Mapping
        pbar.set_description("Visual Mapping")
        visual_segments = visual_mapper.run(revised_segments, input_data.topic)
        
        # Attach chart video paths to segments marked as chart placeholders
        chart_idx = 0
        for seg in visual_segments:
            if seg.is_chart_placeholder and chart_idx < len(chart_video_paths):
                seg.chart_video_path = chart_video_paths[chart_idx]
                chart_idx += 1
        
        pbar.update(1)
    
    # Build title
    title = f"{input_data.topic} Explainer"
    
    # Output directory (topic_slug already defined above)
    output_dir = f"out/{topic_slug}"
    
    # Build YAML spec
    spec = build_yaml_spec(
        title=title,
        segments=visual_segments,
        voice_id=voice_id,
        voice_speed=voice_speed,
        music=music,
        output_dir=output_dir,
    )
    
    # Save if path provided
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

