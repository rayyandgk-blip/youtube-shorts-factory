"""Editor subagent: assembles footage, voiceover and captions into a vertical MP4."""

from functools import cache
from pathlib import Path

import numpy as np
from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
    vfx,
)
from moviepy.video.io.ffmpeg_reader import ffmpeg_parse_infos
from PIL import Image, ImageDraw, ImageFont

from ..config import VIDEO_SIZE
from .captions import Word

WIDTH, HEIGHT = VIDEO_SIZE
WORDS_PER_CAPTION = 3
FONT_SIZE = 86
STROKE = 5
CAPTION_MAX_WIDTH = WIDTH - 160
CAPTION_Y = int(HEIGHT * 0.62)


def _load_filled(path: Path, duration: float) -> VideoFileClip:
    """Open a clip scaled (by ffmpeg, while decoding) to cover the frame, centre-cropped and fitted to duration."""
    w, h = ffmpeg_parse_infos(str(path))["video_size"]
    target = (HEIGHT, None) if w / h >= WIDTH / HEIGHT else (None, WIDTH)
    clip = VideoFileClip(str(path), audio=False, target_resolution=target)
    clip = clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=WIDTH, height=HEIGHT)
    if clip.duration < duration:
        return clip.fx(vfx.loop, duration=duration)
    return clip.subclip(0, duration)


@cache
def _font() -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("DejaVuSans-Bold.ttf", FONT_SIZE)


def _wrap(text: str, font: ImageFont.FreeTypeFont) -> str:
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and font.getlength(candidate) > CAPTION_MAX_WIDTH:
            lines.append(line)
            line = word
        else:
            line = candidate
    lines.append(line)
    return "\n".join(lines)


def _caption_image(text: str) -> np.ndarray:
    """White, black-outlined, centred caption on a transparent RGBA canvas."""
    font = _font()
    text = _wrap(text, font)
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    _, top, _, bottom = measure.multiline_textbbox((0, 0), text, font=font, stroke_width=STROKE, align="center")
    image = Image.new("RGBA", (WIDTH, bottom - top + 2 * STROKE))
    ImageDraw.Draw(image).multiline_text(
        (WIDTH / 2, STROKE - top),
        text,
        font=font,
        fill="white",
        stroke_width=STROKE,
        stroke_fill="black",
        anchor="ma",
        align="center",
    )
    return np.array(image)


def _caption_clips(words: list[Word]) -> list[ImageClip]:
    clips = []
    for i in range(0, len(words), WORDS_PER_CAPTION):
        group = words[i:i + WORDS_PER_CAPTION]
        text = " ".join(w.text for w in group).upper()
        clip = ImageClip(_caption_image(text))
        clips.append(clip.set_start(group[0].start).set_end(group[-1].end).set_position(("center", CAPTION_Y)))
    return clips


def render(clip_paths: list[Path], voice_path: Path, words: list[Word], out_path: Path) -> Path:
    audio = AudioFileClip(str(voice_path))
    segment = audio.duration / len(clip_paths)
    parts = [_load_filled(p, segment) for p in clip_paths]
    video = (
        CompositeVideoClip([concatenate_videoclips(parts), *_caption_clips(words)], size=VIDEO_SIZE)
        .set_audio(audio)
        .set_duration(audio.duration)
    )
    try:
        video.write_videofile(
            str(out_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None,
        )
    finally:
        video.close()
        audio.close()
        for part in parts:
            part.close()
    return out_path
