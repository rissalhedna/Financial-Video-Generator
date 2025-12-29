"""
SSML enhancement utilities for natural speech (Google TTS compatible).

Supported tags:
- <break time="Xms"/>
- <prosody rate="..." pitch="...">
- <emphasis level="...">
- <speak>
"""

from typing import Optional, List


def _scale_prosody(val_str: str, intensity: float) -> str:
    """
    Scale prosody value by intensity.
    val_str: "+2st", "-1st", "110%", "90%"
    intensity: 0.0 to 2.0 (1.0 is normal)
    """
    if intensity == 1.0:
        return val_str
    
    if "st" in val_str:
        # Pitch semitones
        try:
            val = float(val_str.replace("st", "").replace("+", ""))
            scaled = val * intensity
            sign = "+" if scaled >= 0 else ""
            return f"{sign}{scaled:.1f}st"
        except ValueError:
            return val_str
            
    if "%" in val_str:
        # Rate percentage
        try:
            val = float(val_str.replace("%", ""))
            # Center around 100%
            # e.g. 110% -> deviation +10% * intensity -> 100 + (10 * int)
            deviation = val - 100.0
            scaled = 100.0 + (deviation * intensity)
            return f"{scaled:.0f}%"
        except ValueError:
            return val_str
            
    return val_str


def _get_emotion_prosody(emotion: str, intensity: float = 1.0, disable_pitch: bool = False, base_speed_mult: float = 1.0) -> tuple[str, str]:
    """Get start and end tags for prosody based on emotion, scaled by intensity and base speed."""
    emotion = emotion.lower().strip()
    
    # Base settings
    rate_pct = 100
    pitch = "0st"
    volume = "default"
    
    # Enhanced prosody map for more dynamic range
    if emotion == "excited":
        rate_pct = 115
        pitch = "+2st"
        volume = "loud"
    elif emotion == "sad":
        rate_pct = 85
        pitch = "-2st"
        volume = "soft"
    elif emotion == "serious":
        rate_pct = 90
        pitch = "-1st"
        volume = "medium"
    elif emotion == "urgent":
        rate_pct = 125
        pitch = "+1st"
        volume = "loud"
    elif emotion == "dramatic":
        rate_pct = 85
        pitch = "-1.5st"
        volume = "loud"  # Dramatic needs power even if slow
    elif emotion == "curious":
        rate_pct = 105
        pitch = "+1st"
    elif emotion == "informative":
        rate_pct = 100
        pitch = "0st"
        volume = "default"

    # Apply base speed multiplier
    # e.g. if base is slow (0.9) and emotion is excited (1.15) -> 0.9 * 1.15 = 1.035 -> 104%
    final_rate_pct = rate_pct * base_speed_mult

    # Scale prosody (intensity affects deviation from 100%)
    # Reuse _scale_prosody logic but manually since we have floats now
    if intensity != 1.0:
        deviation = final_rate_pct - 100.0
        final_rate_pct = 100.0 + (deviation * intensity)
        
        if "st" in pitch:
            try:
                val = float(pitch.replace("st", "").replace("+", ""))
                scaled_pitch = val * intensity
                sign = "+" if scaled_pitch >= 0 else ""
                pitch = f"{sign}{scaled_pitch:.1f}st"
            except:
                pass
    
    tags = []
    tags.append(f'rate="{int(final_rate_pct)}%"')
    if pitch != "0st" and not disable_pitch:
        tags.append(f'pitch="{pitch}"')
    if volume != "default":
        tags.append(f'volume="{volume}"')
    
    if not tags:
        return "", ""
        
    return f'<prosody {" ".join(tags)}>', '</prosody>'


def enhance_narration_with_ssml(text: str, emotion: str = "neutral", use_ai_control: bool = False, 
                                emphasis_words: Optional[List[str]] = None, 
                                pause_after_ms: Optional[int] = None,
                                emotion_intensity: float = 1.0,
                                disable_prosody: bool = False,
                                disable_pitch: bool = False,
                                base_speed: str = "medium") -> str:
    """
    Add SSML tags to narration text for more natural speech.
    Compatible with Google Cloud TTS.
    
    Args:
        text: The plain narration text
        emotion: The segment emotion
        use_ai_control: If True, use AI-provided pause suggestions
        emphasis_words: Words to wrap in <emphasis> tags
        pause_after_ms: AI-suggested pause after this segment
        emotion_intensity: Scale factor for emotion prosody (0.0-2.0)
        disable_prosody: If True, skip prosody tags (for voices that don't support them like Journey)
        disable_pitch: If True, skip pitch attribute in prosody (for Studio voices)
        base_speed: "slow", "medium", or "fast"
    
    Returns:
        SSML-enhanced text
    """
    # Don't wrap if already has SSML speak tag, but we might want to wrap content inside
    if text.strip().startswith("<speak>"):
        return text
    
    enhanced = text
    
    # Resolve base speed multiplier
    speed_mult_map = {
        "slow": 0.9,
        "medium": 1.0,
        "fast": 1.15,       # Noticeably faster but still clear
        "very_fast": 1.25,  # For punchy content
    }
    speed_mult = speed_mult_map.get(base_speed, 1.0)
    
    # Apply emphasis to specific words
    if emphasis_words:
        for word in emphasis_words:
            # Simple replacement - be careful with partial matches in production logic
            # For now assumes whole word matching via spaces or exact match
            if word in enhanced:
                enhanced = enhanced.replace(word, f'<emphasis level="moderate">{word}</emphasis>')

    # Let Google TTS handle punctuation naturally - no manual breaks
    # Only add explicit breaks if AI control requests them
    if use_ai_control and pause_after_ms and pause_after_ms > 0:
        enhanced += f' <break time="{min(pause_after_ms, 2000)}ms"/>'
    
    # Apply emotion prosody
    if not disable_prosody:
        start_tag, end_tag = _get_emotion_prosody(emotion, emotion_intensity, disable_pitch=disable_pitch, base_speed_mult=speed_mult)
        if start_tag:
            enhanced = f"{start_tag}{enhanced}{end_tag}"

    return enhanced


def add_connecting_pause(prev_emotion: str, curr_emotion: str) -> str:
    """
    Get appropriate pause duration between segments based on emotion change.
    
    Args:
        prev_emotion: Previous segment emotion
        curr_emotion: Current segment emotion
    
    Returns:
        SSML break tag or empty string
    """
    # No pause if same emotion (smooth continuation)
    if prev_emotion == curr_emotion:
        return ""
    
    # Longer pause for dramatic shifts
    dramatic_emotions = ["dramatic", "serious", "sad"]
    energetic_emotions = ["excited", "urgent", "curious"]
    
    prev_dramatic = prev_emotion in dramatic_emotions
    curr_dramatic = curr_emotion in dramatic_emotions
    prev_energetic = prev_emotion in energetic_emotions
    curr_energetic = curr_emotion in energetic_emotions
    
    # Big shift = longer pause
    if (prev_dramatic and curr_energetic) or (prev_energetic and curr_dramatic):
        return '<break time="500ms"/>'
    
    # Moderate shift = medium pause
    if prev_emotion != curr_emotion:
        return '<break time="300ms"/>'
    
    return ""
