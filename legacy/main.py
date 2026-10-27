"""
main.py — ChessCode Master Pipeline
=====================================
Single command to go from a PGN or opening name
to fully rendered, dual-language YouTube-ready videos.

Usage:
  # Game analysis (English only)
  python main.py game.pgn

  # Game analysis + Hindi version
  python main.py game.pgn --hindi

  # Opening theory video
  python main.py --opening "Sicilian Najdorf"
  python main.py --opening "london" --hindi

  # Trap Shorts
  python main.py --trap "Fried Liver Attack" --opening "Italian Game"

  # Full pipeline with upload
  python main.py game.pgn --hindi --upload --quality medium

  # System test (no render)
  python main.py --test
"""

import os, sys, time, argparse, logging, chess, chess.pgn

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("chesscode.log", encoding="utf-8")],
)
logger = logging.getLogger("main")


# ─────────────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="ChessCode Automated Chess Video Pipeline")
    g = p.add_mutually_exclusive_group()
    g.add_argument("pgn",          nargs="?",     help="Path to PGN file (game analysis)")
    g.add_argument("--opening",    metavar="NAME",help="Opening name/alias (opening theory video)")
    g.add_argument("--trap",       metavar="NAME",help="Trap name for a Shorts video")
    g.add_argument("--test",       action="store_true", help="System check, no render")

    p.add_argument("--hindi",      action="store_true", help="Generate Hindi version too")
    p.add_argument("--upload",     action="store_true", help="Upload to YouTube after render")
    p.add_argument("--publish-at", dest="publish_at", metavar="ISO8601", default="",
                   help="Schedule the YouTube publish for an ISO 8601 UTC datetime "
                        "(e.g. 2026-07-20T09:00:00Z). Implies --upload; forces the video "
                        "private until that time.")
    p.add_argument("--quality",    default=cfg.encoding_preset,
                   choices=["ultrafast","superfast","veryfast","faster","fast","medium","slow"],
                   help=f"Encoding preset (default: {cfg.encoding_preset})")
    p.add_argument("--codec",      default=cfg.video_codec,
                   choices=["libx264","h264_qsv","h264_nvenc","h264_amf"],
                   help=f"Video encoder (default: {cfg.video_codec}); "
                        f"h264_qsv/nvenc/amf use GPU hardware encode if available")
    p.add_argument("--depth",      type=int, default=cfg.stockfish_depth,
                   help=f"Stockfish depth (default: {cfg.stockfish_depth})")
    p.add_argument("--theme",      default=cfg.board_theme,
                   choices=["classic","blue","green","dark_mode"])
    p.add_argument("--shorts",     action="store_true", help="Shorts format (1080×1920)")
    p.add_argument("--output",     default=cfg.output_dir)
    p.add_argument("--no-stockfish", action="store_true")
    p.add_argument("--no-claude",    action="store_true")
    p.add_argument("--llm-backend", dest="llm_backend",
                   choices=["claude", "ollama"], default=None,
                   help="LLM backend override (default: from LLM_BACKEND env var)")
    p.add_argument("--tts-backend", dest="tts_backend",
                   choices=["kokoro", "elevenlabs", "gtts"], default=None,
                   help="TTS backend override (default: from TTS_BACKEND env var)")
    p.add_argument("--no-upload", action="store_true",
                   help="Skip YouTube upload even if --upload is passed")
    p.add_argument("--provided-commentary", metavar="PATH",
                   help="Path to a text file with pre-written commentary (skips LLM)")
    p.add_argument("--provided-commentary-json", metavar="PATH",
                   help="Path to a JSON file {intro, move_comments[], conclusion} for a "
                        "strict per-move script (skips LLM)")
    p.add_argument("--provided-commentary-json-hi", metavar="PATH",
                   help="Path to a JSON file {intro, move_comments[], conclusion} with a "
                        "genuinely separate, user-provided Hindi script (used with --hindi; "
                        "skips the bilingual auto-translate generator)")
    p.add_argument("--provided-title", metavar="TITLE",
                   help="Video title when using --provided-commentary")
    p.add_argument("--hindi-only", action="store_true",
                   help="Skip the English-specific TTS/render/thumbnail steps and only "
                        "produce <game_id>_hi.mp4 (requires --hindi). Used to render a "
                        "genuinely independent Hindi-only job without redundant English work.")
    p.add_argument("--opening-payload-json", metavar="PATH",
                   help="Path to a JSON file {famous_players[], players_note, ...} "
                        "for the opening intro card (used with --opening)")
    p.add_argument("--no-avatar", action="store_true",
                   help="Disable talking pawn avatar overlay")
    p.add_argument("--no-stats-intro", action="store_true",
                   help="Disable the animated stats intro card at video start")
    p.add_argument("--dashboard", action="store_true",
                   help="Show content calendar dashboard and exit")
    p.add_argument("--no-arrows", action="store_true",
                   help="Disable arrow visualization on board")
    p.add_argument("--fast-test", dest="fast_test", action="store_true",
                   help="Quick-iteration mode: force gTTS (fast, no local model load), "
                        "shallow Stockfish depth, and skip the avatar + stats intro. "
                        "For previewing render changes without waiting on slow TTS.")
    p.add_argument("--arrow-intensity", default=cfg.arrow_intensity,
                   choices=["conservative", "normal", "aggressive"],
                   help=f"Arrow display intensity: conservative (2 arrows) / normal (4) / aggressive (6)")
    p.add_argument("--legend-name", metavar="NAME",
                   help="Chess legend featured in the sidebar legend card (default: rotates through built-in list)")
    p.add_argument("--legend-title", metavar="TITLE",
                   help="Legend's subtitle line, e.g. 'World Champion 1960-1961'")
    p.add_argument("--legend-fact", metavar="FACT",
                   help="1-2 sentence fact about the legend, word-wrapped in the card")
    p.add_argument("--no-legend-card", action="store_true",
                   help="Disable the legend-card toggle; always show the move list")
    p.add_argument("--calendar", nargs="+", metavar="CMD",
                   help="Calendar commands: list | add <type> <id> <title> | run")
    p.add_argument("--job-id", metavar="ID",
                   help="job_id assigned by the MCP server (mcp_server.py) for this run — "
                        "used to correlate this process with logs/<job_id>_stages.json "
                        "progress tracking. Not needed for direct CLI usage.")
    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
