import re

_SAN = re.compile(r"(?<![A-Za-z0-9])(?:O-O(?:-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?)(?![A-Za-z0-9])")

def extract_san(text: str) -> list[str]:
    return _SAN.findall(text)

def unknown_moves(text: str, game_sans: set[str], engine_sans: set[str]) -> list[str]:
    return list(dict.fromkeys(move for move in extract_san(text) if move not in game_sans and move not in engine_sans))
