#!/usr/bin/env python3
import argparse
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import yaml
from chesscode import audio, tts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", nargs="+", choices=sorted(tts.PROVIDERS), required=True)
    parser.add_argument("--voices", type=Path, default=ROOT / "config" / "bakeoff_voices.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    voices = yaml.safe_load(args.voices.read_text(encoding="utf-8"))
    samples = [(lang, ROOT / "content" / "bakeoff" / f"{lang}.txt") for lang in ("en", "hi")]
    for provider in args.providers:
        for lang, text_path in samples:
            voice = _voice_for(voices, provider, lang)
            if not voice or voice.startswith("TODO"):
                print(f"{provider} {lang}: configure voice id in {args.voices}", file=sys.stderr)
                return 2
            output = ROOT / "build" / "bakeoff" / f"{provider}_{lang}.mp3"
            if args.dry_run:
                print(f"{provider} {lang} voice={voice} -> {output.relative_to(ROOT)}")
    if args.dry_run:
        return 0

    build = ROOT / "build" / "bakeoff"
    build.mkdir(parents=True, exist_ok=True)
    rows = []
    for provider in args.providers:
        for lang, text_path in samples:
            voice = _voice_for(voices, provider, lang)
            text = text_path.read_text(encoding="utf-8").strip()
            cached_audio, words = tts.synthesize(provider, text, voice, lang, build / "cache")
            name = f"{provider}_{lang}"
            output = build / f"{name}.mp3"
            shutil.copy2(cached_audio, output)
            words_path = build / f"{name}.words.json"
            words_path.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
            lufs = audio.measure(output)["input_i"]
            preview = " ".join(f"{html.escape(word['w'])} ({word['start_ms']}-{word['end_ms']} ms)"
                               for word in words[:10])
            rows.append(f"<tr><td>{html.escape(provider)}</td><td>{html.escape(voice)}</td>"
                        f"<td>{lang}</td><td><audio controls src=\"{name}.mp3\"></audio></td>"
                        f"<td>{len(words)}</td><td>{preview}</td><td>{lufs:.2f}</td></tr>")
    page = "<!doctype html><meta charset='utf-8'><title>TTS bake-off</title>"
    page += "<h1>TTS bake-off</h1><table><thead><tr><th>Provider</th><th>Voice</th><th>Lang</th>"
    page += "<th>Audio</th><th>Words</th><th>First 10 words (ms)</th><th>LUFS</th></tr></thead><tbody>"
    page += "".join(rows) + "</tbody></table>"
    (build / "index.html").write_text(page, encoding="utf-8")
    return 0


def _voice_for(voices, provider: str, lang: str) -> str:
    try:
        value = voices[provider][lang]
    except (KeyError, TypeError):
        value = None
    return str(value).strip() if value else ""


if __name__ == "__main__":
    raise SystemExit(main())
