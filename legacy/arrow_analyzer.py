"""arrow_analyzer.py — Analyze board positions to generate smart arrow visualizations.

Detects:
- Best moves (green arrows)
- Threats/attacks/weaknesses (red arrows)
- Defensive moves (yellow arrows)

Uses Stockfish analysis + chess heuristics for smart filtering to prevent clutter.
"""

import logging
from typing import List, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum

import chess
import chess.engine

logger = logging.getLogger(__name__)


class ArrowType(Enum):
    """Arrow classification."""
    BEST_MOVE = "best_move"       # Green solid — rank 1
    CANDIDATE_2 = "candidate_2"   # Green dimmed — rank 2
    CANDIDATE_3 = "candidate_3"   # Green faint — rank 3
    THREAT = "threat"              # Red
    DEFENSIVE = "defensive"        # Yellow


@dataclass
class ChessArrow:
    """A single arrow to display on the board."""
    from_square: int               # 0-63
    to_square: int                 # 0-63
    arrow_type: ArrowType
    confidence: float              # 0.0-1.0 (used for smart filtering)
    reason: str                    # e.g., "King in check from c4" (for logging)

    @property
    def color(self) -> str:
        """Return SVG hex color for this arrow type."""
        colors = {
            ArrowType.BEST_MOVE: "#00AA00",     # Green solid
            ArrowType.CANDIDATE_2: "#007700",   # Green dimmed
            ArrowType.CANDIDATE_3: "#004400",   # Green faint
            ArrowType.THREAT: "#DD2020",        # Red
            ArrowType.DEFENSIVE: "#FFD700",     # Gold/Yellow
        }
        return colors.get(self.arrow_type, "#FFFFFF")


