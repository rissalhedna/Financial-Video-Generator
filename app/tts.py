from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Dict, List, Any

import httpx
from tqdm import tqdm
from pydub import AudioSegment, silence

from .config import get_settings
from .models import Script, TTSResult
from .voice_presets import get_voice_settings
from .ssml_enhancer import enhance_narration_with_ssml

GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

# High-quality audio configuration
# See: https://cloud.google.com/text-to-speech/docs/reference/rest/v1/AudioConfig
AUDIO_CONFIG = {
    "audioEncoding": "LINEAR16",  # Uncompressed WAV (highest quality)
    "sampleRateHertz": 44100,     # CD quality (48000 also supported)
    "effectsProfileId": [
        "headphone-class-device"   # Optimized for headphones/quality playback
    ],
    # "pitch": 0.0,               # Can adjust globally if needed
    # "speakingRate": 1.0,        # Controlled via SSML instead
}

# Fallback for when LINEAR16 isn't ideal (smaller files)
AUDIO_CONFIG_COMPRESSED = {
    "audioEncoding": "OGG_OPUS",  # Best quality-to-size ratio
    "sampleRateHertz": 48000,
    "effectsProfileId": ["headphone-class-device"],
}


def synthesize_segments(
    script: Script, 
    outdir: Path, 
    voice_id: str | None = None, 
    voice_speed: str = "medium", 
    use_ai_speech_control: bool = False,
    emotion_intensity: float = 1.0
) -> Dict[int, TTSResult]:
    """
    Synthesize TTS for the entire script as a single batch (or large chunks) 
    to maintain natural prosody, then split it back into segments using markers.
    
    Args:
        script: The generated script with segments
        outdir: Output directory for audio files
        voice_id: Optional Google Voice Name
        voice_speed: Speech speed ("slow", "medium", "fast")
        use_ai_speech_control: If True, use AI-provided emphasis and pauses
        emotion_intensity: Scale factor for prosody intensity
    
    Returns:
        Dictionary mapping segment IDs to TTSResult objects
    """
    settings = get_settings()
    default_voice = voice_id or settings.default_voice_name or "en-US-Neural2-J"
    outdir.mkdir(parents=True, exist_ok=True)
    results: Dict[int, TTSResult] = {}

    # Prepare the full SSML with markers
    # We will insert a unique silence/marker between segments to detect split points
    # Google TTS allows <mark name="..."/> but standard MP3 output doesn't always preserve it in metadata easily for simple splitting.
    # A robust way is to insert a specific silence duration, e.g., 750ms, and split by silence.
    # OR better: synthesize ONE big text block? 
    # Note: Google TTS has a character limit (5000 bytes).
    # If script is long, we MUST chunk it.
    # But for short scripts (30-60s), it usually fits.
    
    # Let's build a single SSML string with strict pauses between segments
    # We'll use a specific break time to split: <break time="1000ms"/>
    
    full_ssml_parts = []
    segment_map = [] # To map index back to segment ID

    # Determine voice params once (assuming same voice for whole video for consistency)
    # If emotions change drastically, we might want to change voice params?
    # Usually keeping the same voice "persona" is better for continuity.
    # We'll use the "dominant" emotion or just the first segment's emotion to pick the voice?
    # Or just use the default voice if provided.
    
    # Strategy:
    # 1. Pick a single voice for the whole script to ensure continuity.
    # 2. Use SSML tags to change expression/prosody per segment within that single voice context.
    
    # Pick voice from first segment or default
    first_emotion = script.segments[0].emotion if script.segments else "neutral"
    voice_params = get_voice_settings(first_emotion)
    
    if voice_id:
        voice_params["name"] = voice_id
        voice_params.pop("ssmlGender", None)
    
    if "name" not in voice_params:
        voice_params["name"] = default_voice
        voice_params["languageCode"] = "en-US"

    voice_name = voice_params.get("name", "")
    is_journey_voice = "Journey" in voice_name
    is_studio_voice = "Studio" in voice_name
    
    SPLIT_MARKER_MS = 1000  # 1 second silence to split
    
    for i, seg in enumerate(script.segments):
        text = seg.narration.strip()
        if not text:
            continue
            
        enhanced_part = enhance_narration_with_ssml(
            text, 
            seg.emotion or "neutral",
            use_ai_control=use_ai_speech_control,
            emphasis_words=seg.emphasis_words,
            pause_after_ms=None, # Handle pauses manually in batch
            emotion_intensity=emotion_intensity,
            disable_prosody=is_journey_voice,
            disable_pitch=is_studio_voice,
            base_speed=voice_speed
        )
        
        # Strip outer <speak> if present to merge
        if enhanced_part.startswith("<speak>"):
            enhanced_part = enhanced_part[7:]
        if enhanced_part.endswith("</speak>"):
            enhanced_part = enhanced_part[:-8]
            
        full_ssml_parts.append(enhanced_part)
        # Add a distinct break between segments for splitting
        # BUT don't add it after the last one
        if i < len(script.segments) - 1:
            full_ssml_parts.append(f'<break time="{SPLIT_MARKER_MS}ms"/>')
            
        segment_map.append(seg.id)

    # Combine into one SSML doc
    full_ssml = "<speak>" + "".join(full_ssml_parts) + "</speak>"
    
    # Check length limit (rough check)
    if len(full_ssml) > 5000:
        print("Warning: Script too long for single batch TTS. Falling back to segment-by-segment.")
        return _synthesize_segments_individually(script, outdir, voice_id, voice_speed, use_ai_speech_control, emotion_intensity)

    # Call API once with high-quality audio settings
    url = f"{GOOGLE_TTS_URL}?key={settings.google_api_key}"
    payload = {
        "input": {"ssml": full_ssml},
        "voice": voice_params,
        "audioConfig": AUDIO_CONFIG,
    }
    
    audio_content = None
    with httpx.Client(timeout=60.0) as client:
        try:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "audioContent" in data:
                audio_content = base64.b64decode(data["audioContent"])
        except Exception as e:
            print(f"Batch TTS failed: {e}. Falling back to individual segments.")
            return _synthesize_segments_individually(script, outdir, voice_id, voice_speed, use_ai_speech_control, emotion_intensity)

    if not audio_content:
        return {}

    # Save full audio (LINEAR16 = WAV format)
    full_audio_path = outdir / "full_narration.wav"
    with open(full_audio_path, "wb") as f:
        f.write(audio_content)
        
    # Split audio by silence
    # We used SPLIT_MARKER_MS (1000ms).
    # We need to find silences >= ~800ms (allow some tolerance)
    
    try:
        # Load WAV file (LINEAR16 format from Google)
        full_audio = AudioSegment.from_wav(full_audio_path)
        
        # split_on_silence returns list of AudioSegments
        # min_silence_len should be slightly less than our inserted break
        chunks = silence.split_on_silence(
            full_audio, 
            min_silence_len=SPLIT_MARKER_MS - 200, 
            silence_thresh=-50, # dBFS, adjust if needed
            keep_silence=100 # keep a bit of silence for natural end
        )
        
        # Map chunks back to segments
        # Note: silence splitting might be tricky if there are natural long pauses in text.
        # However, our inserted 1s pause is likely longer than natural pauses (usually <500ms).
        
        if len(chunks) != len(segment_map):
            print(f"Warning: Split {len(chunks)} audio chunks but expected {len(segment_map)}. Using fallback mapping or individual method.")
            # If count mismatch, it's safer to fallback to individual generation to ensure sync
            return _synthesize_segments_individually(script, outdir, voice_id, voice_speed, use_ai_speech_control, emotion_intensity)
            
        for i, chunk in enumerate(chunks):
            seg_id = segment_map[i]
            seg_path = outdir / f"seg{seg_id:02d}.mp3"
            
            # Export as high-quality MP3 (320kbps) for smaller file size while keeping quality
            chunk.export(seg_path, format="mp3", bitrate="320k")
            
            # Find the duration
            duration_ms = len(chunk)
            
            results[seg_id] = TTSResult(
                segment_id=seg_id,
                audio_path=str(seg_path),
                duration_ms=duration_ms,
                words=None,
            )
            
    except Exception as e:
        print(f"Error splitting audio: {e}. Falling back.")
        return _synthesize_segments_individually(script, outdir, voice_id, voice_speed, use_ai_speech_control, emotion_intensity)

    return results


