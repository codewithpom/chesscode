from chesscode.calendar import assign

def test_publish_at_is_utc_z_and_unique():
    series=["legendary_games","indian_chess_heroes","opening_explained"]
    games=[{"game_no":i,"pair_id":f"p{i}","series":series[i-1],"tier":"floor"} for i in range(1,4)]
    assigned=assign(games,"floor")
    assert len(assigned)==12
    assert len(set(assigned.values()))==len(assigned)
    assert all(value.endswith("Z") for value in assigned.values())

def test_pair_never_same_day():
    games=[{"game_no":7,"pair_id":"pair","series":"legendary_games","tier":"floor"}]
    assigned=assign(games,"floor")
    en=next(v for k,v in assigned.items() if k.endswith("-en")); hi=next(v for k,v in assigned.items() if k.endswith("-hi"))
    assert en[:10] != hi[:10]

def test_short_1_to_3_days_before_longform():
    games=[{"game_no":8,"series":"opening_explained","tier":"floor"}]
    assigned=assign(games,"floor")
    for language in ("en","hi"):
        long=next(v for k,v in assigned.items() if k.endswith(f"-0008-{language}"))
        short=next(v for k,v in assigned.items() if k.endswith(f"-5008-{language}"))
        from datetime import date
        assert 1 <= (date.fromisoformat(long[:10])-date.fromisoformat(short[:10])).days <= 3

def test_floor_fills_earliest_first():
    first=next(iter(assign([{"game_no":1,"series":"legendary_games","tier":"floor"}],"floor").values()))
    assert first.startswith("2026-11-16")

def test_series_max_two_weeks_in_a_row():
    games=[{"game_no":i,"series":s,"tier":"floor"} for i,s in enumerate(["legendary_games","indian_chess_heroes","opening_explained","blunder_hall_of_fame"]*2,1)]
    schedule=assign(games,"floor")
    ordered=sorted((value,game["series"]) for game in games for key,value in schedule.items() if key.endswith(f"-{game['game_no']:04d}-en"))
    weekly=[]
    for stamp,series in ordered:
        week=stamp[:10]
        if weekly and weekly[-1][0]==week: continue
        weekly.append((week,series))
    assert all(not (weekly[i][1]==weekly[i+1][1]==weekly[i+2][1]) for i in range(len(weekly)-2))
