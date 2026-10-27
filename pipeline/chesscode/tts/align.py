from pathlib import Path

from chesscode.tts.base import Word


def align_words(mp3: Path, text: str, lang: str) -> list[Word]:
    import whisperx

    audio = whisperx.load_audio(str(mp3))
    asr = whisperx.load_model("large-v2", device="cpu", compute_type="int8")
    transcript = asr.transcribe(audio, language=lang)
    model, metadata = whisperx.load_align_model(language_code=lang, device="cpu")
    result = whisperx.align(transcript["segments"], model, metadata, audio, "cpu")
    return [{"w": segment["word"].strip(), "start_ms": round(segment["start"] * 1000),
             "end_ms": round(segment["end"] * 1000)}
            for segment in result["word_segments"] if segment["word"].strip()]
