from chesscode.stages.beats import _mover_score, detect, pace
import json
from pathlib import Path
from chesscode.config import load

CFG = {"min_gap_ms": 20000, "min_gap_intensity3_ms": 60000, "est_ms_per_ply": 4500,
       "priority": ["checkmate", "blunder", "brilliant", "missed_win", "comeback", "rest"],
       "poses": {"blunder":"facepalm", "mistake":"side_eye", "brilliant":"slow_clap", "missed_win":"screaming", "comeback":"shocked", "long_think":"checks_watch", "time_scramble":"sweating", "king_walk":"binoculars", "promotion":"jealous", "checkmate":"mic_drop", "resign":"bow", "opening_exit":"thinking"}}

def row(ply, cp_before=0, cp_after=0, **kw):
    return {"ply":ply,"uci":"e1f1","san":"Kf1","fen_before":"r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1","fen_after":"r3k2r/8/8/8/8/8/8/R4K1R b kq - 1 1","before":[{"cp":cp_before,"mate":None}],"after":[{"cp":cp_after,"mate":None}],"class":"best",**kw}

def test_blunder_drop_2():
    assert any(b['type']=='blunder' for b in detect([row(1,300,100, **{"class": "blunder"})], CFG))

def test_priority_beats_intensity_in_window():
    result=pace([{"type":"mistake","ply":1,"intensity":3,"priority":0},{"type":"blunder","ply":2,"intensity":1,"priority":1}], None, CFG)
    assert [b['type'] for b in result] == ['blunder']

def test_no_clocks_no_clock_beats():
    assert not {b['type'] for b in detect([row(1)], CFG)} & {'long_think','time_scramble'}

def test_winning_to_zero_is_blunder():
    assert any(b["type"]=="blunder" for b in detect([row(1,300,0)],CFG))

def test_mistake_range():
    assert any(b["type"]=="mistake" for b in detect([row(1,150,0, **{"class": "mistake"})],CFG))

def test_comeback_window_20_plies():
    old=row(1,-400,-350)
    current=row(3,50,50)
    assert any(b["type"]=="comeback" for b in detect([old,row(2),current],CFG))

def test_long_think_15_percent():
    assert any(b["type"]=="long_think" for b in detect([row(1,clock_ms=60000,time_spent_ms=10000)],CFG))

def test_time_scramble_60s():
    assert any(b["type"]=="time_scramble" for b in detect([row(1,clock_ms=60000)],CFG))

def test_king_walk_needs_queens():
    fen="8/8/8/8/8/8/8/4K2k w - - 0 1"
    rows=[row(i,fen_before=fen,uci="e1f1") for i in (1,3,5)]
    assert not any(b["type"]=="king_walk" for b in detect(rows,CFG))

def test_underpromotion_intensity_3():
    r=row(1,fen_before="7k/P7/8/8/8/8/8/7K w - - 0 1",uci="a7a8n")
    assert any(b["type"]=="promotion" and b["intensity"]==3 for b in detect([r],CFG))

def test_resign_not_checkmate():
    r=row(1,result="1-0")
    assert any(b["type"]=="resign" for b in detect([r],CFG))

def test_opening_exit_first_non_book():
    rows=[row(1,**{"class":"book"}),row(2),row(3)]
    assert [b["ply"] for b in detect(rows,CFG) if b["type"]=="opening_exit"]==[2]

def test_min_gap_20s():
    c=[{"type":"blunder","ply":1,"intensity":1},{"type":"missed_win","ply":2,"intensity":1}]
    assert len(pace(c,{1:0,2:19999},CFG))==1

def test_intensity3_gap_60s():
    c=[{"type":"blunder","ply":1,"intensity":3},{"type":"checkmate","ply":2,"intensity":3}]
    assert len(pace(c,{1:0,2:59999},CFG))==1

def test_no_same_pose_twice():
    cfg={**CFG,"poses":{**CFG["poses"],"brilliant":"facepalm"}}
    c=[{"type":"blunder","ply":1,"intensity":1},{"type":"brilliant","ply":6,"intensity":1}]
    assert len(pace(c,{1:0,6:30000},cfg))==1


