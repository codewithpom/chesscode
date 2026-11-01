# Gate B audit (Claude, independent): Studio + Shorts

**Verdict: PASS WITH FIXES.** Anti-slop, readability and Devanagari pass. The motion is clean apart from a mascot glitch at scene cuts (high). The rest: audio level, scene lengths, evidence gaps.

Evidence: 22 stills, `clip60.mp4` frames, EBU R128 loudness, phone and 320x180 downscales, token contrast.

## Findings

### High

1. **The mascot breaks at scene cuts** (`StudioVideo.tsx:63-66`, `MascotSlot.tsx`). The mascot is mounted inside each scene Sequence, so a reaction is clamped to that scene's end.
   - Faint at 25 s, across the Playback to KeyMoment cut at frame 810: frames 805-808 the bubble fades out; 809 the bubble disappears and Pyaada snaps upright; 810 the bubble pops back at full opacity and he is mid-fall again.
   - At 47.0 s the brilliant bubble is cut about 1.1 s short of the 3.24 s that section 7 asks for.

   **Fix:** mount the mascot once at composition level, as `StudioCaptions` is, with a box per scene. Add a test that a reaction crossing a scene boundary keeps its `bubbleTo`.

### Medium

2. **The faint passes through the caption band.** At frame 808 the mascot is at x about 1710-1860, y about 815-995. That is inside the caption box (x 1000-1824) and past the 96 px margin. The comment at `MascotLayer.tsx:72` assumes that area is free. The layout test only checks beat frames. **Fix:** keep the fall path above y 800 or clip it. Test the whole faint window.
3. **The mix is -11.9 LUFS** (true peak -1.4 dBTP). The segments are -14.7 LUFS mono, and the stereo upmix adds +2.8 LU. The spec target is -14 ± 1. **Fix:** set narration `volume={0.708}`. Sfx and blips get the same upmix, so their ratios hold. Or run a two-pass `loudnorm` on the render. Add a QA check on the final mix.
4. **Music ducking is unverified.** The fixture bed `gallery-en/music/bed_calm_01.mp3` has a mean level of -91 dB. Voice against sfx and blips is fine: voice reads -10 to -13 LUFS momentary, blips -25 to -29, and sfx is levelled 6.5 LU under the voice. **Fix:** render 20 s with a real bed before Gate C.
5. **Section 5 lengths are not enforced.** `timeline.ts` sizes the TitleCard, PlayerIntro and Verdict from the narration. Only the outro gets padding (`outro_ms: 20000`). In the clip, the Verdict runs 7.2 s (spec 10-15 s) and the TitleCard 2.8 s (spec 2.5 s). **Fix:** add a check for minimum and maximum scene length to `spec-validator`, or pad the Verdict in `timeline.py`.
6. **The clip cannot prove section 8 timing.** The fixture starts narration at 25000 ms, the same ms as the intensity-3 blunder, with no 900 ms gap. "Morphy recaptures with the queen" plays over the faint while 6...Nf6?? is shown. The visual order is fine. **Fix:** rebuild `make_gallery_specs.ts` through `timeline.layout` and recheck.

### Low

7. **The reaction counts from `at_ms`, not from the landing** (`react.ts:46` against `windows.ts:44`). The mascot reacts before the flash, and the move list shows "Nf6??" from the move's first frame, which gives the reveal away. **Fix:** count from `moveDoneFrame` and show the annotation on landing.
8. **Widow "opera"** on the ColdOpen and Shorts hooks. **Fix:** `textWrap: "balance"` at `ColdOpen.tsx:28` and `ShortsVideo.tsx:97`.
9. **The Verdict caption breaks inside "d-file".** **Fix:** use non-breaking hyphens in caption tokens.
10. **KeyMoment "6..." is misaligned** with the right-aligned "7." column. **Fix:** right-align the number cell.
11. **The Shorts bubble is two lines tall for "Two pieces."** **Fix:** fit the box to the final line count.
12. **Rule 7 is only partly met.** `impeccable detect` ran regex-only and no `/impeccable audit` is recorded. **Fix:** run the audit, or record why it was skipped.

## Checklist

1. **Anti-slop: pass.**
   - No gradients, glows or emoji. One Plex system. Sentence case. Tabular Mono figures. Empty regions stay empty.
   - Contrast: muted 6.4:1 on background and 5.9:1 on surface; text 16.3:1; bubble 13.3:1; blunder red on surface 4.85:1.
   - Rule 7 is partly met (finding 12).
   - Not mass-produced: four board themes, a cold open from the game's own beat, chapters from the game, and the thumbnail uses the game's crop and the beat's pose.
2. **Readable: pass.**
   - Smallest text is 28 px; the bubble is 30.
   - On a phone at 390 px wide: hook about 26 px, captions about 32, bubble about 16.
   - Thumbnail at 320x180: text readable in EN and HI, the knight and arrow are clear.
   - Devanagari is intact in all 11 HI stills.
   - Shorts keep the bottom 340 px and right 120 px clear.
3. **Motion: pass except findings 1, 2 and 7.**
   - Pieces move in 280 ms on the shared easing.
   - The UI spring is overdamped (28 against a critical 26.1). The stamp goes from 1.5 to 1.0 with no overshoot.
   - Hard cuts. Cards enter one at a time.
4. **Scenes:**
   - ColdOpen 6 s, PlayerIntro 5.2 s and KeyMoment 15 s pass.
   - Verdict and TitleCard are off (finding 5).
   - The Outro keeps the right two-thirds empty, and the pipeline gives it 20 s.
5. **Funny but professional: yes.** The comedy lives only in the mascot and sfx, and the lines follow the rules. The mascot never covers the board, eval bar or captions in any still. The faint in motion is the one exception (finding 2).

Not checked: `shorts.mp4`, other board themes, HI audio.
