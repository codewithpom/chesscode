import io
from gtts import gTTS
from .base import TTSBackend

class GTTSBackend(TTSBackend):
    def synthesize(self, text: str, language: str = "en", speed: float = 1.0) -> bytes:
        lang_code = "hi" if language == "hi" else "en"
        tts = gTTS(text=text, lang=lang_code, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()
