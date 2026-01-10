#!/usr/bin/env python3
"""
CLI for generating video scripts using the agentic pipeline.

Usage:
    # Generate YAML script only
    python -m app.generate input.json --output videos/my_video.yaml
    
    # Generate script and create video
    python -m app.generate input.json --create-video
    
    # Quick generation with topic only
    python -m app.generate --topic "Apple Inc stock" --output videos/apple.yaml
"""
import json
import sys
from pathlib import Path
from typing import Optional

import typer

from .models import InputData
from .script_pipeline import generate_script, generate_and_create_video


app = typer.Typer(help="Generate video scripts using the agentic pipeline")


@app.command()
def main(
    input_file: Optional[str] = typer.Argument(
        None, 
        help="Path to JSON input file with topic, facts, news"
    ),
    topic: Optional[str] = typer.Option(
        None, 
        "--topic", "-t", 
        help="Topic for the video (alternative to input file)"
    ),
    output: Optional[str] = typer.Option(
        None, 
        "--output", "-o", 
        help="Output path for YAML script"
    ),
    create_video: bool = typer.Option(
        False, 
        "--create-video", "-v", 
        help="Also create the video after generating script"
    ),
    burn_subtitles: bool = typer.Option(True, "--burn-subtitles/--no-burn-subtitles", help="Whether to burn subtitles into the output video"),
    duration: int = typer.Option(
        60, 
        "--duration", "-d", 
        help="Target video duration in seconds"
    ),
    refresh: bool = typer.Option(
        False, 
        "--refresh", "-r", 
        help="Force re-download video assets"
    ),
):
    """
    Generate a video script using the agentic pipeline.
    
    Provide either an input JSON file or use --topic for quick generation.
    """
    # Validate input
    if not input_file and not topic:
        typer.echo("Error: Provide either an input file or --topic", err=True)
        raise typer.Exit(1)
    
    # Build InputData
    if input_file:
        input_path = Path(input_file)
        if not input_path.exists():
            typer.echo(f"Error: File not found: {input_path}", err=True)
            raise typer.Exit(1)
        
        data = json.loads(input_path.read_text(encoding="utf-8"))
        input_data = InputData.model_validate(data)
    else:
        # Quick generation with topic only
        input_data = InputData(
            topic=topic,
            facts=[],
            news=[],
            target_seconds=duration,
            mood="informative",
        )
    
    # Determine output path
    if output:
        output_path = Path(output)
    else:
        topic_slug = input_data.topic.lower().replace(" ", "_").replace(".", "")[:30]
        output_path = Path(f"videos/{topic_slug}.yaml")
    
    try:
        if create_video:
            # Generate script and create video
            video_path = generate_and_create_video(
                input_data,
                yaml_path=output_path,
                force_refresh=refresh,
                burn_subtitles=burn_subtitles,
            )
            typer.echo(f"\n✓ Video created: {video_path}")
        else:
            # Generate script only
            spec = generate_script(input_data, output_path=output_path)
            typer.echo(f"\n✓ Script generated: {output_path}")
            typer.echo(f"  Segments: {len(spec['segments'])}")
            
            # Show preview
            typer.echo("\n📝 Preview:")
            for i, seg in enumerate(spec["segments"][:3], 1):
                text = seg["text"][:60] + "..." if len(seg["text"]) > 60 else seg["text"]
                typer.echo(f"  {i}. [{seg.get('emotion', 'neutral')}] {text}")
            if len(spec["segments"]) > 3:
                typer.echo(f"  ... and {len(spec['segments']) - 3} more segments")
            
            typer.echo(f"\nTo create video: python -m app.create {output_path}")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

