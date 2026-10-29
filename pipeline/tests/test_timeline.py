import pytest

from chesscode.config import load
from chesscode.stages.timeline import layout

CFG = {**load("timeline"), "beats": load("beats")}


def words(n, step=500):
    return [{"w": f"w{i}", "start_ms": i*step, "end_ms": i*step+step-50} for i in range(n)]


def make(kinds, n_words=6, duration=10000):
    segments = [{"kind": k, "ply": p, "text": f"text {i}"} for i, (k, p) in enumerate(kinds)]
    voice = [{"segment_id": f"seg-{i:03d}", "audio": f"audio/en_seg-{i:03d}.mp3", "duration_ms": duration, "words": words(n_words)} for i in range(len(kinds))]
    return segments, voice


def run(kinds, beats=(), n_plies=12, cfg=CFG, **kw):
    segments, voice = make(kinds, **kw)
    return layout(segments, voice, list(beats), [{"ply": n} for n in range(1, n_plies+1)], cfg)


def word_starts(result):
    return {w["start_ms"] for s in result["narration"] for w in s["words"]}


SPARSE = [("cold_open", None), ("ply", 3), ("chapter", None), ("ply", 8)]


def test_no_overlap():
    r = run(SPARSE)
    assert all(a["start_ms"]+a["duration_ms"] <= b["start_ms"] for a, b in zip(r["narration"], r["narration"][1:]))


def test_show_at_non_decreasing_and_on_word_starts():
    r = run(SPARSE)
    times = [r["plies_show_at"][n] for n in range(1, 13)]
    assert times == sorted(times)
    seg_starts = {s["start_ms"] for s in r["narration"]}
    assert all(t in word_starts(r) | seg_starts for t in times)


def test_plies_before_first_ply_segment_show_at_its_start():
    r = run(SPARSE)
    first = r["narration"][1]["start_ms"]
    assert r["plies_show_at"][1] == r["plies_show_at"][2] == r["plies_show_at"][3] == first


def test_range_spreads_over_word_starts_inside_segment():
    r = run(SPARSE)  # ply 3 covers 3..7 (5 plies), 6 words: first at segment start, rest on words
    seg = r["narration"][1]
    assert r["plies_show_at"][3] == seg["start_ms"]
    assert all(seg["start_ms"] <= r["plies_show_at"][n] < seg["start_ms"]+seg["duration_ms"] for n in range(3, 8))
    assert len({r["plies_show_at"][n] for n in range(3, 8)}) == 5
    last = r["narration"][3]  # ply 8 covers 8..12
    assert all(last["start_ms"] <= r["plies_show_at"][n] for n in range(8, 13))


def test_show_at_not_before_segment_start():
    r = run(SPARSE)
    for i, (first, last) in {1: (3, 7), 3: (8, 12)}.items():
        assert all(r["plies_show_at"][n] >= r["narration"][i]["start_ms"] for n in range(first, last+1))


def test_ply_segments_must_increase_and_exist():
    with pytest.raises(ValueError, match="no ply segments"):
        run([("cold_open", None)])
    with pytest.raises(ValueError, match="increasing"):
        run([("ply", 5), ("ply", 3)])
    with pytest.raises(ValueError, match="increasing"):
        run([("ply", 5), ("ply", 99)])


def test_reaction_gap_900_after_segment_covering_intensity2_beat():
    beats = [{"type": "blunder", "ply": 4, "intensity": 2, "priority": 1}]
    r = run(SPARSE, beats)
    n = r["narration"]
    assert n[2]["start_ms"] == n[1]["start_ms"]+10000+900          # ply segment covering ply 4
    assert n[1]["start_ms"] == n[0]["start_ms"]+10000+CFG["segment_gap_ms"]


def test_beat_at_ms_is_its_plies_show_at():
    r = run(SPARSE, [{"type": "blunder", "ply": 5, "intensity": 1, "priority": 1}])
    assert r["beats"][0]["at_ms"] == r["plies_show_at"][5]


def test_duration_is_last_end_plus_outro():
    r = run(SPARSE)
    assert r["duration_ms"] == r["narration"][-1]["start_ms"]+10000+CFG["outro_ms"]


def test_chapters_min_three_and_10s():
    r = run(SPARSE)
    assert len(r["chapters"]) >= 3 and r["chapters"][0]["start_ms"] == 0
    assert all(b["start_ms"]-a["start_ms"] >= 10000 for a, b in zip(r["chapters"], r["chapters"][1:]))


