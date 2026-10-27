"""thumbnail_openai.py — YouTube thumbnail generator using OpenAI's gpt-image-1 API."""

import os
import base64
import logging
from typing import Optional

import requests

from config import cfg

logger = logging.getLogger(__name__)


# Style presets for different thumbnail aesthetics
STYLE_PRESETS = {
    "joshila": "bold, cinematic lighting, intense color, dramatic composition",
    "minimal": "clean, minimalist, high contrast, modern design",
    "dramatic": "dark moody lighting, intense atmosphere, professional gaming aesthetic",
}


def _map_size_to_gpt_image(size: str) -> str:
    """Map arbitrary size strings to gpt-image-1 supported sizes.

    gpt-image-1 supports: "1024x1024", "1536x1024", "1024x1536", "auto"
    Default 1280x720 (16:9) maps to 1536x1024 (landscape).
    """
    size_lower = size.lower().strip()

    # Exact matches
    if size_lower in ("1024x1024", "1536x1024", "1024x1536", "auto"):
        return size_lower

    # Parse dimensions if they look like WxH
    if "x" in size_lower:
        parts = size_lower.split("x")
        if len(parts) == 2:
            try:
                w, h = int(parts[0]), int(parts[1])
                # Prefer landscape (1536x1024) for widescreen
                if w > h:
                    return "1536x1024"
                # Prefer portrait (1024x1536) for vertical
                elif h > w:
                    return "1024x1536"
                # Square
                else:
                    return "1024x1024"
            except ValueError:
                pass

    # Default to landscape for unrecognized sizes
    return "1536x1024"


def generate_thumbnail(
    title: str,
    prompt: str = "",
    reference_image_paths: Optional[list] = None,
    size: str = "1280x720",
    style_preset: str = "",
    output_path: str = "",
) -> dict:
    """Generate a YouTube thumbnail using OpenAI's gpt-image-1 API.

    Args:
        title: Video title (used in default prompt if prompt not given).
        prompt: Custom prompt. If empty, builds default from title + channel style.
        reference_image_paths: List of image paths for style consistency (edits endpoint).
        size: Desired size (default "1280x720"). Maps to gpt-image-1 supported sizes.
        style_preset: Key from STYLE_PRESETS dict (e.g. "joshila"). Appends to final prompt.
        output_path: Where to save the PNG. Default: output/thumbnails/thumb_<slug>.png

    Returns:
        {"path": <local file path>, "prompt_used": <str>}

    Raises:
        RuntimeError: If OPENAI_API_KEY not set or API call fails.
    """

    # Check API key early, with a clear error message
    if not cfg.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set — cannot generate thumbnail. "
            "Add it to your .env file or set the environment variable."
        )

    # Build final prompt
    if not prompt:
        prompt = f"{title}. {cfg.thumbnail_style_prompt}"

    if style_preset and style_preset in STYLE_PRESETS:
        prompt = f"{prompt} {STYLE_PRESETS[style_preset]}"

    # Map size to gpt-image-1 format
    gpt_size = _map_size_to_gpt_image(size)

    # Determine output path
    if not output_path:
        os.makedirs("output/thumbnails", exist_ok=True)
        title_slug = title.lower().replace(" ", "_")[:50]
        output_path = f"output/thumbnails/thumb_{title_slug}.png"
    else:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Filter reference images (only include existing files)
    valid_images = []
    if reference_image_paths:
        valid_images = [p for p in reference_image_paths if os.path.exists(p)]

    try:
        # Choose endpoint based on whether we have reference images
        if valid_images:
            _generate_with_edits(prompt, gpt_size, valid_images, output_path)
        else:
            _generate_with_generations(prompt, gpt_size, output_path)
    except Exception as e:
        # Catch and re-raise with clear message (no API key in error)
        if isinstance(e, RuntimeError):
            # Already a RuntimeError from our code, re-raise as-is
            raise
        if "401" in str(e) or "403" in str(e):
            raise RuntimeError(
                f"OpenAI API authentication failed. "
                "Check that OPENAI_API_KEY is correct."
            ) from e
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            raise RuntimeError(
                f"OpenAI API request failed (HTTP {e.response.status_code}): {e.response.text}"
            ) from e
        if "OPENAI_API_KEY" in str(e):
            # Should not happen (we check upfront), but just in case
            raise RuntimeError(
                "OPENAI_API_KEY not set — cannot generate thumbnail. "
                "Add it to your .env file or set the environment variable."
            ) from e
        # Generic API error
        raise RuntimeError(f"Thumbnail generation failed: {str(e)}") from e

    logger.info(f"Thumbnail generated: {output_path}")
    return {
        "path": output_path,
        "prompt_used": prompt,
    }


def _generate_with_generations(prompt: str, size: str, output_path: str) -> None:
    """Call the /images/generations endpoint and save the result."""
    headers = {
        "Authorization": f"Bearer {cfg.openai_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": size,
        "n": 1,
        "response_format": "b64_json",
    }

    resp = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers=headers,
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()

    # Decode base64 and save
    data = resp.json()
    b64_image = data["data"][0]["b64_json"]
    image_bytes = base64.b64decode(b64_image)

    with open(output_path, "wb") as f:
        f.write(image_bytes)


def _generate_with_edits(
    prompt: str, size: str, image_paths: list, output_path: str
) -> None:
    """Call the /images/edits endpoint with reference images for style consistency."""
    headers = {
        "Authorization": f"Bearer {cfg.openai_api_key}",
    }

    files = {}
    for i, image_path in enumerate(image_paths):
        with open(image_path, "rb") as f:
            files[f"image"] = f.read()
            # Note: OpenAI's edits endpoint accepts a single image file
            # If multiple images provided, we use the first one
            break

    data = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": size,
        "n": 1,
        "response_format": "b64_json",
    }

    resp = requests.post(
        "https://api.openai.com/v1/images/edits",
        headers=headers,
        files=files,
        data=data,
        timeout=120,
    )
    resp.raise_for_status()

    # Decode base64 and save
    result = resp.json()
    b64_image = result["data"][0]["b64_json"]
    image_bytes = base64.b64decode(b64_image)

    with open(output_path, "wb") as f:
        f.write(image_bytes)
