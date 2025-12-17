# AI Video Generator - Testing & Prompt Engineering

Quick notebook for testing each pipeline component independently.

## Run this to start
```python
import sys, json
from pathlib import Path
from IPython.display import Audio, Video, display

sys.path.insert(0, str(Path.cwd()))
from app import *
from app.config import get_settings
from app.models import InputData
from app.script_generator import generate_script
from app.footage_search import search_pexels, plan_and_fetch_visuals
from app.tts import synthesize_segments
from app.arranger import build_render_plan
from app.renderer import render
from app.voice_presets import VOICE_PRESETS

settings = get_settings()
settings.ensure_valid()
Path("notebook_output/audio").mkdir(parents=True, exist_ok=True)
Path("notebook_output/videos").mkdir(parents=True, exist_ok=True)
print("✓ Ready")
```

## 1. TEST SCRIPT GENERATION

```python
# Edit these parameters
test_input = InputData(
    topic="Tesla Robotaxi",
    facts=["Autonomous driving tech", "FSD Beta", "Regulatory challenges"],
    news=["Robotaxi event announced", "Stock reaction mixed"],
    target_seconds=30,
    mood="excited"  # Try: excited, serious, curious, neutral, dramatic
)

script = generate_script(test_input)
print(f"{script.title} - {len(script.segments)} segments\n")
for seg in script.segments:
    print(f"[{seg.id}] {seg.emotion:12} - {seg.narration[:70]}...")
```

**To improve**: Edit `app/prompt_templates.py` SYSTEM_PROMPT

## 2. TEST VOICE PRESETS

```python
# View all presets
for emotion, s in VOICE_PRESETS.items():
    print(f"{emotion:12} stability={s['stability']:.1f} style={s['style']:.1f}")
```

**To improve**: Edit `app/voice_presets.py` to add/modify presets

## 3. GENERATE TTS (uses quota!)

```python
tts_results = synthesize_segments(script, Path("notebook_output/audio"))
print(f"Generated {len(tts_results)} audio files")

# Listen to one
display(Audio(tts_results[1].audio_path))
```

## 4. TEST VISUAL SEARCH

```python
# Search for first segment
test_tags = script.segments[0].visual_tags
results = search_pexels(test_tags, per_page=3)
print(f"Found {len(results)} videos for {test_tags}")
for r in results:
    print(f"  - {r.get('url', '')[:50]}")
```

**To improve**: Adjust visual_tags in script prompt or modify `app/footage_search.py` ranking

## 5. FETCH ALL VISUALS (downloads files!)

```python
visuals = plan_and_fetch_visuals(script, Path("notebook_output/videos"))
print(f"Downloaded {len(visuals)} clips")

# Preview one
display(Video(visuals[1].file_path, width=400))
```

## 6. RENDER FULL VIDEO

```python
plan = build_render_plan(script, visuals, tts_results, Path("notebook_output/video.mp4"))
final = render(plan)
print(f"Done: {final}")
display(Video(str(final), width=400))
```

## QUICK ITERATION HELPER

```python
def quick_test(topic, duration=30, mood="excited"):
    inp = InputData(topic=topic, facts=["fact"], news=["news"], 
                    target_seconds=duration, mood=mood)
    scr = generate_script(inp)
    print(f"{scr.title} ({len(scr.segments)} segs)")
    for s in scr.segments:
        print(f"  [{s.emotion}] {s.narration[:60]}...")
    return scr

# Use it
s = quick_test("Apple Vision Pro Sales", 20, "curious")
```

## A/B TESTING

```python
# Compare different moods
for mood in ["excited", "serious", "neutral"]:
    test_input.mood = mood
    s = generate_script(test_input)
    print(f"\n{mood.upper()}: {s.segments[0].narration[:80]}...")
```

## TUNING GUIDE

**Script too boring?** 
- Increase style values in voice_presets.py
- Add more variety to emotions in prompt_templates.py

**Wrong visual matches?**
- Improve visual_tags in script prompt
- Add better keywords to search

**TTS too slow?**
- Reduce target_seconds for testing
- Use cached audio files

**Voice too monotonic?**
- Increase style parameter (0.6-0.9)
- Lower stability (0.3-0.5)
- Use more varied emotions in script

Save working configs:
```python
Path("my_config.json").write_text(json.dumps(test_input.model_dump(), indent=2))
# Then: python -m app.cli --input my_config.json --out output/ ...
```

