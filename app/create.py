#!/usr/bin/env python3
"""
Simple CLI for creating videos from YAML specifications.

Usage:
    python -m app.create videos/my_video.yaml
    python -m app.create videos/my_video.yaml --output out/custom
    python -m app.create videos/my_video.yaml --refresh
"""
import sys
from pathlib import Path

import typer

from .video_spec import create_video


app = typer.Typer(help="Create videos from YAML specifications")


@app.command()
def main(
    spec_file: str = typer.Argument(..., help="Path to YAML specification file"),
    output: str = typer.Option(None, "--output", "-o", help="Override output directory"),
    refresh: bool = typer.Option(False, "--refresh", "-r", help="Force re-download videos"),
    burn_subtitles: bool = typer.Option(True, "--burn-subtitles/--no-burn-subtitles", help="Whether to burn subtitles into the output video"),
):
    """Create a video from a YAML specification file."""
    spec_path = Path(spec_file)
    
    if not spec_path.exists():
        typer.echo(f"Error: File not found: {spec_path}", err=True)
        raise typer.Exit(1)
    
    try:
        # Load and optionally override output
        if output:
            import yaml
            with open(spec_path) as f:
                data = yaml.safe_load(f)
            data["output_dir"] = output
            result = create_video(data, force_refresh=refresh, burn_subtitles=burn_subtitles)
        else:
            result = create_video(spec_path, force_refresh=refresh, burn_subtitles=burn_subtitles)
        
        typer.echo(f"\n✓ Video created: {result}")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

