import hashlib
import importlib
import json
import logging
from pathlib import Path

import yaml

from .config import load
from .context import Context, REPO_ROOT, StageError, parse_video_id

STAGES = ["select", "fetch", "analyze", "classify", "beats", "script", "voice", "timeline", "metadata", "emit"]
OUTPUTS = {
    "select": ["game.json"], "fetch": ["game.pgn"], "analyze": ["analysis.json"],
    "classify": ["classified.json"], "beats": ["beats.json"], "script": ["script.json"],
    "voice": ["voice.json"], "timeline": ["timeline.json"], "metadata": ["metadata.json"],
    "emit": ["video_spec.json"],
}
log = logging.getLogger(__name__)


def _context(video_id: str) -> Context:
    year, game_no, language, template = parse_video_id(video_id)
    games_path = REPO_ROOT / "content" / "games.yaml"
    try:
        games = yaml.safe_load(games_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StageError(video_id, "select", f"cannot read {games_path}: {exc}") from exc
    source_game_no = game_no % 1000 if template == "shorts" else game_no
    game = next((g for g in (games or []) if g.get("game_no") == source_game_no), None)
    if game is None:
        raise StageError(video_id, "select", f"game {source_game_no} not found in {games_path}")
    if game.get("year", year) != year:
        raise StageError(video_id, "select", f"game {source_game_no} has a different year")
    return Context(video_id, REPO_ROOT / "build" / "specs" / video_id, REPO_ROOT, game, language, template)


def _load_stage(name: str):
    return importlib.import_module(f"chesscode.stages.{name}")


def _input_hash(ctx: Context, inputs: list[str]) -> str:
    digest = hashlib.sha256()
    for name in inputs:
        path = Path(name)
        candidates = [ctx.repo_root / path] if path.parts and path.parts[0] in {"config", "content", "pipeline", "spec"} else [ctx.spec_dir / path]
        if path.is_absolute():
            candidates = [path]
        source = candidates[0]
        digest.update(path.as_posix().encode())
        if source.is_file():
            digest.update(source.read_bytes())
        elif source.is_dir():
            files = sorted(path for path in source.rglob("*") if path.is_file())
            for path in files:
                digest.update(path.relative_to(source).as_posix().encode())
                digest.update(path.read_bytes())
            if not files:
                digest.update(b"<empty-directory>")
        else:
            digest.update(b"<missing>")
    return digest.hexdigest()


def _run_stage(ctx: Context, name: str, force: bool = False) -> None:
    module = _load_stage(name)
    inputs = list(getattr(module, "INPUTS", []))
    outputs = list(getattr(module, "OUTPUTS", OUTPUTS[name]))
    hashes_path = ctx.spec_dir / ".stage_hashes.json"
    try:
        hashes = json.loads(hashes_path.read_text(encoding="utf-8")) if hashes_path.exists() else {}
    except (OSError, json.JSONDecodeError) as exc:
        raise StageError(ctx.video_id, name, f"cannot read stage hashes: {exc}") from exc
    current_hash = _input_hash(ctx, inputs)
    if not force and hashes.get(name) == current_hash and all((ctx.spec_dir / out).is_file() for out in outputs):
        return
    ctx.spec_dir.mkdir(parents=True, exist_ok=True)
    module.run(ctx)
    if not all((ctx.spec_dir / out).is_file() for out in outputs):
        raise StageError(ctx.video_id, name, f"stage did not create expected output(s): {outputs}")
    hashes[name] = current_hash
    hashes_path.write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")


def run_video(video_id: str, stage: str | None = None, until: str | None = None) -> None:
    if stage and stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    if until and until not in STAGES:
        raise ValueError(f"Unknown stage: {until}")
    ctx = _context(video_id)
    if stage:
        _run_stage(ctx, stage, force=True)
        return
    for name in STAGES[:STAGES.index(until) + 1 if until else len(STAGES)]:
        _run_stage(ctx, name)


def main(args) -> int:
    try:
        run_video(args.video, getattr(args, "stage", None), getattr(args, "until", None))
        return 0
    except (StageError, ValueError, KeyError) as exc:
        log.error("%s", exc)
        return 1
