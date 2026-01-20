from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from .config import get_settings
from .pipeline import run_pipeline

app = None  # switched to single-command interface


def main(
    input: str = typer.Option(..., "--input", "-i", help="Path to input JSON"),
    out: str = typer.Option(..., "--out", "-o", help="Output directory"),
    seconds: Optional[int] = typer.Option(None, "--seconds", "-s", help="Override target duration seconds"),
    style: Optional[str] = typer.Option(None, "--style", help="Video style: social-media (short, 45s) or documentary (long, 5+ min)"),
    mood: Optional[str] = typer.Option(None, "--mood", "-m", help="Script mood (e.g., excited, serious)"),
    voice: Optional[str] = typer.Option(None, "--voice", "-v", help="Google Voice Name (e.g. en-US-Neural2-J)"),
    ai_speech: Optional[bool] = typer.Option(None, "--ai-speech", help="Enable AI-driven speech control (emphasis, pauses). Default: from .env USE_AI_SPEECH_CONTROL"),
    burn_subtitles: bool = typer.Option(True, "--burn-subtitles/--no-burn-subtitles", help="Whether to burn subtitles into the output video"),
) -> None:
    """
    Run the AI Financial Video pipeline end-to-end.
    
    Speech Control Modes:
    - AI-driven (--ai-speech): GPT suggests which words to emphasize and pause durations
    - Rule-based (default): Automatic SSML with emotion-based prosody and keyword emphasis
    """
    try:
        # Validate config
        settings = get_settings()
        settings.ensure_valid()
        
        input_path = Path(input)
        if not input_path.exists():
            typer.echo(f"Error: Input file not found: {input_path}", err=True)
            sys.exit(1)
        
        out_dir = Path(out)
        out_path = run_pipeline(
            input_path, 
            out_dir, 
            override_seconds=seconds, 
            video_style=style,
            mood=mood, 
            voice_id=voice,
            use_ai_speech_control=ai_speech,
            burn_subtitles=burn_subtitles,
        )
        typer.echo(f"✓ Done: {out_path}")
    except Exception as e:
        typer.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    typer.run(main)
