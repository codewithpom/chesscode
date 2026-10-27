"""generate_legend_assets.py — offline generator for sidebar legend portraits + decorative panel.

Not imported by the render pipeline. Run manually, once, whenever you want to add or refresh
static art assets:

    python scripts/generate_legend_assets.py --all --decorative
    python scripts/generate_legend_assets.py --name "Judit Polgar"

The renderer (board_renderer.py) already works with zero generated assets — it falls back to a
procedurally-drawn placeholder for both the legend portrait and the decorative panel. This
script only produces the nicer real artwork on top of that fallback.

Before this script can actually generate images, wire your own image-gen client (nano-banana /
Gemini image API, or any other provider) into `generate_image()` below.
"""

import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from board_renderer import _CHESS_LEGENDS, _LAYOUT  # noqa: E402

ASSETS_DIR   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
LEGENDS_DIR  = os.path.join(ASSETS_DIR, "legends")
SIDEBAR_DIR  = os.path.join(ASSETS_DIR, "sidebar")

PORTRAIT_SIZE = 512
ACCENT_HEX    = "#F5A623"

LEGEND_ROSTER = [{"name": legend["name"]} for legend in _CHESS_LEGENDS]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def generate_image(prompt: str) -> bytes:
    """Call an image-gen model and return raw image bytes (PNG/JPEG).

    Wire your own nano-banana / Gemini image API client here, e.g.:

        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.5-flash-image")
        response = model.generate_content(prompt)
        return response.parts[0].inline_data.data
    """
    raise NotImplementedError(
        "generate_image() is a stub. Wire up your nano-banana/Gemini image API client "
        "(with your own API key) before running this script."
    )


def _portrait_prompt(name: str) -> str:
    return (
        f"Stylized digital-painting portrait of chess grandmaster {name}, "
        "non-photorealistic illustrated art style, subtle chess-themed backdrop, "
        "square portrait crop, centered face, no text, no watermarks."
    )


def _decorative_prompt() -> str:
    return (
        "Vertical branded side-panel background art for a chess analysis YouTube channel "
        "called ChessCode. Chess pawn/piece motif, dark near-black background, "
        f"single accent color {ACCENT_HEX}, subtle geometric chess pattern, no text, "
        "no watermarks, portrait orientation."
    )


def _save_portrait(name: str, force: bool) -> None:
    os.makedirs(LEGENDS_DIR, exist_ok=True)
    slug = slugify(name)
    path = os.path.join(LEGENDS_DIR, f"{slug}.png")
    if os.path.isfile(path) and not force:
        print(f"skip (exists): {path}")
        return

    from PIL import Image

    raw = generate_image(_portrait_prompt(name))
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img = img.resize((PORTRAIT_SIZE, PORTRAIT_SIZE), Image.LANCZOS)
    img.save(path)
    print(f"wrote: {path}")


def _save_decorative(force: bool) -> None:
    os.makedirs(SIDEBAR_DIR, exist_ok=True)
    path = os.path.join(SIDEBAR_DIR, "decorative_panel.png")
    if os.path.isfile(path) and not force:
        print(f"skip (exists): {path}")
        return

    from PIL import Image

    width, height = _LAYOUT["DECOR_PANEL_W"], _LAYOUT["FRAME_H"]
    raw = generate_image(_decorative_prompt())
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img = img.resize((width, height), Image.LANCZOS)
    img.save(path)
    print(f"wrote: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Generate portraits for the built-in legend roster")
    parser.add_argument("--name", metavar="NAME", help="Generate a portrait for one legend (any name)")
    parser.add_argument("--decorative", action="store_true", help="Generate the decorative sidebar panel")
    parser.add_argument("--force", action="store_true", help="Regenerate even if the target file already exists")
    args = parser.parse_args()

    if not (args.all or args.name or args.decorative):
        parser.error("Nothing to do — pass --all, --name NAME, and/or --decorative")

    if args.all:
        for legend in LEGEND_ROSTER:
            _save_portrait(legend["name"], args.force)

    if args.name:
        _save_portrait(args.name, args.force)

    if args.decorative:
        _save_decorative(args.force)


if __name__ == "__main__":
    main()
