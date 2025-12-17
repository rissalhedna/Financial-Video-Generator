# Examples

## Quick Start

### 1. YAML Config (Recommended)

Create a YAML file and run it:

```bash
python -m app.create videos/apple_story.yaml
```

### 2. Python Dict

```python
from app.video_spec import create_video

create_video({
    "title": "My Video",
    "segments": [
        {"text": "Hello world!", "emotion": "excited"},
        {"text": "Technology is amazing.", "visuals": ["tech"]},
    ]
})
```

### 3. JSON Input (Original)

```bash
python -m app.cli examples/sample_input.json -o out/demo
```

---

## YAML Spec Format

```yaml
title: "Video Title"
voice_id: "en-US-Studio-O"    # Optional, default
voice_speed: "fast"           # Optional: slow, normal, fast
music: "inspirational"        # Optional: inspirational, ambient
output_dir: "out/my_video"    # Optional

segments:
  - text: "Narration text here."
    emotion: "excited"        # Optional: neutral, curious, excited, dramatic, etc.
    visuals: ["keyword1", "keyword2"]  # Single video clip
    
  - text: "Another segment with multiple clips."
    emotion: "informative"
    clips:                    # Multiple clips for variety
      - tags: ["tech", "innovation"]
        duration_pct: 50      # 50% of segment duration
      - tags: ["future", "digital"]
        duration_pct: 50
```

---

## Running Examples

```bash
# YAML approach
python examples/manual_video_generation.py --approach yaml

# Dict approach
python examples/manual_video_generation.py --approach dict

# Low-level API
python examples/manual_video_generation.py --approach low-level
```
