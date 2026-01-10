import subprocess
from pathlib import Path
from app.models import Script, Segment, VisualAsset, TTSResult
from app.subtitles import write_srt
from app.arranger import build_render_plan
from app.renderer import render


def test_render_with_subtitles_and_audio(tmp_path: Path):
    out_dir = tmp_path
    segments = [
        Segment(id=1, start_ms=0, end_ms=2000, narration='Test audio presence', emotion='neutral', visual_tags=['test'])
    ]
    script = Script(title='Test', target_seconds=2, segments=segments, disclaimer='')
    visuals = {1: [VisualAsset(segment_id=1, source_url='local', file_path=str(Path('tmp/test_video.mp4')), width=720, height=1280, duration_ms=2000)]}
    tts = {1: TTSResult(segment_id=1, audio_path=str(Path('tmp/test_audio.mp3')), duration_ms=2000)}

    srt_file = out_dir / 'subtitles.srt'
    write_srt(script, tts, srt_file)
    plan = build_render_plan(script, visuals, tts, out_dir / 'video.mp4')
    plan.srt_path = str(srt_file)

    out_path = render(plan)

    # Run ffprobe to check for audio stream
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', str(out_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    streams = res.stdout.strip().splitlines()
    assert 'audio' in streams, f'No audio stream found in {out_path}'
