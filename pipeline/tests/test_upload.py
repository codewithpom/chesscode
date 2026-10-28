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
