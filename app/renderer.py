from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

from .models import RenderPlan, RenderSegment


def _split_res(resolution: str) -> tuple[int, int]:
    w, h = resolution.lower().split("x")
    return int(w), int(h)


def _get_duration(file_path: str) -> float:
    """Get duration of media file in seconds using ffprobe."""
    if not file_path:
        raise ValueError("Empty file path provided to _get_duration")
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def _group_segments_by_id(segments: List[RenderSegment]) -> Dict[int, List[RenderSegment]]:
    """Group RenderSegments by segment_id, preserving clip order."""
    grouped = defaultdict(list)
    for seg in segments:
        grouped[seg.segment_id].append(seg)
    for seg_id in grouped:
        grouped[seg_id].sort(key=lambda s: s.clip_index)
    return dict(grouped)


def render(plan: RenderPlan) -> Path:
    out_path = Path(plan.output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    target_w, target_h = _split_res(plan.resolution)
    
    if len(plan.segments) == 0:
        raise ValueError("No segments to render")
    
    grouped = _group_segments_by_id(plan.segments)
    segment_ids = sorted(grouped.keys())
    
    inputs = []
    filter_parts = []
    input_idx = 0
    segment_outputs = []

    for seg_id in segment_ids:
        clips = grouped[seg_id]
        
        audio_path = clips[0].audio_path
        if not audio_path:
            for c in clips:
                if c.audio_path:
                    audio_path = c.audio_path
                    break
        
        if not audio_path:
            print(f"Warning: No audio for segment {seg_id}, skipping")
            continue
        
        audio_dur = _get_duration(audio_path)
        num_clips = len(clips)
        
        if num_clips == 1:
            # Single-clip segment
            clip = clips[0]
            video_dur = _get_duration(clip.video_path)
            seg_dur = audio_dur
            
            v_input_idx = input_idx
            a_input_idx = input_idx + 1
            
            v_filters = [
                f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase",
                f"crop={target_w}:{target_h}",
                "setsar=1",
                f"fps={plan.fps}",
            ]
            
            if video_dur < seg_dur:
                loop_count = int(seg_dur / video_dur) + 1
                v_filters.insert(0, f"loop=loop={loop_count}:size=1:start=0")
            
            v_filters.extend([
                f"trim=start=0:end={seg_dur}",
                "setpts=PTS-STARTPTS",
            ])
            
            is_first_segment = (seg_id == segment_ids[0])
            is_last_segment = (seg_id == segment_ids[-1])
            fade_s = clip.fade_frames / float(plan.fps) if clip.fade_frames > 0 else 0
            
            if fade_s > 0:
                if is_first_segment:
                    v_filters.append(f"fade=t=in:st=0:d={fade_s}")
                if is_last_segment:
                    v_filters.append(f"fade=t=out:st={max(0, seg_dur - fade_s)}:d={fade_s}")
            
            a_filters = ["asetpts=PTS-STARTPTS"]
            
            v_label = f"v_seg{seg_id}"
            a_label = f"a_seg{seg_id}"
            
            filter_parts.append(f"[{v_input_idx}:v]{','.join(v_filters)}[{v_label}]")
            filter_parts.append(f"[{a_input_idx}:a]{','.join(a_filters)}[{a_label}]")
            
            inputs.extend(["-i", clip.video_path, "-i", audio_path])
            input_idx += 2
            segment_outputs.append((v_label, a_label))
            
        else:
            # Multi-clip segment
            clip_durations = []
            for clip in clips:
                if clip.clip_duration_ms:
                    clip_durations.append(clip.clip_duration_ms / 1000.0)
                else:
                    clip_durations.append(audio_dur / num_clips)
            
            total_clip_dur = sum(clip_durations)
            if total_clip_dur > 0:
                scale = audio_dur / total_clip_dur
                clip_durations = [d * scale for d in clip_durations]
            
            clip_v_labels = []
            
            a_input_idx = input_idx
            inputs.extend(["-i", audio_path])
            input_idx += 1
            
            for clip_idx, clip in enumerate(clips):
                video_dur = _get_duration(clip.video_path)
                clip_dur = clip_durations[clip_idx]
                
                v_input_idx = input_idx
                inputs.extend(["-i", clip.video_path])
                input_idx += 1
                
                v_filters = [
                    f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase",
                    f"crop={target_w}:{target_h}",
                    "setsar=1",
                    f"fps={plan.fps}",
                ]
                
                if video_dur < clip_dur:
                    loop_count = int(clip_dur / video_dur) + 1
                    v_filters.insert(0, f"loop=loop={loop_count}:size=1:start=0")
                
                v_filters.extend([
                    f"trim=start=0:end={clip_dur}",
                    "setpts=PTS-STARTPTS",
                ])
                
                clip_label = f"v_seg{seg_id}_clip{clip_idx}"
                filter_parts.append(f"[{v_input_idx}:v]{','.join(v_filters)}[{clip_label}]")
                clip_v_labels.append(clip_label)
            
            concat_clips = "".join([f"[{l}]" for l in clip_v_labels])
            combined_v_label = f"v_seg{seg_id}"
            filter_parts.append(f"{concat_clips}concat=n={num_clips}:v=1:a=0[{combined_v_label}_pre]")
            
            is_first_segment = (seg_id == segment_ids[0])
            is_last_segment = (seg_id == segment_ids[-1])
            fade_s = clips[0].fade_frames / float(plan.fps) if clips[0].fade_frames > 0 else 0
            
            fade_filters = []
            if fade_s > 0:
                if is_first_segment:
                    fade_filters.append(f"fade=t=in:st=0:d={fade_s}")
                if is_last_segment:
                    fade_filters.append(f"fade=t=out:st={max(0, audio_dur - fade_s)}:d={fade_s}")
            
            if fade_filters:
                filter_parts.append(f"[{combined_v_label}_pre]{','.join(fade_filters)}[{combined_v_label}]")
            else:
                filter_parts.append(f"[{combined_v_label}_pre]null[{combined_v_label}]")
            
            a_label = f"a_seg{seg_id}"
            filter_parts.append(f"[{a_input_idx}:a]asetpts=PTS-STARTPTS[{a_label}]")
            
            segment_outputs.append((combined_v_label, a_label))

    # Concat all segments
    n_segments = len(segment_outputs)
    concat_inputs = "".join([f"[{v}][{a}]" for v, a in segment_outputs])
    filter_parts.append(f"{concat_inputs}concat=n={n_segments}:v=1:a=1[vout][a_voice]")

    # Background Music
    if plan.bgm_path:
        inputs.extend(["-i", plan.bgm_path])
        bgm_stream_idx = input_idx

        total_dur = 0
        for seg_id in segment_ids:
            clips = grouped[seg_id]
            audio_path = clips[0].audio_path or next((c.audio_path for c in clips if c.audio_path), None)
            if audio_path:
                total_dur += _get_duration(audio_path)
        
        filter_parts.append(f"[{bgm_stream_idx}:a]aloop=loop=-1:size=2e9[bgm_looped]")
        filter_parts.append(f"[bgm_looped]atrim=0:{total_dur},asetpts=PTS-STARTPTS,volume=0.15[bgm_ready]")
        filter_parts.append(f"[a_voice][bgm_ready]amix=inputs=2:duration=first:weights=1 0.7[aout]")
    else:
        filter_parts.append(f"[a_voice]anull[aout]")
    
    filter_complex = ";".join(filter_parts)
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-r", str(plan.fps),
        "-movflags", "+faststart",
        str(out_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
    return out_path
