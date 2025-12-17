from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .models import RenderPlan, RenderSegment, Script, TTSResult, VisualAsset, VisualClip
from .config import get_settings


def _calculate_trigger_timings(
    narration: str,
    clips: List[VisualClip],
    total_duration_ms: int
) -> List[int]:
    """
    Calculate clip durations based on trigger word positions.
    
    Uses character position as a proxy for speech timing (works well since
    speech rate is fairly constant within a segment).
    
    Returns list of durations in ms for each clip.
    """
    num_clips = len(clips)
    text_len = len(narration)
    
    if text_len == 0 or num_clips == 0:
        return [total_duration_ms] if num_clips == 1 else []
    
    # Find trigger positions (character index where each clip should start)
    trigger_positions = []
    for clip in clips:
        if clip.trigger:
            # Case-insensitive search
            pos = narration.lower().find(clip.trigger.lower())
            if pos >= 0:
                trigger_positions.append(pos)
            else:
                # Trigger not found, use None (will fall back to even split)
                trigger_positions.append(None)
        else:
            trigger_positions.append(None)
    
    # If no triggers specified or found, fall back to duration_pct or even split
    if all(p is None for p in trigger_positions):
        durations = []
        for i, clip in enumerate(clips):
            if clip.duration_pct:
                durations.append(int(total_duration_ms * clip.duration_pct / 100))
            else:
                durations.append(total_duration_ms // num_clips)
        # Adjust last clip to account for rounding
        if durations:
            durations[-1] = total_duration_ms - sum(durations[:-1])
        return durations
    
    # Calculate switch points based on trigger positions
    # First clip starts at 0, subsequent clips start at their trigger position
    switch_points_pct = [0.0]  # First clip always starts at 0%
    
    for i in range(1, num_clips):
        if trigger_positions[i] is not None:
            # Convert character position to percentage
            switch_points_pct.append(trigger_positions[i] / text_len)
        else:
            # No trigger, estimate based on previous clip
            # Use even spacing from last known point
            prev_pct = switch_points_pct[-1]
            remaining_clips = num_clips - i
            switch_points_pct.append(prev_pct + (1.0 - prev_pct) / (remaining_clips + 1))
    
    # Add end point
    switch_points_pct.append(1.0)
    
    # Convert to durations
    durations = []
    for i in range(num_clips):
        start_pct = switch_points_pct[i]
        end_pct = switch_points_pct[i + 1]
        duration = int(total_duration_ms * (end_pct - start_pct))
        durations.append(max(duration, 100))  # Minimum 100ms per clip
    
    # Ensure total adds up
    total = sum(durations)
    if total != total_duration_ms:
        durations[-1] += (total_duration_ms - total)
    
    return durations


def build_render_plan(
    script: Script,
    visuals: Dict[int, List[VisualAsset]],
    tts: Dict[int, TTSResult],
    output_path: Path,
) -> RenderPlan:
    """Build render plan from script, visuals (list per segment), and TTS results."""
    settings = get_settings()
    segments: List[RenderSegment] = []
    missing_segments = []
    
    current_ms = 0
    
    for seg in script.segments:
        va_list = visuals.get(seg.id)
        ta = tts.get(seg.id)
        if not va_list or not ta:
            missing_segments.append(seg.id)
            continue
        
        actual_duration_ms = ta.duration_ms
        start_ms = current_ms
        end_ms = current_ms + actual_duration_ms
        
        num_clips = len(va_list)
        
        # Calculate clip durations using trigger-based timing if available
        if seg.visual_clips and any(c.trigger for c in seg.visual_clips):
            clip_durations = _calculate_trigger_timings(
                seg.narration, seg.visual_clips, actual_duration_ms
            )
        else:
            # Fall back to even split or duration_pct
            clip_durations = []
            for i, va in enumerate(va_list):
                if seg.visual_clips and i < len(seg.visual_clips):
                    pct = seg.visual_clips[i].duration_pct
                    clip_durations.append(int(actual_duration_ms * pct / 100))
                else:
                    clip_durations.append(actual_duration_ms // num_clips)
            if clip_durations:
                clip_durations[-1] = actual_duration_ms - sum(clip_durations[:-1])
        
        for clip_idx, va in enumerate(va_list):
            clip_duration = clip_durations[clip_idx] if clip_idx < len(clip_durations) else actual_duration_ms
            
            segments.append(
                RenderSegment(
                    segment_id=seg.id,
                    video_path=va.file_path,
                    audio_path=ta.audio_path if clip_idx == 0 else "",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    scale_to=settings.resolution,
                    center_crop=True,
                    fade_frames=3 if num_clips > 1 else 5,
                    clip_index=clip_idx,
                    total_clips=num_clips,
                    clip_duration_ms=clip_duration,
                )
            )
        
        current_ms = end_ms
    
    if not segments:
        raise ValueError("No segments available for rendering. All segments are missing assets.")
    
    if missing_segments:
        print(f"Warning: Skipping segments {missing_segments} due to missing assets")
    
    total_ms = current_ms
    
    return RenderPlan(
        resolution=settings.resolution,
        fps=settings.fps,
        total_ms=total_ms,
        segments=segments,
        output_path=str(output_path),
    )
