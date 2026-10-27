"""video_assembler.py — Assembles chess video from board frame images and audio clips."""

import os
import logging
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

try:
    import proglog

    class _EncodeProgressLogger(proglog.ProgressBarLogger):
        def __init__(self):
            super().__init__(min_time_interval=1.0)

        def bars_callback(self, bar, attr, value, old_value=None):
            if attr == "index":
                total = self.bars.get(bar, {}).get("total")
                if total:
                    pct = int(100 * value / total)
                    print(f"[ENCODE] {pct}%", flush=True)

except ImportError:
    _EncodeProgressLogger = None


_LEAD_IN = 0.5   # board shown silently before commentary starts
_IDLE_DUR = 1.0  # duration for frames with no assigned audio segment
_MASTER_SR = 44100  # sample rate used for the assembled master audio track


@dataclass
class AssemblyConfig:
    output_path: str
    format: str = "hd"
    fps: int = 24
    video_bitrate: str = "8000k"
    audio_bitrate: str = "192k"
    preset: str = "veryfast"
    video_codec: str = "h264_qsv"
    crossfade: float = 0.2
    engine: str = "ffmpeg"  # "ffmpeg" (fast, default) or "moviepy" (legacy fallback)
    captions: bool = True   # burn per-segment commentary caption strip at the bottom


