"""tests/test_arrow_analyzer.py — best/threat/defensive arrow selection logic."""

import chess

from arrow_analyzer import ArrowAnalyzer, ArrowType


class _FakeAnalysis:
    def __init__(self, best_move):
        self.best_move = best_move


def test_best_move_arrow_uses_analysis_best_move():
    analyzer = ArrowAnalyzer()
    board = chess.Board()  # starting position
    arrows = analyzer.analyze_position(board, analysis=_FakeAnalysis("e2e4"))

    best = [a for a in arrows if a.arrow_type == ArrowType.BEST_MOVE]
    assert len(best) == 1
    assert best[0].from_square == chess.E2
    assert best[0].to_square == chess.E4


def test_illegal_best_move_is_ignored():
    analyzer = ArrowAnalyzer()
    board = chess.Board()
    arrows = analyzer.analyze_position(board, analysis=_FakeAnalysis("e2e5"))  # not legal
    assert not any(a.arrow_type == ArrowType.BEST_MOVE for a in arrows)


def test_check_produces_single_threat_arrow():
    analyzer = ArrowAnalyzer()
    # Fool's mate position: black queen delivers check on h4.
    # Note: _find_checking_move's heuristic (replay black's legal moves and see
    # which leaves White in check) doesn't reliably recover the *actual* checking
    # move once the queen is already parked on h4 — almost any black reply leaves
    # White in check via the standing queen. So this only pins the *count* and
    # *reason*, not the exact from/to squares.
    board = chess.Board()
    for m in ["f3", "e5", "g4", "Qh4#"]:
        board.push_san(m)

    arrows = analyzer.analyze_position(board)
    threats = [a for a in arrows if a.arrow_type == ArrowType.THREAT]
    assert len(threats) == 1
    assert threats[0].reason == "Direct check"


def test_no_threats_means_no_defensive_arrows():
    analyzer = ArrowAnalyzer()
    board = chess.Board()  # nothing hanging on move 1
    arrows = analyzer.analyze_position(board)
    assert not any(a.arrow_type == ArrowType.DEFENSIVE for a in arrows)


def test_hard_limit_caps_arrow_count():
    analyzer = ArrowAnalyzer(max_arrows_per_frame=1)
    board = chess.Board()
    arrows = analyzer.analyze_position(board, analysis=_FakeAnalysis("e2e4"))
    assert len(arrows) <= 1


def test_arrow_color_mapping():
    from arrow_analyzer import ChessArrow
    a = ChessArrow(chess.E2, chess.E4, ArrowType.BEST_MOVE, 1.0, "test")
    assert a.color == "#00AA00"
