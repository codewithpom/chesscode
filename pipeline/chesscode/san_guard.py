import re
import unicodedata

_SAN = re.compile(r"(?<![A-Za-z0-9])(?:[0O]-[0O](?:-[0O])?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=?[QRBN])?)[+#]?(?![A-Za-z0-9])")
_SQUARE = re.compile(r"[a-h][1-8]")
_MOVE = re.compile(r"([KQRBN])?[a-h]?[1-8]?(x)?([a-h][1-8])(?:=[QRBN])?")
# Piece names a narrator spells out, English and Hindi (Devanagari); NFC keeps nukta spellings comparable.
_NAMES = {"K": ("king", "राजा", "किंग"), "Q": ("queen", "वज़ीर", "वजीर", "रानी", "क्वीन"), "R": ("rook", "हाथी", "रूक"),
          "B": ("bishop", "ऊँट", "ऊंट", "बिशप"), "N": ("knight", "घोड़ा", "घोडा", "नाइट"), "P": ("pawn", "प्यादा", "पॉन")}
_PIECE = {unicodedata.normalize("NFC", name).lower(): letter for letter, names in _NAMES.items() for name in names}
_SPELLED = re.compile(r"(?<![A-Za-z])(" + "|".join(sorted(map(re.escape, _PIECE), key=len, reverse=True)) + r")\s+(?:(takes on|captures on|moves to|goes to|takes|captures|to|x)\s+)?([a-h][1-8])(?![A-Za-z0-9])", re.I)
# the squares every piece starts on: "the rook on a1" names a place, not a move
_START_SQUARES = {f + r for f in "abcdefgh" for r in "1278"}

def extract_san(text: str) -> list[str]:
    return _SAN.findall(text)

def _norm(san: str) -> str:
    """Same move, one spelling: no check suffix, letter O castling, promotion with '='."""
    return re.sub(r"(?<=[1-8])([QRBN])$", r"=\1", san.rstrip("+#").replace("0", "O"))

def _targets(sans: set[str]) -> set[tuple[str, str, bool]]:
    """(piece letter, destination square, is capture) of every move; castling is a king move to g/c."""
    out = set()
    for san in map(_norm, sans):
        if san.startswith("O-O"):
            out |= {("K", f + r, False) for f in ("c" if san == "O-O-O" else "g") for r in "18"}
        elif m := _MOVE.fullmatch(san):
            out.add((m[1] or "P", m[3], bool(m[2])))
    return out

def unknown_moves(text: str, game_sans: set[str], engine_sans: set[str]) -> list[str]:
    """SAN moves, bare destination squares and spelled-out piece moves ("knight to f6", "घोड़ा f6") that no game or engine move backs."""
    known = {_norm(move) for move in game_sans | engine_sans}
    targets = _targets(known); squares = {square for _, square, _ in targets} | _START_SQUARES
    text = unicodedata.normalize("NFC", text)
    bad = [m for m in extract_san(text) if (m not in squares if _SQUARE.fullmatch(m) else _norm(m) not in known)]
    for m in _SPELLED.finditer(text):
        piece, op, square = _PIECE[m[1].lower()], (m[2] or "").lower(), m[3]
        capture = op.startswith(("takes", "captures")) or op == "x"
        if (piece, square, True) not in targets and (capture or (piece, square, False) not in targets): bad.append(m[0])
    return list(dict.fromkeys(bad))
