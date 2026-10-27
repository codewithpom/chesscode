import json

from ..context import StageError

INPUTS = ["content/games.yaml"]
OUTPUTS = ["game.json"]


def next_unrendered(games: list[dict], rendered: set[str], tier: str) -> dict | None:
    for game in games:
        if game.get("tier") != tier:
            continue
        game_no = game["game_no"]
        if not any(video_id.endswith(f"-{game_no:04d}-{lang}") for video_id in rendered for lang in ("en", "hi")):
            return game
    return None


def run(ctx) -> None:
    if not ctx.game:
        raise StageError(ctx.video_id, "select", "game entry is missing")
    ctx.spec_dir.mkdir(parents=True, exist_ok=True)
    (ctx.spec_dir / "game.json").write_text(json.dumps(ctx.game, indent=2) + "\n", encoding="utf-8")
