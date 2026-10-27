from unittest.mock import Mock, patch

import pytest
from google.auth.exceptions import RefreshError

from chesscode import auth


def test_check_returns_channel():
    client = Mock()
    client.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "UC123", "snippet": {"title": "ChessCode"}}]
    }
    with patch.object(auth, "youtube_client", return_value=client):
        assert auth.check() == {"channel_id": "UC123", "title": "ChessCode"}


def test_invalid_grant_raises_auth_error_mentioning_consent_screen(monkeypatch):
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "refresh")
    with patch.object(auth, "_credentials_from_env", side_effect=RefreshError("invalid_grant")):
        with pytest.raises(auth.AuthError, match="In production"):
            auth.load_credentials()


def test_env_credentials_preferred_over_file(monkeypatch):
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "id")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "refresh")
    with patch.object(auth.Credentials, "refresh"):
        credentials = auth.load_credentials()
    assert credentials.refresh_token == "refresh"


def test_check_output_never_contains_refresh_token(capsys):
    client = Mock()
    client.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "UC123", "snippet": {"title": "ChessCode"}}]
    }
    with patch.object(auth, "youtube_client", return_value=client):
        auth.main(Mock(action="check"))
    assert "refresh-token" not in capsys.readouterr().out
