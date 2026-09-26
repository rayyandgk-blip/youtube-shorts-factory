"""Orchestrator agent: Claude plans each Short and delegates every production step to a subagent.

The orchestrator only sees compact summaries; heavy artifacts (audio, clips, video) stay on
disk inside the job directory and are passed between subagents by the Job object.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import anthropic
from anthropic import beta_tool

from . import history
from .agents import captions, editor, footage, script_writer, uploader, voice
from .agents.captions import Word
from .agents.script_writer import Script
from .config import FALLBACK_BETA, MAX_SHORT_SECONDS, MODEL, OUTPUT_DIR, Settings

log = logging.getLogger(__name__)

WORDS_PER_SECOND = 2.5

SYSTEM = """You are the producer of an autonomous faceless YouTube Shorts channel. Each run you publish exactly one Short.

You do not produce anything yourself; you direct subagents through your tools, in this order:
1. write_script - choose a specific, curiosity-driven topic in the channel niche that is not a repeat of a recent title, and brief the script writer with it.
2. produce_voiceover - if the reported duration exceeds the limit, call write_script again with a tighter brief before continuing.
3. generate_captions
4. fetch_footage - if too few clips come back, rewrite the script with more concrete, filmable footage queries.
5. render_video
6. upload_video - only once every earlier step has succeeded.

A tool that fails returns an error; decide whether to retry, revise the script, or stop. When done, reply with a one-line summary."""


@dataclass
class Job:
    dir: Path
    script: Script | None = None
    voice_path: Path | None = None
    words: list[Word] = field(default_factory=list)
    clips: list[Path] = field(default_factory=list)
    video_path: Path | None = None
    video_id: str | None = None

    def require(self, name: str, value):
        if not value:
            raise RuntimeError(f"{name} is missing; run the earlier steps first")
        return value


def produce_short(settings: Settings, client: anthropic.Anthropic) -> Job:
    job = Job(dir=OUTPUT_DIR / datetime.now().strftime("%Y%m%d-%H%M%S"))
    job.dir.mkdir(parents=True)
    max_words = int(MAX_SHORT_SECONDS * WORDS_PER_SECOND)

    @beta_tool
    def write_script(topic: str, angle: str) -> str:
        """Delegate to the script-writer subagent. Replaces any previous script and discards
        everything produced from it.

        Args:
            topic: The specific subject of this Short.
            angle: The hook or framing, plus any revision notes for the writer.
        """
        job.script = script_writer.write_script(client, settings.niche, topic, angle, max_words)
        job.voice_path, job.words, job.clips, job.video_path = None, [], [], None
        return job.script.model_dump_json()

    @beta_tool
    def produce_voiceover() -> str:
        """Delegate to the voice subagent: synthesize the current script's narration."""
        script = job.require("script", job.script)
        job.voice_path = job.dir / "voice.mp3"
        duration = voice.synthesize(script.narration, settings.voice, job.voice_path)
        return json.dumps({"duration_seconds": round(duration, 1), "limit_seconds": MAX_SHORT_SECONDS})

    @beta_tool
    def generate_captions() -> str:
        """Delegate to the caption subagent: word-level timestamps from the voiceover."""
        job.words = captions.transcribe(job.require("voiceover", job.voice_path))
        return json.dumps({"words": len(job.words), "transcript": " ".join(w.text for w in job.words)})

    @beta_tool
    def fetch_footage() -> str:
        """Delegate to the footage subagent: download one portrait stock clip per footage query."""
        script = job.require("script", job.script)
        job.clips = footage.fetch(script.footage_queries, settings.pexels_api_key, job.dir)
        return json.dumps({"queries": len(script.footage_queries), "clips": len(job.clips)})

    @beta_tool
    def render_video() -> str:
        """Delegate to the editor subagent: compose footage, voiceover and captions into the final MP4."""
        job.video_path = editor.render(
            job.require("footage", job.clips),
            job.require("voiceover", job.voice_path),
            job.require("captions", job.words),
            job.dir / "short.mp4",
        )
        return json.dumps({"video": job.video_path.name})

    @beta_tool
    def upload_video() -> str:
        """Delegate to the uploader subagent: publish the rendered Short to YouTube."""
        job.video_id = uploader.upload(
            job.require("rendered video", job.video_path),
            job.require("script", job.script),
            settings.privacy,
        )
        return json.dumps({"video_id": job.video_id, "privacy": settings.privacy})

    recent = history.recent_titles()
    brief = (
        f"Channel niche: {settings.niche}\n"
        f"Recent titles to avoid repeating:\n{chr(10).join(recent) or '(none yet)'}\n\n"
        "Produce and publish today's Short."
    )
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        thinking={"type": "adaptive"},
        system=SYSTEM,
        tools=[write_script, produce_voiceover, generate_captions, fetch_footage, render_video, upload_video],
        messages=[{"role": "user", "content": brief}],
    )
    final = None
    for message in runner:
        final = message
        for block in message.content:
            if block.type == "text":
                log.info("orchestrator: %s", block.text)
            elif block.type == "tool_use":
                log.info("orchestrator -> %s(%s)", block.name, json.dumps(block.input))

    if final is not None and final.stop_reason == "refusal":
        raise RuntimeError(f"orchestrator declined: {final.stop_details}")
    if job.video_id is None:
        raise RuntimeError(f"run ended without an upload; job files are in {job.dir}")
    history.record(job.script.title, job.video_id)
    return job
