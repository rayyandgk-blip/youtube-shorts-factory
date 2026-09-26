"""Caption subagent: word-level timestamps from the voiceover with Whisper."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import whisper

from ..config import WHISPER_MODEL


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


@cache
def _model() -> whisper.Whisper:
    return whisper.load_model(WHISPER_MODEL)


def transcribe(audio_path: Path) -> list[Word]:
    result = _model().transcribe(str(audio_path), word_timestamps=True, fp16=False)
    return [
        Word(w["word"].strip(), w["start"], w["end"])
        for segment in result["segments"]
        for w in segment["words"]
    ]
