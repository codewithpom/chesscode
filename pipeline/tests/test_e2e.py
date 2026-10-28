import json
import shutil
from pathlib import Path

import yaml

from chesscode import llm, tts
from chesscode import runner
from chesscode.stages import analyze, beats, classify, script, voice
from chesscode.stages.emit import validate

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "pipeline/tests/golden"


def test_e2e_golden_specs_validate(tmp_path, monkeypatch):
    games = yaml.safe_load((ROOT / "pipeline/tests/fixtures/golden_games.yaml").read_text())
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "content/openings", repo / "content/openings")
    shutil.copytree(ROOT / "spec", repo / "spec")
    shutil.copytree(GOLDEN / "pgn", repo / "pipeline/tests/golden/pgn")
    (repo / "content/games.yaml").write_text(yaml.safe_dump(games, sort_keys=False))
    monkeypatch.setattr(runner, "REPO_ROOT", repo)
    current_video = [""]
    make_context = runner._context

    def context_for(video_id):
        current_video[0] = video_id
        return make_context(video_id)

    monkeypatch.setattr(runner, "_context", context_for)

    def golden_analysis(ctx):
        name = Path(ctx.game["pgn_file"]).stem
        source = GOLDEN / "analysis" / f"{name}.json"
        shutil.copyfile(source, ctx.spec_dir / "analysis.json")

    monkeypatch.setattr(analyze, "run", golden_analysis)

    stage_cache = {}
    for module in (classify, beats):
        run = module.run

        def cached_stage(ctx, module=module, run=run):
            key = (Path(ctx.game["pgn_file"]).stem, module.__name__)
            path = ctx.spec_dir / module.OUTPUTS[0]
            if key in stage_cache:
                path.write_bytes(stage_cache[key])
            else:
                run(ctx)
                stage_cache[key] = path.read_bytes()

        monkeypatch.setattr(module, "run", cached_stage)

    def fake_llm(model_key, system, user, schema):
        if model_key == "checks":
            return {"ok": True, "best": 0}
        request, _ = json.JSONDecoder().raw_decode(user)
        beats = request["facts"]["beats.json"]
        n_plies = len(request["facts"]["classified.json"])
        short = "Target a total of" in user
        words = (84 if request["language"] == "hi" else 90) if short or "5000" in current_video[0] else 1200
        km_beats = [] if short or "5000" in current_video[0] else sorted((b for b in beats if b["intensity"] >= 2), key=lambda b: b["ply"])
        words -= 60 * len(km_beats)  # each key moment speaks 60 words (24 s with the fake voice)
        # sparse ply segments: plies before the first one, and gaps between them, must still be timed
        wanted = 4 if short else 12
        marks = sorted({1 + (n_plies - 1) * i // wanted for i in range(wanted)} | {max(1, n_plies // 3)})
        if short:  # a Short's ply segments start just before its beat, as the Shorts prompt asks
            first = max(1, request["short_beat"]["ply"] - 3)
            marks = [p for p in range(first, first + 4) if p <= n_plies]
        per = words // (len(marks) + 1)
        texts = [per] * len(marks) + [words - per * len(marks)]
        segments = [{"kind": "cold_open", "ply": None, "text": " ".join(["develops"] * texts[-1])}]
        segments += [{"kind": "ply", "ply": ply, "text": " ".join(["develops"] * count)} for ply, count in zip(marks, texts)]
        for beat in reversed(km_beats):  # right after the ply segment that reaches the beat's move
            at = max(i for i, seg in enumerate(segments) if seg["kind"] == "ply" and seg["ply"] <= beat["ply"]) if any(seg["kind"] == "ply" and seg["ply"] <= beat["ply"] for seg in segments) else 1
            segments.insert(at + 1, {"kind": "key_moment", "ply": beat["ply"], "text": " ".join(["develops"] * 60)})
        return {
            "segments": segments,
            "mascot_lines": {beat["beat_id"]: f"{current_video[0]} {beat['beat_id']} changes everything." for beat in beats},
            "titles": ["A quiet move changes everything", "A chess game with a twist", "The position turns"] ,
            "hook": "A shifting position decides the game.",
            "player_facts": {"white": "White fact.", "black": "Black fact."},
            "cold_open_hook": "A shifting position",
            "thumbnail_text": "Position turns",
            "key_moment_labels": {} if short else {beat["beat_id"]: f"Key moment {beat['beat_id']}" for beat in beats if beat["intensity"] >= 2},
        }

    monkeypatch.setattr(llm, "complete_json", fake_llm)

    def fake_synthesize(provider, text, voice, language, cache_dir):
        path = tmp_path / f"fake-{abs(hash(text))}-{len(text)}.mp3"
        path.write_text(text, encoding="utf-8")
        return path, [{"w": w, "start_ms": i * 400, "end_ms": i * 400 + 350} for i, w in enumerate(text.split())]

    monkeypatch.setattr(tts, "synthesize", fake_synthesize)
    monkeypatch.setattr(voice, "_duration_ms", lambda path: len(Path(path).read_text(encoding="utf-8").split()) * 400)
    monkeypatch.setattr(script, "ensure_specific", lambda output, *args: output)

    specs = []
    for game in games:
        for game_no in (game["game_no"], game["game_no"] + 5000):
            for language in ("en", "hi"):
                video_id = f"cc-2026-{game_no:04d}-{language}"
                runner.run_video(video_id, until="emit")
                spec = json.loads((repo / "build/specs" / video_id / "video_spec.json").read_text())
                validate(spec)
                specs.append(spec)

    assert len(specs) == 40
    assert {spec["spec_version"] for spec in specs} == {"1.1.0"}
    for spec in specs:
        assert spec["thumbnail"]["ply"] == spec["cold_open"]["ply_to"], spec["video_id"]
        assert [k["beat_id"] for k in spec["key_moments"]] == ([] if spec["template"] == "shorts" else [b["beat_id"] for b in spec["beats"] if b["intensity"] >= 2]), spec["video_id"]
    for spec in specs:
        times = [p["show_at_ms"] for p in spec["plies"]]
        assert times == sorted(times), spec["video_id"]
        starts = {w["start_ms"] for seg in spec["narration"] for w in seg["words"]} | {seg["start_ms"] for seg in spec["narration"]}
        assert set(times) <= starts, spec["video_id"]
        first_ply_segment = next(seg for seg in spec["narration"] if seg["kind"] == "ply")
        assert times[0] == first_ply_segment["start_ms"], spec["video_id"]
        assert all(b["at_ms"] == times[b["ply"] - 1] for b in spec["beats"]), spec["video_id"]
    assert {spec["template"] for spec in specs} == {"studio", "shorts"}
    assert all(spec["youtube"]["publish_at"].endswith("Z") for spec in specs)
    shorts = [spec for spec in specs if spec["template"] == "shorts"]
    assert all(spec["format"] == {"width": 1080, "height": 1920, "fps": 30} for spec in shorts)
    assert all(spec["duration_ms"] <= 59000 for spec in shorts)
    assert all(len(spec["beats"]) == 1 for spec in shorts)
    assert all(spec["narration"][0]["kind"] == "cold_open" for spec in shorts)

    by_pair = {}
    for spec in specs:
        game_no = int(spec["pair_id"].split("-")[2])
        if game_no >= 5000:
            game_no -= 5000
        by_pair.setdefault(game_no, {})[(spec["template"], spec["language"])] = spec["youtube"]["publish_at"]
    for slots in by_pair.values():
        for language in ("en", "hi"):
            long = slots[("studio", language)]
            short = slots[("shorts", language)]
            from datetime import date
            assert 1 <= (date.fromisoformat(long[:10]) - date.fromisoformat(short[:10])).days <= 3

    en_hi_pairs = {}
    for spec in specs:
        en_hi_pairs.setdefault((spec["pair_id"], spec["template"]), {})[spec["language"]] = spec["youtube"]["publish_at"]
    assert all(value["en"][:10] != value["hi"][:10] for value in en_hi_pairs.values())
    assert len({spec["youtube"]["publish_at"] for spec in specs}) == 40
    for language in ("en", "hi"):
        longform = sorted((spec for spec in specs if spec["template"] == "studio" and spec["language"] == language), key=lambda spec: spec["youtube"]["publish_at"])
        series = [spec["series"] for spec in longform]
        assert all(not (series[i] == series[i + 1] == series[i + 2]) for i in range(len(series) - 2))
    assert min(spec["youtube"]["publish_at"] for spec in specs).startswith("2026-11-16")