def system_test():
    """Check all dependencies and API keys."""
    print(cfg.summary())
    checks = [
        ("python-chess",  lambda: __import__("chess")),
        ("cairosvg",      lambda: __import__("cairosvg")),
        ("Pillow",        lambda: __import__("PIL")),
        ("MoviePy",       lambda: __import__("moviepy")),
        ("gTTS",          lambda: __import__("gtts")),
        ("requests",      lambda: __import__("requests")),
        ("schedule",      lambda: __import__("schedule")),
        ("Stockfish",     lambda: __import__("subprocess").run(
            [cfg.stockfish_path, "--version"], capture_output=True, timeout=3)),
        ("ffmpeg",        lambda: __import__("subprocess").run(
            ["ffmpeg", "-version"], capture_output=True, timeout=5)),
        ("Hindi font",    lambda: open("assets/fonts/NotoSansDevanagari-Bold.ttf")),
        ("rich",         lambda: __import__("rich")),
        ("httpx",        lambda: __import__("httpx")),
    ]
    all_ok = True
    for name, check in checks:
        try:
            check()
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            all_ok = False

    api_checks = [
        ("Claude API",    cfg.has_anthropic, "Set ANTHROPIC_API_KEY"),
        ("ElevenLabs",    cfg.has_elevenlabs,"Set ELEVENLABS_API_KEY (optional, gTTS free)"),
        ("Leonardo AI",   cfg.has_leonardo,  "Set LEONARDO_API_KEY (optional, PIL fallback)"),
        ("Lichess token", cfg.has_lichess,   "Set LICHESS_TOKEN (optional but recommended)"),
        ("Ollama",        cfg.has_ollama, "Set LLM_BACKEND=ollama (optional, Claude used otherwise)"),
    ]
    for name, ok, hint in api_checks:
        sym = "✓" if ok else "⚠"
        note = "" if ok else f" — {hint}"
        print(f"  {sym} {name}{note}")

    print(f"\n  {'✅ System ready!' if all_ok else '⚠  Some deps missing — check above'}")
    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
