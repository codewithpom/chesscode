"""Generates the 6 mascot voice blips (original sine blips, 80 ms, peak -14 dBFS).

Output: remotion/src/assets/sfx/blip_{1..6}.mp3. Usage: python scripts/make_blips.py
ffmpeg comes from imageio_ffmpeg, so nothing needs installing system-wide.
"""
import subprocess
from pathlib import Path

import imageio_ffmpeg

OUT = Path(__file__).resolve().parent.parent / "remotion" / "src" / "assets" / "sfx"
PITCHES_HZ = [392, 466, 554, 659, 784, 932]  # six different pitches, one blip each
DURATION_S = 0.08  # spec: 60 to 90 ms
GAIN = 1.6  # ffmpeg sine peaks at 0.125, so 0.125 * 1.6 = 0.2 = -14 dBFS, always under the voice (spec: <= -12)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    for i, hz in enumerate(PITCHES_HZ, start=1):
        # Fast attack (4 ms) and decay (the last 50 ms) so it reads as a blip, not a beep.
        afilter = f"afade=t=in:d=0.004,afade=t=out:st={DURATION_S - 0.05}:d=0.05,volume={GAIN}"
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency={hz}:duration={DURATION_S}:sample_rate=44100",
             "-af", afilter, "-ac", "1", "-c:a", "libmp3lame", "-b:a", "96k", str(OUT / f"blip_{i}.mp3")],
            check=True,
        )
        print(f"blip_{i}.mp3  {hz} Hz")


if __name__ == "__main__":
    main()
