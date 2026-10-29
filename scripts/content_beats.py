"""Run the real pipeline (select..beats) on every game in content/games.yaml and write the beats back.

Usage (from the repo root, STOCKFISH_PATH set): python scripts/content_beats.py [game_no ...]
One engine at a time; the engine cache makes reruns free.
"""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT / "content" / "games.yaml"


def move_label(ply: int, san: str) -> str:
    return f"{(ply + 1) // 2}.{san}" if ply % 2 else f"{ply // 2}...{san}"


def beats_for(game_no: int) -> list[str]:
    video_id = f"cc-2026-{game_no:04d}-en"
    result = subprocess.run([sys.executable, "-m", "chesscode", "run", "--video", video_id, "--until", "beats"],
                            cwd=ROOT / "pipeline", capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{video_id}: {(result.stderr or result.stdout).strip().splitlines()[-1:]}")
    spec = ROOT / "build" / "specs" / video_id
    sans = {r["ply"]: r["san"] for r in json.loads((spec / "classified.json").read_text(encoding="utf-8"))}
    beats = json.loads((spec / "beats.json").read_text(encoding="utf-8"))
    return [f"{b['type']}@{move_label(b['ply'], sans[b['ply']])}" + (f" (i{b['intensity']})" if b["intensity"] > 1 else "") for b in beats]


def main(only: list[int]) -> None:
    header = GAMES.read_text(encoding="utf-8").split("\n- ", 1)[0] if GAMES.read_text(encoding="utf-8").startswith("#") else ""
    games = yaml.safe_load(GAMES.read_text(encoding="utf-8"))
    for game in games:
        if only and game["game_no"] not in only:
            continue
        try:
            game["beats"] = beats_for(game["game_no"])
            print(game["game_no"], game["source_id"], len(game["beats"]), flush=True)
        except Exception as exc:  # keep going; the failure is recorded on the game
            game["beats"] = [f"ERROR: {exc}"]
            print(game["game_no"], game["source_id"], "ERROR", exc, flush=True)
        # write after every game so a long run can be interrupted without losing work
        GAMES.write_text(header + "\n" + yaml.safe_dump(games, sort_keys=False, allow_unicode=True, width=200),
                         encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]])
