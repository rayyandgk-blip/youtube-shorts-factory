"""Voice subagent: narration text to speech with Microsoft Edge TTS."""

import asyncio
from pathlib import Path

import edge_tts
from moviepy.editor import AudioFileClip


def synthesize(text: str, voice: str, out_path: Path) -> float:
    """Write the voiceover to out_path and return its duration in seconds."""
    asyncio.run(edge_tts.Communicate(text, voice).save(str(out_path)))
    with AudioFileClip(str(out_path)) as audio:
        return audio.duration
