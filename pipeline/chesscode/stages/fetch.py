import shutil
import time
from pathlib import Path

import requests

from ..context import StageError
from ..lichess import export_game

INPUTS = ["game.json"]
OUTPUTS = ["game.pgn"]
session = requests.Session()
sleep = time.sleep


def run(ctx) -> None:
    game = ctx.game
    source = game.get("source")
    source_id = game.get("source_id")
    if source == "local":
        pgn_file = game.get("pgn_file")
        path = Path(pgn_file) if pgn_file else None
        if path and not path.is_absolute():
            path = ctx.repo_root / path
        if not path or not path.is_file():
            raise StageError(ctx.video_id, "fetch", f"local PGN is missing: {pgn_file}")
        ctx.spec_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, ctx.spec_dir / "game.pgn")
    elif source == "lichess" and source_id:
        cache = ctx.repo_root / "data" / "pgn" / f"{source_id}.pgn"
        if cache.is_file():
            pgn = cache.read_text(encoding="utf-8")
        else:
            try:
                pgn = export_game(source_id, session, sleep=sleep)
            except Exception as exc:
                raise StageError(ctx.video_id, "fetch", f"Lichess export failed: {exc}") from exc
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(pgn, encoding="utf-8")
        ctx.spec_dir.mkdir(parents=True, exist_ok=True)
        (ctx.spec_dir / "game.pgn").write_text(pgn, encoding="utf-8")
    else:
        raise StageError(ctx.video_id, "fetch", f"invalid or missing game source: {source!r}")
