"""Audio processing utilities."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def get_audio_duration(path: Path) -> float:
    """Get audio duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    return 0.0


def normalize_audio(input_path: Path, output_path: Path, target_loudness: float = -16.0) -> Path:
    """
    Normalize audio to target loudness using EBU R128 standard.
    
    Args:
        input_path: Input audio file
        output_path: Output audio file
        target_loudness: Target integrated loudness in LUFS (default -16 for speech)
    
    Returns:
        Path to normalized audio file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Two-pass loudness normalization
    # Pass 1: Measure loudness
    measure_cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-af", f"loudnorm=I={target_loudness}:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-"
    ]
    result = subprocess.run(measure_cmd, capture_output=True, text=True)
    
    # Parse measured values from stderr (ffmpeg outputs to stderr)
    stderr = result.stderr
    
    # Try to find the JSON output
    try:
        # Find the JSON block in stderr
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = stderr[json_start:json_end]
            measured = json.loads(json_str)
            
            # Pass 2: Apply normalization with measured values
            input_i = measured.get("input_i", "-24.0")
            input_tp = measured.get("input_tp", "-2.0")
            input_lra = measured.get("input_lra", "7.0")
            input_thresh = measured.get("input_thresh", "-34.0")
            
            normalize_cmd = [
                "ffmpeg", "-y", "-i", str(input_path),
                "-af", (
                    f"loudnorm=I={target_loudness}:TP=-1.5:LRA=11:"
                    f"measured_I={input_i}:measured_TP={input_tp}:"
                    f"measured_LRA={input_lra}:measured_thresh={input_thresh}:"
                    "linear=true"
                ),
                "-ar", "44100",
                str(output_path)
            ]
            subprocess.run(normalize_cmd, capture_output=True, check=True)
            return output_path
    except (json.JSONDecodeError, subprocess.CalledProcessError):
        pass
    
    # Fallback: simple single-pass normalization
    simple_cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-af", f"loudnorm=I={target_loudness}:TP=-1.5:LRA=11",
        "-ar", "44100",
        str(output_path)
    ]
    subprocess.run(simple_cmd, capture_output=True)
    return output_path


def trim_silence(input_path: Path, output_path: Path, threshold_db: float = -40.0) -> Path:
    """
    Trim silence from start and end of audio.
    
    Args:
        input_path: Input audio file
        output_path: Output audio file  
        threshold_db: Silence threshold in dB
    
    Returns:
        Path to trimmed audio file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-af", (
            f"silenceremove=start_periods=1:start_duration=0.1:start_threshold={threshold_db}dB:"
            f"stop_periods=1:stop_duration=0.1:stop_threshold={threshold_db}dB"
        ),
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path


def add_compression(input_path: Path, output_path: Path) -> Path:
    """
    Add gentle compression to even out dynamics.
    
    Useful for making speech more consistent in volume.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-af", (
            # Gentle compression: 3:1 ratio, -20dB threshold
            "acompressor=threshold=-20dB:ratio=3:attack=5:release=100:makeup=2dB"
        ),
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True)
    return output_path
