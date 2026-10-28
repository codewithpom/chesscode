from chesscode.stages.beats import detect, pace

CFG = {"min_gap_ms": 20000, "min_gap_intensity3_ms": 60000, "est_ms_per_ply": 4500,
       "priority": ["checkmate", "blunder", "brilliant", "missed_win", "comeback", "rest"],
       "poses": {"blunder":"facepalm", "mistake":"side_eye", "brilliant":"slow_clap", "missed_win":"screaming", "comeback":"shocked", "long_think":"checks_watch", "time_scramble":"sweating", "king_walk":"binoculars", "promotion":"jealous", "checkmate":"mic_drop", "resign":"bow", "opening_exit":"thinking"}}

def row(ply, cp_before=0, cp_after=0, **kw):
    return {"ply":ply,"uci":"e1f1","san":"Kf1","fen_before":"r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1","fen_after":"r3k2r/8/8/8/8/8/8/R4K1R b kq - 1 1","before":[{"cp":cp_before,"mate":None}],"after":[{"cp":cp_after,"mate":None}],"class":"best",**kw}

def test_blunder_drop_2():
    assert any(b['type']=='blunder' for b in detect([row(1,300,100)], CFG))

def test_priority_beats_intensity_in_window():
    result=pace([{"type":"mistake","ply":1,"intensity":3,"priority":0},{"type":"blunder","ply":2,"intensity":1,"priority":1}], None, CFG)
    assert [b['type'] for b in result] == ['blunder']

def test_no_clocks_no_clock_beats():
    assert not {b['type'] for b in detect([row(1)], CFG)} & {'long_think','time_scramble'}

def test_winning_to_zero_is_blunder():
    assert any(b["type"]=="blunder" for b in detect([row(1,300,0)],CFG))

def test_mistake_range():
    assert any(b["type"]=="mistake" for b in detect([row(1,150,0)],CFG))

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
