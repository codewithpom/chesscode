from dataclasses import dataclass
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
_VIDEO_ID = re.compile(r"^cc-(\d{4})-(\d{4})-(en|hi)$")


class StageError(Exception):
    def __init__(self, video_id: str, stage: str, reason: str):
        self.video_id = video_id
        self.stage = stage
        self.reason = reason
        super().__init__(f"{video_id} [{stage}]: {reason}")


@dataclass
class Context:
    video_id: str
    spec_dir: Path
    repo_root: Path
    game: dict
    language: str
    template: str


def parse_video_id(video_id: str) -> tuple[int, int, str, str]:
    match = _VIDEO_ID.fullmatch(video_id)
    if not match:
        raise ValueError(f"Invalid video id: {video_id}")
    year, game_no, language = match.groups()
    game_no = int(game_no)
    return int(year), game_no, language, "shorts" if game_no >= 5000 else "studio"
