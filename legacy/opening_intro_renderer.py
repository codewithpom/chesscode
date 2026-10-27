"""opening_intro_renderer.py — SVG-drawn animated opening-intro card.

Renders a short (~6.5s) sequence of PNG frames shown at the very start of an
opening-theory video: the opening's name + ECO, its tagline, a win/draw/loss
popularity bar (real Lichess data), the famous players who championed it, and
the main line. Frames are authored as SVG and rasterised with cairosvg — the
same engine board_renderer.py already uses for the board — so we get gradients,
opacity, transforms and clean typography ("HTML-quality") with zero new deps.

Contract mirrors stats_intro_renderer.render_intro_sequence: returns
(frame_paths, frame_durations) with sum(frame_durations) == duration, ready to
prepend directly into VideoAssembler's frame plan. Content-addressed cached.

Any row whose data is unavailable (empty players / opening_stats is None) is
simply omitted — never a fake placeholder.
"""

import io
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from cache_utils import cache_key, get_cached, put_cached

logger = logging.getLogger(__name__)

# Palette — matches stats_intro_renderer / board_renderer conventions.
BG_TOP = (18, 18, 32)
BG_BOTTOM = (8, 8, 16)
ACCENT = (245, 166, 35)
PANEL_FILL = (22, 22, 36)
PANEL_BORDER = (48, 48, 66)
TEXT_PRIMARY = (232, 232, 238)
TEXT_MUTED = (158, 158, 178)
CHIP_FILL = (34, 30, 44)
CHIP_BORDER = (86, 66, 30)
WIN_COLOR = (100, 220, 100)
DRAW_COLOR = (150, 150, 165)
LOSS_COLOR = (220, 90, 90)

FONT_FAMILY = "'Arial', 'DejaVu Sans', 'Helvetica', sans-serif"


@dataclass
class OpeningIntroData:
    opening_name: str
    eco: str = ""
    tagline: str = ""
    moves: str = ""
    opening_stats: Optional[object] = None       # opening_stats.OpeningStats
    famous_players: List[str] = field(default_factory=list)
    players_note: str = ""
    channel_name: str = "ChessCode"


def _ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def _clamp01(t: float) -> float:
    return max(0.0, min(1.0, t))


def _stagger(eased: float, start: float, end: float) -> float:
    """Local 0..1 progress for an element that animates over [start, end] of the
    global eased timeline. Lets rows fade/slide in one after another."""
    if end <= start:
        return 1.0 if eased >= end else 0.0
    return _clamp01((eased - start) / (end - start))