def test_repace_uses_real_beats_yaml_priority_and_final_beat():
    # time_scramble sits closer than 20 s before resign: with real priority the resign still survives
    segments, voice = make([("cold_open", None), ("ply", 1)], duration=30000)
    beats = [{"type": "time_scramble", "ply": 9, "intensity": 1, "priority": 7}, {"type": "resign", "ply": 12, "intensity": 2, "priority": 8}]
    r = layout(segments, voice, beats, [{"ply": n} for n in range(1, 13)], CFG)
    assert [b["type"] for b in r["beats"]] == ["resign"]
    assert r["beats"][0]["pose"] == "bow"


def test_repace_drops_beats_closer_than_20s():
    beats = [{"type": "blunder", "ply": 2, "intensity": 1, "priority": 1}, {"type": "brilliant", "ply": 3, "intensity": 1, "priority": 2}]
    r = run([("cold_open", None), ("ply", 1)], beats, duration=30000)
    assert [b["type"] for b in r["beats"]] == ["blunder"]


def test_missing_beats_config_is_an_error():
    segments, voice = make([("ply", 1)])
    with pytest.raises(KeyError):
        layout(segments, voice, [], [{"ply": 1}], {k: v for k, v in CFG.items() if k != "beats"})


def test_shorts_skip_chapter_padding():
    r = run([("cold_open", None), ("ply", 1)], n_plies=4, duration=8000, cfg={**CFG, "min_chapters": 0, "outro_ms": 0})
    assert [c["start_ms"] for c in r["chapters"]] == [0]  # no filler "Chapter N" entries for Shorts


def test_plies_never_share_a_timestamp_inside_a_segment_with_few_words():
    r = run([("cold_open", None), ("ply", 1), ("outro", None)], n_words=3, n_plies=5)  # 5 plies, 3 words
    times = [r["plies_show_at"][n] for n in range(1, 6)]
    assert all(b - a >= CFG["piece_move_ms"] for a, b in zip(times, times[1:]))
    assert times == sorted(times) and set(times) <= word_starts(r) | {s["start_ms"] for s in r["narration"]}


def test_plies_on_close_words_are_pushed_to_the_next_word_start():
    segments, voice = make([("cold_open", None), ("ply", 1), ("outro", None)], n_words=8)
    voice[1]["words"] = words(8, step=100)  # words only 100 ms apart
    r = layout(segments, voice, [], [{"ply": n} for n in range(1, 7)], CFG)
    times = [r["plies_show_at"][n] for n in range(1, 7)]
    assert all(b - a >= CFG["piece_move_ms"] for a, b in zip(times, times[1:]))
    assert set(times) <= word_starts(r) | {s["start_ms"] for s in r["narration"]}


def test_chapter_titles_are_never_cut_mid_word():
    long = "alpha " * 11 + "supercalifragilisticexpialidocious and more words follow after that"
    segments, voice = make([("cold_open", None), ("ply", 1), ("chapter", None)], n_words=3, duration=20000)
    segments[2]["text"] = long
    voice[2]["words"] = words(3)
    r = layout(segments, voice, [], [{"ply": n} for n in range(1, 4)], {**CFG, "min_chapters": 1})
    titles = [c["title"] for c in r["chapters"]]
    assert all(len(t) <= 70 for t in titles)
    assert any(t.startswith("alpha alpha") for t in titles)
    for t in titles:
        if t.startswith("alpha"): assert long[len(t)] == " ", t


def test_short_verdict_and_title_are_held_for_the_spec_minimum():
    result = run([("cold_open", None), ("title", None), ("ply", 1), ("verdict", None), ("outro", None)], duration=1500)
    n = result["narration"]
    assert n[2]["start_ms"] - n[1]["start_ms"] >= 2500  # title card 2.5 s
    assert n[1]["start_ms"] - n[0]["start_ms"] >= 6000  # cold open 6 s
    assert n[4]["start_ms"] - n[3]["start_ms"] >= 10000  # verdict 10 s


def test_shorts_have_no_scene_minimums():
    cfg = {**CFG, "min_scene_ms": {}, "outro_ms": 0, "min_chapters": 0}  # as timeline.run sets for Shorts
    result = run([("cold_open", None), ("ply", 1)], duration=1500, cfg=cfg)
    assert result["narration"][1]["start_ms"] - result["narration"][0]["start_ms"] < 6000
