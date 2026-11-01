import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from chesscode import batch, ledger

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))
    wf["triggers"] = wf.get("on", wf.get(True))  # PyYAML reads the bare key `on` as True
    return wf


def steps_text(job):
    return "\n".join(str(s.get("run", "")) for s in job["steps"])


def test_batch_yml_matrix_and_limits():
    wf = load("batch.yml")
    assert set(wf["triggers"]) == {"workflow_dispatch", "workflow_call"}
    assert set(wf["triggers"]["workflow_dispatch"]["inputs"]) == {"batch_id", "video_ids", "upload"}
    assert wf["permissions"] == {"contents": "read"}
    job = wf["jobs"]["video"]
    assert job["timeout-minutes"] == 300
    assert job["strategy"]["fail-fast"] is False and job["strategy"]["max-parallel"] == 2
    assert "fromJson(inputs.video_ids)" in job["strategy"]["matrix"]["video_id"]
    assert job["concurrency"]["group"] == "video-${{ matrix.video_id }}"
    assert job["concurrency"].get("cancel-in-progress") is False


def test_upload_jobs_wait_for_shared_playlist_config():
    wf = load("batch.yml")
    prepare = wf["jobs"]["prepare-upload"]
    assert prepare["if"] == "inputs.upload"
    assert prepare["concurrency"]["group"] == "youtube-playlists"
    assert "auth check" in steps_text(prepare) and "upload --create-playlists" in steps_text(prepare)
    video = wf["jobs"]["video"]
    assert video["needs"] == "prepare-upload" and "'success'" in video["if"]
    config = next(s for s in video["steps"] if s.get("uses", "").startswith("actions/download-artifact"))
    assert config["with"] == {"name": "upload-config", "path": "config"}


def test_batch_yml_steps():
    job = load("batch.yml")["jobs"]["video"]
    uses = [s.get("uses", "") for s in job["steps"]]
    assert any(u.startswith("actions/setup-python") for u in uses) and any(u.startswith("actions/setup-node") for u in uses)
    caches = [s for s in job["steps"] if s.get("uses", "").startswith("actions/cache")]
    paths = " ".join(c["with"]["path"] for c in caches)
    assert "remotion/node_modules" in paths and "tts_cache" in paths
    tts = next(c for c in caches if "tts_cache" in c["with"]["path"])
    assert "content/scripts/**" in tts["with"]["key"] and "config/models.yaml" in tts["with"]["key"]
    text = steps_text(job)
    assert "remotion browser ensure" in text and "chesscode batch" in text
    auth = next(s for s in job["steps"] if "auth check" in str(s.get("run", "")))
    assert "inputs.upload" in auth["if"]


def test_batch_yml_never_uploads_mp4_and_never_echoes_secrets():
    wf = load("batch.yml")
    job = wf["jobs"]["video"]
    artifacts = [s for s in job["steps"] if s.get("uses", "").startswith("actions/upload-artifact")]
    assert artifacts and artifacts[0]["with"]["name"] == "result-${{ matrix.video_id }}"
    for step in artifacts:
        assert "mp4" not in step["with"]["path"].lower() and "out." not in step["with"]["path"]
        assert "build/specs/${{ matrix.video_id }}/result.json" in step["with"]["path"]
    assert "secrets." not in steps_text(job)  # secrets only reach steps through env:


def test_collect_yml():
    wf = load("collect.yml")
    assert wf["triggers"]["workflow_run"]["workflows"] == ["batch"] and wf["triggers"]["workflow_run"]["types"] == ["completed"]
    assert wf["permissions"]["contents"] == "write"
    job = wf["jobs"]["collect"]
    text = steps_text(job)
    assert "ledger collect" in text and "git push" in text and "GITHUB_STEP_SUMMARY" in text
    assert "mp4" not in json.dumps(job).lower()
    assert any(s.get("uses", "").startswith("actions/download-artifact") for s in job["steps"])


# --- batch.py ---
@pytest.fixture
def stubbed(tmp_path, monkeypatch):
    spec_dir = tmp_path / "specs" / "cc-2026-0001-en"
    spec_dir.mkdir(parents=True)
    spec = json.loads((ROOT / "spec" / "fixtures" / "cc-2026-0001-en" / "video_spec.json").read_text(encoding="utf-8"))
    commands = []
    monkeypatch.setattr(batch, "SPECS", tmp_path / "specs")
    monkeypatch.setattr(batch, "run_video", lambda *a, **k: (spec_dir / "video_spec.json").write_text(json.dumps(spec), encoding="utf-8"))
    monkeypatch.setattr(batch, "_sh", lambda cmd, cwd=None: commands.append(cmd))
    return spec_dir, commands


