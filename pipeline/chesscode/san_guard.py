import re

_SAN = re.compile(r"(?<![A-Za-z0-9])(?:[0O]-[0O](?:-[0O])?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=?[QRBN])?)[+#]?(?![A-Za-z0-9])")
_SQUARE = re.compile(r"[a-h][1-8]")

def extract_san(text: str) -> list[str]:
    return _SAN.findall(text)

def _norm(san: str) -> str:
    """Same move, one spelling: no check suffix, letter O castling, promotion with '='."""
    return re.sub(r"(?<=[1-8])([QRBN])$", r"=\1", san.rstrip("+#").replace("0", "O"))

def unknown_moves(text: str, game_sans: set[str], engine_sans: set[str]) -> list[str]:
    known = {_norm(move) for move in game_sans | engine_sans}
    # shortcut: a bare square ("pressure on e5") is a square reference, not a checkable move; revisit with a legal-pawn-move check
    return list(dict.fromkeys(move for move in extract_san(text) if not _SQUARE.fullmatch(move) and _norm(move) not in known))