def run_game_pipeline(args, game_pgn, game_id):
    """Full game analysis → bilingual videos → thumbnails → optional upload."""
    _set_job_ctx(args)
    if getattr(args, "hindi_only", False) and not args.hindi:
        logger.warning("  --hindi-only set without --hindi — no video will be rendered")
    t0 = time.time()
    out = os.path.join(args.output, game_id)
    os.makedirs(out, exist_ok=True)
    fmt = "shorts" if args.shorts else "hd"

    # ── 1. Stockfish ─────────────────────────────────────────────────────────
    _banner(1, "Stockfish analysis")
    analysis = None
    if not args.no_stockfish:
        try:
            from stockfish_analyzer import StockfishAnalyzer
            with StockfishAnalyzer(stockfish_path=cfg.stockfish_path,
                                   depth=args.depth, threads=cfg.stockfish_threads,
                                   workers=cfg.stockfish_workers) as sf:
                analysis = sf.analyze_game(game_pgn, game_id=game_id,
                                           progress_callback=_progress)
            print()
            logger.info(analysis.summary())
        except (RuntimeError, ModuleNotFoundError) as e:
            logger.warning(f"  Stockfish unavailable: {e}")

    from commentary_generator import FallbackCommentaryGenerator, GameScript
    ga = analysis or _dummy_ga(game_pgn, game_id)

    # ── Kick off background work that only needs `ga`/`analysis` ───────────────
    # Board-frame rendering and meme captions don't depend on TTS/avatar output,
    # so start them now instead of after stage 4/4.5 — they run concurrently
    # with commentary/TTS/avatar generation below instead of being sandwiched
    # after it for no data reason.
    from concurrent.futures import ThreadPoolExecutor
    bg_pool = ThreadPoolExecutor(max_workers=2)

    _banner(5, "Board frames (started in background)")
    from board_renderer import BoardRenderer, RenderOptions, THEMES
    from scene_renderer import FORMATS
    vfmt  = FORMATS[fmt]
    theme = THEMES.get(args.theme, THEMES["classic"])
    theme.board_size = cfg.board_size_hd if fmt == "hd" else cfg.board_size_shorts
    opts  = RenderOptions(theme=theme, output_dir=os.path.join(out,"frames"),
                          show_arrows=cfg.show_arrows and not getattr(args, "no_arrows", False),
                          arrow_intensity=getattr(args, "arrow_intensity", cfg.arrow_intensity),
                          enable_transitions=cfg.enable_move_transitions,
                          transition_frame_count=cfg.transition_frame_count,
                          legend_name=getattr(args, "legend_name", None),
                          legend_title=getattr(args, "legend_title", None),
                          legend_fact=getattr(args, "legend_fact", None),
                          show_legend_card=not getattr(args, "no_legend_card", False))
    board_renderer = BoardRenderer(opts, render_workers=cfg.render_workers)
    frames_future = bg_pool.submit(board_renderer.render_game,
                                   game_pgn, ga.to_list() if analysis else [], game_id, ga)

    meme_overlays_future = None
    if cfg.enable_memes and analysis:
        _banner("5.5", "Memes (started in background)")
        from meme_inserter import build_meme_overlays
        from llm_backends import get_backend
        meme_overlays_future = bg_pool.submit(build_meme_overlays, ga, cfg, get_backend(cfg))

    # ── 2. English commentary ─────────────────────────────────────────────────
    _banner(2, "Commentary (English)")

    # ── 1.5. Stats intro ──────────────────────────────────────────────────────
    intro_frames_hd = None
    if cfg.stats_intro_enabled and not getattr(args, "no_stats_intro", False):
        _banner("1.5", "Stats intro")
        try:
            from scene_renderer import FORMATS as _FORMATS
            from stats_intro_renderer import StatsIntroData, PlayerRatingRow, render_intro_sequence
            from opening_stats import get_opening_stats
            from channel_stats import get_channel_stats

            _intro_vfmt = _FORMATS["shorts" if args.shorts else "hd"]

            ratings = None
            if ga.white_elo or ga.black_elo:
                ratings = PlayerRatingRow(white_name=ga.white, black_name=ga.black,
                                          white_elo=ga.white_elo, black_elo=ga.black_elo,
                                          result=ga.result)

            moves_san = " ".join(m.move_san for m in ga.moves[:8]) if ga.moves else ""

            # Both are independent network calls (Lichess / YouTube Data API) —
            # run them concurrently rather than back-to-back.
            with ThreadPoolExecutor(max_workers=2) as stats_ex:
                o_stats_fut = stats_ex.submit(get_opening_stats, ga.opening, moves_san=moves_san,
                                              cache_dir=cfg.opening_stats_cache_dir,
                                              min_games=cfg.opening_stats_min_games)
                c_stats_fut = stats_ex.submit(get_channel_stats, cfg.youtube_api_key, cfg.youtube_channel_id,
                                              cache_dir=cfg.channel_stats_cache_dir,
                                              ttl_seconds=cfg.channel_stats_ttl_seconds)

                o_stats = None
                try:
                    o_stats = o_stats_fut.result()
                except Exception as e:
                    logger.warning(f"  Opening stats unavailable: {e}")

                c_stats = None
                try:
                    c_stats = c_stats_fut.result()
                except Exception as e:
                    logger.warning(f"  Channel stats unavailable: {e}")

            intro_data = StatsIntroData(ratings=ratings, opening_name=ga.opening,
                                        opening_stats=o_stats, channel_stats=c_stats,
                                        channel_name=cfg.channel_name)
            intro_frames_hd = render_intro_sequence(
                intro_data, _intro_vfmt, out_dir=os.path.join(out, "intro"),
                game_id=game_id, duration=cfg.stats_intro_duration, fps=cfg.fps,
                cache_dir=cfg.stats_intro_cache_dir)
            logger.info(f"  Intro: {len(intro_frames_hd[0])} keyframes, "
                       f"{sum(intro_frames_hd[1]):.1f}s")
        except Exception as e:
            logger.warning(f"  Stats intro failed, continuing without it: {e}")
            intro_frames_hd = None

    # --hindi-only runs skip English commentary generation entirely (no LLM call,
    # no en_script) — the English TTS/render/thumbnail/upload steps below are all
    # guarded on this being None, so a --hindi-only job does no redundant English work.
    en_script = None
    if getattr(args, "hindi_only", False):
        logger.info("  --hindi-only: skipping English commentary generation")
    elif args.provided_commentary_json:
        import json as _json
        with open(args.provided_commentary_json, encoding="utf-8") as f:
            _com = _json.load(f)
        _title = args.provided_title or game_id
        intro = (_com.get("intro") or "").strip()
        move_comments = [str(c).strip() for c in _com.get("move_comments", [])]
        conclusion = (_com.get("conclusion") or "").strip()
        # Strict per-move order: intro over the start frame, one comment per move,
        # conclusion over the final frame. No sentence-splitting/smearing.
        segments = ([intro] if intro else []) + move_comments + ([conclusion] if conclusion else [])
        en_script = GameScript(
            title=_title,
            description=intro[:200],
            segments=segments,
            per_move=True,
            intro_hi=(_com.get("intro_hi") or "").strip(),
            segments_hi=[str(c).strip() for c in _com.get("move_comments_hi", [])],
            conclusion_hi=(_com.get("conclusion_hi") or "").strip(),
        )
        # Attach coach insights to analysis move objects if provided
        _coach_list = _com.get("coach_insights", [])
        if _coach_list and ga is not None and ga.moves:
            try:
                from board_renderer import CoachInsights
                for _i, _ci in enumerate(_coach_list):
                    if _i < len(ga.moves):
                        ga.moves[_i].coach = CoachInsights(
                            move_number=_ci.get("move_number", _i + 1),
                            turn=_ci.get("turn", "white"),
                            san_move=_ci.get("san_move", ga.moves[_i].move_san),
                            top_engine_moves=_ci.get("top_engine_moves", []),
                            insights=_ci.get("insights", []),
                        )
            except Exception as _e:
                logger.warning(f"Could not attach coach insights: {_e}")
    elif args.provided_commentary:
        with open(args.provided_commentary, encoding="utf-8") as f:
            _provided_text = f.read().strip()
        _title = args.provided_title or game_id
        sentences = [s.strip() + "." for s in _provided_text.split(".") if s.strip()]
        en_script = GameScript(
            title=_title,
            description=_provided_text[:200],
            segments=sentences,
        )
    elif analysis and cfg.has_anthropic and not args.no_claude:
        from commentary_generator import CommentaryGenerator
        en_script = CommentaryGenerator().generate_game_commentary(analysis)
    else:
        en_script = FallbackCommentaryGenerator().generate_game_commentary(ga)
    if en_script is not None:
        logger.info(f"  Title: {en_script.title}")

    # ── 3. Hindi commentary ───────────────────────────────────────────────────
    hi_script = None
    if getattr(args, "provided_commentary_json_hi", None) and args.hindi:
        # A genuinely separate, user-provided Hindi script — same strict per-move
        # GameScript shape as the English --provided-commentary-json branch above,
        # NOT run through the bilingual auto-translate generator.
        _banner(3, "Commentary (Hindi, provided)")
        import json as _json
        with open(args.provided_commentary_json_hi, encoding="utf-8") as f:
            _com_hi = _json.load(f)
        _title_hi = args.provided_title or game_id
        intro_hi = (_com_hi.get("intro") or "").strip()
        move_comments_hi = [str(c).strip() for c in _com_hi.get("move_comments", [])]
        conclusion_hi = (_com_hi.get("conclusion") or "").strip()
        segments_hi = ([intro_hi] if intro_hi else []) + move_comments_hi + ([conclusion_hi] if conclusion_hi else [])
        hi_script = GameScript(
            title=_title_hi,
            description=intro_hi[:200],
            segments=segments_hi,
            per_move=True,
        )
        logger.info(f"  Hindi title (provided): {hi_script.title}")
    elif not args.provided_commentary and not args.provided_commentary_json \
            and args.hindi and cfg.has_anthropic:
        _banner(3, "Commentary (Hindi)")
        from bilingual import BilingualScriptGenerator, BilingualScript
        try:
            gen = BilingualScriptGenerator()
            bi  = gen.generate(analysis, game_pgn)
            hi_script = bi
            logger.info(f"  Hindi title: {bi.hi_title}")
        except Exception as e:
            logger.warning(f"  Hindi failed: {e}")

    # ── 4. TTS — English ─────────────────────────────────────────────────────
    # Import unconditionally: the Hindi TTS block below (step 7) reuses TTSGenerator
    # too, and must still be able to import it when the English generation is
    # skipped in --hindi-only mode.
    from tts_generator import TTSGenerator
    audio_en = None
    if not getattr(args, "hindi_only", False):
        _banner(4, "TTS — English")
        tts_en   = TTSGenerator(language="en",
                                prefer_elevenlabs=cfg.has_elevenlabs,
                                elevenlabs_api_key=cfg.elevenlabs_api_key,
                                voice_id=cfg.voice_en)
        audio_en = tts_en.generate_batch(en_script.segments,
                                         output_dir=os.path.join(out, "audio_en"))

    # ── 4.5. Talking avatar ───────────────────────────────────────────────────
    avatar_en_path = None
    avatar_hi_path = None
    use_avatar = False
    if use_avatar:
        _banner("4.5", "Talking avatar")
        from avatar_generator import AvatarGenerator
        av_gen = AvatarGenerator(
            sadtalker_dir=cfg.sadtalker_dir,
            avatar_image=cfg.avatar_image_path,
        )
        avatar_en_path = av_gen.generate(audio_en, output_dir=os.path.join(out, "avatar_en"))
        if avatar_en_path:
            logger.info(f"  Avatar (EN): {avatar_en_path}")
        else:
            logger.info("  Avatar skipped (generation failed)")

    # ── 5/5.5. Join background board-frame render + meme captions ─────────────
    _banner(5, "Board frames — joining background render")
    frame_paths = frames_future.result()
    logger.info(f"  {len(frame_paths)} frames")

    meme_overlays = []
    if meme_overlays_future:
        _banner("5.5", "Memes — joining background captions")
        meme_overlays = meme_overlays_future.result()
        logger.info(f"  {len(meme_overlays)} meme overlay(s)")

    bg_pool.shutdown(wait=True)

    # ── 6. Render video (English audio) ──────────────────────────────────────
    # Import unconditionally: the Hindi render block below (step 7) reuses
    # VideoAssembler/AssemblyConfig too, and must still be able to import them when
    # the English render is skipped in --hindi-only mode.
    from video_assembler import VideoAssembler, AssemblyConfig
    en_path = None
    if not getattr(args, "hindi_only", False):
        _banner(6, "Render — English")
        en_path = os.path.join(out, f"{game_id}_en.mp4")
        VideoAssembler(AssemblyConfig(
            output_path=en_path, format=fmt, fps=cfg.fps,
            video_bitrate=cfg.video_bitrate, audio_bitrate=cfg.audio_bitrate,
            preset=args.quality, video_codec=args.codec, crossfade=cfg.crossfade_duration,
        )).assemble(frame_paths, audio_en, ga, en_script,
                    event=game_pgn.headers.get("Event",""),
                    avatar_video_path=avatar_en_path,
                    transition_map=board_renderer.transition_map,
                    intro_frames=intro_frames_hd,
                    meme_overlays=meme_overlays)
        logger.info(f"  ✅ {en_path}")

    # ── 7. Render Hindi version (mux different audio) ─────────────────────────
    hi_path = None
    if args.hindi:
        _banner(7, "Render — Hindi")
        hi_segments = _hi_render_segments(hi_script)
        if hi_segments:
            tts_hi   = TTSGenerator(language="hi",
                                    prefer_elevenlabs=bool(cfg.voice_hi),
                                    voice_id=cfg.voice_hi or cfg.voice_en,
                                    elevenlabs_api_key=cfg.elevenlabs_api_key)
            audio_hi = tts_hi.generate_batch(hi_segments,
                                             output_dir=os.path.join(out,"audio_hi"))
        elif en_script is not None:
            # Fallback: Hindi gTTS on English script text
            logger.info("  Using gTTS Hindi on English script text")
            tts_hi   = TTSGenerator(language="hi")
            audio_hi = tts_hi.generate_batch(en_script.segments,
                                             output_dir=os.path.join(out,"audio_hi"))
        else:
            # No Hindi commentary and no English script to fall back on (e.g. a
            # --hindi-only run whose --provided-commentary-json-hi was empty/missing) —
            # narrate a minimal placeholder instead of crashing.
            logger.warning("  No Hindi commentary and no English script to fall back "
                           "on — using minimal placeholder narration")
            tts_hi   = TTSGenerator(language="hi")
            audio_hi = tts_hi.generate_batch(
                [f"{ga.white} versus {ga.black}. {ga.opening}."],
                output_dir=os.path.join(out,"audio_hi"))

        if use_avatar:
            from avatar_generator import AvatarGenerator
            av_gen_hi = AvatarGenerator(
                sadtalker_dir=cfg.sadtalker_dir,
                avatar_image=cfg.avatar_image_path,
            )
            avatar_hi_path = av_gen_hi.generate(audio_hi, output_dir=os.path.join(out, "avatar_hi"))

        hi_path = os.path.join(out, f"{game_id}_hi.mp4")
        VideoAssembler(AssemblyConfig(
            output_path=hi_path, format=fmt, fps=cfg.fps,
            video_bitrate=cfg.video_bitrate, audio_bitrate=cfg.audio_bitrate,
            preset=args.quality, video_codec=args.codec, crossfade=cfg.crossfade_duration,
        )).assemble(frame_paths, audio_hi, ga,
                    hi_script if hi_script else en_script,
                    event=game_pgn.headers.get("Event",""),
                    avatar_video_path=avatar_hi_path,
                    transition_map=board_renderer.transition_map,
                    intro_frames=intro_frames_hd,
                    meme_overlays=meme_overlays)
        logger.info(f"  ✅ {hi_path}")

    # ── 8. Thumbnails ─────────────────────────────────────────────────────────
    _banner(8, "Thumbnails")
    _make_thumbnails(frame_paths, ga, en_script, hi_script, out,
                     game_id, args.hindi,
                     skip_english=getattr(args, "hindi_only", False))

    # ── 9. Upload ─────────────────────────────────────────────────────────────
    publish_at = getattr(args, "publish_at", "") or ""
    if (args.upload or publish_at) and not getattr(args, "no_upload", False):
        _banner(9, "YouTube upload")
        if en_path and en_script:
            _upload(en_path, en_script, ga, playlist=cfg.playlist_en, publish_at=publish_at)
        if hi_path and hi_script:
            from commentary_generator import GameScript
            if hasattr(hi_script, "title"):
                # Already a GameScript (built from --provided-commentary-json-hi)
                hi_gs = hi_script
            else:
                # BilingualScript from the bilingual auto-translate path
                hi_gs = GameScript(title=hi_script.hi_title,
                                   description=hi_script.hi_description,
                                   tags=hi_script.hi_tags)
            _upload(hi_path, hi_gs, ga, playlist=cfg.playlist_hi, publish_at=publish_at)

    _summary(t0, en_path, hi_path)


