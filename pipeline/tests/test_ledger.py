from unittest.mock import Mock

import pytest

from chesscode import ledger


def row(video_id, status="scheduled", **kw):
    base = {"video_id": video_id, "status": status, "youtube_id": "yt-" + video_id, "publish_at": "2026-11-17T18:30:00Z",
            "title": "T, with comma", "qa_passed": "true", "render_seconds": "60", "batch_id": "b0", "updated_at": "2026-10-29T00:00:00Z"}
    return {**base, **kw}


def test_last_row_wins_and_header_once(tmp_path):
    path = tmp_path / "data" / "upload_log.csv"
    ledger.append(path, row("a", "rendered", youtube_id=""))
    ledger.append(path, row("b"))
    ledger.append(path, row("a", "scheduled"))
    assert path.read_text(encoding="utf-8").count("video_id,status") == 1
    rows = ledger.read_ledger(path)
    assert rows["a"]["status"] == "scheduled" and rows["b"]["title"] == "T, with comma"


def test_read_missing_ledger_is_empty(tmp_path):
    assert ledger.read_ledger(tmp_path / "nope.csv") == {}


def test_append_rejects_bad_status_or_missing_column(tmp_path):
    with pytest.raises(ValueError, match="status"):
        ledger.append(tmp_path / "l.csv", row("a", "published"))
    bad = row("a"); del bad["title"]
    with pytest.raises(ValueError, match="title"):
        ledger.append(tmp_path / "l.csv", bad)


def fake_client(items, privacy="private", publish_at="2026-11-17T18:30:00Z"):
    client = Mock()
    client.channels.return_value.list.return_value.execute.return_value = {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]}
    client.playlistItems.return_value.list.return_value.execute.return_value = {"items": [
        {"snippet": {"resourceId": {"videoId": yt}, "description": f"x\n\nccid: {cc}"}} for cc, yt in items]}
    client.videos.return_value.list.return_value.execute.side_effect = lambda: {"items": [
        {"id": yt, "status": {"privacyStatus": privacy, "publishAt": publish_at}} for _, yt in items]}
    return client


def test_check_reports_each_mismatch_type(tmp_path):
    path = tmp_path / "l.csv"
    ledger.append(path, row("ok"))
    ledger.append(path, row("gone"))
    ledger.append(path, row("moved", publish_at="2026-11-20T18:30:00Z"))
    ledger.append(path, row("failed", "failed_qa", youtube_id=""))  # not expected in Studio
    client = fake_client([("ok", "yt-ok"), ("moved", "yt-moved"), ("stray", "yt-stray")])
    problems = ledger.check(client, path)
    assert sorted(p.split(":")[0] for p in problems) == ["gone", "moved", "stray"]
    assert any("missing in Studio" in p for p in problems if p.startswith("gone"))
    assert any("different publishAt" in p for p in problems if p.startswith("moved"))
    assert any("missing in ledger" in p for p in problems if p.startswith("stray"))


def test_check_clean(tmp_path):
    path = tmp_path / "l.csv"
    ledger.append(path, row("ok"))
    assert ledger.check(fake_client([("ok", "yt-ok")]), path) == []
