from unittest.mock import Mock, patch
from pathlib import Path

import pytest
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

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
    import os
    from argparse import Namespace
    client = Mock()
    client.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "UC123", "snippet": {"title": "ChessCode"}}]
    }
    with patch.dict(os.environ, {"YOUTUBE_REFRESH_TOKEN": "sentinel-refresh-secret"}), \
         patch.object(auth, "youtube_client", return_value=client):
        auth.main(Namespace(action="check"))
    captured = capsys.readouterr()
    assert "sentinel-refresh-secret" not in captured.out + captured.err


def test_login_uses_repo_root_and_restricts_token_permissions(tmp_path, monkeypatch, capsys):
    from argparse import Namespace
    monkeypatch.setattr(auth, "SECRETS_DIR", tmp_path / "data/secrets")
    monkeypatch.setattr(auth, "TOKEN_PATH", tmp_path / "data/secrets/youtube_token.json")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "sentinel-refresh-secret")
    flow = Mock()
    flow.run_local_server.return_value.to_json.return_value = '{"refresh_token":"secret"}'
    with patch.object(auth.InstalledAppFlow, "from_client_secrets_file", return_value=flow) as load, \
         patch.object(Path, "chmod", autospec=True) as chmod:
        assert auth.main(Namespace(action="login")) == 0
    assert load.call_args.args[0] == str(tmp_path / "data/secrets/client_secret.json")
    token = tmp_path / "data/secrets/youtube_token.json"
    assert token.read_text() == '{"refresh_token":"secret"}'
    chmod.assert_called_once_with(token, 0o600)
    captured = capsys.readouterr()
    assert "sentinel-refresh-secret" not in captured.out + captured.err


def test_login_missing_client_secret_is_actionable(tmp_path, monkeypatch, capsys):
    from argparse import Namespace
    monkeypatch.setattr(auth, "SECRETS_DIR", tmp_path / "data" / "secrets")
    with patch.object(auth.InstalledAppFlow, "from_client_secrets_file", side_effect=FileNotFoundError):
        assert auth.main(Namespace(action="login")) == 1
    assert "client_secret.json" in capsys.readouterr().out


def test_refresh_error_is_translated(monkeypatch):
    monkeypatch.setattr(auth, "TOKEN_PATH", auth.REPO_ROOT / "missing-token.json")
    with patch.object(auth.Credentials, "refresh", side_effect=RefreshError("invalid_grant")):
        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "sentinel")
        with pytest.raises(auth.AuthError):
            auth.load_credentials()


@pytest.mark.parametrize("error", [FileNotFoundError("missing"), KeyError("items"),
                                    HttpError(Mock(status=403), b"forbidden")])
def test_auth_check_errors_are_actionable(error):
    with patch.object(auth, "youtube_client", side_effect=error):
        with pytest.raises(auth.AuthError, match="auth login"):
            auth.check()