# ─────────────────────────────────────────────────────────────────────────────
def run_opening_pipeline(args):
    """Opening theory video (English + optional Hindi)."""
    _set_job_ctx(args)
    t0 = time.time()
    from opening_fetcher import OpeningFetcher
    from opening_video_generator import OpeningVideoGenerator

    import json
    fetcher  = OpeningFetcher(lichess_token=cfg.lichess_token)
    opening  = fetcher.get_opening(args.opening)
    safe     = opening.name.lower().replace(" ", "_").replace("'", "")
    logger.info(f"Opening: {opening.name}  |  ECO: {opening.eco}")
    logger.info(f"Tagline: {opening.tagline}")

    # Optional LLM-provided payload (famous players etc.) + rich intro card.
    payload = {}
    if getattr(args, "opening_payload_json", None):
        try:
            with open(args.opening_payload_json, encoding="utf-8") as f:
                payload = json.load(f) or {}
        except Exception as e:
            logger.warning(f"Could not read opening payload {args.opening_payload_json}: {e}")

    intro_data = None
    if not args.no_stats_intro:
        from opening_intro_renderer import OpeningIntroData
        from opening_stats import get_opening_stats
        stats = get_opening_stats(opening.name, opening.moves)
        intro_data = OpeningIntroData(
            opening_name=opening.name,
            eco=opening.eco,
            tagline=opening.tagline,
            moves=opening.moves,
            opening_stats=stats,
            famous_players=payload.get("famous_players", []) or [],
            players_note=payload.get("players_note", "") or "",
            channel_name=getattr(cfg, "channel_name", "ChessCode"),
        )

    out_dir  = os.path.join(args.output, "openings")
    gen      = OpeningVideoGenerator(use_claude=cfg.has_anthropic and not args.no_claude)
    en_path  = gen.generate(opening, output_dir=out_dir,
                            fmt="shorts" if args.shorts else "hd",
                            intro_data=intro_data)
    logger.info(f"✅ English: {en_path}")

    # Hindi version: same frames, different audio (generated inside gen.generate
    # when --hindi flag is set in a future iteration — for now regenerate)
    hi_path = None
    if args.hindi:
        logger.info("Generating Hindi opening video…")
        # Override commentary generator language to Hindi
        from opening_video_generator import OpeningCommentaryGenerator
        hi_gen = OpeningVideoGenerator(use_claude=False)  # use fallback for now
        safe   = opening.name.lower().replace(" ","_").replace("'","")
        hi_path = os.path.join(out_dir, f"{safe}_hi.mp4")
        # Quick: re-mux English video with Hindi TTS audio
        _remux_hindi(en_path, hi_path, opening.tagline)

    # Thumbnails
    from opening_fetcher import OpeningFetcher
    from board_renderer import BoardRenderer, RenderOptions, THEMES
    theme = THEMES["classic"]; theme.board_size = 480
    br = BoardRenderer(RenderOptions(theme=theme, output_dir=os.path.join(out_dir,"thumbframes"), show_arrows=False))
    board_img = br.render_position(opening.game().board().fen())
    from thumbnail_leonardo import ThumbnailGenerator
    tg = ThumbnailGenerator(api_key=cfg.leonardo_api_key, output_dir=out_dir)
    tg.opening_thumbnail(opening.name, opening.eco, opening.tagline, board_img,
                         output_path=os.path.join(out_dir,f"thumb_{safe}_en.jpg"))
    if args.hindi:
        tg.opening_thumbnail(opening.name, opening.eco, opening.tagline, board_img,
                             hindi=True, hindi_name=_hindi_opening_name(opening.name),
                             output_path=os.path.join(out_dir,f"thumb_{safe}_hi.jpg"))

    _summary(t0, en_path, hi_path)


