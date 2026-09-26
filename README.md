# YouTube Shorts Factory

Publishes one faceless YouTube Short per day with no human in the loop.

## Architecture

A Claude **orchestrator** agent (`factory/orchestrator.py`) picks the topic, directs production and
reacts to problems, such as rewriting a script whose voiceover runs too long. It does no production
work itself. Each step is a tool that delegates to a single-purpose **subagent** in `factory/agents/`:

| Subagent | Does | Backed by |
|---|---|---|
| `script_writer` | topic → title, description, tags, narration, footage queries | Claude (structured output) |
| `voice` | narration → `voice.mp3` | edge-tts |
| `captions` | voiceover → word timestamps | Whisper |
| `footage` | footage queries → portrait stock clips | Pexels API |
| `editor` | clips + voice + captions → 1080×1920 `short.mp4` | moviepy / ffmpeg / Pillow |
| `uploader` | `short.mp4` → YouTube video | YouTube Data API v3 |

Artifacts stay on disk in `output/<timestamp>/`, and the orchestrator only sees short summaries of
them. Published titles are appended to `data/history.jsonl` so later runs don't repeat topics.

## Setup

```bash
./setup.sh                 # ffmpeg, fonts, .venv, Python packages
source .venv/bin/activate
```

Environment:

| Variable | Required | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | |
| `PEXELS_API_KEY` | yes | free key at pexels.com/api |
| `SHORTS_NICHE` | no | `surprising science facts` |
| `SHORTS_POST_TIME` | no | `15:00` (local time, 24h) |
| `YOUTUBE_PRIVACY` | no | `private` (`public` / `unlisted` / `private`) |
| `TTS_VOICE` | no | `en-US-GuyNeural` (`edge-tts --list-voices`) |

YouTube access: create an OAuth client of type *Desktop app* in Google Cloud Console with the
YouTube Data API v3 enabled, save it as `data/client_secrets.json`, then run once:

```bash
python main.py auth        # opens a browser for consent; stores data/youtube_token.json
```

## Run

```bash
python main.py once        # produce and publish one Short now
python main.py             # run forever, publishing daily at SHORTS_POST_TIME
```