class VideoAssembler:
    def __init__(self, cfg: AssemblyConfig):
        self.cfg = cfg

    def assemble(self, frame_paths: List[str], audio_paths: List[str],
                 ga, script, event: str = "",
                 avatar_video_path: str = None,
                 transition_map: Dict[int, List[str]] = None,
                 intro_frames: Tuple[List[str], List[float]] = None,
                 meme_overlays: List[dict] = None) -> str:
        if self.cfg.engine == "moviepy":
            if intro_frames and intro_frames[0]:
                logger.warning("stats intro not supported on the moviepy engine — skipping it")
            return self._assemble_moviepy(frame_paths, audio_paths, ga, script,
                                          event, avatar_video_path, meme_overlays)
        try:
            return self._assemble_ffmpeg(frame_paths, audio_paths, ga, script,
                                         event, avatar_video_path, transition_map,
                                         intro_frames, meme_overlays)
        except Exception as e:
            logger.error(f"ffmpeg assembly failed, falling back to moviepy: {e}", exc_info=True)
            if intro_frames and intro_frames[0]:
                logger.warning("stats intro not supported on the moviepy engine — skipping it")
            return self._assemble_moviepy(frame_paths, audio_paths, ga, script,
                                          event, avatar_video_path, meme_overlays)

    # ── ffmpeg engine (fast path) ─────────────────────────────────────────────

    def _assemble_ffmpeg(self, frame_paths: List[str], audio_paths: List[str],
                         ga, script, event: str, avatar_video_path: str,
                         transition_map: Dict[int, List[str]] = None,
                         intro_frames: Tuple[List[str], List[float]] = None,
                         meme_overlays: List[dict] = None) -> str:
        if not frame_paths:
            raise ValueError("No frames to assemble")

        ffmpeg = _ffmpeg_exe()
        from scene_renderer import FORMATS
        vfmt = FORMATS.get(self.cfg.format, FORMATS["hd"])

        out_dir = os.path.dirname(self.cfg.output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        work_dir = tempfile.mkdtemp(prefix="chesscode_assemble_")
        try:
            intro_paths, intro_durs = intro_frames if intro_frames else ([], [])
            intro_total = sum(intro_durs)

            per_move = bool(getattr(script, "per_move", False))
            segment_texts = list(getattr(script, "segments", []) or [])
            frame_paths = list(frame_paths)
            if per_move and len(segment_texts) > len(frame_paths) and frame_paths:
                # Strict per-move script has one extra segment (the conclusion) beyond
                # the move frames — linger on a copy of the final position for it.
                frame_paths += [frame_paths[-1]] * (len(segment_texts) - len(frame_paths))

            frame_durs, frame_to_audio, frame_to_text = _compute_frame_plan(
                frame_paths, audio_paths, ffmpeg,
                segment_texts=segment_texts, per_move=per_move)
            frame_starts = _cumulative_starts(frame_durs)
            board_total_duration = frame_starts[-1] + frame_durs[-1] if frame_durs else 0.0
            total_duration = intro_total + board_total_duration

            display_frames, display_durs = _expand_frame_plan(
                frame_paths, frame_durs, transition_map or {}, self.cfg.fps)
            display_frames = intro_paths + display_frames
            display_durs = intro_durs + display_durs

            resized_frames = _prepare_frames(display_frames, vfmt, work_dir)
            concat_path = _write_ffconcat(resized_frames, display_durs, work_dir)

            frame_move_types = _frame_move_types(frame_paths, ga)
            master_audio_path = os.path.join(work_dir, "master_audio.wav")
            _build_master_audio(frame_starts, frame_to_audio, total_duration,
                                master_audio_path, ffmpeg, _LEAD_IN,
                                frame_move_types=frame_move_types,
                                time_offset=intro_total)

            title = getattr(script, "title", "")
            title_png = None
            if title:
                title_png = os.path.join(work_dir, "title.png")
                _render_title_png(title, vfmt, title_png)

            cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_path,
                   "-i", master_audio_path]
            audio_input_idx = 1
            next_input_idx = 2

            filter_parts = []
            video_label = "0:v"

            if title_png:
                cmd += ["-i", title_png]
                title_idx = next_input_idx
                next_input_idx += 1
                title_end = min(intro_total + 5.0, total_duration)
                filter_parts.append(
                    f"[{video_label}][{title_idx}:v]overlay=x=(W-w)/2:y=40:"
                    f"enable='between(t,{intro_total:.2f},{title_end:.2f})'[vtitled]"
                )
                video_label = "vtitled"

            # ── Per-segment commentary caption strip (bottom) ─────────────────
            if self.cfg.captions and frame_to_text:
                for ci, (fi, ctext) in enumerate(sorted(frame_to_text.items())):
                    if fi >= len(frame_starts) or not ctext.strip():
                        continue
                    cap_png = os.path.join(work_dir, f"caption_{ci}.png")
                    _render_caption_png(ctext, vfmt, cap_png)
                    cmd += ["-i", cap_png]
                    cap_idx = next_input_idx
                    next_input_idx += 1
                    cstart = intro_total + frame_starts[fi]
                    cend = cstart + frame_durs[fi]
                    out_label = f"vcap{ci}"
                    filter_parts.append(
                        f"[{video_label}][{cap_idx}:v]overlay=x=(W-w)/2:y=H-h-40:"
                        f"enable='between(t,{cstart:.2f},{cend:.2f})'[{out_label}]"
                    )
                    video_label = out_label

            has_avatar = bool(avatar_video_path and os.path.exists(avatar_video_path))
            if has_avatar:
                from config import cfg as _cfg
                aw, ah = _cfg.avatar_size
                ax, ay = _cfg.avatar_position
                cmd += ["-stream_loop", "-1", "-i", avatar_video_path]
                avatar_idx = next_input_idx
                next_input_idx += 1
                filter_parts.append(
                    f"[{avatar_idx}:v]scale={aw}:{ah},colorkey=0x00FF00:0.3:0.2[avkeyed]"
                )
                filter_parts.append(
                    f"[{video_label}][avkeyed]overlay=x={ax}:y={ay}:shortest=1:"
                    f"enable='gte(t,{intro_total:.2f})'[vout]"
                )
                video_label = "vout"

            if meme_overlays:
                from config import cfg as _cfg
                mw, mh = _cfg.meme_size
                mx, my = _cfg.meme_position
                for mi, meme in enumerate(meme_overlays):
                    fi = meme["move_index"] + 1  # frame i holds ga.moves[i-1]
                    if fi >= len(frame_starts):
                        continue
                    cmd += ["-i", meme["png_path"]]
                    meme_idx = next_input_idx
                    next_input_idx += 1
                    scaled_label = f"memescaled{mi}"
                    filter_parts.append(f"[{meme_idx}:v]scale={mw}:{mh}[{scaled_label}]")
                    start = intro_total + frame_starts[fi] + _LEAD_IN
                    end = start + meme["duration"]
                    out_label = f"vmeme{mi}"
                    filter_parts.append(
                        f"[{video_label}][{scaled_label}]overlay=x={mx}:y={my}:"
                        f"enable='between(t,{start:.2f},{end:.2f})'[{out_label}]"
                    )
                    video_label = out_label

            if filter_parts:
                cmd += ["-filter_complex", ";".join(filter_parts), "-map", f"[{video_label}]"]
            else:
                cmd += ["-map", "0:v"]
            cmd += ["-map", f"{audio_input_idx}:a"]

            def _encode_args(codec: str) -> List[str]:
                return [
                    "-c:v", codec, "-preset", self.cfg.preset,
                    "-b:v", self.cfg.video_bitrate, "-pix_fmt", "yuv420p",
                    "-r", str(self.cfg.fps),
                    "-c:a", "aac", "-b:a", self.cfg.audio_bitrate,
                    "-shortest",
                    self.cfg.output_path,
                ]

            logger.info(f"[ENCODE] running ffmpeg assembly ({self.cfg.video_codec})...")
            result = subprocess.run(cmd + _encode_args(self.cfg.video_codec),
                                    capture_output=True, text=True, timeout=1800)
            if (result.returncode != 0 or not os.path.exists(self.cfg.output_path)) \
                    and self.cfg.video_codec != "libx264":
                logger.warning(f"[ENCODE] {self.cfg.video_codec} failed, retrying with libx264: "
                               f"{result.stderr[-500:]}")
                result = subprocess.run(cmd + _encode_args("libx264"),
                                        capture_output=True, text=True, timeout=1800)
            if result.returncode != 0 or not os.path.exists(self.cfg.output_path):
                raise RuntimeError(f"ffmpeg assembly failed (rc={result.returncode}): "
                                   f"{result.stderr[-2000:]}")

            logger.info(f"Video written: {self.cfg.output_path}")
            return self.cfg.output_path
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    # ── moviepy engine (legacy fallback) ──────────────────────────────────────

    def _assemble_moviepy(self, frame_paths: List[str], audio_paths: List[str],
                          ga, script, event: str = "",
                          avatar_video_path: str = None,
                          meme_overlays: List[dict] = None) -> str:
        mpe = _import_moviepy()

        if not frame_paths:
            raise ValueError("No frames to assemble")

        from scene_renderer import FORMATS
        vfmt = FORMATS.get(self.cfg.format, FORMATS["hd"])

        out_dir = os.path.dirname(self.cfg.output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        valid_audio = [p for p in audio_paths if p and os.path.exists(p)]

        # Build proportional segment→frame mapping so each move shows BEFORE its commentary.
        # Each assigned frame: silent LEAD_IN → audio plays. Other frames: brief IDLE hold.
        num_frames = len(frame_paths)
        num_segs   = len(valid_audio)
        frame_to_audio: dict = {}
        if num_segs == 1:
            frame_to_audio[0] = valid_audio[0]
        elif num_segs > 1:
            for i, ap in enumerate(valid_audio):
                fi = round(i * (num_frames - 1) / (num_segs - 1))
                frame_to_audio[fi] = ap

        tmp_frames: List[str] = []
        video_clips = []
        frame_starts: List[float] = []
        running_time = 0.0
        for fi, fp in enumerate(frame_paths):
            frame_starts.append(running_time)
            try:
                from PIL import Image
                img = Image.open(fp).convert("RGB")
                if img.size != (vfmt.width, vfmt.height):
                    img = img.resize((vfmt.width, vfmt.height), Image.LANCZOS)
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                img.save(tmp.name)
                tmp.close()
                tmp_frames.append(tmp.name)

                audio_path = frame_to_audio.get(fi)
                if audio_path:
                    seg_dur   = _audio_clip_duration(audio_path, mpe)
                    frame_dur = _LEAD_IN + seg_dur
                    img_clip  = _make_image_clip(mpe, tmp.name, frame_dur)
                    seg_audio = mpe.AudioFileClip(audio_path)
                    # Delay audio by LEAD_IN — board position appears before commentary
                    delayed          = mpe.CompositeAudioClip([_set_start(seg_audio, _LEAD_IN)])
                    delayed.duration = frame_dur
                    img_clip         = _set_audio(img_clip, delayed)
                else:
                    frame_dur = _IDLE_DUR
                    img_clip = _make_image_clip(mpe, tmp.name, frame_dur)

                video_clips.append(img_clip)
                running_time += frame_dur
            except Exception as e:
                logger.debug(f"Frame {fp} skipped: {e}")

        if not video_clips:
            raise RuntimeError("No valid video clips to assemble")

        video = mpe.concatenate_videoclips(video_clips, method="compose")
        # Audio is embedded per-clip above; no global set_audio needed

        title = getattr(script, "title", "")
        if title:
            try:
                txt = mpe.TextClip(
                    title, fontsize=40, color="white", font="Arial",
                    bg_color="black", method="caption",
                    size=(min(vfmt.width - 100, 1400), None),
                )
                txt = _set_duration(txt, min(5.0, video.duration))
                txt = _set_position(txt, ("center", 40))
                video = mpe.CompositeVideoClip([video, txt])
            except Exception as e:
                logger.debug(f"Title overlay skipped: {e}")

        if avatar_video_path and os.path.exists(avatar_video_path):
            try:
                from config import cfg as _cfg
                aw, ah = _cfg.avatar_size
                ax, ay = _cfg.avatar_position
                avatar_clip = mpe.VideoFileClip(avatar_video_path).without_audio()
                avatar_clip = _resize(avatar_clip, (aw, ah))
                # Key out green-screen background from bounce animation
                try:
                    avatar_clip = _mask_color(avatar_clip, color=[0, 255, 0], thr=100, s=5)
                except Exception as e:
                    logger.warning(f"Avatar chroma-key skipped, overlaying as opaque box: {e}")
                if avatar_clip.duration < video.duration:
                    avatar_clip = _loop(avatar_clip, video.duration)
                else:
                    avatar_clip = _subclip(avatar_clip, 0, video.duration)
                avatar_clip = _set_position(avatar_clip, (ax, ay))
                video = mpe.CompositeVideoClip([video, avatar_clip])
                logger.info(f"Avatar overlay added at ({ax},{ay}) size {aw}x{ah}")
            except Exception as e:
                logger.warning(f"Avatar overlay skipped: {e}", exc_info=True)

        for meme in (meme_overlays or []):
            try:
                from config import cfg as _cfg
                fi = meme["move_index"] + 1  # frame i holds ga.moves[i-1]
                if fi >= len(frame_starts):
                    continue
                start = frame_starts[fi] + _LEAD_IN
                meme_clip = _make_image_clip(mpe, meme["png_path"], meme["duration"])
                meme_clip = _resize(meme_clip, _cfg.meme_size)
                meme_clip = _set_position(meme_clip, _cfg.meme_position)
                meme_clip = _set_start(meme_clip, start)
                video = mpe.CompositeVideoClip([video, meme_clip])
            except Exception as e:
                logger.warning(f"Meme overlay skipped: {e}")

        video.write_videofile(
            self.cfg.output_path,
            fps=self.cfg.fps,
            codec="libx264",
            audio_codec="aac",
            bitrate=self.cfg.video_bitrate,
            audio_bitrate=self.cfg.audio_bitrate,
            preset=self.cfg.preset,
            logger=_EncodeProgressLogger() if _EncodeProgressLogger else None,
        )

        for t in tmp_frames:
            try:
                os.unlink(t)
            except OSError:
                pass

        logger.info(f"Video written: {self.cfg.output_path}")
        return self.cfg.output_path


# ── ffmpeg engine helpers ─────────────────────────────────────────────────────

def _ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _audio_duration(path: str, ffmpeg_exe: str) -> float:
    """Duration in seconds. Fast stdlib path for WAV, ffmpeg-probe fallback otherwise."""
    if path.lower().endswith(".wav"):
        try:
            with wave.open(path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate:
                    return max(frames / float(rate), 0.1)
        except Exception:
            pass
    try:
        result = subprocess.run([ffmpeg_exe, "-i", path], capture_output=True,
                                text=True, timeout=15)
        for line in result.stderr.splitlines():
            line = line.strip()
            if line.startswith("Duration:"):
                dur_str = line.split(",")[0].replace("Duration:", "").strip()
                h, m, s = dur_str.split(":")
                return max(int(h) * 3600 + int(m) * 60 + float(s), 0.1)
    except Exception:
        pass
    return 2.0


def _compute_frame_plan(frame_paths: List[str], audio_paths: List[str],
                        ffmpeg_exe: str, segment_texts: List[str] = None,
                        per_move: bool = False,
                        ) -> Tuple[List[float], Dict[int, str], Dict[int, str]]:
    """Map audio segments onto frames.

    per_move=True → strict 1:1: segment i lands on frame i (caller must pad
    frame_paths so len(frames) == len(segments); intro→frame0, move k→frame k,
    conclusion→the appended final-frame copy). No move is left silent.

    per_move=False → legacy proportional spread across [1, num_frames-1].

    Returns (frame_durs, frame_to_audio, frame_to_text). frame_to_text carries the
    caption string for each captioned frame (aligned with segment_texts).
    """
    num_frames = len(frame_paths)
    frame_to_audio: Dict[int, str] = {}
    frame_to_text: Dict[int, str] = {}

    if per_move:
        for i, ap in enumerate(audio_paths):
            if i >= num_frames:
                break
            if ap and os.path.exists(ap):
                frame_to_audio[i] = ap
            if segment_texts and i < len(segment_texts) and segment_texts[i]:
                frame_to_text[i] = segment_texts[i]
    else:
        # Keep audio path paired with its caption text so filtering stays aligned.
        valid = [(ap, (segment_texts[j] if segment_texts and j < len(segment_texts) else None))
                 for j, ap in enumerate(audio_paths) if ap and os.path.exists(ap)]
        num_segs = len(valid)
        if num_segs == 1:
            frame_to_audio[0] = valid[0][0]
            if valid[0][1]:
                frame_to_text[0] = valid[0][1]
        elif num_segs > 1:
            # Frame 0 is the pre-move starting position; frame i (i>=1) already has
            # move i played. Narration about a move must land on/after the frame
            # where it happened, so spread segments across [1, num_frames-1].
            span = num_frames - 2
            for i, (ap, txt) in enumerate(valid):
                fi = 1 + round(i * span / (num_segs - 1)) if span > 0 else min(1, num_frames - 1)
                frame_to_audio[fi] = ap
                if txt:
                    frame_to_text[fi] = txt

    frame_durs = []
    for fi in range(num_frames):
        ap = frame_to_audio.get(fi)
        if ap:
            frame_durs.append(_LEAD_IN + _audio_duration(ap, ffmpeg_exe))
        else:
            frame_durs.append(_IDLE_DUR)
    return frame_durs, frame_to_audio, frame_to_text


def _expand_frame_plan(frame_paths: List[str], frame_durs: List[float],
                       transition_map: Dict[int, List[str]],
                       fps: int) -> Tuple[List[str], List[float]]:
    """Splice each move's slide-transition frames into the front of its existing
    hold window, shrinking the final static frame's duration to compensate so the
    move's total on-screen duration (and therefore all audio/SFX timing, which is
    keyed off the original frame_durs) is unchanged."""
    step_dur = 1.0 / fps if fps > 0 else 1.0 / 24
    out_paths: List[str] = []
    out_durs: List[float] = []

    for fi, (fp, dur) in enumerate(zip(frame_paths, frame_durs)):
        transitions = transition_map.get(fi)
        if not transitions:
            out_paths.append(fp)
            out_durs.append(dur)
            continue

        max_transition_total = dur * 0.7
        max_steps = max(0, int(max_transition_total / step_dur))
        steps = transitions[:max_steps]
        transition_total = step_dur * len(steps)

        out_paths.extend(steps)
        out_durs.extend([step_dur] * len(steps))
        out_paths.append(fp)
        out_durs.append(dur - transition_total)

    return out_paths, out_durs


def _frame_move_types(frame_paths: List[str], ga) -> Dict[int, str]:
    """Map frame index -> move-type sfx key. Frame 0 is the start position (no
    sound). Frame i (i>=1) corresponds to ga.moves[i-1] if available."""
    import move_sfx
    moves = getattr(ga, "moves", None)
    result: Dict[int, str] = {}
    for fi in range(1, len(frame_paths)):
        if moves:
            idx = fi - 1
            if idx >= len(moves):
                continue  # padded final-frame copy (conclusion) — no move, no sfx
            result[fi] = move_sfx.classify_san(moves[idx].move_san)
        else:
            result[fi] = "move"
    return result


def _cumulative_starts(frame_durs: List[float]) -> List[float]:
    starts = []
    acc = 0.0
    for d in frame_durs:
        starts.append(acc)
        acc += d
    return starts


def _prepare_frames(frame_paths: List[str], vfmt, work_dir: str) -> List[str]:
    from PIL import Image
    out_paths = []
    for idx, fp in enumerate(frame_paths):
        img = Image.open(fp).convert("RGB")
        if img.size != (vfmt.width, vfmt.height):
            img = img.resize((vfmt.width, vfmt.height), Image.LANCZOS)
        out_path = os.path.join(work_dir, f"frame_{idx:05d}.png")
        img.save(out_path)
        out_paths.append(out_path)
    return out_paths


def _write_ffconcat(frame_paths: List[str], frame_durs: List[float], work_dir: str) -> str:
    concat_path = os.path.join(work_dir, "frames.ffconcat")
    with open(concat_path, "w", encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for fp, dur in zip(frame_paths, frame_durs):
            safe = fp.replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe}'\n")
            f.write(f"duration {dur:.3f}\n")
        # ffmpeg concat quirk: last entry's duration is only honored if the file
        # is listed once more without a following duration line.
        if frame_paths:
            safe_last = frame_paths[-1].replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_last}'\n")
    return concat_path


def _decode_pcm_mono(path: str, ffmpeg_exe: str) -> bytes:
    cmd = [ffmpeg_exe, "-y", "-i", path, "-ar", str(_MASTER_SR), "-ac", "1",
           "-f", "s16le", "-"]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed for {path}: {result.stderr[-500:]}")
    return result.stdout


def _build_master_audio(frame_starts: List[float], frame_to_audio: Dict[int, str],
                        total_duration: float, out_path: str, ffmpeg_exe: str,
                        lead_in: float, frame_move_types: Dict[int, str] = None,
                        time_offset: float = 0.0) -> None:
    """Build one continuous mono WAV: silence everywhere, with each segment's audio
    copied in at its LEAD_IN-delayed offset. Segments are designed not to overlap.
    Move sound effects (if given) are additively mixed in at each frame's start,
    ahead of the lead-in, so they land right as the move appears on screen.
    time_offset shifts every board-frame timestamp right by that many seconds,
    for a prepended intro segment — the leading time_offset seconds stay silent."""
    total_samples = max(1, int(total_duration * _MASTER_SR))
    buf = bytearray(total_samples * 2)  # 16-bit silence == zero bytes

    if frame_move_types:
        import numpy as np
        import move_sfx
        pcm_view = np.frombuffer(buf, dtype=np.int16)
        for fi, kind in frame_move_types.items():
            if fi >= len(frame_starts) or not kind:
                continue
            sfx_pcm = np.frombuffer(move_sfx.get_sfx_pcm16(kind), dtype=np.int16)
            start_sample = int((time_offset + frame_starts[fi]) * _MASTER_SR)
            end_sample = min(start_sample + len(sfx_pcm), len(pcm_view))
            n = end_sample - start_sample
            if n <= 0:
                continue
            mixed = pcm_view[start_sample:end_sample].astype(np.int32) + \
                sfx_pcm[:n].astype(np.int32)
            pcm_view[start_sample:end_sample] = np.clip(mixed, -32768, 32767).astype(np.int16)

    for fi, audio_path in frame_to_audio.items():
        if not (audio_path and os.path.exists(audio_path)):
            continue
        offset = time_offset + frame_starts[fi] + lead_in
        start_sample = int(offset * _MASTER_SR)
        start_byte = start_sample * 2
        if start_byte >= len(buf):
            continue
        pcm_bytes = _decode_pcm_mono(audio_path, ffmpeg_exe)
        end_byte = min(start_byte + len(pcm_bytes), len(buf))
        n = end_byte - start_byte
        if n > 0:
            buf[start_byte:end_byte] = pcm_bytes[:n]

    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_MASTER_SR)
        wf.writeframes(bytes(buf))


