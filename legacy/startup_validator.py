"""startup_validator.py — Validate configuration on MCP server startup.

This module is called early in mcp_server.py to catch configuration errors before
the server starts serving requests, enabling fast failure with clear error messages.
"""

import logging
import sys
from typing import Dict, Tuple
from config import cfg

logger = logging.getLogger(__name__)

__all__ = ["validate_startup", "StartupValidationError"]


class StartupValidationError(Exception):
    """Raised when critical configuration is missing or invalid."""
    pass


def validate_startup() -> Dict[str, Tuple[bool, str]]:
    """
    Validate critical configuration for MCP server operation.
    
    Returns:
        dict mapping check name → (passed: bool, message: str)
    
    Raises:
        StartupValidationError if critical checks fail
    """
    results: Dict[str, Tuple[bool, str]] = {}
    
    # 1. Check API keys (Claude is critical for LLM operations)
    if cfg.has_anthropic:
        results["Claude API"] = (True, "✓ ANTHROPIC_API_KEY set")
    else:
        # Don't fail here - user may choose to use Ollama instead
        results["Claude API"] = (False, "⚠ ANTHROPIC_API_KEY not set (Ollama fallback available)")
    
    # 2. Check Ollama if that's the configured backend
    if cfg.llm_backend == "ollama" and not cfg.has_ollama:
        msg = f"⚠ LLM_BACKEND=ollama but OLLAMA_URL invalid or unreachable ({cfg.ollama_url})"
        results["Ollama Backend"] = (False, msg)
        # Don't fail - user will see error during job
    else:
        results["Ollama Backend"] = (True, "✓ Ollama accessible" if cfg.has_ollama else "✓ Not selected")
    
    # 3. Check TTS backend availability
    tts_ok = cfg.active_tts_backend != "gtts"  # gtts always works as fallback
    if cfg.active_tts_backend == "kokoro":
        # Check if kokoro model files exist (rough check)
        try:
            import pathlib
            if not (pathlib.Path("kokoro-v1.0.onnx").exists() or pathlib.Path("voices-v1.0.bin").exists()):
                results["TTS Backend"] = (False, "⚠ Kokoro selected but model files not found (will fall back to gTTS)")
            else:
                results["TTS Backend"] = (True, "✓ Kokoro backend ready")
        except Exception as e:
            results["TTS Backend"] = (False, f"⚠ Kokoro check failed: {e} (will fall back to gTTS)")
    elif cfg.active_tts_backend == "elevenlabs":
        results["TTS Backend"] = (True, "✓ ElevenLabs backend ready" if cfg.has_elevenlabs else "⚠ ElevenLabs key missing, will fall back")
    else:
        results["TTS Backend"] = (True, "✓ gTTS (always available)")
    
    # 4. Check database path is writable
    try:
        import os
        db_dir = os.path.dirname(cfg.db_path) or "."
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        with open(cfg.db_path, "a"):
            pass
        results["Database"] = (True, f"✓ Database writable at {cfg.db_path}")
    except Exception as e:
        results["Database"] = (False, f"✗ Database not writable: {e}")
        raise StartupValidationError(f"Critical: Cannot write to database at {cfg.db_path}: {e}")
    
    # 5. Check output directory is writable
    try:
        import os
        os.makedirs(cfg.output_dir, exist_ok=True)
        test_file = os.path.join(cfg.output_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        results["Output Directory"] = (True, f"✓ Output directory writable at {cfg.output_dir}")
    except Exception as e:
        results["Output Directory"] = (False, f"✗ Output directory not writable: {e}")
        raise StartupValidationError(f"Critical: Cannot write to output directory {cfg.output_dir}: {e}")
    
    # 6. Check logs directory is writable
    try:
        import os
        os.makedirs("logs", exist_ok=True)
        test_file = os.path.join("logs", ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        results["Logs Directory"] = (True, "✓ Logs directory writable")
    except Exception as e:
        results["Logs Directory"] = (False, f"✗ Logs directory not writable: {e}")
        raise StartupValidationError(f"Critical: Cannot write to logs directory: {e}")
    
    # Log all results
    logger.info("Startup validation results:")
    for check_name, (passed, msg) in results.items():
        logger.info(f"  {check_name}: {msg}")
    
    # Check if any critical checks failed (only DB and output dir are critical)
    critical_failures = [msg for name, (passed, msg) in results.items() 
                        if not passed and ("Database" in name or "Output Directory" in name or "Logs" in name)]
    
    if critical_failures:
        raise StartupValidationError(f"Critical validation failures: {'; '.join(critical_failures)}")
    
    return results


def print_startup_summary(results: Dict[str, Tuple[bool, str]]) -> None:
    """Pretty-print startup validation results.

    Writes to stderr, never stdout — stdout is the JSON-RPC channel for the
    stdio MCP transport, and any plain text written there corrupts the
    client's message framing.
    """
    lines = ["\n" + "=" * 60, "ChessCode MCP Server -- Startup Validation", "=" * 60]
    for check_name, (passed, msg) in results.items():
        lines.append(f"{check_name:.<30} {msg}")
    lines.append("=" * 60 + "\n")
    text = "\n".join(lines)
    try:
        print(text, file=sys.stderr)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), file=sys.stderr)
