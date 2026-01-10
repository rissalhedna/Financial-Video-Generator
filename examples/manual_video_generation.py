#!/usr/bin/env python3
"""
Example: Create video using the new YAML/dict approach vs manual Python.

Demonstrates both the simple new approach and the lower-level API.
"""

import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def example_yaml_approach():
    """Simplest approach: Create video from YAML spec."""
    from app.video_spec import create_video
    
    # Just point to a YAML file (subtitles will be burned-in by default)
    video_path = create_video("videos/apple_story.yaml", burn_subtitles=True)
    print(f"Created: {video_path}")


def example_dict_approach():
    """Create video from a Python dictionary."""
    from app.video_spec import create_video
    
    spec = {
        "title": "Quick Tech Video",
        "voice_speed": "fast",
        "output_dir": "out/quick_video",
        "segments": [
            {
                "text": "Welcome to this quick overview of modern technology.",
                "emotion": "excited",
                "visuals": ["technology", "innovation"]
            },
            {
                "text": "Smartphones have revolutionized how we communicate.",
                "emotion": "informative",
                "visuals": ["smartphone", "communication"]
            },
            {
                "text": "And cloud computing has transformed how businesses operate.",
                "emotion": "serious",
                "clips": [
                    {"tags": ["cloud computing servers"], "duration_pct": 50},
                    {"tags": ["business office meeting"], "duration_pct": 50},
                ]
            },
            {
                "text": "The future is being built today.",
                "emotion": "impactful",
                "visuals": ["future", "technology"]
            },
        ]
    }
    
    video_path = create_video(spec, burn_subtitles=True)
    print(f"Created: {video_path}")


def example_low_level_api():
    """Lower-level approach using Script and Segment models directly."""
    from pathlib import Path
    from app.models import Script, Segment, VisualClip
    from app.config import get_settings
    from app.footage_search import fetch_visuals_for_script, search_music, download_music
    from app.arranger import build_render_plan
    from app.renderer import render
    from app.tts import synthesize_segments
    from app.subtitles import write_srt
    
    # Create script manually
    segments = [
        Segment(
            id=1, start_ms=0, end_ms=5000,
            narration="This is segment one with manual timing.",
            emotion="neutral",
            visual_tags=["technology", "business"]
        ),
        Segment(
            id=2, start_ms=5000, end_ms=10000,
            narration="This is segment two with multiple clips.",
            emotion="excited",
            visual_clips=[
                VisualClip(tags=["innovation"], duration_pct=50),
                VisualClip(tags=["future"], duration_pct=50),
            ]
        ),
    ]
    
    script = Script(
        title="Low-Level API Example",
        target_seconds=10,
        segments=segments,
        disclaimer="Example video"
    )
    
    # Setup paths
    settings = get_settings()
    output_dir = Path("out/low_level_example")
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(settings.tmp_dir)
    
    # Run pipeline steps manually
    visuals = fetch_visuals_for_script(script, tmp_dir / "videos")
    tts = synthesize_segments(script, tmp_dir / "audio", voice_speed="fast")
    
    # Optional: background music
    tracks = search_music("inspirational")
    bgm_path = None
    if tracks:
        bgm_path = str(download_music(tracks[0]["url"], tmp_dir / "audio" / "bgm.mp3"))
    
# Write subtitles (so they can be burned into the video)
    out_path = output_dir / "video.mp4"
    srt_file = output_dir / "subtitles.srt"
    write_srt(script, tts, srt_file)

    plan = build_render_plan(script, visuals, tts, out_path)
    if bgm_path:
        plan.bgm_path = bgm_path
    if srt_file.exists():
        plan.srt_path = str(srt_file)

    result = render(plan)
    
    print(f"Created: {result}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Video generation examples")
    parser.add_argument(
        "--approach", 
        choices=["yaml", "dict", "low-level"],
        default="dict",
        help="Which approach to demonstrate"
    )
    
    args = parser.parse_args()
    
    if args.approach == "yaml":
        example_yaml_approach()
    elif args.approach == "dict":
        example_dict_approach()
    else:
        example_low_level_api()
