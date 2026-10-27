"""board_renderer.py — Chess board frame renderer (SVG via python-chess + cairosvg/PIL)."""

import os
import io
import re
import logging
import tempfile
import uuid
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import chess
import chess.pgn
import chess.svg

from arrow_analyzer import ArrowAnalyzer, ChessArrow, ArrowType


@dataclass
class CoachInsights:
    """Per-frame data for the coach sidebar panel."""
    move_number: int = 0
    turn: str = "white"
    san_move: str = ""
    top_engine_moves: list = field(default_factory=list)
    # Each item: {"san": str, "score_cp": int, "rank": int, "label": str}
    insights: list = field(default_factory=list)
    # Each item: str with optional <b>tag</b> markup, strictly <= 12 words


logger = logging.getLogger(__name__)

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Bump whenever _board_to_image()'s rendering logic changes (pixelation, outline,
# theming, etc.) so stale disk-cached frames from before the change don't get
# served back out under the same cache key.
_BOARD_CACHE_VERSION = "v4-no-blocky-arrow"

# ── Full-frame layout constants (HD 1920×1080) ────────────────────────────────
_LAYOUT = dict(
    FRAME_W=1920, FRAME_H=1080,
    HEADER_H=72,             # top header bar (channel / tagline / progress)
    # Eval bar sits BETWEEN the board and the info panel (matches the redesign mockup):
    # board shifted left to open a slot for it just inside the sidebar.
    BOARD_X=20, BOARD_Y=90, BOARD_SIZE=900,
    EVAL_X=930, EVAL_Y=90, EVAL_W=42, EVAL_H=900,
    SIDEBAR_X=980, SIDEBAR_W=940,
    # Sidebar splits into a narrow functional column (players + move list,
    # occasional legend card) and a static decorative brand panel on the outer edge.
    NARROW_SIDEBAR_X=980,   # == SIDEBAR_X
    NARROW_SIDEBAR_W=620,
    SIDEBAR_GAP=12,
    DECOR_PANEL_X=1612,     # NARROW_SIDEBAR_X + NARROW_SIDEBAR_W + SIDEBAR_GAP
    DECOR_PANEL_W=308,      # SIDEBAR_W - NARROW_SIDEBAR_W - SIDEBAR_GAP
    BG=(12, 12, 22),
    ACCENT=(245, 166, 35),   # ChessCode orange
)

_CHANNEL_TAGLINE = "Turn losing into winning"

_MOVE_COLORS = {
    "blunder":    (220, 50,  50),
    "mistake":    (220, 140, 50),
    "inaccuracy": (220, 220, 50),
    "normal":     (200, 200, 200),
    "good":       (100, 220, 100),
    "brilliant":  (80,  200, 240),
}
_MOVE_ICONS = {
    "blunder":    "??",
    "mistake":    "?",
    "inaccuracy": "?!",
    "good":       "!",
    "brilliant":  "!!",
    "normal":     "",
}

_CHESS_LEGENDS = [
    {"name": "Magnus Carlsen",  "title": "World Champion 2013-2023",
     "fact": "Became Grandmaster at age 13. Peak rating 2882 - the highest ever recorded."},
    {"name": "Garry Kasparov",  "title": "World Champion 1985-2000",
     "fact": "Ranked world #1 for 255 months. Defeated Deep Blue in 1996 before losing in 1997."},
    {"name": "Bobby Fischer",   "title": "World Champion 1972-1975",
     "fact": "Scored 11/11 at 1963 US Championship. Self-taught Russian to read chess books."},
    {"name": "Mikhail Tal",     "title": "World Champion 1960-1961",
     "fact": "The Magician from Riga. Famous for brilliant piece sacrifices and attacking play."},
    {"name": "Anatoly Karpov",  "title": "World Champion 1975-1985",
     "fact": "Won 3 games and drew 40 vs Kasparov before their 1984 match was controversially stopped."},
]


@dataclass
class Theme:
    name: str
    light_sq: str = "#F0D9B5"
    dark_sq:  str = "#B58863"
    bg_color: str = "#2C2C2C"
    board_size: int = 800
    # UI layer
    panel_bg:        tuple = (16, 16, 28)
    panel_border:    tuple = (80, 80, 120)
    accent:          tuple = (100, 100, 200)
    text_primary:    tuple = (235, 235, 240)
    text_secondary:  tuple = (150, 150, 172)
    text_highlight:  tuple = (100, 180, 255)
    eval_positive:   tuple = (80, 200, 120)
    eval_negative:   tuple = (220, 80, 80)
    # Fonts (relative paths from project root, None = PIL default)
    font_regular: Optional[str] = None
    font_bold:    Optional[str] = None
    font_display: Optional[str] = None  # large titles
    sidebar_font_scale: float = 1.0     # shrink coach-panel headers for wide monospace fonts

    def svg_colors(self) -> dict:
        light = self.light_sq
        if self.name == "cyberpunk":
            # Cap light-square opacity at 15% so magenta-outlined black pieces
            # read with much higher contrast against the board.
            light = f"{self.light_sq}26"  # 0x26/0xFF ≈ 15%
        return {"square light": light, "square dark": self.dark_sq}


THEMES: Dict[str, Theme] = {
    "classic": Theme(
        name="classic",
        light_sq="#F0D9B5", dark_sq="#B58863", bg_color="#1A1612",
        panel_bg=(20, 18, 14), panel_border=(90, 72, 45),
        accent=(185, 142, 58), text_primary=(232, 220, 195),
        text_secondary=(138, 122, 98), text_highlight=(210, 172, 76),
        eval_positive=(88, 185, 110), eval_negative=(200, 78, 78),
        font_regular="assets/fonts/CrimsonText-Regular.ttf",
        font_bold="assets/fonts/CrimsonText-Bold.ttf",
        font_display="assets/fonts/CrimsonText-Bold.ttf",
    ),
    "cyberpunk": Theme(
        name="cyberpunk",
        light_sq="#2E3A4E", dark_sq="#0B0E13", bg_color="#0A0C10",
        panel_bg=(10, 12, 16), panel_border=(0, 240, 255),
        accent=(0, 240, 255), text_primary=(220, 235, 255),
        text_secondary=(80, 110, 145), text_highlight=(255, 0, 127),
        eval_positive=(0, 255, 140), eval_negative=(255, 45, 85),
        font_regular="assets/fonts/Orbitron-Regular.ttf",
        font_bold="assets/fonts/Orbitron-Bold.ttf",
        font_display="assets/fonts/Orbitron-Bold.ttf",
    ),
    "retro": Theme(
        name="retro",
        light_sq="#A3FFD6", dark_sq="#5D3A9B", bg_color="#121212",
        panel_bg=(18, 18, 18), panel_border=(248, 190, 20),
        accent=(248, 190, 20), text_primary=(248, 190, 20),
        text_secondary=(163, 255, 214), text_highlight=(255, 82, 82),
        eval_positive=(163, 255, 214), eval_negative=(255, 82, 82),
        font_regular="assets/fonts/PressStart2P-Regular.ttf",
        font_bold="assets/fonts/PressStart2P-Regular.ttf",
        font_display="assets/fonts/PressStart2P-Regular.ttf",
        sidebar_font_scale=0.72,  # PressStart2P glyphs run ~1.4x wider than proportional fonts
    ),
    # Legacy aliases (preserved, untouched)
    "blue":      Theme("blue",      "#DEE3E6", "#8CA2AD"),
    "green":     Theme("green",     "#FFFFDD", "#86A666"),
    "dark_mode": Theme("dark_mode", "#4E4E4E", "#2C2C2C", "#1A1A1A"),
}


# ── Procedural, theme-aware arrow rendering ────────────────────────────────
# Arrows used to be baked into the chess.svg raster (chess.svg.Arrow). They're
# now drawn in PIL after the board is composited onto the frame canvas, so
# every theme can style them independently (classic vector / cyberpunk neon /
# cyberpunk neon) instead of sharing one SVG marker style.

