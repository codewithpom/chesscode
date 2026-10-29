import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from check_pgns import check_pgn  # noqa: E402

BAD = """[Event "x"]
[Site "x"]
[Date "2000.01.01"]
[Round "1"]
[White "A"]
[Black "B"]
[Result "1-0"]

1. e4 e5 2. Ke3 Nc6 3. Nf3 Nf6 4. Nc3 Nc6 5. d4 d6 6. Bc4 Be7 7. O-O O-O 8. h3 h6 9. a3 a6 10. b3 b6 1-0
"""

SHORT = BAD.split("1. e4")[0] + "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0\n"

MATE_WRONG = """[Event "x"]
[Site "x"]
[Date "2000.01.01"]
[White "A"]
[Black "B"]
[Result "1-0"]

1. f3 e5 2. g4 Qh4# 1-0
"""


def test_every_content_pgn_is_clean():
    files = sorted((ROOT / "content" / "pgn").glob("*.pgn"))
    assert files, "no content PGNs"
    bad = {f.name: check_pgn(f) for f in files if check_pgn(f)}
    assert not bad, bad


def test_checker_rejects_illegal_move(tmp_path):
    p = tmp_path / "bad.pgn"
    p.write_text(BAD)
    assert check_pgn(p)


def test_checker_rejects_short_game_and_missing_header(tmp_path):
    p = tmp_path / "short.pgn"
    p.write_text(SHORT.replace('[Round "1"]\n', "").replace('[Event "x"]\n', ""))
    problems = " ".join(check_pgn(p))
    assert "Event" in problems and "short" in problems


def test_checker_rejects_mate_result_mismatch(tmp_path):
    p = tmp_path / "mate.pgn"
    p.write_text(MATE_WRONG)
    assert any("mate" in s for s in check_pgn(p))
