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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    for idx, seg in enumerate(script.segments, start=1):
        start = seg.start_ms
        end = seg.end_ms
        narr = seg.narration.strip()
        if not narr:
            continue
        lines.append(str(idx))
        lines.append(f"{_format_ts(start)} --> {_format_ts(end)}")
        lines.append(narr)
        lines.append("")  # blank
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


