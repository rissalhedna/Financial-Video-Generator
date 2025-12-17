# Environment Variables

This document describes all environment variables used by the AI Financial Video Generator.

## Required Variables

### `OPENAI_API_KEY`

- **Description**: OpenAI API key for GPT-4o-mini script generation
- **Required**: Yes
- **Example**: `sk-...`

### `GOOGLE_API_KEY`

- **Description**: Google Cloud API key for Text-to-Speech
- **Required**: Yes
- **Example**: `AIzaSy...`

### `FREEPIK_API_KEY`

- **Description**: Freepik API key for stock footage
- **Required**: Yes
- **Example**: `FPSX...`
- **Get it**: https://www.freepik.com/api

## Optional Variables

### `PIXABAY_API_KEY`

- **Description**: Pixabay API key (fallback for stock footage)
- **Required**: No
- **Default**: None
- **Get it**: https://pixabay.com/api/docs/

### `DEFAULT_VOICE_NAME`

- **Description**: Google TTS Voice Name to use for narration
- **Required**: No
- **Default**: `en-US-Neural2-J`
- **Example**: `en-US-Studio-M`
- **Get voices**: https://cloud.google.com/text-to-speech/docs/voices

### `USE_AI_SPEECH_CONTROL`

- **Description**: Enable AI-driven speech control (GPT suggests emphasis and pauses)
- **Required**: No
- **Default**: `false` (rule-based SSML)
- **Values**:
  - `true`: GPT-4o-mini provides `emphasis_words` and `pause_after_ms` for each segment
  - `false`: Automatic SSML with emotion-based prosody and keyword emphasis
- **Note**: AI mode uses more LLM tokens and may be slower, but provides finer control

## Video Settings

### `ASPECT`

- **Description**: Video aspect ratio
- **Default**: `9:16` (vertical)

### `RESOLUTION`

- **Description**: Video resolution
- **Default**: `720x1280`

### `FPS`

- **Description**: Frames per second
- **Default**: `30`

## Directory Settings

### `OUTPUT_DIR`

- **Description**: Output directory for rendered videos
- **Default**: `out`

### `TMP_DIR`

- **Description**: Temporary directory for intermediate files
- **Default**: `tmp`

## LLM Settings

### `LLM_MODEL`

- **Description**: OpenAI model to use for script generation
- **Default**: `gpt-4o-mini`
- **Options**: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`, etc.

### `HTTP_TIMEOUT`

- **Description**: HTTP timeout in seconds for API calls
- **Default**: `60`

## Example `.env` File

```bash
# Required
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIzaSy...
FREEPIK_API_KEY=FPSX...

# Optional
PIXABAY_API_KEY=def789...
DEFAULT_VOICE_NAME=en-US-Neural2-J
USE_AI_SPEECH_CONTROL=false

# Settings (can use defaults)
ASPECT=9:16
RESOLUTION=720x1280
FPS=30
OUTPUT_DIR=out
TMP_DIR=tmp
LLM_MODEL=gpt-4o-mini
HTTP_TIMEOUT=60
```

## Speech Control Modes Comparison

| Feature  | Rule-Based (default)                   | AI-Driven                           |
| -------- | -------------------------------------- | ----------------------------------- |
| Emphasis | Automatic on financial keywords        | GPT suggests specific words         |
| Pauses   | Fixed after punctuation (200-400ms)    | GPT suggests custom durations       |
| Prosody  | Emotion-based rate/pitch (Google SSML) | Optional emotion-based              |
| Speed    | Fast (no extra LLM processing)         | Slower (GPT processes each segment) |
| Cost     | Lower (fewer tokens)                   | Higher (more tokens)                |
| Control  | Consistent, predictable                | Fine-grained, contextual            |

**Recommendation**: Start with rule-based mode (default). Enable AI mode if you need more control over specific word emphasis or pause timing.