def _render_title_png(title: str, vfmt, out_path: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    max_w = min(vfmt.width - 100, 1400)
    pad_x, pad_y = 24, 14
    try:
        font = ImageFont.load_default(size=40)
    except TypeError:
        font = ImageFont.load_default()

    scratch = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(scratch)
    words, lines, cur = title.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = d.textbbox((0, 0), test, font=font)
        if not cur or bbox[2] - bbox[0] <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    line_h = 50
    box_w = max_w + pad_x * 2
    box_h = line_h * len(lines) + pad_y * 2
    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 160))
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = (box_w - tw) // 2
        ty = pad_y + i * line_h
        draw.text((tx, ty), line, fill=(255, 255, 255, 255), font=font)
    img.save(out_path)


def _render_caption_png(text: str, vfmt, out_path: str) -> None:
    """Bottom caption strip: semi-transparent black rounded bar, centered white text.
    Mirrors the mockup's caption band."""
    from PIL import Image, ImageDraw, ImageFont

    max_w = min(vfmt.width - 160, 1500)
    pad_x, pad_y = 30, 16
    try:
        font = ImageFont.load_default(size=34)
    except TypeError:
        font = ImageFont.load_default()

    scratch = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = scratch.textbbox((0, 0), test, font=font)
        if not cur or bbox[2] - bbox[0] <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if not lines:
        lines = [""]

    line_h = 44
    text_w = max((scratch.textbbox((0, 0), ln, font=font)[2] for ln in lines), default=0)
    box_w = text_w + pad_x * 2
    box_h = line_h * len(lines) + pad_y * 2
    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=14, fill=(0, 0, 0, 140))
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = (box_w - tw) // 2
        ty = pad_y + i * line_h
        draw.text((tx, ty), line, fill=(255, 255, 255, 255), font=font)
    img.save(out_path)