def test_mate_scores_are_clamped_before_drop_detection():
    r = row(1, **{"class": "excellent", "before": [{"cp": None, "mate": -5}], "after": [{"cp": None, "mate": -13}]})
    assert not any(b["type"] == "blunder" for b in detect([r], CFG))
    assert _mover_score(r, "before", 10) == -10
    assert _mover_score(r, "after", 10) == -10


def test_pawn_drop_requires_classified_error_or_winning_to_zero():
    assert not any(b["type"] == "blunder" for b in detect([row(1, 1090, 890, **{"class": "good"})], CFG))
    assert not any(b["type"] == "mistake" for b in detect([row(1, 300, 150, **{"class": "best"})], CFG))
    assert any(b["type"] == "mistake" for b in detect([row(1, 300, 150, **{"class": "mistake"})], CFG))


def test_golden_book_plies_only_have_opening_exit():
    rows = json.loads((Path(__file__).parent / "golden" / "analysis" / "opera.json").read_text())
    cfg = load("beats")
    from chesscode.stages.classify import load_openings
    import chess
    openings = load_openings(Path(__file__).parents[2] / "content" / "openings")
    for row_ in rows:
        row_["class"] = "book" if chess.Board(row_["fen_after"]).epd() in openings else "good"
        if row_["class"] == "book":
            types = {b["type"] for b in detect([row_], cfg)}
            assert types <= {"opening_exit"}


def test_beat_poses_alternate_and_final_intensities():
    cfg = load("beats")
    beats = pace([{"type": "blunder", "ply": 1, "intensity": 1}, {"type": "blunder", "ply": 6, "intensity": 1}], {1: 0, 6: 30000}, cfg)
    assert beats[0]["pose"] != beats[1]["pose"]
    mate = row(1, **{"class": "best", "san": "Qh7#", "uci": "e1f1"})
    mate["san"] = "Qh7#"
    mate["result"] = "1-0"
    final = detect([mate], cfg)
    assert next(b["intensity"] for b in final if b["type"] == "checkmate") == 3
    resign = {**mate, "san": "Kf1", "class": "best"}
    final = detect([resign], cfg)
    assert next(b["intensity"] for b in final if b["type"] == "resign") == 2


def test_priority_is_complete_and_promotion_precedes_mistake():
    cfg = load("beats")
    assert cfg["priority"] == ["checkmate", "blunder", "brilliant", "missed_win", "comeback", "promotion", "king_walk", "time_scramble", "resign", "mistake", "long_think", "opening_exit"]


def test_intensity3_gap_only_applies_between_two_intensity3_beats():
    cfg = {"min_gap_ms": 20000, "min_gap_intensity3_ms": 60000, "priority": ["blunder", "mistake"], "poses": {"blunder": "facepalm", "mistake": "side_eye"}}
    cands = [{"type": "blunder", "ply": 1, "intensity": 3}, {"type": "mistake", "ply": 2, "intensity": 1}]
    kept = pace(cands, {1: 0, 2: 25000}, cfg)
    assert [b["type"] for b in kept] == ["blunder", "mistake"]


def test_max_per_type_caps_long_think():
    cfg = {"min_gap_ms": 20000, "priority": ["long_think"], "poses": {"long_think": "checks_watch"},
           "alt_poses": {"long_think": "thinking"}, "max_per_type": {"long_think": 2}}
    cands = [{"type": "long_think", "ply": p, "intensity": 1} for p in range(1, 6)]
    kept = pace(cands, {p: p * 30000 for p in range(1, 6)}, cfg)
    assert len(kept) == 2


def test_intensity3_blunder_faints():
    cfg = {"min_gap_ms": 20000, "priority": ["blunder"], "poses": {"blunder": "facepalm"},
           "pose_by_intensity": {"blunder": {3: "faint"}}}
    kept = pace([{"type": "blunder", "ply": 1, "intensity": 3}, {"type": "blunder", "ply": 9, "intensity": 2}], {1: 0, 9: 90000}, cfg)
    assert [b["pose"] for b in kept] == ["faint", "facepalm"]
