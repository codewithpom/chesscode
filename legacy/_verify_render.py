import os
import chess
from board_renderer import BoardRenderer, RenderOptions, THEMES, CoachInsights
from arrow_analyzer import ChessArrow, ArrowType

board = chess.Board()
board.push_san("e4")
board.push_san("c5")
board.push_san("Nf3")
board.push_san("d6")

arrows = [
    ChessArrow(from_square=chess.G1, to_square=chess.F3, arrow_type=ArrowType.BEST_MOVE, confidence=0.9, reason="best"),
    ChessArrow(from_square=chess.D8, to_square=chess.A5, arrow_type=ArrowType.THREAT, confidence=0.7, reason="threat"),
    ChessArrow(from_square=chess.C8, to_square=chess.G4, arrow_type=ArrowType.DEFENSIVE, confidence=0.6, reason="defend"),
]

coach = CoachInsights(
    move_number=3, turn="black", san_move="d6",
    top_engine_moves=[
        {"san": "Nc6", "score_cp": 35, "rank": 1, "label": "'best"},
        {"san": "d6", "score_cp": 20, "rank": 2, "label": "solid*"},
    ],
    insights=[
        "<b>Nf3</b> develops naturally and eyes <i>e5</i> control.",
        "'Black should contest the center` with ...d5 soon.",
        "<b>Watch</b> the <i>long diagonal</i> for White's bishop.",
    ],
)

os.makedirs("output/_verify", exist_ok=True)

for theme_name in ("classic", "cyberpunk", "retro"):
    opts = RenderOptions(theme=THEMES[theme_name], output_dir="output/_verify")
    renderer = BoardRenderer(opts)
    path = renderer._save_frame(
        board, f"verify_{theme_name}", 0,
        last_move=board.peek(), arrows=arrows,
        analysis_at_frame=type("A", (), {"eval_cp": 25, "ply": 6, "coach": coach})(),
        all_moves_so_far=["e4", "c5", "Nf3", "d6"],
        current_move_idx=3,
        game_meta=type("M", (), {"white": "Alice", "black": "Bob", "opening": "Sicilian Najdorf",
                                  "white_elo": 2400, "black_elo": 2350, "moves": [1,2,3,4]})(),
    )
    print(theme_name, "->", path)
