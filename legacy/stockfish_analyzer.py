"""stockfish_analyzer.py — Stockfish-based chess game analysis."""

import os
import queue
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MoveAnalysis:
    ply: int
    move_san: str
    fen_after: str
    eval_cp: Optional[int] = None
    eval_delta: Optional[int] = None
    best_move: Optional[str] = None
    classification: str = "normal"
    # Top candidate moves from Stockfish MultiPV
    top_moves: List[dict] = field(default_factory=list)
    # Each dict: {"uci": "g1f3", "score_cp": 41, "rank": 1}
    coach: "object" = None  # CoachInsights object, set after analysis by MCP wiring


@dataclass
class GameAnalysis:
    game_id: str = ""
    white: str = "White"
    black: str = "Black"
    result: str = "*"
    opening: str = ""
    white_elo: Optional[int] = None
    black_elo: Optional[int] = None
    moves: List[MoveAnalysis] = field(default_factory=list)
    white_blunders: int = 0
    black_blunders: int = 0
    white_accuracy: Optional[float] = None
    black_accuracy: Optional[float] = None

    def summary(self) -> str:
        return (
            f"Game: {self.white} vs {self.black} ({self.result})\n"
            f"Opening: {self.opening}\n"
            f"Moves analyzed: {len(self.moves)}\n"
            f"Blunders — White: {self.white_blunders}, Black: {self.black_blunders}"
        )

    def to_list(self) -> list:
        return self.moves


def parse_elo(raw: Optional[str]) -> Optional[int]:
    """PGN Elo tags are sometimes '?' or missing entirely — never raise,
    never fabricate: return None so callers can hide the stat."""
    if not raw:
        return None
    try:
        v = int(raw)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


