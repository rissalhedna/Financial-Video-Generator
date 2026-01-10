from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .models import Script, TTSResult


def _format_ts(ms: int) -> str:
    h = ms // 3_600_000
    m = (ms % 3_600_000) // 60_000
    s = (ms % 60_000) // 1000
    ms_rem = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms_rem:03d}"


def write_srt(script: Script, tts: Dict[int, TTSResult], out_path: Path) -> Path:
    """Write SRT using actual TTS timings when available.

    If a TTS result exists for a segment, use the TTS durations to
    compute start/end timestamps (cumulative). This keeps burned-in
    subtitles synced to the produced audio, avoiding visible delays.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []

    # Use cumulative TTS durations when possible to align timing to audio output
    current_ms = 0
    for idx, seg in enumerate(script.segments, start=1):
        narr = seg.narration.strip()
        if not narr:
            continue

        tts_result = tts.get(seg.id)
        if tts_result:
            start = current_ms
            end = current_ms + int(tts_result.duration_ms)
            current_ms = end
        else:
            # Fall back to script timings
            start = seg.start_ms
            end = seg.end_ms

        lines.append(str(idx))
        lines.append(f"{_format_ts(start)} --> {_format_ts(end)}")
        lines.append(narr)
        lines.append("")  # blank

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