# ─────────────────────────────────────────────────────────────────────────────
def run_trap_pipeline(args):
    """Trap Shorts video."""
    _set_job_ctx(args)
    from opening_fetcher import OpeningFetcher, OpeningTrap
    from opening_video_generator import OpeningVideoGenerator

    fetcher = OpeningFetcher()
    traps   = fetcher.get_all_traps()
    trap    = next((t for t in traps if args.trap.lower() in t.name.lower()), None)
    if not trap:
        trap = OpeningTrap(name=args.trap, moves="", opening=args.opening or "")
        logger.warning(f"Trap '{args.trap}' not in database — using minimal stub")

    out_dir = os.path.join(args.output, "traps")
    gen     = OpeningVideoGenerator(use_claude=cfg.has_anthropic)
    path    = gen.generate_trap_short(trap, output_dir=out_dir)
    logger.info(f"✅ Trap Short: {path}")
    _summary(time.time(), path)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_thumbnails(frame_paths, ga, en_script, hi_script, out, game_id, hindi,
                     skip_english=False):
    from thumbnail_leonardo import ThumbnailGenerator
    from board_renderer import BoardRenderer, RenderOptions, THEMES
    from stockfish_analyzer import GameAnalysis

    best_idx = 0
    if isinstance(ga, GameAnalysis) and ga.moves:
        with_delta = [m for m in ga.moves if m.eval_delta]
        if with_delta:
            best_idx = max(with_delta, key=lambda m: abs(m.eval_delta)).ply
    best_idx = min(best_idx, len(frame_paths)-1)

    theme = THEMES["classic"]; theme.board_size = 480
    br  = BoardRenderer(RenderOptions(theme=theme, output_dir=os.path.join(out,"tframes"),
                                       show_arrows=False))
    from PIL import Image as _PILImage
    if frame_paths:
        board_img = _PILImage.open(frame_paths[best_idx])
    else:
        board_img = br.render_position(__import__("chess").Board().fen())

    tg = ThumbnailGenerator(api_key=cfg.leonardo_api_key, output_dir=out)

    # Determine classification from blunders
    classif = "tactical"
    if isinstance(ga, GameAnalysis):
        if ga.white_blunders + ga.black_blunders >= 2: classif = "blunder"
        elif ga.white_accuracy and ga.white_accuracy > 95:  classif = "brilliant"

    if not skip_english:
        tg.game_thumbnail(ga.white, ga.black, ga.opening, ga.opening,
                          classification=classif, board_img=board_img,
                          output_path=os.path.join(out, f"{game_id}_thumb_en.jpg"))
    if hindi:
        tg.game_thumbnail(ga.white, ga.black, ga.opening, ga.opening,
                          classification=classif, board_img=board_img,
                          hindi=True,
                          output_path=os.path.join(out, f"{game_id}_thumb_hi.jpg"))
    logger.info("  Thumbnails generated")


