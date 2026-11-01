from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import http.client
from googleapiclient.errors import HttpError

from chesscode import upload


NOW = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)


def test_refuses_naive_datetime():
    with pytest.raises(upload.UploadRefused):
        upload.check_publish_at(NOW.replace(tzinfo=None), NOW)


def test_refuses_past():
    with pytest.raises(upload.UploadRefused):
        upload.check_publish_at(NOW - timedelta(seconds=1), NOW)


def test_refuses_under_two_hours():
    with pytest.raises(upload.UploadRefused):
        upload.check_publish_at(NOW + timedelta(hours=1, minutes=59), NOW)


def test_accepts_two_hours_ahead():
    upload.check_publish_at(NOW + timedelta(hours=2, minutes=1), NOW)


def test_ccid_footer_idempotent():
    result = upload.with_ccid_footer("Description\n\nccid: game-1", "game-1")
    assert result == "Description\n\nccid: game-1"


def test_find_existing_pages_through_playlist():
    client = Mock()
    channel_list = client.channels.return_value.list.return_value
    channel_list.execute.return_value = {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]}
    pages = client.playlistItems.return_value.list.return_value
    pages.execute.side_effect = [
        {"items": [], "nextPageToken": "next"},
        {"items": [{"snippet": {"resourceId": {"videoId": "yt123"}, "description": "x\nccid: target"}}]},
    ]
    assert upload.find_existing(client, "target") == "yt123"
    assert pages.execute.call_count == 2
    assert all(call.kwargs["maxResults"] == 50 for call in client.playlistItems.return_value.list.call_args_list)


def test_upload_skips_when_ccid_exists(tmp_path):
    client = Mock()
    with patch.object(upload, "find_existing", return_value="yt123"):
        result = upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", [], NOW + timedelta(hours=3), "en", NOW)
    assert result == "yt123"
    client.videos.return_value.insert.assert_not_called()


def test_upload_body_private_with_publish_at(tmp_path):
    client = Mock()
    client.videos.return_value.insert.return_value.execute.return_value = {"id": "yt1"}
    with patch.object(upload, "find_existing", return_value=None), patch.object(upload, "MediaFileUpload") as media:
        upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", ["chess"], NOW + timedelta(hours=3), "hi", NOW)
    media.assert_called_once_with(str(tmp_path / "x.mp4"), resumable=True)
    body = client.videos.return_value.insert.call_args.kwargs["body"]
    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["publishAt"].endswith("Z")
    assert body["status"]["selfDeclaredMadeForKids"] is False
    assert body["status"]["containsSyntheticMedia"] is False
    assert body["snippet"]["categoryId"] == "20"
    assert body["snippet"]["defaultLanguage"] == body["snippet"]["defaultAudioLanguage"] == "hi"
    assert body["status"]["publishAt"] == (NOW + timedelta(hours=3)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_body_truncates_publish_microseconds():
    publish_at = NOW + timedelta(hours=3, microseconds=654321)
    assert upload.build_body("id", "title", "desc", [], publish_at, "en")["status"]["publishAt"] == \
        publish_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_description_limit_includes_ccid_footer():
    with pytest.raises(upload.UploadRefused):
        upload.build_body("game-1", "title", "x" * 4987, [], NOW + timedelta(hours=3), "en")


@pytest.mark.parametrize("title,description", [("x" * 101, "ok"), ("ok", "x" * 5001)])
def test_rejects_oversized_metadata(tmp_path, title, description):
    with pytest.raises(upload.UploadRefused):
        upload.upload_video(Mock(), tmp_path / "x.mp4", "game-1", title, description, [],
                            NOW + timedelta(hours=3), "en", NOW)


def test_retries_5xx_then_succeeds(tmp_path):
    client = Mock()
    request = client.videos.return_value.insert.return_value
    request.execute.side_effect = [HttpError(Mock(status=500), b"server error"), {"id": "yt1"}]
    with patch.object(upload, "find_existing", return_value=None), patch.object(upload, "MediaFileUpload"), patch.object(upload.time, "sleep"):
        assert upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", [], NOW + timedelta(hours=3), "en", NOW) == "yt1"
    assert request.execute.call_count == 2


def test_retries_socket_error(tmp_path):
    client = Mock()
    request = client.videos.return_value.insert.return_value
    request.execute.side_effect = [OSError("connection reset"), {"id": "yt1"}]
    with patch.object(upload, "find_existing", return_value=None) as find, \
         patch.object(upload, "MediaFileUpload"), patch.object(upload.time, "sleep"):
        assert upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", [],
                                   NOW + timedelta(hours=3), "en", NOW) == "yt1"
    assert request.execute.call_count == 2 and find.call_count == 2


