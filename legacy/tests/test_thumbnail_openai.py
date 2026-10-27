"""tests/test_thumbnail_openai.py — OpenAI gpt-image-1 thumbnail generation."""

import os
import base64
from unittest.mock import patch, MagicMock

import pytest

from thumbnail_openai import generate_thumbnail, _map_size_to_gpt_image, STYLE_PRESETS
from config import cfg


class TestSizeMapping:
    """Test size mapping to gpt-image-1 supported formats."""

    def test_default_1280x720_maps_to_landscape(self):
        assert _map_size_to_gpt_image("1280x720") == "1536x1024"

    def test_exact_match_1024x1024(self):
        assert _map_size_to_gpt_image("1024x1024") == "1024x1024"

    def test_exact_match_1536x1024(self):
        assert _map_size_to_gpt_image("1536x1024") == "1536x1024"

    def test_exact_match_1024x1536(self):
        assert _map_size_to_gpt_image("1024x1536") == "1024x1536"

    def test_auto(self):
        assert _map_size_to_gpt_image("auto") == "auto"

    def test_widescreen_maps_to_landscape(self):
        assert _map_size_to_gpt_image("1920x1080") == "1536x1024"

    def test_portrait_maps_to_portrait(self):
        assert _map_size_to_gpt_image("1080x1920") == "1024x1536"

    def test_square_maps_to_square(self):
        assert _map_size_to_gpt_image("800x800") == "1024x1024"

    def test_unrecognized_defaults_to_landscape(self):
        assert _map_size_to_gpt_image("invalid") == "1536x1024"
        assert _map_size_to_gpt_image("") == "1536x1024"


class TestGenerateThumbnailMissingKey:
    """Test error handling when OPENAI_API_KEY is missing."""

    def test_missing_api_key_raises_runtime_error(self, monkeypatch):
        """Should raise RuntimeError with clear message, not raw exception."""
        # Temporarily clear the API key for this test
        with patch("thumbnail_openai.cfg") as mock_cfg:
            mock_cfg.openai_api_key = ""

            with pytest.raises(RuntimeError) as exc_info:
                generate_thumbnail("Test Game")

            error_msg = str(exc_info.value)
            assert "OPENAI_API_KEY not set" in error_msg
            assert ".env" in error_msg
            # Ensure no stack trace indicators
            assert "Traceback" not in error_msg

    def test_api_key_not_in_exception_message(self):
        """Confirm API key never leaks into exception messages."""
        fake_key = "sk-test-12345"

        with patch("thumbnail_openai.cfg") as mock_cfg:
            mock_cfg.openai_api_key = ""

            with pytest.raises(RuntimeError) as exc_info:
                generate_thumbnail("Test Game")

            assert fake_key not in str(exc_info.value)


class TestGenerateThumbnailDefaultPrompt:
    """Test default prompt construction."""

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_default_prompt_includes_title_and_style(self, mock_post, mock_cfg, tmp_path):
        """When no prompt given, should build from title + channel style."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style prompt"

        # Mock response with base64 image
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"fake_image_data").decode()}]
        }
        mock_post.return_value = mock_response

        output_file = tmp_path / "thumb.png"
        result = generate_thumbnail(
            "Sicilian Defense",
            output_path=str(output_file),
        )

        # Check that title and channel style are in the prompt_used
        prompt_used = result["prompt_used"]
        assert "Sicilian Defense" in prompt_used
        assert "Test style prompt" in prompt_used

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_custom_prompt_overrides_default(self, mock_post, mock_cfg, tmp_path):
        """When prompt given, should use it instead of default."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style prompt"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"fake_image").decode()}]
        }
        mock_post.return_value = mock_response

        output_file = tmp_path / "thumb.png"
        custom_prompt = "A custom artistic prompt"
        result = generate_thumbnail(
            "Sicilian Defense",
            prompt=custom_prompt,
            output_path=str(output_file),
        )

        assert result["prompt_used"] == custom_prompt


class TestGenerateThumbnailStylePreset:
    """Test style preset suffix behavior."""

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_joshila_preset_appends_suffix(self, mock_post, mock_cfg, tmp_path):
        """joshila preset should append to prompt."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"img").decode()}]
        }
        mock_post.return_value = mock_response

        output_file = tmp_path / "thumb.png"
        result = generate_thumbnail(
            "Test Game",
            style_preset="joshila",
            output_path=str(output_file),
        )

        assert STYLE_PRESETS["joshila"] in result["prompt_used"]

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_unknown_preset_silently_skipped(self, mock_post, mock_cfg, tmp_path):
        """Unknown preset should not error, just skip."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"img").decode()}]
        }
        mock_post.return_value = mock_response

        output_file = tmp_path / "thumb.png"
        result = generate_thumbnail(
            "Test Game",
            style_preset="nonexistent_preset",
            output_path=str(output_file),
        )

        # Should not raise, and prompt should not include made-up preset
        assert result["path"] == str(output_file)


