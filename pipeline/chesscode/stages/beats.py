import json

import chess
import chess.pgn

from ..config import load
from ..context import StageError

INPUTS = ["classified.json", "game.pgn", "config/beats.yaml"]
OUTPUTS = ["beats.json"]
_FX = {"blunder": ["board_shake", "red_flash", "replay_move"], "mistake": ["move_underline"], "brilliant": ["gold_glint", "stamp_brilliant"], "missed_win": ["ghost_arrow"], "comeback": ["eval_whip"], "long_think": ["clock_pulse"], "time_scramble": ["clock_red"], "king_walk": ["king_trail"], "promotion": ["crown_sparkle"], "checkmate": ["freeze_frame"], "resign": ["freeze_frame"], "opening_exit": ["out_of_theory_label"]}

def _mover_score(row, key):
    score = row.get(key) or {}
    if isinstance(score, list): score = score[0] if score else {}
    cp, mate = score.get("cp"), score.get("mate")
    white_turn = chess.Board(row["fen_before"]).turn
    return (float("inf") if mate is not None and mate > 0 else float("-inf") if mate is not None else cp / 100) * (1 if white_turn else -1)

def detect(rows: list[dict], cfg: dict) -> list[dict]:
    trig = cfg.get("triggers", {})
    found = []
    def add(kind, row, intensity=1):
        priority = (cfg.get("priority", [])).index(kind) if kind in cfg.get("priority", []) else len(cfg.get("priority", []))
        found.append({"type": kind, "ply": row["ply"], "intensity": intensity, "priority": priority})
    clock_seen = set(); last_clock = {}; kings = {chess.WHITE: 0, chess.BLACK: 0}; opening_done = False
    for i, row in enumerate(rows):
        before = _mover_score(row, "before"); after = _mover_score(row, "after") if row.get("after") else before
        drop = before - after
        cls = row.get("class")
        if cls == "blunder" or drop >= trig.get("blunder_drop", 2) or (before >= trig.get("winning_eval", 2) and after <= 0):
            intensity = 3 if drop >= 4 or (before >= 2 and after <= trig.get("losing_eval", -2)) else 2 if drop >= 3 else 1
            add("blunder", row, intensity)
        elif cls == "mistake" or trig.get("mistake_drop", 1) <= drop < trig.get("mistake_max_drop", 2): add("mistake", row)
        if cls in ("brilliant", "missed_win"): add(cls, row)
        if not opening_done and cls != "book": add("opening_exit", row); opening_done = True
        board = chess.Board(row["fen_before"]); move = chess.Move.from_uci(row["uci"]); mover = board.turn
        if move.promotion: add("promotion", row, 3 if move.promotion != chess.QUEEN else 1)
        san = row.get("san", "")
        if san.endswith("#") and i == len(rows)-1: add("checkmate", row)
        if i == len(rows)-1 and row.get("result") in ("1-0", "0-1") and not san.endswith("#"): add("resign", row)
        clock = row.get("clock_ms")
        if clock is not None:
            side = "white" if mover else "black"
            if clock <= trig.get("time_scramble_ms", 60000) and side not in clock_seen: add("time_scramble", row); clock_seen.add(side)
            spent = row.get("time_spent_ms", last_clock.get(side, clock)-clock)
            if spent is not None and spent > 0 and (spent >= trig.get("long_think_ms", 300000) or spent >= clock * trig.get("long_think_fraction", .15)): add("long_think", row)
            last_clock[side] = clock
        if board.piece_at(move.from_square).piece_type == chess.KING and not board.is_castling(move):
            kings[mover] += 1
            if kings[mover] == trig.get("king_walk_count", 3) and board.fullmove_number < trig.get("king_walk_before_move", 30) and board.pieces(chess.QUEEN, True) and board.pieces(chess.QUEEN, False): add("king_walk", row)
        if not opening_done: continue
        for old in rows[max(0, i-trig.get("comeback_plies",20)):i]:
            old_board=chess.Board(old["fen_before"]) if old.get("fen_before") else None
            if old_board and old_board.turn==mover and _mover_score(old,"before") <= trig.get("comeback_was",-3) and after >= trig.get("comeback_now",0):
                add("comeback", row); break
    return found

def pace(cands: list[dict], ply_times_ms: dict[int,int] | None, cfg: dict) -> list[dict]:
    priority = cfg.get("priority", [])
    ordered = sorted(cands, key=lambda b: (priority.index(b["type"]) if b["type"] in priority else len(priority), -b.get("intensity", 1), b["ply"]))
    selected = []
    def at(b): return (ply_times_ms or {}).get(b["ply"], b["ply"] * cfg.get("est_ms_per_ply", 4500))
    for beat in ordered:
        gap = cfg.get("min_gap_intensity3_ms", 60000) if beat.get("intensity") == 3 and any(x.get("intensity")==3 for x in selected) else cfg.get("min_gap_ms",20000)
        if any(abs(at(beat)-at(prev)) < gap for prev in selected): continue
        selected.append(beat)
    result=[]
    for beat in sorted(selected,key=lambda b:(at(b),b["ply"])):
        if result and cfg.get("poses",{}).get(beat["type"])==cfg.get("poses",{}).get(result[-1]["type"]): continue
        result.append(beat)
    return result

def run(ctx):
    try:
        rows = json.loads((ctx.spec_dir / "classified.json").read_text(encoding="utf-8"))
        cfg = load("beats", root=ctx.repo_root)
        pgn=chess.pgn.read_game(__import__("io").StringIO((ctx.spec_dir/"game.pgn").read_text(encoding="utf-8")))
        if pgn and rows: rows[-1]["result"]=pgn.headers.get("Result")
        beats = pace(detect(rows, cfg), None, cfg)
        beats=[{"beat_id":f"b-{i:02d}",**beat} for i,beat in enumerate(beats,1)]
        (ctx.spec_dir / "beats.json").write_text(json.dumps(beats, indent=2)+"\n", encoding="utf-8")
    except Exception as exc:
        raise StageError(ctx.video_id, "beats", str(exc)) from exc
