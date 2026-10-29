# M4 mascot rig: design critique

Evidence: sheet, reel frames in `remotion/build/m4/frames/`, concept sheet. `npx impeccable detect remotion/src`: 0 findings (regex-only, undercount). Shorts 260 px not rendered.

Verdict: on-model; failures are props, the faint exit and motion details.

## Fixes (most severe first)

1. **High, faint (`react.ts` motion, `MascotLayer.tsx` clipPath).** Verified, but the head is geometrically attached (same overlap as idle). The real reel fault: he tips right and is sliced by the box clip at x=1824, 96 px inside the frame, then the bubble talks to empty space for ~1.5 s. Spec 7: "falls backward out of frame". Fix: no clip for the mascot during `faint` (right/bottom of the box is free of board and captions). Fall with ease-in: lean 0 to -25 over 4 frames (anticipation), then offsetY +300 and lean 90. Hide the bubble tail while offscreen. Sheet: browY 0 (eyes+brows read as cracks).
2. **High, mic_drop (`Props.tsx` mic).** Verified. Mic is head r10 + 8x26 handle in body color: about 15 px at 200 px, the same as the hand ball. It lands at x≈222, outside the base, at the clip edge. Fix: ink handle 10x44, head r16 in `P.shade` with 2 ink grille lines, origin on the `up` hand tip, landing at x≈196 on the base rim. Start the fall at t=15, not 6: the arm is still rising when it drops now.
3. **High, crown (`poseState.prop`, single slot).** The crown vanishes in checks_watch, binoculars and mic_drop, then pops back on return to idle. It is the signature prop (spec 7); mic_drop is the final beat and thumbnail. Fix: separate `crown: 0..1` (or draw it unless prop is `party_hat` or arms=`hold`); hand props go in their own slot.
4. **Medium, screaming (`poses.ts`, `react.ts`).** The `wide` mouth sits low and crosses the collar, so it reads as a beak. Shake `3*sin(sec*90)` is 14 Hz at 30 fps (Nyquist), so it aliases into ~2 px jitter and is invisible. Fix: mouth centre up ~10 units, eyeScale 1.25, browY 1.2. Shake 5 units at ~6 Hz (`sec*38`). Squash 1±0.06 at ~4 Hz.
5. **Medium, blink overrides acting (`react.ts` poseAt).** Eyes shut on shocked at 13.5 s and jealous at 16.0 s, but spec 7 says "eyes do most of the acting". Fix: skip blinks for 30 frames after `reactFrame`.
6. **Medium, empty bubble (`speech.tsx` wordFrames).** The bubble shows blank for ~0.4 s (frames 4.5 s, 11.5 s) because a word appears only after its last character time. Fix: word i appears at `from + charsBefore(i)/12 s`, so word 1 shows on frame 10 as spec 8 requires.
7. **Medium, bow (`poses.ts`).** squash 1.1 + offsetY 6 + shut eyes reads as dozing. Fix: motion dip squash 1.18 to 1.0 over 18 frames, head offset +12, both arms crossed at the belly, mouth `flat`.
8. **Low, checks_watch (`Props.tsx` watch).** Watch ~6 px at 200 px. Fix: r13 with tick marks, pupils down toward it (pupilY 1).
9. **Low, sweating (`poses.ts`).** Mouth `flat`; the approved sheet has a wavy worried mouth. Add a `wobble` MouthId.
10. **Low, spring feel (`theme/motion.ts` uiSpring).** Damping 28 / stiffness 170 is overdamped (critical 26.1), so no overshoot: pass. But it takes ~0.5 s to settle, which softens the frame-7 snap. Consider a mascot-only critically damped spring (stiffness 400, damping 40).

## Passes

idle, wave, thinking, side_eye, facepalm, slow_clap, jealous, binoculars, point. Timing: freeze 6, react frame 7, bubble frame 10, 1.8 s + 60 ms/char. Bubble: 30 px, ~14:1, tail on mouth. Idle (4 s + 3.1 s, seeded blinks) never visibly loops. No anti-slop hits. Party confetti unverified (not in reel).