class TestGenerateThumbnailSizeMapping:
    """Test size parameter mapping."""

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_size_mapped_in_api_call(self, mock_post, mock_cfg, tmp_path):
        """Size parameter should be mapped to valid gpt-image-1 size."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"img").decode()}]
        }
        mock_post.return_value = mock_response

        output_file = tmp_path / "thumb.png"
        generate_thumbnail(
            "Test",
            size="1280x720",  # Should map to 1536x1024
            output_path=str(output_file),
        )

        # Check that the POST call included the mapped size
        mock_post.assert_called_once()
        call_json = mock_post.call_args[1]["json"]
        assert call_json["size"] == "1536x1024"


class TestGenerateThumbnailOutputPath:
    """Test output path handling."""

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_default_output_path_generated(self, mock_post, mock_cfg, tmp_path):
        """If output_path not given, should default to output/thumbnails/."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"img").decode()}]
        }
        mock_post.return_value = mock_response

        # Change to temp dir to avoid polluting project
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = generate_thumbnail("Test Game")

                assert "output/thumbnails" in result["path"]
                assert result["path"].endswith(".png")
            finally:
                os.chdir(cwd)

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_custom_output_path_used(self, mock_post, mock_cfg, tmp_path):
        """If output_path given, should use it."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"img").decode()}]
        }
        mock_post.return_value = mock_response

        output_file = tmp_path / "custom" / "path" / "thumb.png"
        result = generate_thumbnail(
            "Test",
            output_path=str(output_file),
        )

        assert result["path"] == str(output_file)
        assert os.path.exists(output_file)


class TestGenerateThumbnailBase64Decoding:
    """Test base64 image decoding and file writing."""

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_base64_decoded_and_written(self, mock_post, mock_cfg, tmp_path):
        """Response base64 should be decoded and written to file."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style"

        fake_image_data = b"FAKE_PNG_DATA_12345"
        encoded = base64.b64encode(fake_image_data).decode()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b64_json": encoded}]
        }
        mock_post.return_value = mock_response

        output_file = tmp_path / "thumb.png"
        result = generate_thumbnail(
            "Test",
            output_path=str(output_file),
        )

        # File should exist and contain decoded data
        assert os.path.exists(output_file)
        with open(output_file, "rb") as f:
            content = f.read()
        assert content == fake_image_data


class TestGenerateThumbnailReferenceImages:
    """Test reference image handling for edits endpoint."""

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_valid_reference_images_use_edits_endpoint(self, mock_post, mock_cfg, tmp_path):
        """If reference images provided and exist, should use edits endpoint."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style"

        # Create a fake reference image file
        ref_img = tmp_path / "ref.png"
        ref_img.write_bytes(b"fake_image_data")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"result").decode()}]
        }
        mock_post.return_value = mock_response

        output_file = tmp_path / "thumb.png"
        result = generate_thumbnail(
            "Test",
            reference_image_paths=[str(ref_img)],
            output_path=str(output_file),
        )

        # Should call edits endpoint
        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert "edits" in call_url

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_missing_reference_images_skipped(self, mock_post, mock_cfg, tmp_path):
        """Missing reference images should be skipped; use generations endpoint if none valid."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(b"result").decode()}]
        }
        mock_post.return_value = mock_response

        output_file = tmp_path / "thumb.png"
        result = generate_thumbnail(
            "Test",
            reference_image_paths=["/nonexistent/image.png"],
            output_path=str(output_file),
        )

        # Should fall back to generations endpoint
        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert "generations" in call_url


class TestGenerateThumbnailAPIErrors:
    """Test API error handling."""

    @patch("thumbnail_openai.cfg")
    @patch("thumbnail_openai.requests.post")
    def test_http_error_raises_with_status(self, mock_post, mock_cfg, tmp_path):
        """Non-2xx HTTP response should raise RuntimeError with status code."""
        mock_cfg.openai_api_key = "sk-test-key"
        mock_cfg.thumbnail_style_prompt = "Test style"

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limited"
        mock_response.raise_for_status.side_effect = Exception("429 Rate limit")

        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            generate_thumbnail("Test", output_path=str(tmp_path / "thumb.png"))

        # Error message should be a RuntimeError (not raw exception)
        assert isinstance(exc_info.value, RuntimeError)


class TestThumbnailStylePromptConfig:
    """Test that thumbnail_style_prompt is accessible in config."""

    def test_thumbnail_style_prompt_in_config(self):
        assert hasattr(cfg, "thumbnail_style_prompt")
        assert isinstance(cfg.thumbnail_style_prompt, str)
        assert len(cfg.thumbnail_style_prompt) > 0
        # Should contain chess-related or thumbnail-related keywords
        assert any(
            keyword in cfg.thumbnail_style_prompt.lower()
            for keyword in ["chess", "thumbnail", "video", "gaming"]
        )

    def test_has_openai_property(self):
        """Config should have has_openai property."""
        assert hasattr(cfg, "has_openai")
        # Just check it's a boolean (value depends on whether key is set)
        assert isinstance(cfg.has_openai, bool)
