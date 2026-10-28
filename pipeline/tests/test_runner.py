import json
from pathlib import Path

import pytest

from chesscode import context, runner


def modules(monkeypatch, tmp_path, input_by_stage=None, output_by_stage=None, errors=None):
    input_by_stage = input_by_stage or {}
    output_by_stage = output_by_stage or {}
    errors = errors or {}
    calls = []
    stage_modules = {}
    for name in runner.STAGES:
        def run(ctx, name=name):
            calls.append(name)
            if name in errors:
                raise errors[name]
            for output in output_by_stage.get(name, [f"{name}.json"]):
                value = name
                seed = ctx.spec_dir / "seed.txt"
                if name == "select" and seed.exists():
                    value += seed.read_text()
                (ctx.spec_dir / output).write_text(value)
        stage_modules[name] = type("Stage", (), {
            "INPUTS": input_by_stage.get(name, [f"{name}.json"]),
            "OUTPUTS": output_by_stage.get(name, [f"{name}.json"]),
            "run": staticmethod(run),
        })()
    monkeypatch.setattr(runner, "_load_stage", lambda stage: stage_modules[stage])
    monkeypatch.setattr(runner, "_context", lambda video_id: context.Context(
        video_id, tmp_path / video_id, tmp_path, {}, "en", "studio"
    ))
    return calls


def test_stage_order_until(monkeypatch, tmp_path):
    calls = modules(monkeypatch, tmp_path)
    runner.run_video("cc-2026-0042-en", until="classify")
    assert calls == runner.STAGES[:4]


def test_unchanged_inputs_skip(monkeypatch, tmp_path):
    calls = modules(monkeypatch, tmp_path, {"select": ["seed.txt"]})
    seed = tmp_path / "cc-2026-0042-en" / "seed.txt"
    seed.parent.mkdir()
    seed.write_text("same")
    runner.run_video("cc-2026-0042-en", until="select")
    runner.run_video("cc-2026-0042-en", until="select")
    assert calls == ["select"]


def test_changed_input_reruns_only_downstream(monkeypatch, tmp_path):
    calls = modules(monkeypatch, tmp_path, {"select": ["seed.txt"], "fetch": ["select.json"]}, {"select": ["select.json"]})
    seed = tmp_path / "cc-2026-0042-en" / "seed.txt"
    seed.parent.mkdir()
    seed.write_text("one")
    runner.run_video("cc-2026-0042-en", until="fetch")
    calls.clear()
    seed.write_text("two")
    runner.run_video("cc-2026-0042-en", until="fetch")
    assert calls == ["select", "fetch"]


def test_forced_stage_runs(monkeypatch, tmp_path):
    calls = modules(monkeypatch, tmp_path)
    runner.run_video("cc-2026-0042-en", stage="select")
    runner.run_video("cc-2026-0042-en", stage="select")
    assert calls == ["select", "select"]


def test_stage_error_exit_code_nonzero_and_logged(monkeypatch, tmp_path, caplog):
    calls = modules(monkeypatch, tmp_path, errors={"select": context.StageError("cc-2026-0042-en", "select", "bad")})
    assert runner.main(type("Args", (), {"video": "cc-2026-0042-en", "stage": None, "until": None})()) == 1
    assert "bad" in caplog.text
    assert calls == ["select"]


@pytest.mark.parametrize("video_id, expected", [
    ("cc-2026-0042-hi", (2026, 42, "hi", "studio")),
    ("cc-2026-5042-en", (2026, 5042, "en", "shorts")),
    ("cc-2026-6042-hi", (2026, 6042, "hi", "shorts")),
])
def test_parse_video_id(video_id, expected):
    assert context.parse_video_id(video_id) == expected


def test_config_missing_names_file(tmp_path):
    with pytest.raises(KeyError, match="missing.yaml"):
        from chesscode.config import load
        load("missing", root=tmp_path)


def test_directory_input_changes_hash(tmp_path):
    ctx = context.Context("cc-2026-0001-en", tmp_path / "spec", tmp_path, {}, "en", "studio")
    source = tmp_path / "content" / "openings"
    source.mkdir(parents=True)
    opening = source / "a.tsv"
    opening.write_text("one")
    before = runner._input_hash(ctx, ["content/openings"])
    opening.write_text("two")
    assert runner._input_hash(ctx, ["content/openings"]) != before