class ArrowAnalyzer:
    """Analyzes chess positions and generates arrow data for visualization."""

    def __init__(self, max_arrows_per_frame: int = 5, smart_mode: bool = True):
        """
        Args:
            max_arrows_per_frame: Hard limit on arrows shown per position
            smart_mode: If True, filter arrows intelligently to reduce clutter
        """
        self.max_arrows_per_frame = max_arrows_per_frame
        self.smart_mode = smart_mode

    def analyze_position(
        self,
        board: chess.Board,
        analysis: Optional["MoveAnalysis"] = None,
        analysis_data: Optional[dict] = None,
    ) -> List[ChessArrow]:
        """
        Analyze a position and return arrows to display.

        Args:
            board: Current chess board state
            analysis: MoveAnalysis object (if available from Stockfish)
            analysis_data: Raw analysis dict with best_move, top_moves, threats, etc.

        Returns:
            List of ChessArrow objects, prioritized and filtered for display
        """
        arrows: List[ChessArrow] = []

        # 1. Best move arrow from MultiPV analysis.
        # Only the rank-1 move gets a green arrow. Showing rank 2/3 candidates
        # (all green shades) buried the actual best move under a wash of green —
        # the classic "green arrows everywhere" clutter.
        if analysis and hasattr(analysis, 'top_moves') and analysis.top_moves:
            # Use top_moves if available (MultiPV candidates)
            for move_data in analysis.top_moves[:1]:
                try:
                    move = chess.Move.from_uci(move_data["uci"])
                    if move in board.legal_moves:
                        rank = move_data.get("rank", 1)
                        arrow_types = [
                            ArrowType.BEST_MOVE,
                            ArrowType.CANDIDATE_2,
                            ArrowType.CANDIDATE_3,
                        ]
                        confidences = [1.0, 0.7, 0.5]
                        atype = arrow_types[min(rank - 1, 2)]
                        conf = confidences[min(rank - 1, 2)]
                        arrows.append(
                            ChessArrow(
                                from_square=move.from_square,
                                to_square=move.to_square,
                                arrow_type=atype,
                                confidence=conf,
                                reason=f"Candidate move rank {rank}",
                            )
                        )
                except (ValueError, KeyError, IndexError):
                    continue
        else:
            # Fallback: original single best_move logic
            best_arrow = self._get_best_move_arrow(board, analysis)
            if best_arrow:
                arrows.append(best_arrow)

        # 2. Threat arrows (detect attacks on own pieces)
        threat_arrows = self._detect_threat_arrows(board)
        arrows.extend(threat_arrows)

        # 3. Defensive arrows (moves protecting threatened pieces)
        if threat_arrows:  # Only add if there are threats to defend against
            defense_arrows = self._detect_defensive_arrows(board, threat_arrows)
            arrows.extend(defense_arrows)

        # Apply smart filtering if enabled
        if self.smart_mode:
            arrows = self._smart_filter(board, arrows)

        # Enforce hard limit
        if len(arrows) > self.max_arrows_per_frame:
            arrows = arrows[:self.max_arrows_per_frame]

        return arrows

    def _get_best_move_arrow(
        self, board: chess.Board, analysis: "MoveAnalysis"
    ) -> Optional[ChessArrow]:
        """Extract best move from analysis and create arrow."""
        if not hasattr(analysis, "best_move") or not analysis.best_move:
            return None

        try:
            move = chess.Move.from_uci(analysis.best_move)
            if move in board.legal_moves:
                return ChessArrow(
                    from_square=move.from_square,
                    to_square=move.to_square,
                    arrow_type=ArrowType.BEST_MOVE,
                    confidence=1.0,
                    reason="Best move from analysis",
                )
        except (ValueError, AttributeError):
            pass

        return None

    def _detect_threat_arrows(self, board: chess.Board) -> List[ChessArrow]:
        """
        Detect threats on own pieces and create red threat arrows.
        Shows opponent's most dangerous move (attacking move that threatens our material).
        """
        threats: List[ChessArrow] = []

        # Check for immediate checks first (highest priority threat)
        if board.is_check():
            # Find which piece is checking us
            checking_move = self._find_checking_move(board)
            if checking_move:
                threats.append(
                    ChessArrow(
                        from_square=checking_move.from_square,
                        to_square=checking_move.to_square,
                        arrow_type=ArrowType.THREAT,
                        confidence=1.0,
                        reason="Direct check",
                    )
                )
            return threats  # Focus only on check if it exists

        # Find undefended/hanging pieces
        opponent_board = board.copy()
        opponent_board.turn = not opponent_board.turn

        for move in opponent_board.legal_moves:
            # Skip quiet moves and checks for now (focus on captures/attacks)
            if opponent_board.is_capture(move):
                threats.append(
                    ChessArrow(
                        from_square=move.from_square,
                        to_square=move.to_square,
                        arrow_type=ArrowType.THREAT,
                        confidence=0.8,
                        reason="Opponent can capture",
                    )
                )
                break  # Show only the most critical threat

        return threats

    def _detect_defensive_arrows(
        self, board: chess.Board, threat_arrows: List[ChessArrow]
    ) -> List[ChessArrow]:
        """
        Suggest defensive moves that protect threatened pieces.
        Yellow arrows showing moves that defend.
        """
        defensive: List[ChessArrow] = []

        if not threat_arrows:
            return defensive

        # Get the first threat (most critical)
        threat = threat_arrows[0]
        threatened_square = threat.to_square

        # Find moves that defend the threatened square
        for move in board.legal_moves:
            # After this move, is the threatened square defended?
            board_after = board.copy()
            board_after.push(move)

            # Check if we can now defend that square or move the piece away
            if (
                board_after.is_attacked_by(board_after.turn, threatened_square)
                == False
            ):
                defensive.append(
                    ChessArrow(
                        from_square=move.from_square,
                        to_square=move.to_square,
                        arrow_type=ArrowType.DEFENSIVE,
                        confidence=0.7,
                        reason="Defends threatened piece",
                    )
                )
                break  # Show only one defensive arrow (best one)

        return defensive

    def _find_checking_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Find the move that's currently giving check."""
        opponent_board = board.copy()
        opponent_board.turn = not opponent_board.turn

        for move in opponent_board.legal_moves:
            board_after = opponent_board.copy()
            board_after.push(move)
            if board_after.is_check():
                return move

        return None

    def _smart_filter(
        self, board: chess.Board, arrows: List[ChessArrow]
    ) -> List[ChessArrow]:
        """
        Intelligently filter arrows to reduce clutter on complex positions.
        Rules:
        - Always keep best move + candidate arrows (rank 1-3, green family)
        - On complex positions (3+ legal moves available), limit to 2 threats max
        - Remove low-confidence defensive moves if space is tight
        - Candidate arrows have lower priority: include if space available
        """
        if len(arrows) <= 2:
            return arrows  # No filtering needed

        # Count legal moves (complexity indicator)
        legal_move_count = len(list(board.legal_moves))
        is_complex = legal_move_count >= 20

        # Separate by type (green candidates sorted by confidence/rank)
        best_moves = [
            a
            for a in arrows
            if a.arrow_type in (ArrowType.BEST_MOVE, ArrowType.CANDIDATE_2, ArrowType.CANDIDATE_3)
        ]
        threats = [a for a in arrows if a.arrow_type == ArrowType.THREAT]
        defensives = [a for a in arrows if a.arrow_type == ArrowType.DEFENSIVE]

        # Sort green moves by confidence (best first)
        best_moves_sorted = sorted(best_moves, key=lambda a: a.confidence, reverse=True)

        # Rebuild with priority
        filtered = []

        # 1. Always include best move (rank 1)
        best_only = [a for a in best_moves_sorted if a.arrow_type == ArrowType.BEST_MOVE]
        filtered.extend(best_only)

        # 2. Include top threats
        max_threats = 1 if is_complex else 2
        filtered.extend(threats[:max_threats])

        # 3. Include candidates (rank 2-3) only if space available
        if len(filtered) < self.max_arrows_per_frame:
            remaining_space = self.max_arrows_per_frame - len(filtered)
            candidates = [a for a in best_moves_sorted if a.arrow_type != ArrowType.BEST_MOVE]
            filtered.extend(candidates[:remaining_space])

        # 4. Include defensives only if still not too crowded
        if len(filtered) < self.max_arrows_per_frame:
            remaining_space = self.max_arrows_per_frame - len(filtered)
            filtered.extend(defensives[:remaining_space])

        return filtered

    def _find_most_critical_threat(
        self, threats: List[ChessArrow]
    ) -> Optional[ChessArrow]:
        """
        From a list of threats, return the most critical one.
        Prioritize: checks > captures of high-value pieces > other attacks
        """
        if not threats:
            return None

        # Sort by confidence (higher = more critical)
        threats_sorted = sorted(threats, key=lambda a: a.confidence, reverse=True)
        return threats_sorted[0]


# ── Integration helper ──────────────────────────────────────────────────────


def get_arrows_for_frame(
    board: chess.Board,
    analysis: Optional[object] = None,
    analyzer: Optional[ArrowAnalyzer] = None,
) -> List[ChessArrow]:
    """
    Convenience function to get arrows for a board state.
    Creates analyzer if not provided.
    """
    if analyzer is None:
        analyzer = ArrowAnalyzer(max_arrows_per_frame=5, smart_mode=True)

    return analyzer.analyze_position(board, analysis)
