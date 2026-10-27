"""tests/test_classification.py — move-quality classification thresholds.

_classify() boundary tests below just pin the raw eval-delta thresholds.

_classify_move() tests cover the fix for a visual-QA finding: at the MCP
render_video path's hardcoded --depth 12, ordinary opening theory moves
produced eval swings large enough to cross these thresholds and get
mislabeled "mistake"/"blunder" in the rendered move list (see
output/dc9a356a_pgn/frames/..._frame_0009.png — Nf3/Bb5/Ba4/Nf6/O-O all
tagged "?"). Fixed by giving the first OPENING_BOOK_PLIES plies a pass on
classification regardless of delta.
"""

from stockfish_analyzer import _classify, _classify_move, OPENING_BOOK_PLIES


def test_none_delta_is_normal():
    assert _classify(None) == "normal"


def test_no_loss_or_small_gain_is_normal():
    assert _classify(0) == "normal"
    assert _classify(-5) == "normal"
    assert _classify(50) == "normal"


def test_boundary_just_past_normal_is_inaccuracy():
    assert _classify(-6) == "inaccuracy"
    assert _classify(-20) == "inaccuracy"


def test_boundary_just_past_inaccuracy_is_mistake():
    assert _classify(-21) == "mistake"
    assert _classify(-100) == "mistake"


def test_boundary_past_mistake_is_blunder():
    assert _classify(-101) == "blunder"
    assert _classify(-900) == "blunder"


def test_classify_move_forces_normal_within_book_plies_even_on_huge_swing():
    # Ply 8 = O-O in the Ruy Lopez (1.e4 e5 2.Nf3 Nc6 3.Bb5 a6 4.Ba4 Nf6 5.O-O),
    # exactly the move falsely tagged "?" in the visual-QA finding.
    assert _classify_move(-300, ply=8) == "normal"


def test_classify_move_uses_real_thresholds_once_past_book():
    assert _classify_move(-300, ply=OPENING_BOOK_PLIES) == "blunder"
    assert _classify_move(-300, ply=OPENING_BOOK_PLIES + 1) == "blunder"
    assert _classify_move(0, ply=OPENING_BOOK_PLIES) == "normal"


def test_classify_move_book_boundary_is_exclusive_of_book_plies_count():
    assert _classify_move(-300, ply=OPENING_BOOK_PLIES - 1) == "normal"
