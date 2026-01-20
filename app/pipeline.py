from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from .arranger import build_render_plan
from .config import get_settings
from .footage_search import plan_and_fetch_visuals, search_music, download_music
from .models import InputData
from .renderer import render
from .script_generator import generate_script
from .subtitles import write_srt
from .tts import synthesize_segments


def run_pipeline(
    input_json_path: Path,
    output_dir: Path,
    override_seconds: Optional[int] = None,
    video_style: Optional[str] = None,
    mood: Optional[str] = None,
    voice_id: Optional[str] = None,
    use_ai_speech_control: Optional[bool] = None,
    burn_subtitles: bool = True,
) -> Path:
    settings = get_settings()
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(settings.tmp_dir)
    (tmp_dir / "videos").mkdir(parents=True, exist_ok=True)
    (tmp_dir / "audio").mkdir(parents=True, exist_ok=True)
    
    # Use provided value or fall back to config
    ai_speech = use_ai_speech_control if use_ai_speech_control is not None else settings.use_ai_speech_control

    # Ingest
    data = json.loads(Path(input_json_path).read_text(encoding="utf-8"))
    input_data = InputData.model_validate(data)
    if override_seconds:
        input_data.target_seconds = override_seconds
    if video_style:
        input_data.video_style = video_style
    if mood:
        input_data.mood = mood

    # Prefer CLI voice arg, then input JSON voice, then default
    actual_voice_id = voice_id or input_data.voice_id

    with tqdm(total=5, desc="Pipeline", unit="step") as pbar:
        # Script
        pbar.set_description("Generating script")
        script = generate_script(input_data, use_ai_speech_control=ai_speech)
        pbar.update(1)

        # Visuals
        pbar.set_description("Fetching footage")
        visuals = plan_and_fetch_visuals(script, tmp_dir / "videos", force_refresh=input_data.force_cache_refresh)
        
        # Background Music
        bgm_path = None
        try:
            music_query = input_data.mood or "inspirational"
            bgm_tracks = search_music(music_query, limit=1)
            if bgm_tracks:
                bgm_url = bgm_tracks[0]["url"]
                bgm_dest = tmp_dir / "audio" / f"bgm_{music_query}.mp3"
                bgm_path = str(download_music(bgm_url, bgm_dest))
        except Exception as e:
            print(f"Warning: Failed to fetch background music: {e}")
        
        pbar.update(1)

        # TTS
        pbar.set_description("Synthesizing audio")
        tts = synthesize_segments(
            script, 
            tmp_dir / "audio", 
            voice_id=actual_voice_id, 
            use_ai_speech_control=ai_speech,
            voice_speed=input_data.voice_speed
        )
        pbar.update(1)

        # Subtitles (SRT)
        pbar.set_description("Writing subtitles")
        srt_file = output_dir / "subtitles.srt"
        write_srt(script, tts, srt_file)
        pbar.update(1)

        # Arrange & Render
        pbar.set_description("Rendering video")
        out_path = output_dir / "video.mp4"
        plan = build_render_plan(script, visuals, tts, out_path)
        if bgm_path:
            plan.bgm_path = bgm_path
        # Attach subtitles path so renderer can burn them in (if requested)
        if burn_subtitles and srt_file.exists():
            plan.srt_path = str(srt_file)
            
        result_path = render(plan)
        pbar.update(1)

    # Manifest
    manifest = {
        "title": script.title,
        "target_seconds": script.target_seconds,
        "disclaimer": script.disclaimer,
        "segments": [s.model_dump() for s in script.segments],
        "output": str(result_path),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return result_path


