from pathlib import Path

from chesscode.tts.base import Word


def align_words(mp3: Path, text: str, lang: str) -> list[Word]:
    import whisperx

    audio = whisperx.load_audio(str(mp3))
    model, metadata = whisperx.load_align_model(language_code=lang, device="cpu")
    duration = len(audio) / 16_000
    result = whisperx.align([{"start": 0, "end": duration, "text": text}], model, metadata, audio, "cpu")
    segments = result["word_segments"]
    words = []
    for index, segment in enumerate(segments):
        word = segment["word"].strip()
        if not word:
            continue
        start = segment.get("start", duration * index / max(len(segments), 1))
        end = segment.get("end", duration * (index + 1) / max(len(segments), 1))
        words.append({"w": word, "start_ms": round(start * 1000), "end_ms": round(end * 1000)})
    return words