def test_transport_retry_checks_playlist_for_ambiguous_success(tmp_path):
    client = Mock()
    request = client.videos.return_value.insert.return_value
    request.execute.side_effect = http.client.IncompleteRead(b"partial")
    with patch.object(upload, "find_existing", side_effect=[None, "already-uploaded"] ) as find, \
         patch.object(upload, "MediaFileUpload"), patch.object(upload.time, "sleep"):
        result = upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", [],
                                     NOW + timedelta(hours=3), "en", NOW)
    assert result == "already-uploaded"
    assert find.call_count == 2
    assert request.execute.call_count == 1


def test_does_not_retry_client_error(tmp_path):
    client = Mock()
    request = client.videos.return_value.insert.return_value
    request.execute.side_effect = HttpError(Mock(status=400), b"bad request")
    with patch.object(upload, "find_existing", return_value=None), patch.object(upload, "MediaFileUpload"), \
         patch.object(upload.time, "sleep"):
        with pytest.raises(HttpError):
            upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", [],
                                NOW + timedelta(hours=3), "en", NOW)
    assert request.execute.call_count == 1


def test_gives_up_after_5_tries(tmp_path):
    client = Mock()
    request = client.videos.return_value.insert.return_value
    request.execute.side_effect = HttpError(Mock(status=503), b"server error")
    with patch.object(upload, "find_existing", return_value=None), patch.object(upload, "MediaFileUpload"), patch.object(upload.time, "sleep"):
        with pytest.raises(Exception):
            upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", [], NOW + timedelta(hours=3), "en", NOW)
    assert request.execute.call_count == 5


# --- upload_from_spec (M6) ---
import json
import shutil

from chesscode import ledger

FIXTURE_SPEC = Path(__file__).resolve().parents[2] / "spec" / "fixtures" / "cc-2026-0001-en" / "video_spec.json"
PUBLISH = datetime(2026, 11, 17, 18, 30, tzinfo=timezone.utc)
FAKE_CFG = {"category_id": 20, "contains_synthetic_media": False, "daily_cap": 60, "playlists": {"legendary_games": "PL1"}}


@pytest.fixture
def spec_dir(tmp_path):
    d = tmp_path / "spec"
    d.mkdir()
    shutil.copy(FIXTURE_SPEC, d / "video_spec.json")
    (d / "out.mp4").write_bytes(b"mp4")
    (d / "thumb.png").write_bytes(b"png")
    (d / "qa.json").write_text(json.dumps({"passed": True}), encoding="utf-8")
    return d


def ledger_row(video_id, status="scheduled", **kw):
    return {"video_id": video_id, "status": status, "youtube_id": "yt-" + video_id, "publish_at": "2026-11-17T18:30:00Z", "title": "t",
            "qa_passed": "true", "render_seconds": "1", "batch_id": "b", "updated_at": "2026-10-29T00:00:00Z", **kw}


