# Fiindo - AI Financial Video Generator

Generate short-form financial videos with AI-generated scripts, stock footage, and text-to-speech.

## Features

- **Agentic Script Generation**: Multi-agent LLM pipeline for storytelling
- **Stock Footage Search**: Pexels, Pixabay, Freepik integration
- **Google Cloud TTS**: Natural voice synthesis with SSML
- **Word-Level Visual Sync**: Clips switch at trigger words
- **Animated Charts**: Manim-powered line, bar, and pie charts with blurred video backgrounds
- **Context-Aware Visuals**: AI selects business-appropriate stock footage (not literal word matching)

## Quick Start

### Prerequisites

- Python 3.10+
- ffmpeg installed on PATH
- API keys (see Setup)

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your keys
```

**Required API Keys** (in `.env`):

- `OPENAI_API_KEY` - For script generation
- `GOOGLE_API_KEY` - For Text-to-Speech
- At least one of:
  - `PEXELS_API_KEY`
  - `PIXABAY_API_KEY`
  - `FREEPIK_API_KEY`

### Generate a Video

**Option 1: From Topic (Quick)**

```bash
python -m app.generate --topic "Apple Inc stock" --create-video
```

**Option 2: From JSON Input**

```bash
# Create input file
cat > inputs/apple.json << 'EOF'
{
  "topic": "Apple Inc stock",
  "facts": [
    "Founded in 1976 by Steve Jobs and Steve Wozniak",
    "Stock was $31 in 2014, now over $227",
    "Most valuable company on Earth"
  ],
  "news": [],
  "target_seconds": 60,
  "mood": "informative"
}
EOF

# Generate script and video
python -m app.generate inputs/apple.json --create-video
```

**Option 3: From YAML Spec (Direct)**

```bash
python -m app.create videos/my_video.yaml
```

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Agentic Script Pipeline                      │
├─────────────────────────────────────────────────────────────┤
│  Introduction → Development → Charts → Conclusion            │
│       ↓                                                      │
│  Revision → Visual Mapper → YAML Builder                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    Video Pipeline                            │
├─────────────────────────────────────────────────────────────┤
│  YAML → Footage Search → TTS → Arranger → Renderer → MP4    │
└─────────────────────────────────────────────────────────────┘
```

## Commands

### Generate Script Only

```bash
python -m app.generate --topic "Tesla stock" --output videos/tesla.yaml
```

### Generate Script + Video

```bash
python -m app.generate inputs/topic.json --create-video
```

### Create Video from Existing YAML

```bash
python -m app.create videos/my_video.yaml
python -m app.create videos/my_video.yaml --refresh  # Force re-download
```

### UI Prototype (experimental)

We scaffolded a minimal interactive prototype to visualize and step through the pipeline.

Quick start (run backend + frontend in two terminals):

```bash
# Backend
cd ui/backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8001

# Frontend (requires Node.js)
cd ui/frontend
npm install
npm run dev
```

The current prototype shows a pipeline node list, an inspector panel, and a live logs area (SSE). It's intentionally minimal — next steps include integrating React Flow for the interactive graph, editable segments, and live video previews.

### Subtitles / Burn-in

By default Fiindo writes `subtitles.srt` to the output directory and will also _burn_ those subtitles into the final MP4. Subtitles are sized very small by default (font size 10) to avoid obscuring content, and timings are aligned to the actual synthesized audio (so subtitle changes match spoken audio). If you'd rather keep the separate SRT file and avoid overlaying text on the video, pass the `--no-burn-subtitles` flag to the CLI.

Examples:

```bash
# Burn subtitles into video (default, very small font)
python -m app.create videos/my_video.yaml

# Do NOT burn subtitles (SRT is still written)
python -m app.create videos/my_video.yaml --no-burn-subtitles

# Generate+create video without burning subtitles
python -m app.generate inputs/topic.json --create-video --no-burn-subtitles
```

### Legacy Pipeline (JSON input → Video)

```bash
python -m app.cli \
  --input examples/sample_input.json \
  --out out/demo \
  --seconds 45 \
  --mood excited
```

## Project Structure

```
Fiindo/
├── app/
│   ├── agents/           # Agentic script generation
│   │   ├── introduction.py
│   │   ├── development.py
│   │   ├── charts.py
│   │   ├── conclusion.py
│   │   ├── revision.py
│   │   └── visual_mapper.py
│   ├── script_pipeline.py  # Agent orchestration
│   ├── generate.py         # CLI for script generation
│   ├── video_spec.py       # YAML → Video
│   ├── create.py           # CLI for video creation
│   ├── footage_search.py   # Stock video fetching
│   ├── tts.py              # Google Cloud TTS
│   ├── arranger.py         # Timing calculations
│   └── renderer.py         # FFmpeg video rendering
├── prompts/              # Prompt library (documentation)
├── videos/               # YAML video specs
├── inputs/               # JSON input files
└── out/                  # Generated videos
```

## YAML Spec Format

```yaml
title: "Apple Stock Explainer"
voice_id: en-US-Studio-O
voice_speed: fast
music: inspirational
output_dir: out/apple_story
segments:
  - text: "What if I told you a $10,000 investment turned into $70,000?"
    emotion: curious
    visuals:
      - money cash dollars finance

  - text: "This is Apple. Started in a garage. Now worth three trillion."
    emotion: serious
    clips:
      - tags:
          - garage workshop vintage
        trigger: "garage"
      - tags:
          - skyscraper modern corporate
        trigger: "trillion"
```

## Prompts Library

All agent prompts are documented in `/prompts/`:

- [introduction.md](prompts/introduction.md)
- [development.md](prompts/development.md)
- [charts.md](prompts/charts.md)
- [conclusion.md](prompts/conclusion.md)
- [revision.md](prompts/revision.md)
- [visual_mapper.md](prompts/visual_mapper.md)

## Output

Videos are saved to `out/<topic>/`:

- `video.mp4` - Final rendered video (720x1280, 30fps)
- `subtitles.srt` - Generated subtitles
- `manifest.json` - Metadata

## Configuration

**Voice Options** (Google TTS):

- `en-US-Studio-O` (default, natural)
- `en-US-Neural2-J` (energetic)
- `en-US-Journey-D` (storytelling)

**Voice Speed**: `slow`, `medium`, `fast`

**Music**: `inspirational`, `dramatic`, `upbeat`

**Chart Settings** (in `.env`):

- `CHART_BLUR_BACKGROUND=true` - Composite charts over blurred stock video (default: true)
- `CHART_BLUR_BACKGROUND=false` - White background for charts

**Chart Types** (auto-selected by AI):

- `line` - For time series data (stock prices, revenue over time)
- `bar` - For comparisons (revenue by year, quarterly earnings)
- `pie` - For proportions (revenue by product category)

## Technical Notes

- Aspect ratio: 9:16 vertical (720x1280)
- FPS: 30
- Codec: H.264 (CRF 20) + AAC 128k
- TTS: Google Cloud with SSML enhancement
- Footage: Cached in `tmp/videos/` with tag-based hashing
