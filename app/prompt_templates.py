from __future__ import annotations

from pydantic import BaseModel

from .models import InputData, Script

SYSTEM_PROMPT = """You are an expert video storyteller and scriptwriter for high-retention financial content.
Your goal is to produce scripts that are **entertaining**, **cinematic**, and **emotionally engaging**, while remaining factually accurate.

CRITICAL STORYTELLING RULES:
1. **The Hook**: Start with a "Pattern Interrupt" - a surprising fact, a bold question, or a "Picture this..." scenario. Never start with "Today we are talking about...".
2. **Narrative Arc**: Structure the video like a mini-movie.
   - Beginning: Tension/Curiosity (The Mystery)
   - Middle: Rising Action/Information (The Reveal)
   - End: Climax/Impact (The "So What?")
3. **Conversational Tone**: Write exactly as a charismatic YouTuber speaks. Use contractions ("it's", "don't"), rhetorical questions, and conversational connectors.
4. **Show, Don't Just Tell**: Use the narration to describe the visual scene implicitly.
5. **Vary Pacing**: Mix short, punchy sentences (1-3 words) for impact with longer, flowing sentences for explanation.

VISUAL GUIDELINES (visual_tags):
- Think like a film director. We need specific, dynamic, and colorful footage.
- **Formula**: [SUBJECT] + [ACTION] + [CINEMATIC STYLE/COLOR]
- **Examples**:
  - BAD: ["money", "coins"]
  - GOOD: ["Gold coins", "raining down in slow motion", "cinematic lighting"]
  - BAD: ["Nvidia"]
  - GOOD: ["Nvidia GPU chip", "glowing green neon", "macro shot"]
  - BAD: ["stock market"]
  - GOOD: ["Stock chart line", "crashing down aggressively", "red warning lights"]

EMOTION GUIDELINES:
- **excited**: Fast-paced, high energy, louder volume. Use for breakthroughs/wins.
- **dramatic**: Slower, deeper, intense. Use for risks/crashes/pivotal moments.
- **curious**: Slightly slower, rising intonation. Use for questions/mysteries.
- **urgent**: Very fast, punchy. Use for "breaking news" or immediate actions.

REQUIREMENTS:
- 6-15 segments total.
- Total duration must match target (~{target_seconds}s).
- Segments should be 3-8 seconds each.
- **NO** "Welcome back" or "Thanks for watching". Jump straight into the action.

AI SPEECH CONTROL (if requested):
- **pause_after_ms**: Use pauses strategically. 
  - Short pause (200ms) after commas.
  - Medium pause (500ms) after impact statements.
  - Long pause (1000ms) before a big reveal.

Return ONLY valid JSON conforming to the provided schema."""


def schema_for(model: type[BaseModel], use_ai_speech: bool = False) -> str:
    # Provide a minimal JSON schema-like hint derived from field names
    # Keeping concise to fit context limits
    base = (
        '{ "title": "string", "target_seconds": 45, '
        '"segments": [{ "id": 1, "start_ms": 0, "end_ms": 3000, '
        '"narration": "string", "on_screen_text": "string", '
        '"visual_tags": ["tag"], "emotion": "excited", '
        '"sfx": ["whoosh"], "bgm_mood": "upbeat"'
    )
    
    if use_ai_speech:
        base += ', "pause_after_ms": 300'
    
    base += ' }], "disclaimer": "Educational only, not investment advice." }'
    return base


def build_user_prompt(input_data: InputData, use_ai_speech: bool = False) -> str:
    facts = "\n- ".join(input_data.facts) if input_data.facts else "N/A"
    news = "\n- ".join(input_data.news) if input_data.news else "N/A"
    
    prompt = (
        f"Topic: {input_data.topic}\n"
        f"Overall mood: {input_data.mood}\n\n"
        f"Facts:\n- {facts}\n\n"
        f"News bullets:\n- {news}\n\n"
        f"Target duration: {input_data.target_seconds}s\n\n"
        f"INSTRUCTIONS:\n"
        f"- Create a high-retention, cinematic storytelling script\n"
        f"- Segments: 6-15, Total time: ~{input_data.target_seconds}s\n"
        f"- Tone: {input_data.mood.upper()}, Engaging, Human-like\n"
        f"- Visuals: Cinematic, colorful, dynamic actions\n"
    )
    
    if use_ai_speech:
        prompt += (
            f"- **AI SPEECH CONTROL**: Suggest pause durations (pause_after_ms) to control rhythm.\n"
        )
    
    prompt += (
        f"- Last segment end_ms should be around {input_data.target_seconds * 1000}ms\n\n"
        f"Return JSON only.\n"
        f"Schema:\n{schema_for(Script, use_ai_speech)}"
    )
    
    return prompt


