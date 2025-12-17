## AI Financial Video Generator (Stock Footage + Google TTS)

- Input: raw financial data (company/stock/news) as JSON
- Output: 10–60s vertical 720x1280 MP4, synced TTS, neutral/educational tone
- Pipeline: script → stock visuals → TTS → subtitles → render

### Prerequisites

- Python 3.10+
- ffmpeg installed on PATH
- API keys in `.env`:
  - `OPENAI_API_KEY`
  - `GOOGLE_API_KEY` (for Text-to-Speech)
  - `FREEPIK_API_KEY` (for visuals)
  - Optional: `PIXABAY_API_KEY`

### Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # fill keys (or export vars)
```

### Run

```bash
python -m app.cli \
  --input examples/sample_input.json \
  --out out/demo \
  --seconds 45 \
  --mood excited \
  --voice en-US-Neural2-J
```

### Speech Control Modes

The pipeline supports two modes for controlling speech intonation:

**1. Rule-Based (Default)**

- Automatic SSML enhancement
- Emotion-based prosody (rate/pitch via Google SSML)
- Keyword emphasis on financial terms
- Natural pauses after punctuation

**2. AI-Driven**

- GPT-4o-mini suggests specific words to emphasize
- AI determines pause durations between segments
- More fine-grained control over delivery

Enable AI-driven mode:

```bash
python -m app.cli \
  --input examples/sample_input.json \
  --out out/demo \
  --ai-speech
```

Or set in `.env`:

```
USE_AI_SPEECH_CONTROL=true
```

The output video is saved to `out/<name>/video.mp4` with `subtitles.srt` and a `manifest.json`.

### Notes

- Aspect: 9:16 vertical at 720x1280, 30fps
- No financial advice: scripts are story-led and educational only
- Visuals: Freepik search (video filter), fallback to Pixabay
- TTS: Google Cloud TTS with SSML enhancement for natural intonation
  - Natural pauses after punctuation (200-400ms)
  - Emphasis on key financial terms
  - Emotion-based prosody (rate/pitch variations)
- Rendering: H.264 (CRF 20) + AAC 128k, seamless transitions
