"""meme_inserter.py — Auto-generated meme overlays for dramatic chess moments.

Picks the most severe moves (blunder > mistake > inaccuracy, ranked further by
eval swing), draws an AI-captioned meme onto a blank template image, and hands
back timed overlays for video_assembler to composite — the same overlay
mechanism it already uses for the avatar and title.
"""

import logging
import os
import random
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Optional

from cache_utils import cache_key, get_cached, put_cached

logger = logging.getLogger(__name__)

_SEVERITY = {"blunder": 3, "mistake": 2, "inaccuracy": 1}

_FALLBACK_CAPTIONS = {
    "blunder": [
        "me, watching my own move a second too late",
        "the eval bar has left the chat",
        "nobody: ... this guy: hangs the queen",
    ],
    "mistake": [
        "it's not a blunder, it's a creative choice",
        "the position was fine until it wasn't",
    ],
    "inaccuracy": [
        "engine: -0.3 / human: 'still winning though'",
        "close enough for a Tuesday",
    ],
}


@dataclass
class MemeMoment:
    move_index: int  # index into ga.moves (0-based)
    classification: str
    move_san: str
    eval_delta: Optional[int]


def pick_meme_moments(ga, max_n: int = 3) -> List[MemeMoment]:
    """Rank moves by classification severity + eval swing, return top max_n."""
    candidates = []
    for i, mv in enumerate(getattr(ga, "moves", [])):
        cls = getattr(mv, "classification", "normal")
        if cls not in _SEVERITY:
            continue
        candidates.append((i, mv, cls))

    candidates.sort(key=lambda c: (_SEVERITY[c[2]], abs(c[1].eval_delta or 0)), reverse=True)

    return [
        MemeMoment(move_index=i, classification=cls, move_san=mv.move_san, eval_delta=mv.eval_delta)
        for i, mv, cls in candidates[:max_n]
    ]


def select_template(classification: str, assets_dir: str) -> Optional[str]:
    folder = os.path.join(assets_dir, "memes", classification)
    if not os.path.isdir(folder):
        return None
    templates = [f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    if not templates:
        return None
    return os.path.join(folder, random.choice(templates))


def generate_caption(classification: str, move_san: str, llm_backend) -> str:
    try:
        system = (
            "You write one-line funny captions for chess reaction memes. "
            "Reply with ONLY the caption text, no quotes, under 12 words."
        )
        user = f"A player just played a {classification} ({move_san}). Write a funny meme caption."
        caption = llm_backend.generate(system, user, max_tokens=40).strip().strip('"')
        if caption:
            return caption
    except Exception as e:
        logger.warning(f"Meme caption generation failed, using fallback: {e}")
    return random.choice(_FALLBACK_CAPTIONS.get(classification, _FALLBACK_CAPTIONS["mistake"]))


def render_meme_png(template_path: str, caption: str, cache_dir: str) -> str:
    """Draw caption onto template, cached by (template, caption) content hash."""
    key = cache_key(template_path, caption)
    cached = get_cached(cache_dir, key, ".png")
    if cached:
        return cached

    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=max(18, img.width // 14))
    except TypeError:
        font = ImageFont.load_default()

    words = caption.split()
    lines, line = [], ""
    for w in words:
        trial = f"{line} {w}".strip()
        if line and draw.textlength(trial, font=font) > img.width * 0.9:
            lines.append(line)
            line = w
        else:
            line = trial
    if line:
        lines.append(line)
    text = "\n".join(lines)

    bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (img.width - tw) / 2
    y = img.height - th - 12

    draw.multiline_text((x, y), text, font=font, fill="white", stroke_width=3,
                         stroke_fill="black", align="center")

    os.makedirs(cache_dir, exist_ok=True)
    # uuid-suffixed so concurrent caption renders never collide on the same temp path.
    tmp_path = os.path.join(cache_dir, f"_tmp_{key}_{uuid.uuid4().hex}.png")
    img.save(tmp_path)
    cached_path = put_cached(cache_dir, key, ".png", tmp_path)
    os.remove(tmp_path)
    return cached_path


def build_meme_overlays(ga, cfg, llm_backend) -> List[dict]:
    """Top-level entry point: returns overlays ready for video_assembler —
    [{move_index, png_path, duration}, ...]. Never raises; any failure just
    yields fewer (or zero) overlays so a render is never blocked by memes."""
    if not getattr(cfg, "enable_memes", True):
        return []

    overlays = []
    try:
        moments = pick_meme_moments(ga, max_n=getattr(cfg, "meme_max_per_video", 3))
        duration = getattr(cfg, "meme_duration", 2.5)

        def _build_one(m: "MemeMoment") -> Optional[dict]:
            try:
                template = select_template(m.classification, cfg.assets_dir)
                if not template:
                    logger.info(f"No meme templates for '{m.classification}', skipping")
                    return None
                caption = generate_caption(m.classification, m.move_san, llm_backend)
                png_path = render_meme_png(template, caption, cfg.meme_cache_dir)
                return {
                    "move_index": m.move_index,
                    "png_path": png_path,
                    "duration": duration,
                }
            except Exception as e:
                logger.warning(f"Meme moment (move {m.move_index}) failed, skipping: {e}")
                return None

        if len(moments) <= 1:
            results = [_build_one(m) for m in moments]
        else:
            with ThreadPoolExecutor(max_workers=min(len(moments), 4)) as ex:
                results = list(ex.map(_build_one, moments))

        overlays = [r for r in results if r]
    except Exception as e:
        logger.warning(f"Meme overlay generation failed, continuing without: {e}")
    return overlays