def test_batch_render_commands_and_result_when_qa_fails(stubbed, monkeypatch):
    spec_dir, commands = stubbed
    monkeypatch.setattr(batch.qa, "run_checks", lambda *a: {"passed": False})
    uploaded = Mock()
    monkeypatch.setattr(batch.upload, "upload_from_spec", uploaded)
    assert batch.run_one("cc-2026-0001-en", do_upload=True, batch_id="b0") == 0
    render = next(c for c in commands if "render" in c)
    assert render[render.index("render") + 1] == "StudioVideo" and "--public-dir=" + str(spec_dir) in render and "--crf=18" in render
    assert any("still" in c and "Thumbnail" in c for c in commands)
    uploaded.assert_not_called()
    result = json.loads((spec_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed_qa" and result["qa_passed"] is False and result["batch_id"] == "b0" and "render_seconds" in result


def test_batch_without_upload_flag_is_rendered(stubbed, monkeypatch):
    spec_dir, _ = stubbed
    monkeypatch.setattr(batch.qa, "run_checks", lambda *a: {"passed": True})
    assert batch.run_one("cc-2026-0001-en", do_upload=False, batch_id="b0") == 0
    assert json.loads((spec_dir / "result.json").read_text(encoding="utf-8"))["status"] == "rendered"


def test_batch_upload_merges_upload_result(stubbed, monkeypatch):
    spec_dir, _ = stubbed
    monkeypatch.setattr(batch.qa, "run_checks", lambda *a: {"passed": True})
    monkeypatch.setattr(batch.auth, "youtube_client", lambda: object())
    monkeypatch.setattr(batch.upload, "upload_from_spec", lambda *a, **k: {"video_id": "cc-2026-0001-en", "status": "scheduled", "youtube_id": "yt1", "publish_at": "2026-11-17T18:30:00Z"})
    assert batch.run_one("cc-2026-0001-en", do_upload=True, batch_id="b0") == 0
    result = json.loads((spec_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "scheduled" and result["youtube_id"] == "yt1" and result["qa_passed"] is True


def test_batch_refused_upload_is_recorded_not_crash(stubbed, monkeypatch):
    spec_dir, _ = stubbed
    monkeypatch.setattr(batch.qa, "run_checks", lambda *a: {"passed": True})
    monkeypatch.setattr(batch.auth, "youtube_client", lambda: object())
    def refuse(*a, **k): raise batch.upload.UploadRefused("publish_at must be at least 2 hours in the future")
    monkeypatch.setattr(batch.upload, "upload_from_spec", refuse)
    assert batch.run_one("cc-2026-0001-en", do_upload=True, batch_id="b0") == 0
    result = json.loads((spec_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed_upload" and "2 hours" in result["error"]


# --- ledger collect ---
def test_collect_appends_rows_and_writes_review(tmp_path):
    art = tmp_path / "collected"
    for vid, status in (("v1", "scheduled"), ("v2", "failed_qa")):
        d = art / f"result-{vid}"; d.mkdir(parents=True)
        (d / "result.json").write_text(json.dumps({"video_id": vid, "status": status, "youtube_id": "yt" if status == "scheduled" else "", "publish_at": "2026-11-17T18:30:00Z",
                                                  "title": f"Title, {vid}", "qa_passed": status == "scheduled", "render_seconds": 90, "batch_id": "b7"}), encoding="utf-8")
    (art / "result-empty").mkdir()  # a job that crashed uploads nothing
    summary = ledger.collect(art, tmp_path / "log.csv", tmp_path / "review", "https://example/run/1")
    assert set(ledger.read_ledger(tmp_path / "log.csv")) == {"v1", "v2"}
    assert ledger.read_ledger(tmp_path / "log.csv")["v2"]["status"] == "failed_qa"
    assert "| v1 |" in summary and "| v2 |" in summary and "1.5" in summary
    review = (tmp_path / "review" / "b7.md").read_text(encoding="utf-8")
    assert "Title, v1" in review and "https://example/run/1" in review
