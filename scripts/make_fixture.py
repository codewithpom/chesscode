"""One-off generator for the contract fixture spec (Opera Game, 60 s, EN).

shortcut: hand-built narration and silent audio; real fixtures come from the
pipeline once M2 lands. Usage: STOCKFISH_PATH=... python scripts/make_fixture.py
"""
import json
import math
import os
import subprocess
from pathlib import Path

import chess
import chess.engine
import chess.pgn
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "spec" / "fixtures" / "cc-2026-0001-en"
PGN = """[Event "Paris Opera"]
[Site "Paris FRA"]
[Date "1858.11.02"]
[White "Paul Morphy"]
[Black "Duke Karl / Count Isouard"]
[Result "1-0"]
[ECO "C41"]

1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7
8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7
14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0"""

SEGMENTS = [  # (kind, ply, text, start_ms, duration_ms)
    ("cold_open", 33, "Seventeen moves. One queen sacrifice. And a checkmate people still study.", 0, 5000),
    ("ply", 1, "Paris, 1858. Paul Morphy sits down at the opera, between acts.", 5400, 4600),
    ("ply", 6, "Black pins the knight early, then gives up the bishop for it.", 10400, 4800),
    ("ply", 13, "Morphy develops with tempo. Every move makes a threat.", 15600, 4400),
    ("ply", 19, "The knight takes on b5. A full piece, just to open lines.", 20400, 4600),
    ("ply", 23, "Castles queenside, and the rook lands on the open file.", 25400, 4200),
    ("ply", 31, "Then the queen goes to b8, check. Black has to take it.", 30000, 4600),
    ("ply", 33, "Rook to d8. Checkmate, with only two pieces left.", 35000, 5000),
]
OUTRO_MS = 20000


def silent_mp3(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "anullsrc=r=48000:cl=mono", "-t", f"{seconds:.3f}", "-q:a", "9", str(path)],
        check=True,
    )


def words_for(text: str, start: int, duration: int) -> list[dict]:
    tokens = text.split()
    step = duration // len(tokens)
    return [{"w": w, "start_ms": start + i * step, "end_ms": start + (i + 1) * step - 20}
            for i, w in enumerate(tokens)]


def eval_of(score: chess.engine.PovScore) -> dict:
    s = score.white()
    return {"cp": None, "mate": s.mate()} if s.is_mate() else {"cp": s.score(), "mate": None}


def win_pct(cp: int) -> float:
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def classify(i: int, uci: str, best: str, before_cp: int, after_cp: int) -> str:
    if i < 6:
        return "book"
    if uci == best:
        return "best"
    drop = win_pct(before_cp) - win_pct(after_cp)  # Lichess-style win% loss
    return "good" if drop < 10 else "inaccuracy" if drop < 20 else "mistake" if drop < 30 else "blunder"


