# AI Content Factory

`AI Content Factory` is a file-based Python project for generating faceless short videos for multiple YouTube and Instagram channels. The current upgrade focuses on `local-first quality` for one channel at a time while preserving safe fallbacks.

## Current provider flow

- Scripts: `Ollama -> OpenAI-compatible endpoint -> deterministic fallback`
- Voice: `Piper -> Windows SAPI -> synthetic fallback`
- Visuals: `styled vertical social cards` by default
- Uploading: `mock only`

This means the project still runs when local AI tools are missing, but quality improves automatically as soon as better local providers are configured.

## What the project does

- Reads channel configs from `data/channels.json`
- Generates non-duplicate topics and tracks them in `data/used_topics.json`
- Builds short scripts with `hook`, `body`, and `CTA`
- Splits scripts into 5-6 scenes
- Creates vertical visuals for each scene
- Generates local narration audio
- Generates `.srt` subtitles from scene timings
- Renders `1080x1920` MP4 shorts with FFmpeg
- Generates publish metadata
- Tracks success and failure registries
- Exposes a minimal FastAPI API and APScheduler runner

## Project layout

- `app/`: application code
- `data/`: channel config and registries
- `examples/`: sample channel config and output flow
- `output/`: generated artifacts
- `prompts/`: provider prompts
- `tests/`: pytest coverage for core flows

## Install

Windows PowerShell:

```powershell
cd ai_content_factory
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cd ai_content_factory
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## FFmpeg setup

Windows:

1. Install FFmpeg
2. Add `ffmpeg` to `PATH`, or set `FFMPEG_BIN` in `.env`
3. Verify:

```powershell
ffmpeg -version
```

Linux VPS:

```bash
sudo apt update
sudo apt install ffmpeg
ffmpeg -version
```

## Script generation setup

### Preferred local setup: Ollama

Install Ollama, then pull a small instruct model:

```powershell
ollama pull qwen2.5:3b-instruct
```

Set these in `.env`:

```env
SCRIPT_PROVIDER=auto
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b-instruct
```

If Ollama is not available, the pipeline falls back automatically.

### Optional OpenAI-compatible endpoint

If you want to use a hosted or self-hosted OpenAI-compatible API later:

```env
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://your-endpoint/v1
OPENAI_MODEL=your-model
```

## TTS setup

### Preferred local setup: Piper

1. Install the `piper` binary
2. Download a voice model
3. Set:

```env
PIPER_BIN=piper
PIPER_MODEL_PATH=./models/en_US-lessac-medium.onnx
PIPER_SPEAKER=
```

### Windows fallback

If Piper is not configured on Windows, the app uses Windows SAPI automatically.

### Last fallback

If neither Piper nor Windows SAPI is available, the pipeline still runs with synthetic audio.

## Run one improved channel

This is the recommended first command:

```powershell
python -m app.run_once --channel tech_facts_daily
```

Inspect output after the run:

- `output/scripts/tech_facts_daily/`
- `output/scenes/tech_facts_daily/`
- `output/images/tech_facts_daily/`
- `output/audio/tech_facts_daily/`
- `output/subtitles/tech_facts_daily/`
- `output/videos/tech_facts_daily/`
- `output/metadata/tech_facts_daily/`

Sample flow reference:

- `examples/sample_channels.json`
- `examples/sample_output_flow.md`

## Run the API

```powershell
python -m uvicorn app.main:app --reload
```

Available endpoints:

- `GET /health`
- `POST /run-once`
- `GET /channels`
- `POST /channels/reload-config`

Run all active channels once:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/run-once `
  -Method Post `
  -ContentType "application/json" `
  -Body '{}'
```

Run one channel:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/run-once `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"channel_id":"tech_facts_daily"}'
```

## Run the scheduler

```powershell
python -m app.scheduler.scheduler
```

The scheduler creates an interval job per active channel based on `videos_per_day`.

## Fallback behavior

- No Ollama / no API endpoint -> deterministic short-form script fallback
- No Piper -> Windows SAPI on Windows
- No Windows SAPI -> synthetic tone fallback
- No real image model -> styled local social-card generator
- No upload provider -> mock uploader only

## Tech facts example channel

The first channel in `data/channels.json` is optimized for tech facts shorts:

- fast, specific script style
- strong tech visual theme
- short CTA
- curated seed topics
- social-ready hashtags

## Testing

Run tests:

```powershell
python -m pytest
```

Current tests cover:

- topic duplicate prevention
- scene split
- subtitle timing
- output file creation
- config path resolution
- scheduler wiring
- script fallback shaping
- styled image output

## Windows and Linux notes

- Path handling uses `pathlib`
- Relative `.env` paths resolve from project root
- Windows local runs can use SAPI speech automatically
- Linux VPS runs stay compatible with FFmpeg and file-based output

## MVP limitations

- Best script quality still depends on a real LLM provider such as Ollama
- Best narration quality still depends on Piper
- Visuals are polished cards, not model-generated imagery yet
- Uploading is still mock only
- Scheduling is interval-based, not campaign-level orchestration
- No dashboard, auth, queue, or database is included yet
