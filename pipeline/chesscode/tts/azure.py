import os
from pathlib import Path
from datetime import timedelta

from chesscode.tts.base import Word


def ticks_to_ms(ticks: int) -> int:
    return round(ticks / 10_000)


def synthesize(text: str, voice: str, lang: str, out_mp3: Path) -> list[Word]:
    import azure.cognitiveservices.speech as speechsdk

    speech_config = speechsdk.SpeechConfig(subscription=os.environ["AZURE_SPEECH_KEY"],
                                            region=os.environ["AZURE_SPEECH_REGION"])
    speech_config.speech_synthesis_voice_name = voice
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3)
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    words = []
    def add_word(event):
        if event.boundary_type != speechsdk.SpeechSynthesisBoundaryType.Word:
            return
        duration_ms = round(event.duration.total_seconds() * 1000) if isinstance(event.duration, timedelta) else ticks_to_ms(event.duration)
        words.append({"w": event.text, "start_ms": ticks_to_ms(event.audio_offset),
                      "end_ms": ticks_to_ms(event.audio_offset) + duration_ms})
    synthesizer.synthesis_word_boundary.connect(add_word)
    result = synthesizer.speak_text_async(text).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError("Azure Speech synthesis failed")
    out_mp3.write_bytes(result.audio_data)
    return words