def go(client, spec_dir, tmp_path, now=NOW, existing=None, cfg=FAKE_CFG, **kw):
    with patch.object(upload, "find_existing", **({"side_effect": existing} if isinstance(existing, list) else {"return_value": existing})) as find, \
         patch.object(upload, "MediaFileUpload"), patch.object(upload.time, "sleep"), patch.object(upload, "load", return_value=cfg):
        result = upload.upload_from_spec(client, spec_dir, tmp_path / "ledger.csv", now, **kw)
    return result, find


def test_from_spec_happy_path(spec_dir, tmp_path):
    client = Mock()
    client.videos.return_value.insert.return_value.execute.return_value = {"id": "yt1"}
    result, _ = go(client, spec_dir, tmp_path)
    assert result == {"video_id": "cc-2026-0001-en", "status": "scheduled", "youtube_id": "yt1", "publish_at": "2026-11-17T18:30:00Z"}
    client.thumbnails.return_value.set.assert_called_once()
    assert client.playlistItems.return_value.insert.call_args.kwargs["body"]["snippet"]["playlistId"] == "PL1"
    assert "#Shorts" not in client.videos.return_value.insert.call_args.kwargs["body"]["snippet"]["description"]


def test_from_spec_refuses_failed_qa(spec_dir, tmp_path):
    (spec_dir / "qa.json").write_text(json.dumps({"passed": False}), encoding="utf-8")
    client = Mock()
    result, _ = go(client, spec_dir, tmp_path)
    assert result["status"] == "failed_qa"
    client.videos.return_value.insert.assert_not_called()


def test_from_spec_missing_qa_json_stops(spec_dir, tmp_path):
    (spec_dir / "qa.json").unlink()
    with pytest.raises(upload.UploadRefused, match="qa.json"):
        go(Mock(), spec_dir, tmp_path)


def test_from_spec_ledger_hit_skips_without_touching_youtube(spec_dir, tmp_path):
    ledger.append(tmp_path / "ledger.csv", ledger_row("cc-2026-0001-en", youtube_id="ytOLD"))
    client = Mock()
    result, find = go(client, spec_dir, tmp_path)
    assert result["status"] == "scheduled" and result["youtube_id"] == "ytOLD"
    find.assert_not_called(); client.videos.return_value.insert.assert_not_called()


def test_from_spec_playlist_hit_skips(spec_dir, tmp_path):
    client = Mock()
    result, _ = go(client, spec_dir, tmp_path, existing="ytEARLIER")
    assert result["youtube_id"] == "ytEARLIER" and result["status"] == "scheduled"
    client.videos.return_value.insert.assert_not_called()


def test_from_spec_timeout_then_retry_finds_upload_no_second_insert(spec_dir, tmp_path):
    client = Mock()
    insert = client.videos.return_value.insert
    insert.return_value.execute.side_effect = OSError("timed out")
    result, _ = go(client, spec_dir, tmp_path, existing=[None, "ytLANDED"])
    assert result["youtube_id"] == "ytLANDED"
    assert insert.call_count == 1 and insert.return_value.execute.call_count == 1


def test_from_spec_refuses_one_hour_ahead(spec_dir, tmp_path):
    client = Mock()
    with pytest.raises(upload.UploadRefused):
        go(client, spec_dir, tmp_path, now=PUBLISH - timedelta(hours=1))
    client.videos.return_value.insert.assert_not_called()


def test_from_spec_cap_reached_defers(spec_dir, tmp_path):
    for i in range(60):  # NOW is 05:00 Pacific on Oct 27
        ledger.append(tmp_path / "ledger.csv", ledger_row(f"v{i}", updated_at="2026-10-27T08:00:00Z"))
    ledger.append(tmp_path / "ledger.csv", ledger_row("old", updated_at="2026-10-26T08:00:00Z"))  # other Pacific day: not counted
    client = Mock()
    result, _ = go(client, spec_dir, tmp_path)
    assert result["status"] == "deferred" and result["youtube_id"] == ""
    client.videos.return_value.insert.assert_not_called()