def _hex(rgb: Tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _fmt_int(n: int) -> str:
    return f"{n:,}"


def render_intro_sequence(data: OpeningIntroData, vfmt, out_dir: str, game_id: str,
                          duration: float = 6.5, fps: int = 24,
                          cache_dir: Optional[str] = None
                          ) -> Tuple[List[str], List[float]]:
    """Returns (frame_paths, frame_durations); sum(frame_durations) == duration."""
    cache_dir = cache_dir or os.path.normpath(
        os.path.join(out_dir, "..", ".cache", "opening_intro"))
    os.makedirs(out_dir, exist_ok=True)

    key = cache_key(
        "opening_intro_v2",   # bump when the frame/animation scheme changes
        data.opening_name, data.eco, data.tagline, data.moves,
        str(data.opening_stats), "|".join(data.famous_players), data.players_note,
        data.channel_name, vfmt.name, f"{duration}", f"{fps}",
    )

    meta_path = get_cached(cache_dir, key, "_meta.txt")
    if meta_path:
        try:
            with open(meta_path, encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
            frame_paths, frame_durs, all_present = [], [], True
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
            logger.warning(f"opening_intro_renderer: cache meta unreadable, re-rendering: {e}")

    # Sample one frame per output frame across a short animate-in window so the
    # motion is smooth at `fps` (not a ~2.5fps slideshow), then hold the settled
    # frame for the rest. A snappy ~2s animate-in reads better than a slow drift.
    animating_duration = min(2.0, duration * 0.4)
    hold_duration = duration - animating_duration
    n_anim = max(2, int(round(animating_duration * fps)))
    per_sample_dur = animating_duration / n_anim
    # t_norm sweeps 0→1 over the animate-in frames; last entry is the held frame.
    t_samples = [i / n_anim for i in range(n_anim)] + [1.0]

    frame_paths: List[str] = []
    frame_durs: List[float] = []
    for i, t_norm in enumerate(t_samples):
        png = _render_frame_png(data, vfmt, t_norm)
        tmp_path = os.path.join(out_dir, f"{game_id}_opening_intro_{i:03d}.png")
        with open(tmp_path, "wb") as f:
            f.write(png)
        cached_path = put_cached(cache_dir, f"{key}_{i:03d}", ".png", tmp_path)
        frame_paths.append(cached_path)
        is_last = (i == len(t_samples) - 1)
        frame_durs.append(hold_duration if is_last else per_sample_dur)

    try:
        with open(os.path.join(cache_dir, f"{key}_meta.txt"), "w", encoding="utf-8") as f:
            for p, d in zip(frame_paths, frame_durs):
                f.write(f"{p}\t{d}\n")
    except OSError as e:
        logger.warning(f"opening_intro_renderer: failed to write cache meta: {e}")

    return frame_paths, frame_durs


def _render_frame_png(data: OpeningIntroData, vfmt, t_norm: float) -> bytes:
    svg = _build_svg(data, vfmt, _ease_out_cubic(_clamp01(t_norm)))
    try:
        import cairosvg
        return cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                                output_width=vfmt.width, output_height=vfmt.height)
    except ImportError:
        return _pil_fallback_png(data, vfmt)


# ─────────────────────────────────────────────────────────────────────────────
# SVG authoring
# ─────────────────────────────────────────────────────────────────────────────
def _build_svg(data: OpeningIntroData, vfmt, eased: float) -> str:
    W, H = vfmt.width, vfmt.height
    cx = W / 2
    parts: List[str] = []

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">')

    # Background gradient + card panel.
    parts.append(
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{_hex(BG_TOP)}"/>'
        f'<stop offset="1" stop-color="{_hex(BG_BOTTOM)}"/></linearGradient></defs>')
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="url(#bg)"/>')

    mx, my = W * 0.08, H * 0.10
    card_x, card_y = mx, my
    card_w, card_h = W - 2 * mx, H - 2 * my
    parts.append(
        f'<rect x="{card_x:.0f}" y="{card_y:.0f}" width="{card_w:.0f}" '
        f'height="{card_h:.0f}" rx="26" fill="{_hex(PANEL_FILL)}" '
        f'stroke="{_hex(PANEL_BORDER)}" stroke-width="2"/>')
    parts.append(
        f'<rect x="{card_x:.0f}" y="{card_y:.0f}" width="{card_w:.0f}" height="10" '
        f'rx="5" fill="{_hex(ACCENT)}"/>')

    inner_x = card_x + card_w * 0.06
    inner_w = card_w * 0.88
    # Font sizes scale with card width so HD and Shorts both read well.
    s = inner_w / 1000.0

    # Fixed vertical anchors as fractions of card_h — avoids cumulative drift so
    # rows never collide regardless of which optional rows are present.
    def ay(frac):
        return card_y + card_h * frac

    # ── Header row: opening title + ECO chip ────────────────────────────────
    p1 = _stagger(eased, 0.0, 0.45)
    dy1 = (1 - p1) * 30
    title_size = 60 * s
    parts.append(f'<g opacity="{p1:.3f}" transform="translate(0 {dy1:.1f})">')
    parts.append(_text(cx, ay(0.15), _esc(data.opening_name or "Opening"),
                       title_size, TEXT_PRIMARY, weight="bold", baseline="middle"))
    if data.eco:
        chip_h = 46 * s
        chip_w = 150 * s
        chip_cy = ay(0.26)
        parts.append(
            f'<rect x="{cx - chip_w/2:.0f}" y="{chip_cy - chip_h/2:.0f}" '
            f'width="{chip_w:.0f}" height="{chip_h:.0f}" rx="{chip_h/2:.0f}" '
            f'fill="{_hex(CHIP_FILL)}" stroke="{_hex(CHIP_BORDER)}" stroke-width="1.5"/>')
        parts.append(_text(cx, chip_cy, f"ECO {_esc(data.eco)}",
                           26 * s, ACCENT, weight="bold", baseline="middle"))
    parts.append('</g>')

    # ── Tagline ──────────────────────────────────────────────────────────────
    if data.tagline:
        p2 = _stagger(eased, 0.10, 0.55)
        tagline = data.tagline if len(data.tagline) <= 90 else data.tagline[:87] + "…"
        parts.append(_text(cx, ay(0.37), _esc(tagline), 30 * s, TEXT_MUTED,
                           opacity=p2, italic=True, baseline="middle"))

    # ── Win / Draw / Loss bar ───────────────────────────────────────────────
    st = data.opening_stats
    if st is not None:
        p3 = _stagger(eased, 0.22, 0.72)
        bar_w = inner_w
        bar_h = 44 * s
        bar_x = inner_x
        bar_y = ay(0.45)
        w_frac = getattr(st, "white_win_pct", 0) / 100.0
        d_frac = getattr(st, "draw_pct", 0) / 100.0
        b_frac = getattr(st, "black_win_pct", 0) / 100.0
        filled = bar_w * p3
        segs = ((w_frac, WIN_COLOR), (d_frac, DRAW_COLOR), (b_frac, LOSS_COLOR))
        parts.append(
            f'<clipPath id="barclip"><rect x="{bar_x:.0f}" y="{bar_y:.0f}" '
            f'width="{max(0.1, filled):.1f}" height="{bar_h:.0f}" '
            f'rx="{bar_h/2:.0f}"/></clipPath>')
        parts.append('<g clip-path="url(#barclip)">')
        cxb = bar_x
        for frac, color in segs:
            seg_w = bar_w * frac
            parts.append(
                f'<rect x="{cxb:.1f}" y="{bar_y:.0f}" width="{seg_w:.1f}" '
                f'height="{bar_h:.0f}" fill="{_hex(color)}"/>')
            cxb += seg_w
        parts.append('</g>')
        parts.append(
            f'<rect x="{bar_x:.0f}" y="{bar_y:.0f}" width="{bar_w:.0f}" '
            f'height="{bar_h:.0f}" rx="{bar_h/2:.0f}" fill="none" '
            f'stroke="{_hex(PANEL_BORDER)}" stroke-width="2"/>')

        parts.append(_text(cx, ay(0.56),
                           (f"White {getattr(st,'white_win_pct',0):.0f}%   ·   "
                            f"Draw {getattr(st,'draw_pct',0):.0f}%   ·   "
                            f"Black {getattr(st,'black_win_pct',0):.0f}%"),
                           26 * s, TEXT_PRIMARY, opacity=p3, baseline="middle"))
        games = int(getattr(st, "total_games", 0) * p3)
        parts.append(_text(cx, ay(0.61), f"{_fmt_int(games)} games analyzed",
                           20 * s, TEXT_MUTED, opacity=p3, baseline="middle"))

    # ── Famous players ──────────────────────────────────────────────────────
    players = [p for p in (data.famous_players or []) if p.strip()][:5]
    if players:
        p4 = _stagger(eased, 0.38, 0.90)
        parts.append(_text(cx, ay(0.70), "CHAMPIONED BY", 22 * s, ACCENT,
                           weight="bold", opacity=p4, tracking=4, baseline="middle"))
        parts.append(_player_pills(players, cx, ay(0.78), s, p4))
        if data.players_note:
            note = (data.players_note if len(data.players_note) <= 80
                    else data.players_note[:77] + "…")
            parts.append(_text(cx, ay(0.86), _esc(note), 22 * s, TEXT_MUTED,
                               opacity=p4, baseline="middle", italic=True))

    # ── Main line + channel ribbon (bottom-anchored) ────────────────────────
    p5 = _stagger(eased, 0.5, 1.0)
    if data.moves:
        moves = data.moves if len(data.moves) <= 78 else data.moves[:75] + "…"
        parts.append(_text(cx, ay(0.93), _esc(moves), 23 * s, TEXT_PRIMARY,
                           opacity=p5, baseline="middle"))
    parts.append(_text(cx, ay(0.965), _esc(data.channel_name), 22 * s, ACCENT,
                       weight="bold", opacity=p5, tracking=2, baseline="middle"))

    parts.append('</svg>')
    return "".join(parts)


def _player_pills(players: List[str], cx: float, y: float, s: float,
                  opacity: float) -> str:
    """A centred row of name pills. Approximates text width by char count so we
    can lay them out without a font-metrics backend."""
    pad = 22 * s
    gap = 16 * s
    pill_h = 52 * s
    char_w = 15.5 * s
    widths = [len(p) * char_w + pad * 2 for p in players]
    total = sum(widths) + gap * (len(players) - 1)
    x = cx - total / 2
    out = [f'<g opacity="{opacity:.3f}">']
    for name, w in zip(players, widths):
        out.append(
            f'<rect x="{x:.1f}" y="{y - pill_h/2:.1f}" width="{w:.1f}" '
            f'height="{pill_h:.1f}" rx="{pill_h/2:.0f}" fill="{_hex(CHIP_FILL)}" '
            f'stroke="{_hex(CHIP_BORDER)}" stroke-width="1.5"/>')
        out.append(_text(x + w / 2, y, _esc(name), 25 * s, TEXT_PRIMARY,
                         weight="bold", baseline="middle"))
        x += w + gap
    out.append('</g>')
    return "".join(out)


def _text(x, y, content, size, color, weight="normal", opacity=1.0,
          baseline="alphabetic", italic=False, tracking=0.0) -> str:
    style = ""
    if italic:
        style = ' font-style="italic"'
    ls = f' letter-spacing="{tracking}"' if tracking else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT_FAMILY}" '
            f'font-size="{size:.1f}" font-weight="{weight}" fill="{_hex(color)}" '
            f'text-anchor="middle" dominant-baseline="{baseline}" '
            f'opacity="{opacity:.3f}"{style}{ls}>{content}</text>')


def _pil_fallback_png(data: OpeningIntroData, vfmt) -> bytes:
    """Plain PIL card if cairosvg is unavailable — keeps the pipeline alive."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = vfmt.width, vfmt.height
    img = Image.new("RGB", (W, H), BG_BOTTOM)
    draw = ImageDraw.Draw(img)
    try:
        font_big = ImageFont.load_default(size=int(W * 0.05))
        font_small = ImageFont.load_default(size=int(W * 0.02))
    except TypeError:
        font_big = font_small = ImageFont.load_default()
    draw.text((W / 2, H * 0.4), data.opening_name or "Opening", fill=TEXT_PRIMARY,
              font=font_big, anchor="mm")
    if data.famous_players:
        draw.text((W / 2, H * 0.55), "  ·  ".join(data.famous_players[:5]),
                  fill=ACCENT, font=font_small, anchor="mm")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
