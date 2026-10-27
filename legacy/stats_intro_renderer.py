"""stats_intro_renderer.py — PIL-drawn animated stats intro card.

Renders a short (~5.5s) sequence of PNG frames shown at the very start of the
video: player ratings + result, opening win/draw/loss % + popularity, and a
channel subscriber/view ribbon. Visually matches board_renderer.py's palette
and font conventions (dark navy + orange, PIL.ImageFont.load_default) — no
matplotlib, so it doesn't look like a different app bolted onto the video.

Any row whose data is unavailable (None) is simply omitted — never a fake
placeholder number.
"""

import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

from cache_utils import cache_key, get_cached, put_cached

logger = logging.getLogger(__name__)

BG = (12, 12, 22)
ACCENT = (245, 166, 35)
PANEL_FILL = (22, 22, 36)
PANEL_HEADER = (26, 26, 40)
BORDER = (45, 45, 62)
TEXT_PRIMARY = (225, 225, 225)
TEXT_MUTED = (160, 160, 178)
WIN_COLOR = (100, 220, 100)
DRAW_COLOR = (150, 150, 165)
LOSS_COLOR = (220, 90, 90)


@dataclass
class PlayerRatingRow:
    white_name: str
    black_name: str
    white_elo: Optional[int]
    black_elo: Optional[int]
    result: str


@dataclass
class StatsIntroData:
    ratings: Optional[PlayerRatingRow]
    opening_name: str
    opening_stats: Optional[object]   # opening_stats.OpeningStats
    channel_stats: Optional[object]   # channel_stats.ChannelStats
    channel_name: str = "ChessCode"


def _ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def _fmt_int(n: int) -> str:
    return f"{n:,}"


