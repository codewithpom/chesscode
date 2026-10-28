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


from collections import Counter
from datetime import date

from chesscode.calendar import schedule

SERIES = ["legendary_games", "indian_chess_heroes", "opening_explained", "blunder_hall_of_fame"]


def ids(game_no, year=2026):
    return [f"cc-{year}-{n:04d}-{lang}" for n in (game_no, game_no + 5000) for lang in ("en", "hi")]


def test_target_tier_schedules_without_crashing():
    games = [{"game_no": i, "series": SERIES[i % 4], "tier": "target"} for i in range(1, 4)]
    assigned, unassigned = schedule(games)
    for i in range(1, 4):
        en, hi = assigned[f"cc-2026-{i:04d}-en"], assigned[f"cc-2026-{i:04d}-hi"]
        assert date.fromisoformat(en[:10]).weekday() == 5 and date.fromisoformat(hi[:10]).weekday() == 6  # Sat EN, Sun HI
    assert len(set(assigned.values())) == len(assigned)


def test_overflow_is_unassigned_with_a_reason_not_a_crash():
    games = [{"game_no": i, "series": SERIES[i % 4], "tier": "floor"} for i in range(1, 31)]
    assigned, unassigned = schedule(games)
    assert unassigned and all(reason for reason in unassigned.values())
    assert all(v < "2027-02-16" for v in assigned.values())
    for game in games:  # every video of every game is either scheduled or explained
        assert all(vid in assigned or vid in unassigned for vid in ids(game["game_no"]))


def test_unbalanced_series_do_not_drop_games():
    games = [{"game_no": i, "series": "legendary_games", "tier": "floor"} for i in (1, 2)]
    games += [{"game_no": 3, "series": "opening_explained", "tier": "floor"}, {"game_no": 4, "series": "legendary_games", "tier": "floor"}, {"game_no": 5, "series": "legendary_games", "tier": "floor"}]
    assigned, unassigned = schedule(games)
    for game in games:
        assert all(vid in assigned or vid in unassigned for vid in ids(game["game_no"]))
    assert f"cc-2026-0003-en" in assigned


def test_series_rule_leaves_a_third_game_in_a_row_unassigned():
    games = [{"game_no": i, "series": "legendary_games", "tier": "floor"} for i in range(1, 6)]
    assigned, unassigned = schedule(games)
    assert {k for k in assigned if int(k.split("-")[2]) < 5000} == {"cc-2026-0001-en", "cc-2026-0001-hi", "cc-2026-0002-en", "cc-2026-0002-hi"}
    assert "series rule" in unassigned["cc-2026-0003-en"]


def test_floor_and_target_share_one_clock():
    games = [{"game_no": i, "series": SERIES[i % 4], "tier": "floor" if i % 2 else "target"} for i in range(1, 9)]
    assigned, _ = schedule(games)
    assert len(set(assigned.values())) == len(assigned)
    floor_en = [v for k, v in assigned.items() if k.endswith("-en") and int(k.split("-")[2]) in (1, 3, 5, 7)]
    assert sorted(floor_en)[0].startswith("2026-11-17")  # Tuesday of the first week, floor first


def test_shorts_for_target_games_keep_the_one_to_three_day_rule():
    assigned, _ = schedule([{"game_no": 1, "series": "legendary_games", "tier": "target"}])
    en_long, en_short = assigned["cc-2026-0001-en"], assigned["cc-2026-5001-en"]
    assert 1 <= (date.fromisoformat(en_long[:10]) - date.fromisoformat(en_short[:10])).days <= 3


def test_every_target_game_gets_both_shorts():
    games = [{"game_no": i, "series": SERIES[i % 4], "tier": "target"} for i in range(1, 9)]
    assigned, unassigned = schedule(games)
    assert not unassigned
    for i in range(1, 9):
        for lang in ("en", "hi"):
            long, short = assigned[f"cc-2026-{i:04d}-{lang}"], assigned[f"cc-2026-{5000 + i:04d}-{lang}"]
            assert 1 <= (date.fromisoformat(long[:10]) - date.fromisoformat(short[:10])).days <= 3
