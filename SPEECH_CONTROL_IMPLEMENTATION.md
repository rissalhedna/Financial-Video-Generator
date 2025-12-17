# Speech Control Implementation Summary

## Overview

Implemented a configurable speech control system that allows switching between **Rule-Based** and **AI-Driven** SSML enhancement for better voiceover intonation and natural speech.

## Key Changes

### 1. **Configuration** (`app/config.py`)

- Added `use_ai_speech_control: bool` setting
- Defaults to `false` (rule-based mode)
- Can be overridden via `USE_AI_SPEECH_CONTROL` env variable or `--ai-speech` CLI flag

### 2. **Data Models** (`app/models.py`)

- Added `emphasis_words: Optional[List[str]]` to `Segment` model
- Added `pause_after_ms: Optional[int]` to `Segment` model
- These fields store AI suggestions when AI mode is enabled

### 3. **Prompt Engineering** (`app/prompt_templates.py`)

- Updated `schema_for()` to conditionally include AI speech control fields
- Updated `build_user_prompt()` to request emphasis/pause suggestions when AI mode enabled
- Enhanced system prompt to guide GPT on providing speech control hints

### 4. **Script Generation** (`app/script_generator.py`)

- Added `use_ai_speech_control` parameter to `generate_script()`
- Passes control mode to prompt builder

### 5. **SSML Enhancement** (`app/ssml_enhancer.py`)

- Refactored `enhance_narration_with_ssml()` to support both modes:
  - **Rule-Based**: Automatic keyword emphasis, punctuation pauses, emotion prosody
  - **AI-Driven**: Uses GPT-provided `emphasis_words` and `pause_after_ms`
- Added `use_ai_control` parameter with branching logic

### 6. **TTS Synthesis** (`app/tts.py`)

- Added `use_ai_speech_control` parameter to `synthesize_segments()`
- Passes AI hints (emphasis_words, pause_after_ms) to SSML enhancer

### 7. **Pipeline** (`app/pipeline.py`)

- Added `use_ai_speech_control` parameter to `run_pipeline()`
- Propagates setting to both script generation and TTS synthesis
- Falls back to config default if not explicitly provided

### 8. **CLI** (`app/cli.py`)

- Added `--ai-speech` flag to enable AI-driven mode
- Updated help text to explain both modes
- Passes parameter through to pipeline

### 9. **Documentation**

- Updated `README.md` with speech control modes comparison
- Created `ENV_VARIABLES.md` with detailed configuration docs
- Regenerated `dev_testing.ipynb` with new parameters

## Usage

### Rule-Based Mode (Default)

```bash
python -m app.cli --input examples/sample_input.json --out out/demo
```

**How it works:**

- Automatic pauses after commas (200ms), periods (400ms)
- Emphasis on financial keywords: "billion", "million", "percent", "record", etc.
- Emotion-based prosody: excited = faster/higher, serious = slower/lower (via Google SSML)

### AI-Driven Mode

```bash
python -m app.cli --input examples/sample_input.json --out out/demo --ai-speech
```

**How it works:**

- GPT-4o-mini analyzes each segment narration
- Suggests 1-3 key words to emphasize per segment
- Determines optimal pause duration (200-500ms) after each segment
- More contextual but slower and uses more tokens

### Environment Variable

```bash
# In .env file
USE_AI_SPEECH_CONTROL=true
```

## Comparison

| Aspect          | Rule-Based              | AI-Driven                     |
| --------------- | ----------------------- | ----------------------------- |
| **Speed**       | Fast                    | Slower (extra LLM processing) |
| **Cost**        | Lower tokens            | Higher tokens                 |
| **Emphasis**    | Financial keywords      | Contextual, GPT-suggested     |
| **Pauses**      | Fixed punctuation-based | Dynamic, GPT-suggested        |
| **Prosody**     | Emotion-based           | Optional emotion-based        |
| **Consistency** | Very consistent         | May vary per generation       |
| **Control**     | Predictable             | Fine-grained, contextual      |

## Benefits

✅ **Flexibility**: Choose mode based on use case  
✅ **Backward Compatible**: Default behavior unchanged  
✅ **Developer Control**: Can override via CLI or config  
✅ **Better Intonation**: Both modes improve over flat narration  
✅ **Extensible**: Easy to add more AI-driven features later

## Technical Implementation

### Rule-Based Flow

```
Text → SSML Enhancer (rule-based) → Google TTS → Audio
        - Add pauses at punctuation
        - Emphasize financial keywords
        - Apply emotion prosody
```

### AI-Driven Flow

```
Text → GPT-4o-mini → Segment with hints → SSML Enhancer (AI-driven) → Google TTS → Audio
       - Suggests emphasis_words
       - Suggests pause_after_ms
       - Applies AI suggestions via SSML
```

## Future Enhancements

- Add AI-driven prosody suggestions (rate, pitch per segment)
- Support custom emphasis levels (moderate vs strong)
- Allow mixed mode (rule-based + AI refinement)
- Cache AI suggestions for repeated generations
- Add voice modulation tags (whisper, breathing, etc.)

## Testing

Use the developer notebook (`dev_testing.ipynb`) to:

- Compare both modes side-by-side
- Test different emotion combinations
- Analyze SSML output for each mode
- Benchmark performance and token usage
- Fine-tune voice presets per mode
