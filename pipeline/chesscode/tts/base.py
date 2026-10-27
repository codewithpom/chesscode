from pathlib import Path
from typing import Callable, TypedDict


class Word(TypedDict):
    w: str
    start_ms: int
    end_ms: int


Synth = Callable[[str, str, str, Path], list[Word]]