def _upload(video_path, script, ga, playlist=None, publish_at=None):
    if not os.path.exists("client_secret.json"):
        logger.warning("  client_secret.json not found — skipping upload")
        return
    try:
        from youtube_uploader import YouTubeUploader, VideoMetadata
        meta          = VideoMetadata.from_script(script, ga)
        meta.privacy  = cfg.default_privacy
        meta.playlist_id = playlist
        if publish_at:
            meta.publish_at = publish_at
        vid_id = YouTubeUploader().upload(video_path, meta)
        logger.info(f"  ✅ https://youtu.be/{vid_id}")
    except Exception as e:
        logger.error(f"  Upload failed: {e}")


def _remux_hindi(en_path, hi_path, text_hint):
    """Quick mux: generate Hindi TTS for a short phrase, apply to video."""
    import subprocess, tempfile
    from tts_generator import TTSGenerator
    tts = TTSGenerator(language="hi")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    tts._write_silent_mp3(tmp, 3.0)
    cmd = ["ffmpeg","-y","-i",en_path,"-i",tmp,"-c:v","copy","-c:a","aac",
           "-shortest","-map","0:v:0","-map","1:a:0", hi_path]
    subprocess.run(cmd, capture_output=True)
    os.unlink(tmp)


def _hi_render_segments(hi_script):
    """Hindi narration segments from either a BilingualScript (auto-translated by
    bilingual.py, exposes `.hi_segments`) or a GameScript built from
    --provided-commentary-json-hi (exposes `.segments` directly, `.per_move=True`).
    Returns [] (not an error) if hi_script is None or has neither."""
    if hi_script is None:
        return []
    segs = getattr(hi_script, "hi_segments", None)
    if segs:
        return segs
    return getattr(hi_script, "segments", None) or []


