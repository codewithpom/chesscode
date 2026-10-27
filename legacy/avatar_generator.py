"""avatar_generator.py — Generates a talking avatar video using Wav2Lip (with fallbacks)."""

import os
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

logger = logging.getLogger(__name__)


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


class AvatarGenerator:
    def __init__(self,
                 wav2lip_dir: str = "Wav2Lip",
                 sadtalker_dir: str = "SadTalker",
                 avatar_image: str = "assets/avatar_pawn.png"):
        self.wav2lip_dir = wav2lip_dir
        self.sadtalker_dir = sadtalker_dir
        self.avatar_image = avatar_image

    def _wav2lip_available(self) -> bool:
        script = os.path.join(self.wav2lip_dir, "inference.py")
        ckpt = os.path.join(self.wav2lip_dir, "checkpoints", "wav2lip.pth")
        return os.path.exists(script) and os.path.exists(ckpt) and os.path.exists(self.avatar_image)

    def _sadtalker_available(self) -> bool:
        script = os.path.join(self.sadtalker_dir, "inference.py")
        return os.path.exists(script) and os.path.exists(self.avatar_image)

    def concat_audio(self, audio_paths: List[str], output_path: str) -> bool:
        valid = [p for p in audio_paths if p and os.path.exists(p)]
        if not valid:
            return False
        list_file = output_path + "_list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for p in valid:
                f.write(f"file '{os.path.abspath(p)}'\n")
        cmd = [_ffmpeg(), "-y", "-f", "concat", "-safe", "0",
               "-i", list_file, "-ar", "16000", "-ac", "1", output_path]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            os.unlink(list_file)
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Audio concat failed: {e}")
            return False

    def generate(self, audio_paths: List[str], output_dir: str) -> Optional[str]:
        """
        Animate avatar with audio. Tries Wav2Lip → SadTalker → static fallback.
        Returns path to output video, or None on complete failure.
        """
        os.makedirs(output_dir, exist_ok=True)

        concat_wav = os.path.join(output_dir, "avatar_audio.wav")
        if not self.concat_audio(audio_paths, concat_wav):
            logger.warning("Avatar audio concat failed")
            return None

        # 1. Try Wav2Lip (best for cartoon faces)
        if self._wav2lip_available():
            result = self._run_wav2lip(concat_wav, output_dir)
            if result:
                return result
            logger.warning("Wav2Lip failed, trying SadTalker")

        # 2. Try SadTalker (works on realistic faces)
        if self._sadtalker_available():
            result = self._run_sadtalker(concat_wav, output_dir)
            if result:
                return result
            logger.warning("SadTalker failed, trying amplitude animation")

        # 3. Amplitude-based mouth animation (cartoon-safe, no ML)
        result = self._amplitude_mouth_animation(concat_wav, output_dir)
        if result:
            return result
        logger.warning("Amplitude animation failed, using static fallback")

        # 4. Static fallback
        return self._fallback_static_avatar(concat_wav, output_dir)

    def _run_wav2lip(self, audio_path: str, output_dir: str) -> Optional[str]:
        out_path = os.path.join(output_dir, "avatar_wav2lip.mp4")
        ckpt = os.path.join(self.wav2lip_dir, "checkpoints", "wav2lip.pth")
        cmd = [
            "python", os.path.join(self.wav2lip_dir, "inference.py"),
            "--checkpoint_path", ckpt,
            "--face", self.avatar_image,
            "--audio", audio_path,
            "--outfile", out_path,
            "--nosmooth",
            "--pads", "0", "10", "0", "0",
        ]
        try:
            logger.info("Running Wav2Lip...")
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=600, cwd=self.wav2lip_dir
            )
            if result.returncode == 0 and os.path.exists(out_path):
                logger.info(f"Wav2Lip success: {out_path}")
                return out_path
            logger.warning(f"Wav2Lip stderr: {result.stderr[-400:]}")
        except subprocess.TimeoutExpired:
            logger.warning("Wav2Lip timed out")
        except Exception as e:
            logger.warning(f"Wav2Lip error: {e}")
        return None

    def _run_sadtalker(self, audio_path: str, output_dir: str) -> Optional[str]:
        result_dir = os.path.join(output_dir, "sadtalker_out")
        os.makedirs(result_dir, exist_ok=True)
        cmd = [
            "python", os.path.join(self.sadtalker_dir, "inference.py"),
            "--driven_audio", audio_path,
            "--source_image", self.avatar_image,
            "--result_dir", result_dir,
            "--still", "--preprocess", "full",
        ]
        try:
            logger.info("Running SadTalker...")
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=600, cwd=self.sadtalker_dir
            )
            if result.returncode == 0:
                for f in os.listdir(result_dir):
                    if f.endswith(".mp4"):
                        return os.path.join(result_dir, f)
            logger.warning(f"SadTalker stderr: {result.stderr[-400:]}")
        except subprocess.TimeoutExpired:
            logger.warning("SadTalker timed out")
        except Exception as e:
            logger.warning(f"SadTalker error: {e}")
        return None

    def _amplitude_mouth_animation(self, audio_path: str, output_dir: str) -> Optional[str]:
        """Bounce animation: pawn scales up slightly when audio is loud — clean, no mouth drawing."""
        try:
            import librosa
            import numpy as np
            from PIL import Image
        except ImportError as e:
            logger.warning(f"Bounce animation deps missing: {e}")
            return None

        FPS = 25
        MAX_SCALE = 1.10   # 10% bigger at loudest
        SMOOTHING = 5      # rolling average for smooth motion

        try:
            y, sr = librosa.load(audio_path, sr=None, mono=True)
        except Exception as e:
            logger.warning(f"librosa load failed: {e}")
            return None

        hop_length = max(1, int(sr / FPS))
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0].astype(float)

        kernel = np.ones(SMOOTHING) / SMOOTHING
        rms_smooth = np.convolve(rms, kernel, mode="same")
        rms_max = rms_smooth.max()
        rms_norm = rms_smooth / rms_max if rms_max > 0 else rms_smooth

        # Prefer no-background version if available
        nobg = self.avatar_image.replace(".png", "_nobg.png")
        src_image = nobg if os.path.exists(nobg) else self.avatar_image
        try:
            pawn = Image.open(src_image).convert("RGBA")
        except Exception as e:
            logger.warning(f"Avatar image load failed: {e}")
            return None

        W, H = pawn.size
        # Green-screen background — keyed out during video compositing
        BG = (0, 255, 0, 255)
        frames_dir = os.path.join(output_dir, "anim_frames")
        os.makedirs(frames_dir, exist_ok=True)

        def _render_one(i: int, norm: float) -> None:
            scale = 1.0 + float(norm) * (MAX_SCALE - 1.0)
            nw, nh = int(W * scale), int(H * scale)
            resized = pawn.resize((nw, nh), Image.LANCZOS)
            canvas = Image.new("RGBA", (W, H), BG)
            px = (W - nw) // 2
            py = H - nh          # pin bottom: pawn jumps upward
            canvas.paste(resized, (px, py), resized)
            canvas.convert("RGB").save(os.path.join(frames_dir, f"frame_{i:05d}.png"))

        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
            list(ex.map(_render_one, range(len(rms_norm)), rms_norm))

        out_path = os.path.join(output_dir, "avatar_animated.mp4")
        cmd = [
            _ffmpeg(), "-y",
            "-framerate", str(FPS),
            "-i", os.path.join(frames_dir, "frame_%05d.png"),
            "-i", audio_path,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            out_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            if result.returncode == 0 and os.path.exists(out_path):
                logger.info(f"Bounce animation success: {out_path}")
                return out_path
            logger.warning(f"Bounce animation ffmpeg stderr: {result.stderr[-400:]}")
        except Exception as e:
            logger.warning(f"Bounce animation ffmpeg failed: {e}")
        return None

    def _fallback_static_avatar(self, audio_path: str, output_dir: str) -> Optional[str]:
        """Pawn image looped for audio duration — no lip sync but always works."""
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "avatar_static.mp4")
        cmd = [
            _ffmpeg(), "-y",
            "-loop", "1", "-i", self.avatar_image,
            "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-shortest",
            out_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode == 0:
                logger.info("Using static avatar fallback")
                return out_path
        except Exception as e:
            logger.warning(f"Static avatar fallback failed: {e}")
        return None
