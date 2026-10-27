"""tests/test_job_stages.py — unit tests for main.py's structured stage-progress
side channel (logs/<job_id>_stages.json), written explicitly by _write_stage_status
at each pipeline phase boundary (_banner/_summary). This is NOT log-regex parsing —
see job_monitor.py for that (separate, human-facing web dashboard) use case.
"""

import json
import os

import main


def _read_stages(job_id):
    path = os.path.join("logs", f"{job_id}_stages.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_write_stage_status_marks_done_running_pending(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    job_id = "job-mid"

    # current_step=4 -> "TTS — English" (BASE_STAGES step "4")
    main._write_stage_status(job_id, 4)

    data = _read_stages(job_id)
    by_status = {s["status"] for s in data["stages"]}
    assert "done" in by_status
    assert "running" in by_status
    assert "pending" in by_status

    statuses = {s["name"]: s["status"] for s in data["stages"]}
    assert statuses["Stockfish analysis"] == "done"
    assert statuses["Commentary (English)"] == "done"
    assert statuses["TTS — English"] == "running"
    assert statuses["Board frames"] == "pending"
    assert statuses["Thumbnails"] == "pending"


def test_write_stage_status_complete_marks_everything_done(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    job_id = "job-done"

    main._write_stage_status(job_id, 1)
    main._write_stage_status(job_id, "complete")

    data = _read_stages(job_id)
    assert all(s["status"] == "done" for s in data["stages"])


def test_write_stage_status_includes_hindi_avatar_upload_stages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    job_id = "job-flags-on"

    main._write_stage_status(job_id, 1, hindi=True, avatar=True, upload=True)

    names = {s["name"] for s in _read_stages(job_id)["stages"]}
    assert "Commentary (Hindi)" in names
    assert "Render — Hindi" in names
    assert "Talking avatar" in names
    assert "YouTube upload" in names


def test_write_stage_status_excludes_hindi_avatar_upload_stages_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    job_id = "job-flags-off"

    main._write_stage_status(job_id, 1, hindi=False, avatar=False, upload=False)

    names = {s["name"] for s in _read_stages(job_id)["stages"]}
    assert "Commentary (Hindi)" not in names
    assert "Render — Hindi" not in names
    assert "Talking avatar" not in names
    assert "YouTube upload" not in names


def test_write_stage_status_noop_without_job_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Must not raise and must not create logs/ or any file.
    main._write_stage_status(None, 1)
    main._write_stage_status("", 1)

    assert not os.path.exists("logs")


def test_banner_writes_stage_file_using_job_ctx(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    job_id = "job-ctx"
    monkeypatch.setitem(main._job_ctx, "job_id", job_id)
    monkeypatch.setitem(main._job_ctx, "hindi", False)
    monkeypatch.setitem(main._job_ctx, "avatar", False)
    monkeypatch.setitem(main._job_ctx, "upload", False)

    main._banner(2, "Commentary (English)")

    data = _read_stages(job_id)
    statuses = {s["name"]: s["status"] for s in data["stages"]}
    assert statuses["Commentary (English)"] == "running"
    assert statuses["Stockfish analysis"] == "done"


def test_set_job_ctx_reads_args(monkeypatch):
    # Register the current _job_ctx dict for automatic restoration, since
    # _set_job_ctx reassigns the module-level global outright.
    monkeypatch.setattr(main, "_job_ctx", dict(main._job_ctx))

    class Args:
        job_id = "abc123"
        hindi = True
        no_avatar = True
        upload = True
        no_upload = False

    main._set_job_ctx(Args())
    assert main._job_ctx == {
        "job_id": "abc123",
        "hindi": True,
        "avatar": False,
        "upload": True,
    }


def test_set_job_ctx_upload_suppressed_by_no_upload(monkeypatch):
    monkeypatch.setattr(main, "_job_ctx", dict(main._job_ctx))

    class Args:
        job_id = "abc123"
        hindi = False
        no_avatar = False
        upload = True
        no_upload = True

    main._set_job_ctx(Args())
    assert main._job_ctx["upload"] is False
