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
        start, end = segment.get("start"), segment.get("end")
        if start is None or end is None:
            first = index
            while first > 0 and (segments[first - 1].get("start") is None or segments[first - 1].get("end") is None):
                first -= 1
            last = index
            while last + 1 < len(segments) and (segments[last + 1].get("start") is None or segments[last + 1].get("end") is None):
                last += 1
            previous_end = next((item.get("end") for item in reversed(segments[:first]) if item.get("end") is not None), 0)
            next_start = next((item.get("start") for item in segments[last + 1:] if item.get("start") is not None), duration)
            position = index - first
            count = last - first + 1
            start = previous_end + (next_start - previous_end) * position / count
            end = previous_end + (next_start - previous_end) * (position + 1) / count
        words.append({"w": word, "start_ms": round(start * 1000), "end_ms": round(end * 1000)})
    return words