def test_from_spec_under_cap_proceeds(spec_dir, tmp_path):
    for i in range(59):
        ledger.append(tmp_path / "ledger.csv", ledger_row(f"v{i}", updated_at="2026-10-27T08:00:00Z"))
    client = Mock()
    client.videos.return_value.insert.return_value.execute.return_value = {"id": "yt1"}
    assert go(client, spec_dir, tmp_path)[0]["status"] == "scheduled"


def test_from_spec_thumbnail_failure_leaves_scheduled_needs_repair(spec_dir, tmp_path):
    client = Mock()
    client.videos.return_value.insert.return_value.execute.return_value = {"id": "yt1"}
    client.thumbnails.return_value.set.return_value.execute.side_effect = HttpError(Mock(status=403), b"no")
    result, _ = go(client, spec_dir, tmp_path)
    assert result["status"] == "scheduled" and result["needs_repair"] is True and result["youtube_id"] == "yt1"
    client.playlistItems.return_value.insert.assert_called_once()


def test_from_spec_unset_playlist_refused_before_insert(spec_dir, tmp_path):
    client = Mock()
    with pytest.raises(upload.UploadRefused, match="playlist"):
        go(client, spec_dir, tmp_path, cfg={**FAKE_CFG, "playlists": {"legendary_games": None}})
    client.videos.return_value.insert.assert_not_called()


def test_shorts_get_hashtag(spec_dir, tmp_path):
    spec = json.loads((spec_dir / "video_spec.json").read_text(encoding="utf-8"))
    spec["template"] = "shorts"
    (spec_dir / "video_spec.json").write_text(json.dumps(spec), encoding="utf-8")
    client = Mock()
    client.videos.return_value.insert.return_value.execute.return_value = {"id": "yt1"}
    go(client, spec_dir, tmp_path)
    description = client.videos.return_value.insert.call_args.kwargs["body"]["snippet"]["description"]
    assert "#Shorts" in description and description.splitlines()[-1] == "ccid: cc-2026-0001-en"


def test_repair_reruns_thumbnail_and_playlist_once(spec_dir, tmp_path):
    ledger.append(tmp_path / "ledger.csv", ledger_row("cc-2026-0001-en", youtube_id="ytOLD"))
    client = Mock()
    client.playlistItems.return_value.list.return_value.execute.return_value = {"items": []}
    result, _ = go(client, spec_dir, tmp_path, repair=True)
    assert result["status"] == "scheduled" and result["youtube_id"] == "ytOLD" and not result.get("needs_repair")
    client.videos.return_value.insert.assert_not_called()
    client.thumbnails.return_value.set.assert_called_once()
    client.playlistItems.return_value.insert.assert_called_once()
    client.playlistItems.return_value.list.return_value.execute.return_value = {"items": [{"id": "x"}]}
    go(client, spec_dir, tmp_path, repair=True)
    client.playlistItems.return_value.insert.assert_called_once()  # already in the playlist: not added twice


def test_repair_requires_scheduled_ledger_row(spec_dir, tmp_path):
    with pytest.raises(upload.UploadRefused, match="repair"):
        go(Mock(), spec_dir, tmp_path, repair=True)


def test_create_playlists_fills_only_null_ids(tmp_path):
    path = tmp_path / "youtube.yaml"
    path.write_text("daily_cap: 60\nplaylists:\n  legendary_games: PLOLD\n  opening_explained: null\n", encoding="utf-8")
    client = Mock()
    client.playlists.return_value.insert.return_value.execute.return_value = {"id": "PLNEW"}
    upload.create_playlists(client, path)
    body = client.playlists.return_value.insert.call_args.kwargs["body"]
    assert body["snippet"]["title"] == "Opening Explained" and body["status"]["privacyStatus"] == "public"
    assert client.playlists.return_value.insert.call_count == 1
    text = path.read_text(encoding="utf-8")
    assert "legendary_games: PLOLD" in text and "opening_explained: PLNEW" in text
