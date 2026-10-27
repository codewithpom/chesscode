"""
config.py — ChessCode Pipeline
================================
Centralised configuration. All settings live here.
Values read from environment variables (set in .env file).

Usage:
    from config import cfg

    print(cfg.stockfish_depth)   # 18
    print(cfg.output_dir)        # "output"
    print(cfg.has_leonardo)      # True if key set
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

# ── Load .env automatically if present ────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

def _int(key: str, default: int) -> int:
    try: return int(os.environ.get(key, default))
    except ValueError: return default

def _bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key, str(default)).lower()
    return v in ("1", "true", "yes", "on")


@dataclass
class ChessCodeConfig:
    """All runtime configuration for the ChessCode pipeline."""

    # ── API Keys ──────────────────────────────────────────────────────────────
    anthropic_api_key:  str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    elevenlabs_api_key: str = field(default_factory=lambda: _env("ELEVENLABS_API_KEY"))
    leonardo_api_key:   str = field(default_factory=lambda: _env("LEONARDO_API_KEY"))
    openai_api_key:     str = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    lichess_token:      str = field(default_factory=lambda: _env("LICHESS_TOKEN"))

    # ElevenLabs voice IDs
    voice_en: str = field(default_factory=lambda: _env("ELEVENLABS_VOICE_EN", "21m00Tcm4TlvDq8ikWAM"))  # Rachel
    voice_hi: str = field(default_factory=lambda: _env("ELEVENLABS_VOICE_HI", ""))

    # LLM Backend
    llm_backend:    str = field(default_factory=lambda: _env("LLM_BACKEND", "claude"))
    ollama_url:     str = field(default_factory=lambda: _env("OLLAMA_URL", "http://localhost:11434"))
    ollama_model:   str = field(default_factory=lambda: _env("OLLAMA_MODEL", "llama3.2"))

    # ── Channel settings ──────────────────────────────────────────────────────
    channel_name:       str = "ChessCode"
    publish_english:    bool= field(default_factory=lambda: _bool("PUBLISH_EN", True))
    publish_hindi:      bool= field(default_factory=lambda: _bool("PUBLISH_HI", True))
    default_privacy:    str = field(default_factory=lambda: _env("YT_PRIVACY", "private"))
    playlist_en:        str = field(default_factory=lambda: _env("YT_PLAYLIST_EN"))
    playlist_hi:        str = field(default_factory=lambda: _env("YT_PLAYLIST_HI"))

    # ── Content schedule (2 long-form/week, Mon + Thu) ────────────────────────
    videos_per_week:    int  = field(default_factory=lambda: _int("VIDEOS_PER_WEEK", 2))
    upload_days:        List[int] = field(default_factory=lambda: [0, 3])  # Mon=0, Thu=3
    upload_time_ist:    str  = field(default_factory=lambda: _env("UPLOAD_TIME_IST", "09:00"))
    opening_ratio:      float = 0.4   # 40% opening theory, 60% game analysis

    # ── Video quality ─────────────────────────────────────────────────────────
    resolution:         str  = field(default_factory=lambda: _env("RESOLUTION", "1920x1080"))
    fps:                int  = field(default_factory=lambda: _int("FPS", 24))
    video_bitrate:      str  = field(default_factory=lambda: _env("VIDEO_BITRATE", "8000k"))
    audio_bitrate:      str  = field(default_factory=lambda: _env("AUDIO_BITRATE", "192k"))
    encoding_preset:    str  = field(default_factory=lambda: _env("ENCODING_PRESET", "veryfast"))
    video_codec:        str  = field(default_factory=lambda: _env("VIDEO_CODEC", "h264_qsv"))
    crossfade_duration: float = 0.2   # seconds between board positions

    # ── Board rendering ───────────────────────────────────────────────────────
    board_theme:        str  = field(default_factory=lambda: _env("BOARD_THEME", "classic"))
    board_size_hd:      int  = 800     # pixels, for 1920×1080
    board_size_shorts:  int  = 900     # pixels, for 1080×1920
    show_arrows:        bool = True
    arrow_intensity:    str  = field(default_factory=lambda: _env("ARROW_INTENSITY", "normal"))  # conservative, normal, aggressive
    enable_move_transitions: bool = field(default_factory=lambda: _bool("MOVE_TRANSITIONS", True))
    transition_frame_count:  int  = 12   # slide sub-frames per move (~0.5s at 24fps)

    # ── Stockfish ─────────────────────────────────────────────────────────────
    stockfish_path:     str  = field(default_factory=lambda: _env("STOCKFISH_PATH", "stockfish"))
    stockfish_depth:    int  = field(default_factory=lambda: _int("STOCKFISH_DEPTH", 18))
    stockfish_threads:  int  = field(default_factory=lambda: _int("STOCKFISH_THREADS", 4))
    # 0 = auto: min(4, cpu_count // stockfish_threads), computed by StockfishAnalyzer itself
    stockfish_workers:  int  = field(default_factory=lambda: _int("STOCKFISH_WORKERS", 0))

    # ── Board frame rendering concurrency ─────────────────────────────────────
    render_workers:     int  = field(default_factory=lambda: _int("RENDER_WORKERS", 0))

    # ── TTS ───────────────────────────────────────────────────────────────────
    tts_backend:        str  = field(default_factory=lambda: _env("TTS_BACKEND", "kokoro"))
    kokoro_voice_en:    str  = field(default_factory=lambda: _env("KOKORO_VOICE_EN", "af_heart"))
    kokoro_voice_hi:    str  = field(default_factory=lambda: _env("KOKORO_VOICE_HI", "hf_alpha"))
    tts_slow:           bool = False

    # ── Paths ─────────────────────────────────────────────────────────────────
    output_dir:     str = field(default_factory=lambda: _env("OUTPUT_DIR", "output"))
    db_path:        str = field(default_factory=lambda: _env("DB_PATH", "chesscode.db"))
    pgn_cache_dir:  str = field(default_factory=lambda: _env("PGN_CACHE", "output/pgn_cache"))
    tts_cache_dir:  str = field(default_factory=lambda: _env("TTS_CACHE_DIR", "output/.cache/tts"))
    frame_cache_dir: str = field(default_factory=lambda: _env("FRAME_CACHE_DIR", "output/.cache/frames"))
    assets_dir:     str = "assets"
    font_dir:       str = "assets/fonts"

    # ── Avatar (talking pawn) ─────────────────────────────────────────────────
    avatar_enabled:     bool  = field(default_factory=lambda: _bool("AVATAR_ENABLED", True))
    avatar_image_path:  str   = field(default_factory=lambda: _env("AVATAR_IMAGE", "assets/avatar_pawn.png"))
    sadtalker_dir:      str   = field(default_factory=lambda: _env("SADTALKER_DIR", "SadTalker"))
    avatar_size:        tuple = (280, 280)
    avatar_position:    tuple = (1620, 780)

    # ── Memes (reaction overlays on blunders/mistakes/inaccuracies) ───────────
    enable_memes:       bool  = field(default_factory=lambda: _bool("ENABLE_MEMES", True))
    meme_max_per_video: int   = field(default_factory=lambda: _int("MEME_MAX_PER_VIDEO", 3))
    meme_size:          tuple = (320, 320)
    meme_position:      tuple = (20, 740)   # opposite corner from the avatar
    meme_duration:      float = 2.5
    meme_cache_dir:     str   = field(default_factory=lambda: _env("MEME_CACHE_DIR", "output/.cache/memes"))

    # ── Leonardo AI ───────────────────────────────────────────────────────────
    leonardo_model: str = "de7d3faf-762f-48e0-b3b9-5702c67d2ee7"  # Phoenix 1.0

    # ── Thumbnail generation ──────────────────────────────────────────────────
    thumbnail_style_prompt: str = "Bold, cinematic chess video thumbnail, dramatic lighting, intense color, high contrast, professional YouTube gaming thumbnail style."

    # ── Stats intro (animated combo card at video start) ──────────────────────
    stats_intro_enabled:   bool  = field(default_factory=lambda: _bool("STATS_INTRO_ENABLED", True))
    stats_intro_duration:  float = field(default_factory=lambda: float(_env("STATS_INTRO_DURATION", "5.5")))
    stats_intro_cache_dir: str   = field(default_factory=lambda: _env("STATS_INTRO_CACHE_DIR", "output/.cache/stats_intro"))

    # ── Opening intro (rich SVG card at start of opening-theory videos) ───────
    opening_intro_enabled:  bool  = field(default_factory=lambda: _bool("OPENING_INTRO_ENABLED", True))
    opening_intro_duration: float = field(default_factory=lambda: float(_env("OPENING_INTRO_DURATION", "6.5")))

    # ── Opening Explorer (Lichess, no API key needed) ──────────────────────────
    opening_stats_cache_dir: str = field(default_factory=lambda: _env("OPENING_STATS_CACHE_DIR", "output/.cache/opening_stats"))
    opening_stats_min_games: int = field(default_factory=lambda: _int("OPENING_STATS_MIN_GAMES", 5))

    # ── YouTube Data API (channel stats ribbon) ────────────────────────────────
    youtube_api_key:           str = field(default_factory=lambda: _env("YOUTUBE_API_KEY"))
    youtube_channel_id:        str = field(default_factory=lambda: _env("YOUTUBE_CHANNEL_ID"))
    channel_stats_ttl_seconds: int = field(default_factory=lambda: _int("CHANNEL_STATS_TTL_SECONDS", 3600))
    channel_stats_cache_dir:   str = field(default_factory=lambda: _env("CHANNEL_STATS_CACHE_DIR", "output/.cache/channel_stats"))

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_elevenlabs(self) -> bool:
        return bool(self.elevenlabs_api_key)

    @property
    def has_leonardo(self) -> bool:
        return bool(self.leonardo_api_key)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_lichess(self) -> bool:
        return bool(self.lichess_token)

    @property
    def has_ollama(self) -> bool:
        return self.llm_backend == "ollama"

    @property
    def has_youtube_data_api(self) -> bool:
        return bool(self.youtube_api_key and self.youtube_channel_id)

    @property
    def canvas_size(self):
        w, h = self.resolution.split("x")
        return int(w), int(h)

    @property
    def active_tts_backend(self) -> str:
        if self.tts_backend == "kokoro":
            return "kokoro"
        if self.tts_backend == "elevenlabs" and self.has_elevenlabs:
            return "elevenlabs"
        return "gtts"

    def summary(self) -> str:
        w, h = self.canvas_size
        ollama_info = f" ({self.ollama_model} @ {self.ollama_url})" if self.has_ollama else ""
        return (
            f"\n━━━━  ChessCode Config  ━━━━\n"
            f"  Resolution:   {w}×{h} @ {self.fps}fps\n"
            f"  Encoding:     {self.video_bitrate} / {self.encoding_preset} preset\n"
            f"  Stockfish:    depth {self.stockfish_depth}, {self.stockfish_threads} threads, "
            f"{self.stockfish_workers or 'auto'} workers\n"
            f"  Render:       {self.render_workers or 'auto'} workers\n"
            f"  LLM:          {self.llm_backend}{ollama_info}\n"
            f"  TTS:          {self.active_tts_backend}\n"
            f"  Languages:    "
            f"{'English ' if self.publish_english else ''}"
            f"{'+ Hindi' if self.publish_hindi else ''}\n"
            f"  Schedule:     {self.videos_per_week}/week "
            f"({'Mon+Thu' if self.upload_days == [0,3] else str(self.upload_days)}) "
            f"at {self.upload_time_ist} IST\n"
            f"  APIs ready:   "
            f"{'Claude ' if self.has_anthropic else '[NO CLAUDE] '}"
            f"{'ElevenLabs ' if self.has_elevenlabs else ''}"
            f"{'Leonardo ' if self.has_leonardo else ''}"
            f"{'Lichess ' if self.has_lichess else ''}"
            f"{'YouTubeDataAPI' if self.has_youtube_data_api else ''}\n"
        )


# Global singleton — import this everywhere
cfg = ChessCodeConfig()