_ARROW_BASE_COLORS = {
    ArrowType.BEST_MOVE:   (0, 190, 0),
    ArrowType.CANDIDATE_2: (0, 150, 70),
    ArrowType.CANDIDATE_3: (0, 120, 90),
    ArrowType.THREAT:      (225, 40, 40),
    ArrowType.DEFENSIVE:   (255, 215, 0),
}


def _draw_vector_arrow(draw, sx, sy, ex, ey, color, square_size,
                       width_ratio=0.2, head_ratio=0.75, margin_ratio=0.1):
    """Smooth solid-line arrow with a triangular head, proportioned exactly like
    python-chess's own chess.svg arrow markers (see chess/svg.py: marker_size =
    0.75*SQUARE_SIZE, marker_margin = 0.1*SQUARE_SIZE, shaft stroke-width =
    0.2*SQUARE_SIZE) — shaft width and head size scale with the board's square
    size instead of using fixed pixel widths, so arrows read as a bold, tapered
    shape (thick shaft narrowing into a wide arrowhead) rather than a thin line."""
    import math
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    if length < 1e-3:
        return
    ux, uy = dx / length, dy / length
    margin = margin_ratio * square_size
    head_len = head_ratio * square_size
    shaft_width = max(2, round(width_ratio * square_size))

    tip_x, tip_y = ex - ux * margin, ey - uy * margin
    shaft_x, shaft_y = ex - ux * (head_len + margin), ey - uy * (head_len + margin)

    draw.line([(sx, sy), (shaft_x, shaft_y)], fill=color, width=shaft_width)
    perp_x, perp_y = -uy, ux
    p1 = (tip_x, tip_y)
    p2 = (shaft_x + perp_x * head_len / 2, shaft_y + perp_y * head_len / 2)
    p3 = (shaft_x - perp_x * head_len / 2, shaft_y - perp_y * head_len / 2)
    draw.polygon([p1, p2, p3], fill=color)


def draw_themed_arrow(draw, start_pos, end_pos, arrow_type, theme, square_size):
    """Draw one board arrow styled for the active theme.

    - classic: smooth solid-color vector line + triangular head, in the exact
      shaft/head/margin proportions python-chess uses for its own SVG arrows.
    - cyberpunk: saturated neon line (cyan for best-move, magenta for
      threat/defend/candidates) with a thin white core for a glow effect.
    - retro: same smooth vector arrow as classic (board/pieces stay clear,
      only the color scheme and header font are retro).
    """
    sx, sy = start_pos
    ex, ey = end_pos
    base_color = _ARROW_BASE_COLORS.get(arrow_type, theme.accent)

    if theme.name == "cyberpunk":
        neon = theme.accent if arrow_type == ArrowType.BEST_MOVE else theme.text_highlight
        _draw_vector_arrow(draw, sx, sy, ex, ey, neon, square_size,
                           width_ratio=0.28, head_ratio=0.8)
        _draw_vector_arrow(draw, sx, sy, ex, ey, (255, 255, 255), square_size,
                           width_ratio=0.09, head_ratio=0.4)
        return

    _draw_vector_arrow(draw, sx, sy, ex, ey, base_color, square_size)


@dataclass
class RenderOptions:
    theme: Theme = field(default_factory=lambda: THEMES["classic"])
    output_dir: str = "output/frames"
    show_best_arrow: bool = False
    show_arrows: bool = True                # New: enable/disable all arrows
    arrow_intensity: str = "normal"         # New: "conservative", "normal", "aggressive"
    flipped: bool = False
    enable_transitions: bool = True         # slide-move animation between board states
    transition_frame_count: int = 12
    # Legend card: Claude-authored legend takes priority over the built-in rotation
    legend_name: Optional[str] = None
    legend_title: Optional[str] = None
    legend_fact: Optional[str] = None
    show_legend_card: bool = True
    legend_cadence_cycle: int = 12          # move-pair rows per full cycle
    legend_cadence_window: int = 4          # trailing rows of each cycle showing the card
    decorative_panel_path: Optional[str] = None   # override; else assets/sidebar/decorative_panel.png


