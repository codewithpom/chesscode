"""opening_fetcher.py — Fetch chess opening theory data."""

import io
import logging
from dataclasses import dataclass, field
from typing import List

import chess
import chess.pgn

logger = logging.getLogger(__name__)

_OPENINGS = {
    "sicilian najdorf": {
        "name": "Sicilian Najdorf", "eco": "B90",
        "moves": "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6",
        "tagline": "The sharpest and most popular response to 1.e4",
    },
    "sicilian defense": {
        "name": "Sicilian Defense", "eco": "B20",
        "moves": "1. e4 c5",
        "tagline": "The most popular reply to 1.e4",
    },
    "london system": {
        "name": "London System", "eco": "D02",
        "moves": "1. d4 d5 2. Nf3 Nf6 3. Bf4",
        "tagline": "A solid and reliable system for White",
    },
    "king's indian defense": {
        "name": "King's Indian Defense", "eco": "E60",
        "moves": "1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O",
        "tagline": "A dynamic hypermodern defense",
    },
    "ruy lopez": {
        "name": "Ruy Lopez", "eco": "C60",
        "moves": "1. e4 e5 2. Nf3 Nc6 3. Bb5",
        "tagline": "The Spanish Opening — classical and principled",
    },
    "italian game": {
        "name": "Italian Game", "eco": "C50",
        "moves": "1. e4 e5 2. Nf3 Nc6 3. Bc4",
        "tagline": "One of the oldest and most studied openings",
    },
    "french defense": {
        "name": "French Defense", "eco": "C00",
        "moves": "1. e4 e6 2. d4 d5",
        "tagline": "A solid and counterattacking defense",
    },
    "caro-kann defense": {
        "name": "Caro-Kann Defense", "eco": "B10",
        "moves": "1. e4 c6 2. d4 d5",
        "tagline": "Solid and resilient — a grandmaster favorite",
    },
    "queen's gambit": {
        "name": "Queen's Gambit", "eco": "D06",
        "moves": "1. d4 d5 2. c4",
        "tagline": "The most classical of all openings",
    },
    "king's gambit": {
        "name": "King's Gambit", "eco": "C30",
        "moves": "1. e4 e5 2. f4",
        "tagline": "Aggressive and swashbuckling",
    },
    "queens gambit": {
        "name": "Queen's Gambit", "eco": "D06",
        "moves": "1. d4 d5 2. c4",
        "tagline": "The most classical of all openings",
    },
    "kings gambit": {
        "name": "King's Gambit", "eco": "C30",
        "moves": "1. e4 e5 2. f4",
        "tagline": "Aggressive and swashbuckling",
    },
    "kings indian defense": {
        "name": "King's Indian Defense", "eco": "E60",
        "moves": "1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O",
        "tagline": "A dynamic hypermodern defense",
    },
}

_TRAPS = [
    {"name": "Fried Liver Attack", "opening": "Italian Game",
     "moves": "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Nxd5 6. Nxf7"},
    {"name": "Scholar's Mate", "opening": "King's Pawn",
     "moves": "1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7"},
    {"name": "Legal Trap", "opening": "Italian Game",
     "moves": "1. e4 e5 2. Nf3 Nc6 3. Bc4 d6 4. Nc3 Bg4 5. Nxe5 Bxd1 6. Bxf7+"},
    {"name": "Blackburne Shilling Gambit", "opening": "Italian Game",
     "moves": "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nd4"},
]


@dataclass
class Opening:
    name: str
    eco: str
    moves: str
    tagline: str

    def game(self) -> chess.pgn.Game:
        pgn_text = (
            f'[Event "Opening Theory"]\n'
            f'[White "Theory"]\n'
            f'[Black "Theory"]\n'
            f'[Result "*"]\n\n'
            f'{self.moves} *'
        )
        return chess.pgn.read_game(io.StringIO(pgn_text))


@dataclass
class OpeningTrap:
    name: str
    moves: str
    opening: str = ""


class OpeningFetcher:
    def __init__(self, lichess_token: str = ""):
        self._token = lichess_token

    def get_opening(self, name: str) -> Opening:
        key = name.lower().strip().replace("'", "'").replace("'", "")
        key_clean = key.replace("'", "")

        for k, d in _OPENINGS.items():
            k_clean = k.replace("'", "")
            if key_clean == k_clean or key == k:
                return Opening(**d)

        for k, d in _OPENINGS.items():
            k_clean = k.replace("'", "")
            if key_clean in k_clean or k_clean in key_clean:
                return Opening(**d)

        if self._token:
            try:
                return self._fetch_lichess(name)
            except Exception as e:
                logger.warning(f"Lichess fetch failed: {e}")

        logger.warning(f"Opening '{name}' not in database — using stub")
        return Opening(
            name=name, eco="A00",
            moves="1. e4 e5",
            tagline=f"A classic chess opening",
        )

    def get_all_traps(self) -> List[OpeningTrap]:
        return [OpeningTrap(**t) for t in _TRAPS]

    def _fetch_lichess(self, name: str) -> Opening:
        import requests
        resp = requests.get(
            "https://lichess.org/api/opening",
            params={"q": name},
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return Opening(
            name=data.get("name", name),
            eco=data.get("eco", ""),
            moves=data.get("pgn", "1. e4 e5"),
            tagline=data.get("desc", f"Learn the {name}"),
        )
