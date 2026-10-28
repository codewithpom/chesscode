import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch

from chesscode import tts

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "tts_bakeoff.py"
spec = importlib.util.spec_from_file_location("tts_bakeoff", SCRIPT)
bakeoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bakeoff)


def test_dry_run_lists_files_without_calling_a_provider(capsys):
    with patch.object(tts, "synthesize", side_effect=AssertionError("provider must not run")):
        assert bakeoff.main(["--providers", "kokoro", "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "kokoro en voice=af_heart -> build\\bakeoff\\kokoro_en.mp3" in output
    assert "kokoro hi voice=hf_alpha" in output


def test_placeholder_provider_refuses_to_run():
    with patch.object(tts, "synthesize", side_effect=AssertionError("provider must not run")):
        assert bakeoff.main(["--providers", "azure"]) == 2