def _dummy_ga(game_pgn, game_id):
    from stockfish_analyzer import GameAnalysis, parse_elo
    h = game_pgn.headers
    return GameAnalysis(game_id=game_id, white=h.get("White","White"),
                        black=h.get("Black","Black"), result=h.get("Result","*"),
                        opening=h.get("Opening",""),
                        white_elo=parse_elo(h.get("WhiteElo")),
                        black_elo=parse_elo(h.get("BlackElo")))


def _hindi_opening_name(en_name: str) -> str:
    names = {"Sicilian Defense":"सिसिलियन डिफेंस","Sicilian Najdorf":"सिसिलियन नजदोर्फ",
             "London System":"लंदन सिस्टम","King's Indian Defense":"किंग्स इंडियन",
             "Ruy Lopez":"रुई लोपेज़","Italian Game":"इटालियन गेम",
             "French Defense":"फ्रेंच डिफेंस","Caro-Kann Defense":"कारो-कान",
             "Queen's Gambit":"क्वींस गैम्बिट","King's Gambit":"किंग्स गैम्बिट"}
    return names.get(en_name, en_name)


def _handle_calendar(cmd_args: list):
    from content_calendar import ContentCalendar
    cal = ContentCalendar(cfg.db_path)

    if not cmd_args or cmd_args[0] == "list":
        status = cal.get_status()
        import json
        print(json.dumps(status, indent=2, default=str))

    elif cmd_args[0] == "add" and len(cmd_args) >= 4:
        # add <type> <id> <title...>
        content_type = cmd_args[1]
        content_id = cmd_args[2]
        title = " ".join(cmd_args[3:])
        row_id = cal.add(content_type, content_id, title)
        print(f"Added to queue: id={row_id}, [{content_type}] {title!r}")

    elif cmd_args[0] == "run":
        from autonomous_runner import _run_scheduled_job
        _run_scheduled_job()

    else:
        print("Usage: --calendar list | add <type> <id> <title> | run")
        print("  Types: game | opening | trap")
        print("  Example: --calendar add opening 'London System' 'London System Guide'")


# ─────────────────────────────────────────────────────────────────────────────
# Structured stage-progress side channel (logs/<job_id>_stages.json).
#
# This is deliberately NOT derived from log text (see job_monitor.py, which does
# its own separate log-regex progress estimate for its human-facing web dashboard
# — a different, lower-stakes use case). Here, every pipeline phase boundary
# (_banner call) explicitly writes its own status so any MCP client can build a
# real progress tracker off get_job_status() without scraping logs.
# ─────────────────────────────────────────────────────────────────────────────

# Set once at the top of each run_*_pipeline() from `args`; read by _banner()/_summary()
# so those ~15 call sites don't each need `args` threaded through them individually.
_job_ctx = {"job_id": None, "hindi": False, "avatar": False, "upload": False}