# ── moviepy compat helpers (legacy path only) ─────────────────────────────────

def _import_moviepy():
    try:
        import moviepy.editor as mpe
        return mpe
    except ImportError:
        pass
    try:
        import moviepy as mpe
        return mpe
    except ImportError:
        raise RuntimeError("moviepy not installed — run: pip install moviepy")


def _make_image_clip(mpe, path: str, duration: float):
    clip = mpe.ImageClip(path)
    return _set_duration(clip, duration)


def _set_duration(clip, dur):
    try:
        return clip.set_duration(dur)
    except AttributeError:
        return clip.with_duration(dur)


def _set_audio(clip, audio):
    try:
        return clip.set_audio(audio)
    except AttributeError:
        return clip.with_audio(audio)


def _set_position(clip, pos):
    try:
        return clip.set_position(pos)
    except AttributeError:
        return clip.with_position(pos)


def _subclip(clip, t1, t2):
    try:
        return clip.subclip(t1, t2)
    except AttributeError:
        return clip.subclipped(t1, t2)


def _resize(clip, size):
    try:
        return clip.resize(size)
    except AttributeError:
        return clip.resized(size)


def _loop(clip, duration):
    try:
        return clip.loop(duration=duration)
    except AttributeError:
        from moviepy import vfx
        return clip.with_effects([vfx.Loop(duration=duration)])


def _mask_color(clip, color, thr, s):
    try:
        from moviepy.video.fx.mask_color import mask_color
        return clip.fx(mask_color, color=color, thr=thr, s=s)
    except (ImportError, AttributeError):
        from moviepy import vfx
        return clip.with_effects([vfx.MaskColor(color=tuple(color), threshold=thr, stiffness=s)])


def _total_audio_duration(audio_paths: List[str], mpe) -> float:
    total = 0.0
    for ap in audio_paths:
        try:
            c = mpe.AudioFileClip(ap)
            total += c.duration
            c.close()
        except Exception:
            pass
    return total


def _audio_clip_duration(path: str, mpe) -> float:
    """Return duration of a single audio file in seconds."""
    try:
        c = mpe.AudioFileClip(path)
        dur = c.duration
        c.close()
        return max(float(dur), 0.1)
    except Exception:
        return 2.0


def _set_start(clip, t):
    try:
        return clip.set_start(t)
    except AttributeError:
        return clip.with_start(t)
