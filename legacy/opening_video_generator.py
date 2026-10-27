"""opening_video_generator.py — Generate opening theory and trap short videos."""

import io
import os
import logging

logger = logging.getLogger(__name__)


class OpeningCommentaryGenerator:
    def __init__(self, use_claude: bool = False):
        self.use_claude = use_claude

    def generate(self, opening) -> str:
        if self.use_claude:
            try:
                from commentary_generator import CommentaryGenerator
                gen = CommentaryGenerator()
                script = gen.generate_opening_commentary(
                    opening_name=opening.name,
                    eco=opening.eco,
                    moves=opening.moves,
                )
                return "\n".join(script.segments)
            except Exception as e:
                logger.warning(f"LLM commentary failed ({e}), using fallback")
        return self._fallback(opening)

    def _fallback(self, opening) -> str:
        return (
            f"Welcome to ChessCode! Today we're studying the {opening.name}.\n"
            f"This opening carries ECO code {opening.eco}.\n"
            f"{opening.tagline}.\n"
            f"The main line begins: {opening.moves}.\n"
            "Understanding this opening will improve your chess significantly.\n"
            "Thanks for watching ChessCode — like and subscribe for more!"
        )


class OpeningVideoGenerator:
    def __init__(self, use_claude: bool = False):
        self.use_claude = use_claude

    def generate(self, opening, output_dir: str = "output/openings",
                 fmt: str = "hd", intro_data=None) -> str:
        os.makedirs(output_dir, exist_ok=True)
        safe = opening.name.lower().replace(" ", "_").replace("'", "")
        out_path = os.path.join(output_dir, f"{safe}_en.mp4")

        commentary = OpeningCommentaryGenerator(use_claude=self.use_claude).generate(opening)
        segments = [s.strip() for s in commentary.split("\n") if s.strip()]

        from tts_generator import TTSGenerator
        audio_paths = TTSGenerator(language="en").generate_batch(
            segments, output_dir=os.path.join(output_dir, f"{safe}_audio_en"),
        )

        from board_renderer import BoardRenderer, RenderOptions, THEMES
        theme = THEMES["classic"]
        theme.board_size = 800 if fmt == "hd" else 900
        board_renderer = BoardRenderer(RenderOptions(
            theme=theme,
            output_dir=os.path.join(output_dir, f"{safe}_frames"),
            show_arrows=False,
        ))
        frame_paths = board_renderer.render_game(opening.game(), game_id=safe)

        from commentary_generator import GameScript
        script = GameScript(
            title=f"{opening.name} - Opening Guide",
            description=opening.tagline,
            tags=["chess", "opening", opening.name.lower()],
            segments=segments,
        )

        # Rich animated opening intro (SVG → cairosvg), prepended to the video.
        intro_frames = None
        if intro_data is not None:
            try:
                from scene_renderer import FORMATS
                from opening_intro_renderer import render_intro_sequence
                from config import cfg
                vfmt = FORMATS.get(fmt, FORMATS["hd"])
                intro_frames = render_intro_sequence(
                    intro_data, vfmt,
                    out_dir=os.path.join(output_dir, f"{safe}_frames"),
                    game_id=safe,
                    duration=getattr(cfg, "opening_intro_duration", 6.5),
                )
            except Exception as e:
                logger.warning(f"opening intro render failed, continuing without it: {e}")

        from video_assembler import VideoAssembler, AssemblyConfig
        VideoAssembler(AssemblyConfig(output_path=out_path, format=fmt)).assemble(
            frame_paths, audio_paths,
            _stub_ga(opening.name), script,
            transition_map=board_renderer.transition_map,
            intro_frames=intro_frames,
        )
        return out_path

    def generate_trap_short(self, trap, output_dir: str = "output/traps") -> str:
        import chess.pgn

        os.makedirs(output_dir, exist_ok=True)
        safe = trap.name.lower().replace(" ", "_")
        out_path = os.path.join(output_dir, f"{safe}_short.mp4")

        commentary = (
            f"Watch out for the {trap.name}!\n"
            f"This trap arises in the {trap.opening}.\n"
            f"The key moves are: {trap.moves}\n"
            "Knowing this trap can win you games in seconds!"
        )
        segments = [s.strip() for s in commentary.split("\n") if s.strip()]

        from tts_generator import TTSGenerator
        audio_paths = TTSGenerator(language="en").generate_batch(
            segments, output_dir=os.path.join(output_dir, f"{safe}_audio"),
        )

        pgn_text = (
            f'[Event "Trap"]\n[White "White"]\n[Black "Black"]\n[Result "*"]\n\n'
            f'{trap.moves} *'
        )
        game = chess.pgn.read_game(io.StringIO(pgn_text))

        from board_renderer import BoardRenderer, RenderOptions, THEMES
        theme = THEMES["classic"]
        theme.board_size = 900
        frame_paths = []
        board_renderer = BoardRenderer(RenderOptions(
            theme=theme,
            output_dir=os.path.join(output_dir, f"{safe}_frames"),
            show_arrows=False,
        ))
        if game:
            frame_paths = board_renderer.render_game(game, game_id=safe)

        from commentary_generator import GameScript
        script = GameScript(title=f"The {trap.name}!", segments=segments)

        from video_assembler import VideoAssembler, AssemblyConfig
        VideoAssembler(AssemblyConfig(output_path=out_path, format="shorts")).assemble(
            frame_paths, audio_paths, _stub_ga(trap.name), script,
            transition_map=board_renderer.transition_map,
        )
        return out_path


def _stub_ga(name: str):
    class _GA:
        white = "White"
        black = "Black"
        result = "*"
        opening = name
    return _GA()