def _set_job_ctx(args):
    """Populate the module-level job context from parsed CLI args (called once per
    run_*_pipeline invocation, before any _banner()/_summary() calls)."""
    global _job_ctx
    _job_ctx = {
        "job_id": getattr(args, "job_id", None),
        "hindi": bool(getattr(args, "hindi", False)),
        "avatar": not getattr(args, "no_avatar", False),
        "upload": bool(getattr(args, "upload", False)) and not getattr(args, "no_upload", False),
    }


def _write_stage_status(job_id, current_step, hindi=False, avatar=False, upload=False):
    """Write logs/<job_id>_stages.json: ordered stage list with done/running/pending status.

    `current_step` matches the "N" argument passed to _banner() (e.g. 1, "1.5", "4.5", 9),
    or the sentinel string "complete" to mark every stage "done" (used once the pipeline
    finishes successfully). Stage numbering/titles come from job_monitor's
    BASE_STAGES/HINDI_STAGES/AVATAR_STAGE/UPLOAD_STAGE — the same canonical tables
    job_monitor already derives from these banners for its own (log-regex-based, separate)
    dashboard — so there's one source of truth for stage names, not two.

    No-op (no file written, no exception raised) if job_id is falsy — e.g. running
    main.py directly from the CLI without the MCP server. Never raises: a failure to
    write this side-channel file must not break an actual render.
    """
    if not job_id:
        return
    try:
        from job_monitor import BASE_STAGES, HINDI_STAGES, AVATAR_STAGE, UPLOAD_STAGE
        import json as _json

        stages = list(BASE_STAGES)
        if hindi:
            stages.extend(HINDI_STAGES)
        if avatar:
            stages.append(AVATAR_STAGE)
        if upload:
            stages.append(UPLOAD_STAGE)
        stages.sort(key=lambda s: float(s[0]))

        out = []
        if current_step == "complete":
            for _num, title in stages:
                out.append({"name": title, "status": "done"})
        else:
            cur = float(current_step)
            for num, title in stages:
                n = float(num)
                if n < cur:
                    st = "done"
                elif n == cur:
                    st = "running"
                else:
                    st = "pending"
                out.append({"name": title, "status": st})

        os.makedirs("logs", exist_ok=True)
        path = os.path.join("logs", f"{job_id}_stages.json")
        with open(path, "w", encoding="utf-8") as f:
            _json.dump({"job_id": job_id, "stages": out}, f)
    except Exception as e:
        logger.warning(f"  Failed to write stage status for job {job_id}: {e}")


def _banner(n, title):
    logger.info(f"\n━━━━  Step {n}: {title}  ━━━━")
    _write_stage_status(_job_ctx.get("job_id"), n,
                         hindi=_job_ctx.get("hindi", False),
                         avatar=_job_ctx.get("avatar", False),
                         upload=_job_ctx.get("upload", False))


def _progress(curr, total):
    bar = "█"*int(curr/total*30) + "░"*(30-int(curr/total*30))
    print(f"\r  [{bar}] {curr}/{total}", end="", flush=True)


def _summary(t0, *paths):
    elapsed = time.time() - t0
    logger.info(f"\n{'━'*52}")
    logger.info(f"  ✅ Done in {elapsed:.0f}s")
    for p in paths:
        if p and os.path.exists(p):
            sz = os.path.getsize(p)/(1024*1024)
            logger.info(f"  📹 {p}  ({sz:.1f} MB)")
    logger.info("━"*52)
    _write_stage_status(_job_ctx.get("job_id"), "complete",
                         hindi=_job_ctx.get("hindi", False),
                         avatar=_job_ctx.get("avatar", False),
                         upload=_job_ctx.get("upload", False))


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = parse_args()

    # Fast-test: force gTTS + shallow depth, skip slow avatar/stats-intro steps.
    if getattr(args, "fast_test", False):
        args.tts_backend = args.tts_backend or "gtts"
        if args.depth == cfg.stockfish_depth:   # only lower if user didn't set --depth
            args.depth = 8
        args.no_avatar = True
        args.no_stats_intro = True

    # Apply CLI backend overrides to cfg
    if args.llm_backend:
        cfg.llm_backend = args.llm_backend
    if args.tts_backend:
        cfg.tts_backend = args.tts_backend

    if args.dashboard:
        from dashboard import show
        show()
        sys.exit(0)

    if args.calendar:
        _handle_calendar(args.calendar)
        sys.exit(0)

    if args.test:
        system_test()
        sys.exit(0)

    if args.trap:
        run_trap_pipeline(args)
    elif args.opening:
        run_opening_pipeline(args)
    elif args.pgn:
        if not os.path.exists(args.pgn):
            print(f"Error: {args.pgn} not found", file=sys.stderr)
            sys.exit(1)
        with open(args.pgn, encoding="utf-8") as f:
            game_pgn = chess.pgn.read_game(f)
        if not game_pgn:
            print("Error: no game found in PGN", file=sys.stderr)
            sys.exit(1)
        game_id = os.path.splitext(os.path.basename(args.pgn))[0]
        run_game_pipeline(args, game_pgn, game_id)
    else:
        print("Usage: main.py [game.pgn | --opening NAME | --trap NAME | --test]")
        sys.exit(1)