def main() -> None:
    game = chess.pgn.read_game(__import__("io").StringIO(PGN))
    moves = list(game.mainline_moves())
    seg_start = {s[1]: s[3] for s in SEGMENTS if s[0] == "ply"}
    board = game.board()
    plies = []
    show = 5400
    with chess.engine.SimpleEngine.popen_uci(os.environ["STOCKFISH_PATH"]) as engine:
        for i, move in enumerate(moves, start=1):
            before = engine.analyse(board, chess.engine.Limit(depth=14))
            best = before["pv"][0].uci()
            san = board.san(move)
            board.push(move)
            after = engine.analyse(board, chess.engine.Limit(depth=14)) if not board.is_game_over() else None
            ev = eval_of(after["score"]) if after else {"cp": None, "mate": 1 if i % 2 else -1}
            mover = chess.WHITE if i % 2 else chess.BLACK
            b_cp = before["score"].pov(mover).score(mate_score=10000)
            a_cp = after["score"].pov(mover).score(mate_score=10000) if after else 10000
            show = seg_start.get(i, show + 900)
            highlights = [{"square": chess.square_name(move.from_square), "kind": "last_move"},
                          {"square": chess.square_name(move.to_square), "kind": "last_move"}]
            if board.is_check():
                highlights.append({"square": chess.square_name(board.king(board.turn)), "kind": "check"})
            plies.append({
                "ply": i, "san": san, "uci": move.uci(), "fen_after": board.fen(), "eval": ev,
                "best_uci": best, "class": classify(i, move.uci(), best, b_cp, a_cp),
                "clock_ms": None, "show_at_ms": show, "arrows": [], "highlights": highlights,
            })

    narration = []
    for n, (kind, ply, text, start, dur) in enumerate(SEGMENTS):
        audio = f"audio/en_seg-{n:03d}.mp3"
        silent_mp3(OUT / audio, dur / 1000)
        narration.append({"segment_id": f"seg-{n:03d}", "kind": kind, "ply": ply, "text": text,
                          "audio": audio, "start_ms": start, "duration_ms": dur,
                          "words": words_for(text, start, dur)})
    last_end = narration[-1]["start_ms"] + narration[-1]["duration_ms"]
    duration = last_end + OUTRO_MS
    silent_mp3(OUT / "music/bed_calm_01.mp3", duration / 1000)

    spec = {
        "spec_version": "1.1.0", "video_id": "cc-2026-0001-en", "pair_id": "cc-2026-0001",
        "language": "en", "template": "studio", "series": "legendary_games",
        "board": {"orientation": "white", "theme": "bone_slate"},
        "format": {"width": 1920, "height": 1080, "fps": 30}, "duration_ms": duration,
        "game": {
            "source": "local", "source_id": "opera-game-1858",
            "white": {"name": "Paul Morphy", "rating": None, "title": None, "country": "US",
                      "fact": "Unofficial world's best player at 21, retired from chess at 22."},
            "black": {"name": "Duke Karl / Count Isouard", "rating": None, "title": None, "country": None,
                      "fact": "Two noblemen consulting on every move, in their own opera box."},
            "event": "Paris Opera", "date": "1858-11-02", "result": "1-0", "eco": "C41",
            "opening": "Philidor Defense", "pgn": PGN,
        },
        "plies": plies,
        "narration": narration,
        "beats": [
            {"beat_id": "b-01", "type": "opening_exit", "ply": 7, "at_ms": plies[6]["show_at_ms"],
             "intensity": 1, "mascot": {"pose": "thinking", "line": "Wait, is this still theory?"},
             "fx": ["out_of_theory_label"], "sfx": None},
            {"beat_id": "b-02", "type": "checkmate", "ply": 33, "at_ms": plies[32]["show_at_ms"],
             "intensity": 3, "mascot": {"pose": "mic_drop", "line": "Two pieces. That's all he needed."},
             "fx": ["freeze_frame"], "sfx": "sting_01"},
        ],
        "chapters": [{"title": "The opening", "start_ms": 0}, {"title": "The attack", "start_ms": 20400},
                     {"title": "The finish", "start_ms": 30000}],
        "cold_open": {"ply_from": 31, "ply_to": 33, "hook": "A queen sacrifice at the opera"},
        "key_moments": [],
        "verdict": {"turning_point_ply": 19, "accuracy": {"white": 92.0, "black": 61.0}},
        "thumbnail": {"text": "Queen sac, mate", "ply": 31, "crop_origin": "a5", "pose": "mic_drop"},
        "music": {"track": "music/bed_calm_01.mp3", "volume": 0.12, "duck_under_voice": 0.06},
        "youtube": {
            "title": "He gave up his queen at the opera (and mated in 17)",
            "description": "Morphy's Opera Game, move by move.\n\n00:00 The opening\n00:20 The attack\n"
                           "00:30 The finish\n\nccid: cc-2026-0001-en",
            "tags": ["chess", "morphy", "opera game"], "playlist": "Legendary Games",
            "publish_at": "2026-11-17T18:30:00Z", "default_language": "en", "made_for_kids": False,
            "contains_synthetic_media": False, "thumbnail": "thumb.png",
        },
    }
    (OUT / "video_spec.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print(f"wrote {OUT} ({len(plies)} plies, {duration} ms)")


if __name__ == "__main__":
    main()
