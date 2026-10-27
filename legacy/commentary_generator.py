"""commentary_generator.py — Chess game commentary using configured LLM backend."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GameScript:
    """Structured output from commentary generation."""
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    segments: List[str] = field(default_factory=list)  # list of narration text segments
    # When set, the script is a strict per-move script: segments == [intro] +
    # move_comments (one per ply, in order) + [conclusion]. Signals the video
    # assembler to map segments 1:1 onto move frames instead of proportionally.
    per_move: bool = False
    # Hindi fields (populated from MCP call or bilingual fallback)
    title_hi: str = ""
    intro_hi: str = ""
    segments_hi: List[str] = field(default_factory=list)
    conclusion_hi: str = ""
    tags_hi: List[str] = field(default_factory=list)

    @property
    def has_hindi(self) -> bool:
        return bool(self.segments_hi or self.intro_hi)


class CommentaryGenerator:
    """Generates game commentary using the configured LLM backend (Claude or Ollama)."""

    SYSTEM_PROMPT = (
        "You are an expert chess commentator for a YouTube channel. "
        "Write engaging, educational commentary that sounds natural when spoken aloud. "
        "PUNCTUATION RULES — critical for TTS voice quality:\n"
        "- Use commas for natural breath pauses within sentences.\n"
        "- Use ellipsis (...) for dramatic pauses before reveals or surprising moves.\n"
        "- Use exclamation marks sparingly for genuinely brilliant or shocking moments.\n"
        "- Use question marks when posing rhetorical questions to the viewer.\n"
        "- Never write wall-of-text sentences. Break at natural speaking rhythm.\n"
        "Example good: 'And here... Rxf7! The rook sacrifice that changes everything.'\n"
        "Example bad: 'The rook moves to f7 and captures the pawn which leads to a winning position.'"
    )

    def __init__(self):
        from config import cfg
        from llm_backends import get_backend
        self._backend = get_backend(cfg)

    def generate_game_commentary(self, analysis) -> GameScript:
        """Generate English commentary for a game analysis object."""
        user_prompt = self._build_game_prompt(analysis)
        response = self._backend.generate(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=800,
        )
        return self._parse_response(response, analysis)

    def generate_opening_commentary(self, opening_name: str, eco: str = "", moves: str = "") -> GameScript:
        """Generate commentary for an opening theory video."""
        user_prompt = (
            f"Create a YouTube video script for the chess opening: {opening_name}.\n"
            f"ECO code: {eco}\n"
            f"Key moves: {moves}\n\n"
            "Include: introduction, key ideas, main variations summary, tips for players. "
            "Keep it under 3 minutes when spoken aloud."
        )
        response = self._backend.generate(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=600,
        )
        return GameScript(
            title=f"{opening_name} — Chess Opening Guide",
            description=response[:200],
            segments=[response],
        )

    def _build_game_prompt(self, analysis) -> str:
        white = getattr(analysis, "white", "White")
        black = getattr(analysis, "black", "Black")
        result = getattr(analysis, "result", "*")
        opening = getattr(analysis, "opening", "Unknown opening")
        return (
            f"Create commentary for this chess game:\n"
            f"Players: {white} vs {black}\n"
            f"Result: {result}\n"
            f"Opening: {opening}\n\n"
            "Write 5-8 sentences of engaging commentary. "
            "End with one key lesson for the viewer."
        )

    def _parse_response(self, response: str, analysis) -> GameScript:
        white = getattr(analysis, "white", "White")
        black = getattr(analysis, "black", "Black")
        result = getattr(analysis, "result", "*")
        opening = getattr(analysis, "opening", "")
        title = f"{white} vs {black} — {opening or 'Chess Game'}"
        sentences = [s.strip() for s in response.replace("\n", " ").split(".") if s.strip()]
        return GameScript(
            title=title,
            description=response[:200],
            tags=["chess", "chesscode", white.lower(), black.lower(), opening.lower()],
            segments=sentences[:8],
        )


class FallbackCommentaryGenerator:
    """Template-based fallback when no LLM is available."""

    def generate_game_commentary(self, analysis) -> GameScript:
        white = getattr(analysis, "white", "White")
        black = getattr(analysis, "black", "Black")
        result = getattr(analysis, "result", "*")
        opening = getattr(analysis, "opening", "this opening")
        segments = [
            f"Welcome to ChessCode! Today we're watching {white} face {black}.",
            f"This game features {opening}.",
            f"The game concluded with result {result}.",
            "Stay tuned for more chess analysis on ChessCode!",
        ]
        return GameScript(
            title=f"{white} vs {black}",
            description=f"Game analysis: {white} vs {black}, {result}",
            tags=["chess", "chesscode"],
            segments=segments,
        )

    def generate_opening_commentary(self, opening_name: str, eco: str = "", moves: str = "") -> GameScript:
        segments = [
            f"Welcome to ChessCode! Today we're studying the {opening_name}.",
            f"This opening (ECO: {eco}) is a popular choice at all levels.",
            "Watch carefully as we walk through the key ideas.",
            "Thanks for watching ChessCode!",
        ]
        return GameScript(
            title=f"{opening_name} — Opening Guide",
            description=f"Learn the {opening_name} chess opening.",
            tags=["chess", "opening", opening_name.lower()],
            segments=segments,
        )