class BoardRenderer:
    def __init__(self, opts: RenderOptions, render_workers: int = 0):
        self.opts = opts
        # 0 = auto: min(cpu_count, 8), matching the avatar_generator.py convention
        # but capped so it doesn't spawn absurd thread counts that just shift the
        # bottleneck onto disk I/O.
        self._render_workers = render_workers if render_workers else min(os.cpu_count() or 4, 8)
        os.makedirs(opts.output_dir, exist_ok=True)
        # Initialize arrow analyzer with smart mode and max arrows based on intensity
        max_arrows = {"conservative": 2, "normal": 4, "aggressive": 6}
        self.arrow_analyzer = ArrowAnalyzer(
            max_arrows_per_frame=max_arrows.get(opts.arrow_intensity, 4),
            smart_mode=True
        )
        # frame_idx -> ordered list of intermediate slide-transition frame paths
        self.transition_map: Dict[int, List[str]] = {}
        self._piece_sprite_cache: Dict[tuple, "object"] = {}
        self._legend_portrait_cache: Dict[tuple, "object"] = {}
        self._circle_mask_cache: Dict[int, "object"] = {}
        self._font_cache: Dict[str, object] = {}

    def render_game(self, game_pgn, analysis: list = [], game_id: str = "",
                    game_meta=None) -> List[str]:
        """Render each board position to PNG. Returns list of file paths.

        Frames are rendered concurrently (one worker task per move — a move's
        transition burst + landed frame share setup, so splitting finer would
        just recompute that setup redundantly). To make that safe, every piece
        of state that the old serial loop carried between iterations
        (`last_eval_cp`, `moves_accumulated`) is precomputed up front as plain
        arrays derived purely from `analysis` — each move's render becomes a
        pure function of its own index, touching no shared mutable state.
        """
        if isinstance(game_pgn, str):
            game = chess.pgn.read_game(io.StringIO(game_pgn))
        else:
            game = game_pgn

        if not game:
            logger.warning("No game to render — returning empty frame list")
            return []

        moves = list(game.mainline_moves())
        total = len(moves)

        # ── Precompute board snapshots (sequential, cheap — pure Python push/pop) ──
        board = game.board()
        boards_before, boards_after = [], []
        for move in moves:
            boards_before.append(board.copy())
            board.push(move)
            boards_after.append(board.copy())

        # ── Precompute the "moves_accumulated" / "last_eval_cp" scan up front ──
        # acc_pre[i] / eval_pre[i]: state *before* move i (what the old loop's
        # `moves_accumulated`/`last_eval_cp` held at the start of iteration i).
        # acc_post[i] / ana_at_frame[i]: state *after* move i is applied.
        acc_pre, eval_pre = [None] * total, [None] * total
        acc_post, ana_at_frame = [None] * total, [None] * total
        running_acc, running_eval = [], None
        for i in range(total):
            acc_pre[i] = running_acc
            eval_pre[i] = running_eval
            ana = analysis[i] if i < len(analysis) else None
            ana_at_frame[i] = ana
            if ana:
                running_acc = running_acc + [ana]
                running_eval = self._eval_cp_of(ana)
            acc_post[i] = running_acc

        initial_frame = self._save_frame(game.board(), game_id, 0,
                                         all_moves_so_far=[],
                                         current_move_idx=-1,
                                         game_meta=game_meta)

        def _render_one(i: int):
            move = moves[i]
            idx = i + 1
            transition_paths = []
            if self.opts.enable_transitions:
                try:
                    transition_paths = self._render_transition_frames(
                        boards_before[i], move, game_id, idx,
                        eval_cp=eval_pre[i],
                        moves_so_far=acc_pre[i],
                        current_move_idx=len(acc_pre[i]) - 1,
                        game_meta=game_meta)
                except Exception as e:
                    logger.debug(f"Transition frames skipped for move {idx}: {e}")
            path = self._save_frame(boards_after[i], game_id, idx,
                                    last_move=move,
                                    analysis_at_frame=ana_at_frame[i],
                                    all_moves_so_far=acc_post[i],
                                    current_move_idx=len(acc_post[i]) - 1,
                                    game_meta=game_meta)
            return i, transition_paths, path

        landed_paths = [None] * total
        if total > 0:
            with ThreadPoolExecutor(max_workers=min(self._render_workers, total)) as ex:
                futures = [ex.submit(_render_one, i) for i in range(total)]
                for fut in futures:
                    i, transition_paths, path = fut.result()
                    self.transition_map[i + 1] = transition_paths
                    landed_paths[i] = path

        frame_paths = [initial_frame] + landed_paths
        logger.info(f"Rendered {len(frame_paths)} frames → {self.opts.output_dir}")
        return frame_paths

    def render_position(self, fen: str):
        """Render a single FEN position. Returns PIL Image (board only, no sidebar)."""
        board = chess.Board(fen)
        return self._board_to_image(board)

    # ── private ────────────────────────────────────────────────────────────────

    def _save_frame(self, board, game_id, idx,
                    last_move=None, arrows=None,
                    analysis_at_frame=None,
                    all_moves_so_far=None,
                    current_move_idx=0,
                    game_meta=None) -> str:
        path = os.path.join(self.opts.output_dir, f"{game_id}_frame_{idx:04d}.png")

        # Generate arrows using analyzer if enabled
        if self.opts.show_arrows and arrows is None:
            arrows = self.arrow_analyzer.analyze_position(board, analysis_at_frame)

        board_img = self._board_to_image(board, last_move=last_move,
                                         size_override=_LAYOUT["BOARD_SIZE"])

        eval_cp = self._eval_cp_of(analysis_at_frame)
        coach = getattr(analysis_at_frame, 'coach', None)
        if coach is None:
            coach = self._fallback_coach(board, analysis_at_frame, eval_cp)
        frame = self._compose_frame(board_img, eval_cp, all_moves_so_far or [],
                                    current_move_idx, game_meta, board=board, coach=coach,
                                    arrows=arrows)
        frame.save(path)
        return path

    def _fallback_coach(self, board, analysis_at_frame, eval_cp):
        """Build a coach panel straight from Stockfish output when no LLM coach
        payload was attached. Without this the sidebar reads 'Analyzing...' on
        every frame whenever commentary was generated without a coach_insights
        block (e.g. --no-claude, or any LLM run that didn't emit one)."""
        top_moves = getattr(analysis_at_frame, "top_moves", None)
        if not top_moves:
            return None

        engine_moves = []
        for md in top_moves[:4]:
            uci = md.get("uci")
            san = uci or ""
            try:
                mv = chess.Move.from_uci(uci)
                if mv in board.legal_moves:
                    san = board.san(mv)
            except (ValueError, AttributeError):
                pass
            engine_moves.append({
                "san": san,
                "score_cp": md.get("score_cp", 0),
                "rank": md.get("rank", len(engine_moves) + 1),
                "label": "best" if md.get("rank", 0) == 1 else "",
            })

        insights = []
        if engine_moves:
            insights.append(f"Engine prefers <b>{engine_moves[0]['san']}</b> here.")
        if eval_cp is not None:
            side = "White" if eval_cp >= 0 else "Black"
            insights.append(f"{side} is better by <b>{abs(eval_cp)/100:.1f}</b> pawns.")

        return SimpleNamespace(top_engine_moves=engine_moves, insights=insights)

    def _eval_cp_of(self, analysis_at_frame):
        if analysis_at_frame and hasattr(analysis_at_frame, "eval_cp"):
            raw_cp = analysis_at_frame.eval_cp
            if raw_cp is not None:
                ply = getattr(analysis_at_frame, "ply", 1)
                # Stockfish score is side-to-move relative.
                # After White moves (even ply) → Black to move → negate for White's perspective.
                return raw_cp if ply % 2 == 1 else -raw_cp
        return None

    def _compose_frame(self, board_img, eval_cp, moves_so_far, current_move_idx, game_meta,
                       board=None, total_moves=None, coach=None, arrows=None):
        white = "White"
        black = "Black"
        opening = ""
        white_elo = black_elo = None
        if game_meta:
            white = getattr(game_meta, "white", "White") or "White"
            black = getattr(game_meta, "black", "Black") or "Black"
            opening = getattr(game_meta, "opening", "") or ""
            white_elo = getattr(game_meta, "white_elo", None)
            black_elo = getattr(game_meta, "black_elo", None)
            if total_moves is None:
                mv = getattr(game_meta, "moves", None)
                total_moves = len(mv) if mv else None

        # White to move after the start frame (idx -1) and after every Black move (odd idx).
        white_to_move = (current_move_idx % 2 != 0)
        w_caps, b_caps = self._material_captured(board) if board is not None else ("", "")
        card_info = dict(
            white_elo=white_elo, black_elo=black_elo,
            eval_cp=eval_cp, white_to_move=white_to_move,
            white_captured=w_caps, black_captured=b_caps,
        )

        eval_bar = self._render_eval_bar(eval_cp, _LAYOUT["EVAL_H"])
        sidebar = self._render_sidebar(white, black, opening,
                                       moves_so_far, current_move_idx,
                                       _LAYOUT["SIDEBAR_W"],
                                       _LAYOUT["FRAME_H"] - _LAYOUT["HEADER_H"], card_info,
                                       coach=coach)
        progress = None
        if total_moves:
            shown = min(max(current_move_idx + 1, 0), total_moves)
            progress = f"Move {shown} / {total_moves}"
        return self._compose_full_frame(board_img, eval_bar, sidebar, progress, arrows=arrows)

    @staticmethod
    def _material_captured(board):
        """Return (white_captured, black_captured) short labels of pieces each side has
        taken, derived from what's missing off the starting army."""
        start = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1}
        letters = {chess.QUEEN: "Q", chess.ROOK: "R", chess.BISHOP: "B",
                   chess.KNIGHT: "N", chess.PAWN: "P"}
        order = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]

        def taken_by(capturer_color, victim_color):
            parts = []
            for pt in order:
                missing = start[pt] - len(board.pieces(pt, victim_color))
                if missing > 0:
                    parts.append(letters[pt] * missing)
            return " ".join(parts)

        # White's captures = Black pieces missing; Black's captures = White pieces missing.
        return taken_by(chess.WHITE, chess.BLACK), taken_by(chess.BLACK, chess.WHITE)

    def _render_eval_bar(self, eval_cp, height: int):
        """Draw vertical eval bar. Returns EVAL_W×height PIL Image."""
        from PIL import Image, ImageDraw, ImageFont

        w = _LAYOUT["EVAL_W"]
        img = Image.new("RGB", (w, height), (20, 20, 20))
        draw = ImageDraw.Draw(img)

        if eval_cp is None:
            white_fraction = 0.5
            label = None
            is_mate = False
        else:
            abs_cp = abs(eval_cp)
            is_mate = abs_cp >= 29000
            clamped = max(-900, min(900, eval_cp))
            white_fraction = 0.5 + clamped / 1800.0
            if is_mate:
                white_fraction = 1.0 if eval_cp > 0 else 0.0
                mate_n = (30000 - abs_cp) // 100 if abs_cp < 30000 else 1
                label = f"M{mate_n}"
            else:
                abs_pawns = abs_cp / 100.0
                label = f"+{abs_pawns:.1f}" if eval_cp >= 0 else f"-{abs_pawns:.1f}"

        boundary = int(height * (1.0 - white_fraction))
        boundary = max(0, min(height, boundary))

        # Black section (top) — dark charcoal
        if boundary > 0:
            draw.rectangle([0, 0, w - 1, boundary - 1], fill=(22, 22, 28))

        # White section (bottom) — bright white
        if boundary < height:
            draw.rectangle([0, boundary, w - 1, height - 1], fill=(245, 245, 240))

        # Boundary accent line (3px, accent color)
        for dy in range(3):
            y = boundary - 1 + dy
            if 0 <= y < height:
                draw.line([(0, y), (w - 1, y)], fill=(100, 160, 255), width=1)

        # Eval label
        if label:
            try:
                font = ImageFont.load_default(size=20)
            except TypeError:
                font = ImageFont.load_default()
            text_color = (230, 230, 230) if eval_cp is not None and eval_cp < 0 else (30, 30, 30)
            label_y = boundary - 28 if (eval_cp or 0) >= 0 else boundary + 6
            label_y = max(2, min(height - 24, label_y))
            # center text in bar width
            draw.text((w // 2, label_y), label, fill=text_color, font=font, anchor="mt")

        return img

    def _load_font(self, path, size: int):
        """Load a PIL font, using cache. Falls back to default if path missing."""
        from PIL import ImageFont
        key = f"{path}:{size}"
        if key not in self._font_cache:
            try:
                if path and os.path.isfile(path):
                    self._font_cache[key] = ImageFont.truetype(path, size)
                else:
                    self._font_cache[key] = ImageFont.load_default(size=size)
            except Exception:
                try:
                    self._font_cache[key] = ImageFont.load_default(size=size)
                except TypeError:
                    self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _render_sidebar(self, white: str, black: str, opening: str,
                        moves_so_far: list, current_idx: int,
                        width: int, height: int, card_info: dict = None,
                        coach=None):
        """Compose sidebar: narrow move-history column + dynamic coach insights panel."""
        from PIL import Image

        img = Image.new("RGB", (width, height), _LAYOUT["BG"])

        show_legend, legend = self._resolve_legend_state(current_idx)
        narrow = self._render_narrow_sidebar(white, black, opening, moves_so_far, current_idx,
                                             show_legend, legend,
                                             _LAYOUT["NARROW_SIDEBAR_W"], height,
                                             card_info or {})
        decor = self._render_coach_panel(_LAYOUT["DECOR_PANEL_W"], height, coach)

        img.paste(narrow, (0, 0))
        img.paste(decor, (_LAYOUT["NARROW_SIDEBAR_W"] + _LAYOUT["SIDEBAR_GAP"], 0))
        return img

    def _resolve_legend_state(self, current_idx: int):
        """Decide whether this frame shows the legend card, and which legend to feature.

        Cadence windows at the *end* of each cycle so the opening moves (row 0, and the
        initial current_idx=-1 frame) always render as the move list first.
        """
        row   = max(current_idx, 0) // 2
        cycle = max(1, self.opts.legend_cadence_cycle)
        window = self.opts.legend_cadence_window
        show_legend = self.opts.show_legend_card and (row % cycle) >= (cycle - window)

        if self.opts.legend_name:
            legend = {
                "name": self.opts.legend_name,
                "title": self.opts.legend_title or "",
                "fact": self.opts.legend_fact or "",
            }
        else:
            legend = _CHESS_LEGENDS[(row // cycle) % len(_CHESS_LEGENDS)]

        return show_legend, legend

    def _render_narrow_sidebar(self, white: str, black: str, opening: str,
                               moves_so_far: list, current_idx: int,
                               show_legend: bool, legend: dict,
                               width: int, height: int, card_info: dict = None):
        """Narrow functional column: player panels + move list, occasionally a legend card.

        Card-based layout: each section is a rounded panel with a small margin, rather than
        full-bleed strips. Fonts are sized for legibility at 1920x1080 output scale.
        """
        from PIL import Image, ImageDraw

        t = self.opts.theme
        s = t.sidebar_font_scale
        ACCENT = t.accent
        BG     = t.panel_bg
        CARD   = (20, 20, 34)
        CARD_BORDER = (48, 48, 68)

        img  = Image.new("RGB", (width, height), BG)
        draw = ImageDraw.Draw(img)

        font_name = self._load_font(t.font_bold,    round(38 * s))  # player names
        font_tag  = self._load_font(t.font_regular, round(24 * s))  # BLACK/WHITE tag, opening text
        font_hdr  = self._load_font(t.font_regular, round(24 * s))  # table/arrow-key headers
        font_move = self._load_font(t.font_regular, round(32 * s))  # move list SAN text

        PAD = 10
        x0, x1 = PAD, width - PAD
        GAP = 12

        # ── Section boundaries (bottom-up so the move-list body absorbs slack) ─
        BLK_H   = 96
        WHT_H   = 96
        OPEN_H  = 48
        ARROW_H = 60 if self.opts.show_arrows else 0

        BLK_Y0 = 8
        BLK_Y1 = BLK_Y0 + BLK_H

        WHT_Y1 = height - 8
        WHT_Y0 = WHT_Y1 - WHT_H

        OPEN_Y1 = WHT_Y0 - GAP
        OPEN_Y0 = OPEN_Y1 - OPEN_H

        if self.opts.show_arrows:
            ARROW_Y1 = OPEN_Y0 - GAP
            ARROW_Y0 = ARROW_Y1 - ARROW_H
            BODY_Y1  = ARROW_Y0 - GAP
        else:
            BODY_Y1  = OPEN_Y0 - GAP

        BODY_Y0 = BLK_Y1 + GAP

        # ── Black player card ────────────────────────────────────────────────
        ci = card_info or {}
        draw.rounded_rectangle([x0, BLK_Y0, x1, BLK_Y1], radius=14, fill=CARD, outline=CARD_BORDER, width=1)
        av = 64
        draw.ellipse([x0 + 14, BLK_Y0 + (BLK_H - av) // 2, x0 + 14 + av, BLK_Y0 + (BLK_H - av) // 2 + av],
                     fill=(60, 60, 84))
        b_name = black + (f"  {ci['black_elo']}" if ci.get("black_elo") else "")
        draw.text((x0 + 92, BLK_Y0 + 18), b_name, fill=(235, 235, 240), font=font_name)
        b_sub = "BLACK"
        if ci.get("black_captured"):
            b_sub += "   captured: " + ci["black_captured"]
        draw.text((x0 + 92, BLK_Y0 + 60), b_sub, fill=(150, 150, 172), font=font_tag)
        self._draw_card_status(draw, ci, black_side=True, x1=x1,
                               y0=BLK_Y0, card_h=BLK_H, font_name=font_name, font_tag=font_tag)

        # ── Body: move list, or occasional legend card ─────────────────────
        if show_legend:
            self._render_legend_card_body(draw, img, legend, BODY_Y0, BODY_Y1, width, x0, x1,
                                          CARD, CARD_BORDER)
        else:
            self._render_move_list_body(draw, moves_so_far, current_idx, BODY_Y0, BODY_Y1,
                                        x0, x1, font_hdr, font_move, ACCENT, CARD, CARD_BORDER)

        # ── Opening pill ────────────────────────────────────────────────────
        draw.rounded_rectangle([x0, OPEN_Y0, x1, OPEN_Y1], radius=12, fill=(28, 22, 10),
                               outline=(70, 52, 18), width=1)
        if opening:
            opening_text = opening[:56] + "..." if len(opening) > 56 else opening
            draw.text(((x0 + x1) // 2, (OPEN_Y0 + OPEN_Y1) // 2), opening_text,
                      fill=ACCENT, font=font_tag, anchor="mm")

        # ── Arrow legend card (if arrows are enabled) ───────────────────────
        if self.opts.show_arrows:
            draw.rounded_rectangle([x0, ARROW_Y0, x1, ARROW_Y1], radius=12, fill=CARD,
                                   outline=CARD_BORDER, width=1)
            sx = x0 + 14
            my = ARROW_Y0 + 30   # shared vertical midline for header, swatches, labels
            draw.text((sx, my), "ARROW KEY:", fill=(140, 140, 160), font=font_hdr, anchor="lm")
            sx += draw.textlength("ARROW KEY:", font=font_hdr) + 16
            for label, color in (("Best", (0, 190, 0)), ("Threat", (225, 40, 40)), ("Defend", (255, 215, 0))):
                draw.rounded_rectangle([sx, my - 7, sx + 14, my + 7], radius=3, fill=color)
                draw.text((sx + 20, my), label, fill=(180, 180, 195), font=font_tag, anchor="lm")
                sx += 20 + draw.textlength(label, font=font_tag) + 18

        # ── White player card ────────────────────────────────────────────────
        draw.rounded_rectangle([x0, WHT_Y0, x1, WHT_Y1], radius=14, fill=CARD, outline=CARD_BORDER, width=1)
        draw.ellipse([x0 + 14, WHT_Y0 + (WHT_H - av) // 2, x0 + 14 + av, WHT_Y0 + (WHT_H - av) // 2 + av],
                     fill=(210, 205, 180))
        w_name = white + (f"  {ci['white_elo']}" if ci.get("white_elo") else "")
        draw.text((x0 + 92, WHT_Y0 + 18), w_name, fill=(235, 235, 240), font=font_name)
        w_sub = "WHITE"
        if ci.get("white_captured"):
            w_sub += "   captured: " + ci["white_captured"]
        draw.text((x0 + 92, WHT_Y0 + 60), w_sub, fill=(150, 150, 172), font=font_tag)
        self._draw_card_status(draw, ci, black_side=False, x1=x1,
                               y0=WHT_Y0, card_h=WHT_H, font_name=font_name, font_tag=font_tag)

        return img

    @staticmethod
    def _draw_card_status(draw, ci, black_side, x1, y0, card_h, font_name, font_tag):
        """On the side-to-move card, draw the current eval (green/red by that side's
        perspective) and a 'to move · thinking' tag on the right edge."""
        if not ci:
            return
        is_active = (ci.get("white_to_move") is False) if black_side else bool(ci.get("white_to_move"))
        if not is_active:
            return
        eval_cp = ci.get("eval_cp")
        rx = x1 - 16
        if eval_cp is not None:
            persp = -eval_cp if black_side else eval_cp  # + means this side is better
            abs_cp = abs(eval_cp)
            if abs_cp >= 29000:
                mate_n = (30000 - abs_cp) // 100 if abs_cp < 30000 else 1
                label = f"M{mate_n}"
            else:
                p = abs_cp / 100.0
                label = f"+{p:.1f}" if persp >= 0 else f"-{p:.1f}"
            color = (127, 216, 143) if persp >= 0 else (224, 96, 96)
            draw.text((rx, y0 + 18), label, fill=color, font=font_name, anchor="ra")
        draw.text((rx, y0 + card_h - 32), "to move · thinking",
                  fill=(138, 147, 166), font=font_tag, anchor="ra")

    def _render_move_list_body(self, draw, moves_so_far: list, current_idx: int,
                               y0: int, y1: int, x0: int, x1: int,
                               font_hdr, font_move, ACCENT, CARD, CARD_BORDER):
        """Draw the move-history table into the body region (y0-y1) as a rounded card."""
        draw.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=CARD, outline=CARD_BORDER, width=1)
        ROW_H   = 54
        HDR_H   = 42
        COL_NUM = x0 + 18
        COL_W   = x0 + 70
        COL_B   = x0 + (x1 - x0) // 2 + 20

        draw.text((COL_NUM, y0 + 12), "#",     fill=(110, 110, 135), font=font_hdr)
        draw.text((COL_W,   y0 + 12), "WHITE", fill=(110, 110, 135), font=font_hdr)
        draw.text((COL_B,   y0 + 12), "BLACK", fill=(110, 110, 135), font=font_hdr)
        draw.line([(x0 + 10, y0 + HDR_H), (x1 - 10, y0 + HDR_H)], fill=CARD_BORDER, width=1)

        row_start_y = y0 + HDR_H + 6
        visible     = max(0, (y1 - 8 - row_start_y) // ROW_H)

        rows = []
        ri = 0
        while ri < len(moves_so_far):
            ma_w  = moves_so_far[ri]
            w_san = getattr(ma_w, "move_san", "?")
            w_cls = getattr(ma_w, "classification", "normal") or "normal"
            w_icon  = _MOVE_ICONS.get(w_cls, "")
            w_label = f"{w_icon} {w_san}".strip() if w_icon else w_san
            move_num = (getattr(ma_w, "ply", ri) // 2) + 1
            b_label, b_cls = "", "normal"
            if ri + 1 < len(moves_so_far):
                ma_b  = moves_so_far[ri + 1]
                b_san = getattr(ma_b, "move_san", "?")
                b_cls = getattr(ma_b, "classification", "normal") or "normal"
                b_icon  = _MOVE_ICONS.get(b_cls, "")
                b_label = f"{b_icon} {b_san}".strip() if b_icon else b_san
            rows.append((move_num, w_label, w_cls, b_label, b_cls))
            ri += 2

        current_row = current_idx // 2 if current_idx >= 0 else -1
        scroll      = max(0, current_row - visible // 2)

        for r_idx in range(visible):
            row_num = scroll + r_idx
            if row_num >= len(rows):
                break
            ry = row_start_y + r_idx * ROW_H
            move_num, w_label, w_cls, b_label, b_cls = rows[row_num]

            if row_num % 2 == 1:
                draw.rectangle([x0 + 4, ry, x1 - 4, ry + ROW_H - 4], fill=(24, 24, 40))
            if row_num == current_row:
                draw.rounded_rectangle([x0 + 4, ry, x1 - 4, ry + ROW_H - 4], radius=8, fill=(46, 34, 8))
                draw.rounded_rectangle([x0 + 4, ry, x0 + 9, ry + ROW_H - 4], radius=3, fill=ACCENT)

            draw.text((COL_NUM, ry + 13), f"{move_num}.", fill=(110, 110, 140), font=font_hdr)

            w_color = _MOVE_COLORS.get(w_cls, (210, 210, 220))
            if current_idx >= 0 and (current_idx // 2) == row_num and current_idx % 2 == 0:
                w_color = ACCENT
            draw.text((COL_W, ry + 11), w_label, fill=w_color, font=font_move)

            if b_label:
                b_color = _MOVE_COLORS.get(b_cls, (210, 210, 220))
                if current_idx >= 0 and (current_idx // 2) == row_num and current_idx % 2 == 1:
                    b_color = ACCENT
                draw.text((COL_B, ry + 11), b_label, fill=b_color, font=font_move)

    def _render_legend_card_body(self, draw, img, legend: dict, y0: int, y1: int, width: int,
                                 x0: int, x1: int, CARD, CARD_BORDER):
        """Draw an enlarged legend portrait/name/title/fact card into the body region (y0-y1)."""
        ACCENT = _LAYOUT["ACCENT"]
        t = self.opts.theme
        s = t.sidebar_font_scale
        font_hdr   = self._load_font(t.font_bold, round(18 * s))
        font_name  = self._load_font(t.font_bold, round(26 * s))
        font_title = self._load_font(t.font_regular, round(18 * s))
        font_fact  = self._load_font(t.font_regular, round(15 * s))

        draw.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=CARD, outline=CARD_BORDER, width=1)
        draw.rounded_rectangle([x0, y0, x1, y0 + 40], radius=14, fill=(28, 20, 6))
        draw.rectangle([x0, y0 + 26, x1, y0 + 40], fill=(28, 20, 6))
        draw.text((x0 + 16, y0 + 10), "CHESS LEGEND", fill=ACCENT, font=font_hdr)

        inner_w = x1 - x0
        portrait_size = min(220, inner_w - 60, (y1 - y0) - 230)
        portrait_size = max(80, portrait_size)
        px0 = x0 + (inner_w - portrait_size) // 2
        py0 = y0 + 60
        portrait = self._load_legend_portrait(legend.get("name", ""), portrait_size)
        if portrait is not None:
            mask = self._circle_mask(portrait_size)
            img.paste(portrait, (px0, py0), mask)
        else:
            cx, cy = x0 + inner_w // 2, py0 + portrait_size // 2
            r = portrait_size // 2
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 24, 8))
            draw.ellipse([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8],
                        outline=ACCENT, width=3)
            initial = (legend.get("name") or "?")[:1].upper()
            draw.text((cx, cy), initial, fill=ACCENT, font=font_name, anchor="mm")

        cx = x0 + inner_w // 2
        text_y = py0 + portrait_size + 20
        draw.text((cx, text_y), legend.get("name", ""), fill=(238, 238, 240),
                  font=font_name, anchor="mt")
        draw.text((cx, text_y + 32), legend.get("title", ""), fill=ACCENT,
                  font=font_title, anchor="mt")

        fact = legend.get("fact", "")
        words, lines, cur = fact.split(), [], ""
        for word in words:
            test = (cur + " " + word).strip()
            if len(test) <= 46:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        fact_y = text_y + 70
        max_lines = max(0, (y1 - 10 - fact_y) // 22)
        for li, fline in enumerate(lines[:max_lines]):
            draw.text((cx, fact_y + li * 22), fline, fill=(190, 190, 205),
                      font=font_fact, anchor="mt")

    def _circle_mask(self, size: int):
        """Cached circular alpha mask for pasting a square portrait as a circle."""
        if size in self._circle_mask_cache:
            return self._circle_mask_cache[size]
        from PIL import Image, ImageDraw
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
        self._circle_mask_cache[size] = mask
        return mask

    def _cover_fit(self, image, target_w: int, target_h: int):
        """Resize+center-crop an image to exactly (target_w, target_h), preserving aspect."""
        from PIL import Image as PILImage
        src_w, src_h = image.size
        scale = max(target_w / src_w, target_h / src_h)
        new_w, new_h = max(1, round(src_w * scale)), max(1, round(src_h * scale))
        resized = image.resize((new_w, new_h), PILImage.LANCZOS)
        left = (new_w - target_w) // 2
        top  = (new_h - target_h) // 2
        return resized.crop((left, top, left + target_w, top + target_h))

    def _load_legend_portrait(self, name: str, size: int):
        """Load+cache a legend portrait PNG asset resized to size×size. None if missing."""
        from PIL import Image

        slug = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")
        if not slug:
            return None
        cache_key = (slug, size)
        if cache_key in self._legend_portrait_cache:
            return self._legend_portrait_cache[cache_key]

        path = os.path.join(_ASSETS_DIR, "legends", f"{slug}.png")
        portrait = None
        if os.path.isfile(path):
            try:
                portrait = self._cover_fit(Image.open(path).convert("RGB"), size, size)
            except Exception as e:
                logger.debug(f"Failed to load legend portrait {path}: {e}")
                portrait = None

        self._legend_portrait_cache[cache_key] = portrait
        return portrait

    def _fit_font(self, path, base_size: int, text: str, draw, max_width: int, floor: int = 8):
        """Shrink font size until `text` fits max_width. Wide monospace fonts (PressStart2P)
        need this for section headers that don't wrap — headers are single draw.text() calls,
        not run through the bullet word-wrapper."""
        size = base_size
        font = self._load_font(path, size)
        while size > floor and draw.textlength(text, font=font) > max_width:
            size -= 1
            font = self._load_font(path, size)
        return font

    def _render_coach_panel(self, width: int, height: int, coach=None):
        """Dynamic per-frame coach insights panel."""
        from PIL import Image, ImageDraw
        t = self.opts.theme
        img = Image.new("RGB", (width, height), t.panel_bg)
        draw = ImageDraw.Draw(img)

        # Left accent stripe
        draw.rectangle([0, 0, 4, height - 1], fill=t.accent)

        s = t.sidebar_font_scale
        f_header = self._load_font(t.font_display, round(22 * s))
        f_body   = self._load_font(t.font_regular, round(14 * s))
        f_bold   = self._load_font(t.font_bold, round(14 * s))
        f_sm     = self._load_font(t.font_regular, round(11 * s))

        y = 10
        draw.text((width // 2, y), "ChessCode", fill=t.text_primary,
                  font=f_header, anchor="mt")
        y += 32
        draw.text((width // 2, y), "Analysis & Commentary", fill=t.text_secondary,
                  font=f_sm, anchor="mt")
        y += 20
        draw.line([(8, y), (width - 8, y)], fill=t.panel_border, width=1)
        y += 12

        if coach is None:
            draw.text((width // 2, height // 2), "Analyzing...", fill=t.text_secondary,
                      font=f_body, anchor="mm")
            self._render_coach_footer(draw, width, height, f_sm, t)
            return img

        # ── Candidate Move Breakdown ────────────────────────────────────────
        hdr1 = "Candidate Move Breakdown"
        draw.text((10, y), hdr1, fill=t.text_primary,
                  font=self._fit_font(t.font_bold, round(18 * s), hdr1, draw, width - 20),
                  anchor="lt")
        y += 24
        draw.text((10, y), "Engine Evaluations (Stockfish)", fill=t.text_secondary,
                  font=f_sm, anchor="lt")
        y += 20
        for move_data in (coach.top_engine_moves or [])[:4]:
            san   = self._clean_llm_text(move_data.get("san", ""))
            cp    = move_data.get("score_cp", 0)
            rank  = move_data.get("rank", 1)
            label = self._clean_llm_text(move_data.get("label", ""))
            try:
                score_str = f"+{cp/100:.2f}" if cp >= 0 else f"{cp/100:.2f}"
            except (TypeError, ValueError):
                score_str = "?"
            bullet = f"• {san}  {score_str}" + (f"  ({label})" if label else "")
            san_color = t.accent if rank == 1 else t.text_primary
            draw.text((14, y), bullet, fill=san_color, font=f_body, anchor="lt")
            y += 20
        y += 8
        draw.line([(8, y), (width - 8, y)], fill=t.panel_border, width=1)
        y += 12

        # ── Coach's Tactical Insights ──────────────────────────────────────
        hdr2 = "Coach's Tactical Insights"
        draw.text((10, y), hdr2, fill=t.text_primary,
                  font=self._fit_font(t.font_bold, round(18 * s), hdr2, draw, width - 20),
                  anchor="lt")
        y += 26
        for insight_text in (coach.insights or [])[:3]:
            draw.text((10, y), "•", fill=t.accent, font=f_bold, anchor="lt")
            y = self._draw_inline_html(
                draw, insight_text,
                x=22, y=y,
                font_regular=f_body, font_bold=f_bold,
                color_regular=t.text_primary, color_highlight=t.text_highlight,
                max_width=width - 28, line_height=18,
            )
            y += 6

        self._render_coach_footer(draw, width, height, f_sm, t)
        return img

    _ORPHAN_CHARS_RE = re.compile(r"^['`*]+|['`*]+$")
    _STRAY_TAG_RE = re.compile(r'</?[bi]>', re.IGNORECASE)

    def _clean_llm_text(self, s: str) -> str:
        """Strip orphaned leading/trailing quote/backtick/asterisk artifacts left
        behind when the LLM's text parser splits or truncates a string."""
        return self._ORPHAN_CHARS_RE.sub('', s.strip())

    def _draw_inline_html(self, draw, text: str, x: int, y: int,
                          font_regular, font_bold,
                          color_regular, color_highlight,
                          max_width: int, line_height: int = 18) -> int:
        """Draw text with <b>tag</b>/<i>tag</i> inline HTML. Returns final y position.

        <i> has no italic font variant available (theme fonts only ship regular/bold),
        so italic spans are rendered in the regular style with tags stripped rather
        than printed literally. Any stray/unmatched <b>/<i> markup left in a plain
        chunk is stripped defensively so raw tags never reach the frame.
        """
        text = self._clean_llm_text(text)
        chunks = re.split(r'(<b>.*?</b>|<i>.*?</i>)', text)
        cx = x
        for chunk in chunks:
            if not chunk:
                continue
            if chunk.startswith('<b>') and chunk.endswith('</b>'):
                word = chunk[3:-4]
                font, color = font_bold, color_highlight
            elif chunk.startswith('<i>') and chunk.endswith('</i>'):
                word = chunk[3:-4]
                font, color = font_regular, color_regular
            else:
                word = self._STRAY_TAG_RE.sub('', chunk)
                font, color = font_regular, color_regular
            for token in word.split(' '):
                token = self._clean_llm_text(token)
                if not token:
                    continue
                try:
                    tw = draw.textlength(token + ' ', font=font)
                except Exception:
                    tw = len(token) * 8
                if cx + tw > x + max_width and cx > x:
                    y += line_height
                    cx = x
                draw.text((cx, y), token + ' ', fill=color, font=font, anchor="lt")
                cx += tw
        return y + line_height

    def _render_coach_footer(self, draw, width: int, height: int, font, theme):
        """Render the like/subscribe CTA footer in the coach panel."""
        footer_y = height - 80
        draw.line([(8, footer_y), (width - 8, footer_y)], fill=theme.panel_border, width=1)
        draw.text((width // 2, footer_y + 20), "Enjoying the analysis?",
                  fill=theme.text_secondary, font=font, anchor="mt")
        like_box = [10, footer_y + 38, width // 2 - 5, footer_y + 62]
        try:
            draw.rounded_rectangle(like_box, radius=4, fill=theme.accent)
        except AttributeError:
            draw.rectangle(like_box, fill=theme.accent)
        draw.text(((like_box[0] + like_box[2]) // 2, (like_box[1] + like_box[3]) // 2),
                  "Like", fill=theme.panel_bg, font=font, anchor="mm")
        sub_box = [width // 2 + 5, footer_y + 38, width - 10, footer_y + 62]
        try:
            draw.rounded_rectangle(sub_box, radius=4, outline=theme.accent, width=1)
        except AttributeError:
            draw.rectangle(sub_box, outline=theme.accent)
        draw.text(((sub_box[0] + sub_box[2]) // 2, (sub_box[1] + sub_box[3]) // 2),
                  "Subscribe", fill=theme.accent, font=font, anchor="mm")

    def _draw_pawn_icon(self, draw, cx: float, cy: float, scale: float, fill, cutout_fill):
        """Geometric pawn icon (head/cutout/stem/base), scale=1.0 matches the original header size."""
        d = lambda v: v * scale
        draw.ellipse([cx - d(18), cy - d(24), cx + d(18), cy + d(12)], fill=fill)
        draw.ellipse([cx - d(13), cy - d(19), cx + d(13), cy + d(7)],  fill=cutout_fill)
        draw.rectangle([cx - d(7), cy + d(10), cx + d(7), cy + d(24)], fill=fill)
        draw.rectangle([cx - d(18), cy + d(22), cx + d(18), cy + d(30)], fill=fill)

    def _compose_full_frame(self, board_img, eval_bar, sidebar, progress=None, arrows=None):
        """Composite header + eval bar + board + sidebar into 1920×1080 frame."""
        from PIL import Image, ImageDraw

        canvas = Image.new("RGB",
                           (_LAYOUT["FRAME_W"], _LAYOUT["FRAME_H"]),
                           _LAYOUT["BG"])

        board_size = _LAYOUT["BOARD_SIZE"]
        if board_img.size != (board_size, board_size):
            board_img = board_img.resize((board_size, board_size), Image.LANCZOS)

        canvas.paste(eval_bar, (_LAYOUT["EVAL_X"], _LAYOUT["EVAL_Y"]))
        canvas.paste(board_img, (_LAYOUT["BOARD_X"], _LAYOUT["BOARD_Y"]))
        canvas.paste(sidebar, (_LAYOUT["SIDEBAR_X"], _LAYOUT["HEADER_H"]))

        # Separator line between board area and sidebar (below the header)
        draw = ImageDraw.Draw(canvas)
        sx = _LAYOUT["SIDEBAR_X"] - 1
        draw.line([(sx, _LAYOUT["HEADER_H"]), (sx, _LAYOUT["FRAME_H"] - 1)], fill=(60, 60, 80), width=1)

        if arrows:
            theme = self.opts.theme
            for arr in arrows if isinstance(arrows, list) else [arrows]:
                if not isinstance(arr, ChessArrow):
                    continue
                sx_px, sy_px, sq_px = self._square_center_px(arr.from_square, board_size)
                ex_px, ey_px, _ = self._square_center_px(arr.to_square, board_size)
                start = (_LAYOUT["BOARD_X"] + sx_px, _LAYOUT["BOARD_Y"] + sy_px)
                end = (_LAYOUT["BOARD_X"] + ex_px, _LAYOUT["BOARD_Y"] + ey_px)
                draw_themed_arrow(draw, start, end, arr.arrow_type, theme, sq_px)

        self._render_header(canvas, progress)
        return canvas

    def _render_header(self, canvas, progress=None):
        """Top bar: channel name (gold, left), tagline (center), move progress (right)."""
        from PIL import ImageDraw
        try:
            from config import cfg as _cfg
            channel = (_cfg.channel_name or "ChessCode")
        except Exception:
            channel = "ChessCode"

        t = self.opts.theme
        s = t.sidebar_font_scale
        W, H = _LAYOUT["FRAME_W"], _LAYOUT["HEADER_H"]
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, W - 1, H - 1], fill=t.panel_bg)
        font_brand = self._load_font(t.font_display, round(40 * s))
        font_tag   = self._load_font(t.font_regular, round(30 * s))
        font_prog  = self._load_font(t.font_regular, round(28 * s))

        cy = H // 2
        draw.text((28, cy), channel.upper(), fill=t.accent, font=font_brand, anchor="lm")
        draw.text((W // 2, cy), _CHANNEL_TAGLINE, fill=t.text_primary, font=font_tag, anchor="mm")
        if progress:
            draw.text((W - 28, cy), progress, fill=t.text_secondary, font=font_prog, anchor="rm")

    def _board_to_image(self, board, last_move=None, size_override=None):
        """Rasterize the board (no arrows — those are drawn in PIL after
        compositing, see draw_themed_arrow). Cyberpunk pieces are composited
        per-square so a per-piece outline can be applied to black pieces."""
        from PIL import Image
        from cache_utils import cache_key, get_cached, put_cached
        from config import cfg

        theme = self.opts.theme
        size = size_override if size_override is not None else theme.board_size
        colors = theme.svg_colors()

        key = cache_key(_BOARD_CACHE_VERSION, board.fen(), str(last_move), theme.name,
                        theme.light_sq, theme.dark_sq,
                        str(size), str(self.opts.flipped))
        cached = get_cached(cfg.frame_cache_dir, key, ".png")
        if cached:
            return Image.open(cached)

        try:
            import cairosvg

            if theme.name in ("cyberpunk", "retro"):
                # Per-piece sprite compositing: board/squares stay full-res, only
                # the piece layer is styled. A whole-board downsample (old retro
                # approach) blurred pieces into unrecognizable blobs — pixelating
                # just the sprite keeps the silhouette readable.
                piece_board = board.copy()
                piece_map = piece_board.piece_map()
                for sq in piece_map:
                    piece_board.remove_piece_at(sq)
                svg_str = chess.svg.board(board=piece_board, size=size, colors=colors,
                                          lastmove=last_move, flipped=self.opts.flipped)
                png_data = cairosvg.svg2png(bytestring=svg_str.encode(),
                                            output_width=size, output_height=size)
                img = Image.open(io.BytesIO(png_data)).convert("RGBA")
                for square, piece in piece_map.items():
                    cx, cy, sq_px = self._square_center_px(square, size)
                    sprite = self._get_piece_sprite(piece, int(round(sq_px)))
                    if theme.name == "cyberpunk" and piece.color == chess.BLACK:
                        sprite = self._apply_piece_outline(sprite, theme.text_highlight)
                    paste_x, paste_y = int(round(cx - sq_px / 2)), int(round(cy - sq_px / 2))
                    img.alpha_composite(sprite, (paste_x, paste_y))
            else:
                svg_str = chess.svg.board(board=board, size=size, colors=colors,
                                          lastmove=last_move, flipped=self.opts.flipped)
                png_data = cairosvg.svg2png(bytestring=svg_str.encode(),
                                            output_width=size, output_height=size)
                img = Image.open(io.BytesIO(png_data))
        except ImportError:
            img = self._pil_fallback(board, size)

        try:
            # uuid-suffixed so concurrent renders of the same position (common —
            # repeated positions across transition sub-frames) never collide on
            # the same temp filename.
            tmp_path = os.path.join(tempfile.gettempdir(), f"_boardcache_{key}_{uuid.uuid4().hex}.png")
            img.save(tmp_path)
            put_cached(cfg.frame_cache_dir, key, ".png", tmp_path)
            os.unlink(tmp_path)
        except Exception as e:
            logger.debug(f"Board frame cache write skipped: {e}")

        return img

    # ── move-transition (slide) frames ──────────────────────────────────────────

    # chess.svg.board() layout constants (default coordinates=True): 8 squares of
    # SQUARE_SIZE units plus a MARGIN on each side for the a-h/1-8 labels.
    _SVG_SQUARE_UNITS = 45
    _SVG_MARGIN_UNITS = 20

    def _square_center_px(self, square: int, size: int) -> "tuple":
        """Pixel center of `square` in a size×size board image rendered the same
        way as _board_to_image() (same orientation/coordinates as chess.svg.board)."""
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        viewbox = 8 * self._SVG_SQUARE_UNITS + 2 * self._SVG_MARGIN_UNITS
        scale = size / viewbox
        sq_px = self._SVG_SQUARE_UNITS * scale
        margin_px = self._SVG_MARGIN_UNITS * scale
        if self.opts.flipped:
            col = 7 - file
            row = rank
        else:
            col = file
            row = 7 - rank
        x = margin_px + (col + 0.5) * sq_px
        y = margin_px + (row + 0.5) * sq_px
        return x, y, sq_px

    def _get_piece_sprite(self, piece: "chess.Piece", sq_px: int):
        """Rasterize a single piece to a transparent sq_px×sq_px PNG, cached."""
        from PIL import Image
        key = (piece.piece_type, piece.color, sq_px)
        cached = self._piece_sprite_cache.get(key)
        if cached is not None:
            return cached
        import cairosvg
        svg_str = chess.svg.piece(piece, size=sq_px)
        png_data = cairosvg.svg2png(bytestring=svg_str.encode(),
                                    output_width=sq_px, output_height=sq_px)
        img = Image.open(io.BytesIO(png_data)).convert("RGBA")
        self._piece_sprite_cache[key] = img
        return img

    def _apply_piece_outline(self, sprite, color, dilate: int = 2):
        """Return a copy of `sprite` (RGBA) with an N-pixel outer stroke of `color`
        behind it, built by dilating the sprite's own alpha channel. Used for the
        cyberpunk theme's magenta glow around black pieces for board contrast."""
        from PIL import Image, ImageFilter
        alpha = sprite.split()[-1]
        dilated = alpha.filter(ImageFilter.MaxFilter(2 * dilate + 1))
        glow = Image.new("RGBA", sprite.size, tuple(color) + (255,))
        glow.putalpha(dilated)
        out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
        out.alpha_composite(glow)
        out.alpha_composite(sprite)
        return out

    def _render_transition_frames(self, board_before: "chess.Board", move: "chess.Move",
                                  game_id: str, idx: int,
                                  eval_cp=None, moves_so_far=None,
                                  current_move_idx=-1, game_meta=None) -> List[str]:
        """Render a short burst of intermediate frames sliding the moved piece(s)
        from source to destination square. Returns ordered list of PNG paths.
        Sidebar/eval-bar reuse the pre-move state — they catch up once the piece
        lands, matching how broadcast overlays update on move completion."""
        n = max(0, self.opts.transition_frame_count)
        if n == 0:
            return []

        mover = board_before.piece_at(move.from_square)
        if mover is None:
            return []

        movers = [(mover, move.from_square, move.to_square)]

        is_castling = board_before.is_castling(move)
        if is_castling:
            rank = chess.square_rank(move.from_square)
            if board_before.is_kingside_castling(move):
                rook_from = chess.square(7, rank)
                rook_to = chess.square(5, rank)
            else:
                rook_from = chess.square(0, rank)
                rook_to = chess.square(3, rank)
            rook = board_before.piece_at(rook_from)
            if rook is not None:
                movers.append((rook, rook_from, rook_to))

        is_en_passant = board_before.is_en_passant(move)
        ep_capture_sq = None
        if is_en_passant:
            ep_capture_sq = chess.square(chess.square_file(move.to_square),
                                         chess.square_rank(move.from_square))

        # Background board: remove every mover from its source square, and clear
        # whatever's being captured, so it isn't double-drawn under the sprite.
        bg_board = board_before.copy()
        for _, from_sq, _ in movers:
            bg_board.remove_piece_at(from_sq)
        if ep_capture_sq is not None:
            bg_board.remove_piece_at(ep_capture_sq)
        else:
            bg_board.remove_piece_at(move.to_square)

        size = _LAYOUT["BOARD_SIZE"]
        bg_img = self._board_to_image(bg_board, size_override=size)
        if bg_img.mode != "RGBA":
            bg_img = bg_img.convert("RGBA")

        sprite_specs = []
        for piece, from_sq, to_sq in movers:
            sx, sy, sq_px = self._square_center_px(from_sq, size)
            dx, dy, _ = self._square_center_px(to_sq, size)
            sprite = self._get_piece_sprite(piece, int(round(sq_px)))
            if self.opts.theme.name == "cyberpunk" and piece.color == chess.BLACK:
                sprite = self._apply_piece_outline(sprite, self.opts.theme.text_highlight)
            sprite_specs.append((sprite, sx, sy, dx, dy, sq_px))

        paths = []
        for t in range(1, n + 1):
            p_raw = t / n
            p = p_raw * p_raw * (3 - 2 * p_raw)  # smoothstep ease-in-out
            board_frame = bg_img.copy()
            for sprite, sx, sy, dx, dy, sq_px in sprite_specs:
                cx = sx + (dx - sx) * p
                cy = sy + (dy - sy) * p
                paste_x = int(round(cx - sq_px / 2))
                paste_y = int(round(cy - sq_px / 2))
                board_frame.alpha_composite(sprite, (paste_x, paste_y))
            full_frame = self._compose_frame(board_frame.convert("RGB"), eval_cp,
                                             moves_so_far or [], current_move_idx,
                                             game_meta, board=board_before)
            out_path = os.path.join(self.opts.output_dir,
                                    f"{game_id}_frame_{idx:04d}_t{t:02d}.png")
            full_frame.save(out_path)
            paths.append(out_path)

        return paths

    def _pil_fallback(self, board, size: int):
        """Simple PIL board when cairosvg is unavailable."""
        from PIL import Image, ImageDraw

        sq = size // 8
        img = Image.new("RGB", (size, size), (44, 44, 44))
        draw = ImageDraw.Draw(img)

        light_rgb = _hex_to_rgb(self.opts.theme.light_sq)
        dark_rgb  = _hex_to_rgb(self.opts.theme.dark_sq)

        piece_chars = {
            chess.PAWN: "P", chess.KNIGHT: "N", chess.BISHOP: "B",
            chess.ROOK: "R", chess.QUEEN: "Q", chess.KING: "K",
        }

        for rank in range(8):
            for file in range(8):
                x0, y0 = file * sq, (7 - rank) * sq
                color = light_rgb if (file + rank) % 2 == 0 else dark_rgb
                draw.rectangle([x0, y0, x0 + sq - 1, y0 + sq - 1], fill=color)

                piece = board.piece_at(chess.square(file, rank))
                if piece:
                    sym = piece_chars.get(piece.piece_type, "?")
                    if piece.color == chess.BLACK:
                        sym = sym.lower()
                    fg = (30, 30, 30) if piece.color == chess.WHITE else (220, 220, 220)
                    draw.text((x0 + sq // 3, y0 + sq // 5), sym, fill=fg)

        return img


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