def _fmt_compact(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _load_font(size: int):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def render_intro_sequence(data: StatsIntroData, vfmt, out_dir: str, game_id: str,
                          duration: float = 5.5, fps: int = 24,
                          cache_dir: Optional[str] = None
                          ) -> Tuple[List[str], List[float]]:
    """Returns (frame_paths, frame_durations) ready to prepend directly into
    VideoAssembler's frame plan. sum(frame_durations) == duration exactly."""
    cache_dir = cache_dir or os.path.normpath(os.path.join(out_dir, "..", ".cache", "stats_intro"))
    os.makedirs(out_dir, exist_ok=True)

    key = cache_key(
        "stats_intro_v1",
        str(data.ratings), data.opening_name, str(data.opening_stats),
        str(data.channel_stats), data.channel_name,
        vfmt.name, f"{duration}", f"{fps}",
    )

    meta_path = get_cached(cache_dir, key, "_meta.txt")
    if meta_path:
        try:
            with open(meta_path, encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
            frame_paths, frame_durs = [], []
            all_present = True
            for ln in lines:
                path, dur = ln.rsplit("\t", 1)
                if not os.path.exists(path):
                    all_present = False
                    break
                frame_paths.append(path)
                frame_durs.append(float(dur))
            if all_present and frame_paths:
                return frame_paths, frame_durs
        except Exception as e:
            logger.warning(f"stats_intro_renderer: cache meta unreadable, re-rendering: {e}")

    # Animating portion: ~55% of total duration, non-uniform (dense early,
    # sparse late) sample points; final settled frame held for the rest.
    t_samples = [0.0, 0.05, 0.10, 0.15, 0.20, 0.28, 0.36, 0.44, 0.55, 0.65, 0.75, 0.85, 1.0]
    animating_duration = duration * 0.55
    per_sample_dur = animating_duration / (len(t_samples) - 1)
    hold_duration = duration - animating_duration

    frame_paths: List[str] = []
    frame_durs: List[float] = []
    for i, t_norm in enumerate(t_samples):
        img = _draw_card_frame(data, vfmt, t_norm)
        tmp_path = os.path.join(out_dir, f"{game_id}_intro_{i:02d}.png")
        img.save(tmp_path)
        cached_path = put_cached(cache_dir, f"{key}_{i:02d}", ".png", tmp_path)
        frame_paths.append(cached_path)
        is_last = (i == len(t_samples) - 1)
        frame_durs.append(hold_duration if is_last else per_sample_dur)

    try:
        with open(os.path.join(cache_dir, f"{key}_meta.txt"), "w", encoding="utf-8") as f:
            for p, d in zip(frame_paths, frame_durs):
                f.write(f"{p}\t{d}\n")
    except OSError as e:
        logger.warning(f"stats_intro_renderer: failed to write cache meta: {e}")

    return frame_paths, frame_durs


def _draw_card_frame(data: StatsIntroData, vfmt, t_norm: float):
    from PIL import Image, ImageDraw

    eased = _ease_out_cubic(max(0.0, min(1.0, t_norm)))
    W, H = vfmt.width, vfmt.height

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    margin_x = int(W * 0.10)
    margin_y = int(H * 0.12)
    card_x0, card_y0 = margin_x, margin_y
    card_x1, card_y1 = W - margin_x, H - margin_y
    card_w = card_x1 - card_x0
    card_h = card_y1 - card_y0

    draw.rounded_rectangle([card_x0, card_y0, card_x1, card_y1], radius=24,
                           fill=PANEL_FILL, outline=BORDER, width=2)
    draw.rounded_rectangle([card_x0, card_y0, card_x1, card_y0 + 8], radius=4, fill=ACCENT)

    pad = int(card_w * 0.05)
    inner_x0, inner_x1 = card_x0 + pad, card_x1 - pad
    inner_w = inner_x1 - inner_x0

    rows = []
    if data.ratings is not None:
        rows.append("ratings")
    rows.append("opening")
    if data.channel_stats is not None:
        rows.append("channel")

    row_weights = {"ratings": 0.34, "opening": 0.46, "channel": 0.14}
    total_weight = sum(row_weights[r] for r in rows)
    gap = int(card_h * 0.03)
    usable_h = card_h - pad * 2 - gap * (len(rows) - 1)

    y = card_y0 + pad
    row_bounds = {}
    for r in rows:
        h = int(usable_h * (row_weights[r] / total_weight))
        row_bounds[r] = (y, y + h)
        y += h + gap

    if "ratings" in row_bounds:
        _draw_ratings_row(draw, data.ratings, inner_x0, inner_x1, *row_bounds["ratings"], eased)
    _draw_opening_row(draw, data.opening_name, data.opening_stats, inner_x0, inner_x1,
                      *row_bounds["opening"], eased)
    if "channel" in row_bounds:
        _draw_channel_row(draw, data.channel_stats, data.channel_name, inner_x0, inner_x1,
                          *row_bounds["channel"], eased)

    return img


def _draw_ratings_row(draw, ratings: PlayerRatingRow, x0, x1, y0, y1, eased):
    font_name = _load_font(30)
    font_elo = _load_font(44)
    font_vs = _load_font(22)
    font_result = _load_font(26)

    mid_y = (y0 + y1) // 2
    half_w = (x1 - x0) // 2

    white_elo_val = int((ratings.white_elo or 0) * eased) if ratings.white_elo else None
    black_elo_val = int((ratings.black_elo or 0) * eased) if ratings.black_elo else None

    wx = x0 + half_w // 2
    draw.text((wx, mid_y - 40), ratings.white_name, fill=TEXT_PRIMARY, font=font_name, anchor="mm")
    if white_elo_val is not None:
        draw.text((wx, mid_y + 10), str(white_elo_val), fill=ACCENT, font=font_elo, anchor="mm")

    draw.text((x0 + half_w, mid_y - 15), "VS", fill=TEXT_MUTED, font=font_vs, anchor="mm")
    if eased >= 0.99:
        result_label = {"1-0": "1 - 0", "0-1": "0 - 1", "1/2-1/2": "1/2 - 1/2"}.get(ratings.result, ratings.result)
        draw.text((x0 + half_w, mid_y + 20), result_label, fill=ACCENT, font=font_result, anchor="mm")

    bx = x0 + half_w + half_w // 2
    draw.text((bx, mid_y - 40), ratings.black_name, fill=TEXT_PRIMARY, font=font_name, anchor="mm")
    if black_elo_val is not None:
        draw.text((bx, mid_y + 10), str(black_elo_val), fill=ACCENT, font=font_elo, anchor="mm")


def _draw_opening_row(draw, opening_name, opening_stats, x0, x1, y0, y1, eased):
    font_title = _load_font(34)
    font_pct = _load_font(20)
    font_meta = _load_font(16)

    title_y = y0 + 30
    draw.text(((x0 + x1) // 2, title_y), opening_name or "This Game", fill=TEXT_PRIMARY,
              font=font_title, anchor="mm")

    if opening_stats is None:
        return

    bar_y0 = title_y + 45
    bar_h = 36
    bar_w = x1 - x0

    w_frac = opening_stats.white_win_pct / 100.0
    d_frac = opening_stats.draw_pct / 100.0
    b_frac = opening_stats.black_win_pct / 100.0

    w_w = int(bar_w * w_frac * eased)
    d_w = int(bar_w * d_frac * eased)
    b_w = int(bar_w * b_frac * eased)

    cx = x0
    for width, color in ((w_w, WIN_COLOR), (d_w, DRAW_COLOR), (b_w, LOSS_COLOR)):
        if width > 0:
            draw.rectangle([cx, bar_y0, cx + width, bar_y0 + bar_h], fill=color)
            cx += width
    draw.rectangle([x0, bar_y0, x1, bar_y0 + bar_h], outline=BORDER, width=2)

    label_y = bar_y0 + bar_h + 22
    pct_label = (f"White {opening_stats.white_win_pct:.0f}%  ·  "
                f"Draw {opening_stats.draw_pct:.0f}%  ·  "
                f"Black {opening_stats.black_win_pct:.0f}%")
    draw.text(((x0 + x1) // 2, label_y), pct_label, fill=TEXT_PRIMARY, font=font_pct, anchor="mm")

    games_val = int(opening_stats.total_games * eased)
    meta_y = label_y + 30
    draw.text(((x0 + x1) // 2, meta_y), f"{_fmt_int(games_val)} games analyzed",
              fill=TEXT_MUTED, font=font_meta, anchor="mm")


def _draw_channel_row(draw, channel_stats, channel_name, x0, x1, y0, y1, eased):
    font = _load_font(20)
    mid_y = (y0 + y1) // 2

    subs_val = int(channel_stats.subscriber_count * eased)
    views_val = int(channel_stats.view_count * eased)

    text = (f"{channel_name}  ·  {_fmt_compact(subs_val)} subscribers  ·  "
           f"{_fmt_compact(views_val)} views")
    draw.text(((x0 + x1) // 2, mid_y), text, fill=ACCENT, font=font, anchor="mm")