class _EngineHandle:
    """One Stockfish subprocess + its UCI plumbing. Not thread-safe on its own —
    each instance is meant to be driven by exactly one worker thread at a time."""

    def __init__(self, path: str, depth: int, threads: int):
        self._path = path
        self._depth = depth
        self._threads = threads
        self._proc = None

    def start(self):
        try:
            self._proc = subprocess.Popen(
                [self._path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            self._send("uci")
            self._send(f"setoption name Threads value {self._threads}")
            self._send("isready")
            self._wait_for("readyok")
        except (FileNotFoundError, OSError) as e:
            raise RuntimeError(f"Stockfish not available at '{self._path}': {e}")
        return self

    def stop(self):
        if self._proc:
            try:
                self._send("quit")
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()

    def _send(self, cmd: str):
        self._proc.stdin.write(cmd + "\n")
        self._proc.stdin.flush()

    def _wait_for(self, token: str) -> list:
        lines = []
        while True:
            line = self._proc.stdout.readline().strip()
            if line:
                lines.append(line)
            if line.startswith(token):
                return lines

    def eval_position(self, fen: str) -> Optional[int]:
        self._send(f"position fen {fen}")
        self._send(f"go depth {self._depth}")
        best_cp = None
        while True:
            line = self._proc.stdout.readline().strip()
            if line.startswith("bestmove"):
                break
            if "score cp" in line:
                parts = line.split("score cp")
                if len(parts) > 1:
                    try:
                        best_cp = int(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass
            elif "score mate" in line:
                parts = line.split("score mate")
                if len(parts) > 1:
                    try:
                        mate_in = int(parts[1].split()[0])
                        best_cp = 30000 if mate_in > 0 else -30000
                    except (ValueError, IndexError):
                        pass
        return best_cp

    def eval_position_multipv(self, fen: str, multipv: int = 3) -> tuple:
        """Returns (best_cp, top_moves_list, best_move_uci).
        top_moves: list of dicts {"uci": str, "score_cp": int, "rank": int}
        best_move_uci: UCI notation of the best move from bestmove line
        """
        self._send(f"setoption name MultiPV value {multipv}")
        self._send(f"position fen {fen}")
        self._send(f"go depth {self._depth}")

        best_cp = None
        top_moves_raw = {}  # rank -> {"uci": str, "score_cp": int}
        bm_uci = None

        while True:
            line = self._proc.stdout.readline().strip()
            if line.startswith("bestmove"):
                # Parse best move from "bestmove e2e4 ponder ..."
                parts = line.split()
                if len(parts) > 1 and parts[1] != "(none)":
                    bm_uci = parts[1]
                break

            # Parse multipv info lines: "info depth N multipv R score cp V ... pv M1 M2..."
            if "multipv" in line and ("score cp" in line or "score mate" in line):
                try:
                    # Extract multipv rank
                    mp_idx = line.index("multipv")
                    rank = int(line[mp_idx:].split()[1])

                    # Extract score
                    if "score cp" in line:
                        cp_idx = line.index("score cp")
                        score_cp = int(line[cp_idx:].split()[2])
                    elif "score mate" in line:
                        mt_idx = line.index("score mate")
                        mate_in = int(line[mt_idx:].split()[2])
                        score_cp = 30000 if mate_in > 0 else -30000
                    else:
                        continue

                    # Extract first move from pv
                    if " pv " in line:
                        pv_part = line.split(" pv ")[1].strip()
                        first_move = pv_part.split()[0]
                        top_moves_raw[rank] = {"uci": first_move, "score_cp": score_cp, "rank": rank}

                    # Track best_cp from rank 1
                    if rank == 1:
                        best_cp = score_cp
                except (ValueError, IndexError):
                    continue

        # Reset MultiPV to 1 for next call (avoid affecting single-line callers)
        self._send("setoption name MultiPV value 1")

        top_moves = [top_moves_raw[r] for r in sorted(top_moves_raw.keys())]
        return best_cp, top_moves, bm_uci


class StockfishAnalyzer:
    def __init__(self, stockfish_path: str = "stockfish", depth: int = 18, threads: int = 4,
                 workers: Optional[int] = None):
        self._path = stockfish_path
        self._depth = depth
        self._threads = threads
        # N parallel engine processes, each internally using `threads` search threads —
        # cap N so N * threads doesn't oversubscribe logical cores. 0/None = auto.
        self._requested_workers = workers if workers else \
            min(4, max(1, (os.cpu_count() or 4) // max(1, threads)))
        self._engines: List[_EngineHandle] = []

    def __enter__(self):
        try:
            first = _EngineHandle(self._path, self._depth, self._threads).start()
        except RuntimeError:
            raise
        self._engines = [first]
        for _ in range(self._requested_workers - 1):
            self._engines.append(_EngineHandle(self._path, self._depth, self._threads).start())
        return self

    def __exit__(self, *_):
        for engine in self._engines:
            engine.stop()
        self._engines = []

    def analyze_game(self, game_pgn, game_id: str = "",
                     progress_callback=None) -> GameAnalysis:
        import chess
        import chess.pgn
        import io

        if isinstance(game_pgn, str):
            game = chess.pgn.read_game(io.StringIO(game_pgn))
        else:
            game = game_pgn

        if not game:
            raise ValueError("Invalid PGN")

        headers = game.headers
        ga = GameAnalysis(
            game_id=game_id,
            white=headers.get("White", "White"),
            black=headers.get("Black", "Black"),
            result=headers.get("Result", "*"),
            opening=headers.get("Opening", ""),
            white_elo=parse_elo(headers.get("WhiteElo")),
            black_elo=parse_elo(headers.get("BlackElo")),
        )

        # ── Sequential, cheap: build (ply, san, fen) for every move ──────────
        board = game.board()
        moves = list(game.mainline_moves())
        total = len(moves)
        plies = []
        for i, move in enumerate(moves):
            san = board.san(move)
            board.push(move)
            plies.append((i, san, board.fen()))

        # ── Pass A: evaluate every position in parallel across the engine pool ──
        # Engines are handed out via a queue rather than round-robin indexing so
        # a busy engine is never handed a second concurrent task regardless of
        # how the thread pool schedules workers — each task holds exclusive use
        # of one engine for the duration of its eval, then returns it.
        engines = self._engines or [_EngineHandle(self._path, self._depth, self._threads).start()]
        eval_by_ply: dict = {}
        multipv_by_ply: dict = {}
        bestmove_by_ply: dict = {}
        done_count = 0

        if len(engines) <= 1 or total <= 1:
            engine = engines[0]
            for ply, _san, fen in plies:
                cp, top_moves, bm = engine.eval_position_multipv(fen)
                eval_by_ply[ply] = cp
                multipv_by_ply[ply] = top_moves
                bestmove_by_ply[ply] = bm
                done_count += 1
                if progress_callback:
                    progress_callback(done_count, total)
        else:
            engine_pool: "queue.Queue[_EngineHandle]" = queue.Queue()
            for e in engines:
                engine_pool.put(e)

            def _eval_one(ply: int, fen: str) -> tuple:
                engine = engine_pool.get()
                try:
                    cp, top_moves, bm = engine.eval_position_multipv(fen)
                    return ply, cp, top_moves, bm
                finally:
                    engine_pool.put(engine)

            with ThreadPoolExecutor(max_workers=len(engines)) as ex:
                futures = [ex.submit(_eval_one, ply, fen) for ply, _san, fen in plies]
                for fut in futures:
                    ply, cp, top_moves, bm = fut.result()
                    eval_by_ply[ply] = cp
                    multipv_by_ply[ply] = top_moves
                    bestmove_by_ply[ply] = bm
                    done_count += 1
                    if progress_callback:
                        progress_callback(done_count, total)

        # ── Pass B: sequential, cheap — deltas/classification/blunders need prev_eval ──
        prev_eval: Optional[int] = None
        for i, san, fen in plies:
            eval_cp = eval_by_ply.get(i)

            delta = None
            if prev_eval is not None and eval_cp is not None:
                delta = (eval_cp - prev_eval) if i % 2 == 0 else (prev_eval - eval_cp)

            classification = _classify_move(delta, i)
            if classification == "blunder":
                if i % 2 == 0:
                    ga.white_blunders += 1
                else:
                    ga.black_blunders += 1

            ga.moves.append(MoveAnalysis(
                ply=i,
                move_san=san,
                fen_after=fen,
                eval_cp=eval_cp,
                eval_delta=delta,
                best_move=bestmove_by_ply.get(i),
                classification=classification,
                top_moves=multipv_by_ply.get(i, []),
            ))
            prev_eval = eval_cp

        return ga


def _classify(delta: Optional[int]) -> str:
    if delta is None:
        return "normal"
    if delta >= -5:
        return "normal"
    if delta >= -20:
        return "inaccuracy"
    if delta >= -100:
        return "mistake"
    return "blunder"


# First N plies (5 full moves each side) are still known opening theory in the
# vast majority of games. Shallow eval (esp. the MCP render_video path's fast
# --depth 12) is noisy enough there to swing 20-100+ cp between book moves for
# no real reason, which used to mislabel moves like Nf3/Bb5/O-O as "mistake"/
# "blunder" in the rendered move list. Book moves get a pass on classification
# regardless of eval delta — real inaccuracies still get caught once the game
# leaves theory.
OPENING_BOOK_PLIES = 10


def _classify_move(delta: Optional[int], ply: int, book_plies: int = OPENING_BOOK_PLIES) -> str:
    if ply < book_plies:
        return "normal"
    return _classify(delta)
