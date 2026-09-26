"""Script-writer subagent: a focused Claude call that turns a topic into a Short script."""

import anthropic
from pydantic import BaseModel

from ..config import FALLBACK_BETA, MODEL

SYSTEM = """You write scripts for faceless YouTube Shorts (vertical, voiced by TTS, stock footage behind burned-in captions).

- The narration is read aloud verbatim: plain spoken sentences, no stage directions, emojis, hashtags or markdown.
- Open with a hook in the first sentence; end with a line that rewards rewatching or invites a comment.
- Stay within the word budget you are given; TTS reads roughly 2.5 words per second.
- Only state facts you are confident are true.
- title: at most 90 characters and ends with " #Shorts".
- description: two or three sentences followed by 3-5 relevant hashtags.
- tags: 5-10 short search keywords.
- footage_queries: 4-6 short, concrete stock-video search terms (e.g. "ocean waves aerial"), in narration order."""


class Script(BaseModel):
    title: str
    description: str
    tags: list[str]
    narration: str
    footage_queries: list[str]


def write_script(client: anthropic.Anthropic, niche: str, topic: str, angle: str, max_words: int) -> Script:
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Channel niche: {niche}\nTopic: {topic}\nAngle: {angle}\nWord budget: at most {max_words} words.",
        }],
        output_format=Script,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"script writer declined the topic: {response.stop_details}")
    return response.parsed_output
