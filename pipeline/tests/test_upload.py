from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
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


def test_upload_skips_when_ccid_exists(tmp_path):
    client = Mock()
    with patch.object(upload, "find_existing", return_value="yt123"):
        result = upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", [], NOW + timedelta(hours=3), "en", NOW)
    assert result == "yt123"
    client.videos.return_value.insert.assert_not_called()


def test_upload_body_private_with_publish_at(tmp_path):
    client = Mock()
    client.videos.return_value.insert.return_value.execute.return_value = {"id": "yt1"}
    with patch.object(upload, "find_existing", return_value=None), patch.object(upload, "MediaFileUpload"):
        upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", ["chess"], NOW + timedelta(hours=3), "hi", NOW)
    body = client.videos.return_value.insert.call_args.kwargs["body"]
    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["publishAt"].endswith("Z")
    assert body["status"]["selfDeclaredMadeForKids"] is False
    assert body["snippet"]["categoryId"] == "20"
    assert body["snippet"]["defaultLanguage"] == body["snippet"]["defaultAudioLanguage"] == "hi"


def test_retries_5xx_then_succeeds(tmp_path):
    client = Mock()
    request = client.videos.return_value.insert.return_value
    request.execute.side_effect = [HttpError(Mock(status=500), b"server error"), {"id": "yt1"}]
    with patch.object(upload, "find_existing", return_value=None), patch.object(upload, "MediaFileUpload"), patch.object(upload.time, "sleep"):
        assert upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", [], NOW + timedelta(hours=3), "en", NOW) == "yt1"
    assert request.execute.call_count == 2


def test_gives_up_after_5_tries(tmp_path):
    client = Mock()
    request = client.videos.return_value.insert.return_value
    request.execute.side_effect = HttpError(Mock(status=503), b"server error")
    with patch.object(upload, "find_existing", return_value=None), patch.object(upload, "MediaFileUpload"), patch.object(upload.time, "sleep"):
        with pytest.raises(Exception):
            upload.upload_video(client, tmp_path / "x.mp4", "game-1", "title", "desc", [], NOW + timedelta(hours=3), "en", NOW)
    assert request.execute.call_count == 5