def _synthesize_segments_individually(
    script: Script, 
    outdir: Path, 
    voice_id: str | None, 
    voice_speed: str, 
    use_ai_speech_control: bool,
    emotion_intensity: float
) -> Dict[int, TTSResult]:
    """Fallback to original individual segment synthesis."""
    settings = get_settings()
    default_voice = voice_id or settings.default_voice_name or "en-US-Neural2-J"
    outdir.mkdir(parents=True, exist_ok=True)
    results: Dict[int, TTSResult] = {}
    url = f"{GOOGLE_TTS_URL}?key={settings.google_api_key}"

    with httpx.Client(timeout=60.0) as client:
        for seg in tqdm(script.segments, desc="TTS segments (fallback)", unit="seg", leave=False):
            text = seg.narration.strip()
            if not text:
                continue
            
            voice_params = get_voice_settings(seg.emotion)
            if voice_id:
                voice_params["name"] = voice_id
                voice_params.pop("ssmlGender", None)
            if "name" not in voice_params:
                voice_params["name"] = default_voice
                voice_params["languageCode"] = "en-US"

            voice_name = voice_params.get("name", "")
            is_journey_voice = "Journey" in voice_name
            is_studio_voice = "Studio" in voice_name
            
            enhanced_text = enhance_narration_with_ssml(
                text, 
                seg.emotion or "neutral",
                use_ai_control=use_ai_speech_control,
                emphasis_words=seg.emphasis_words,
                pause_after_ms=seg.pause_after_ms,
                emotion_intensity=emotion_intensity,
                disable_prosody=is_journey_voice,
                disable_pitch=is_studio_voice,
                base_speed=voice_speed
            )
            
            if not enhanced_text.strip().startswith("<speak>"):
                enhanced_text = f"<speak>{enhanced_text}</speak>"

            payload = {
                "input": {"ssml": enhanced_text},
                "voice": voice_params,
                "audioConfig": AUDIO_CONFIG,  # High-quality LINEAR16
            }
            
            audio_content = None
            try:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                if "audioContent" in data:
                    audio_content = base64.b64decode(data["audioContent"])
            except Exception:
                pass
            
            if not audio_content:
                continue

            # Save as WAV first (LINEAR16 format), then convert to high-quality MP3
            raw_path = outdir / f"seg{seg.id:02d}_raw.wav"
            audio_path = outdir / f"seg{seg.id:02d}.mp3"
            
            with open(raw_path, "wb") as f:
                f.write(audio_content)
            
            # Convert WAV to normalized high-quality MP3
            try:
                _normalize_segment_audio(raw_path, audio_path)
                raw_path.unlink()  # Remove raw WAV file
            except Exception:
                # Fallback: convert without normalization
                try:
                    audio = AudioSegment.from_wav(raw_path)
                    audio.export(audio_path, format="mp3", bitrate="320k")
                    raw_path.unlink()
                except Exception:
                    raw_path.rename(audio_path)
            
            # Get ACTUAL duration from audio file, not estimated
            try:
                audio = AudioSegment.from_mp3(audio_path)
                actual_duration_ms = len(audio)
            except Exception:
                actual_duration_ms = seg.duration_ms  # fallback to estimate
            
            results[seg.id] = TTSResult(
                segment_id=seg.id,
                audio_path=str(audio_path),
                duration_ms=actual_duration_ms,
                words=None,
            )
    return results


def _normalize_segment_audio(input_path: Path, output_path: Path) -> None:
    """Normalize a single audio segment for consistent volume.
    
    Converts from any input format (WAV/MP3) to high-quality MP3.
    Uses fast volume normalization instead of slow loudnorm.
    """
    import subprocess
    
    # Fast normalization using dynaudnorm (much faster than loudnorm)
    # dynaudnorm is a single-pass filter that normalizes audio dynamically
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-af", "dynaudnorm=f=150:g=15",  # Fast dynamic normalization
        "-ar", "44100",
        "-c:a", "libmp3lame",
        "-b:a", "256k",  # Good quality, faster encoding
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
