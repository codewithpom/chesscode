Five verified findings against committed `HEAD` (`c16e225`), all **P2 / medium**:

1. **Key-moment lines can be cut short** — [KeyMoment.tsx:23](</D:/chess code/.worktrees/m5-templates/remotion/src/scenes/KeyMoment.tsx:23>). A valid 15-second scene with eight legal moves schedules its final move at 15.5 seconds. Reproduction shows only seven moves before the cut, omitting the line’s conclusion. **Fix:** derive spacing from the available duration, allowing it below two seconds while preserving move completion and the final hold.

2. **Thumbnail and verdict can show the wrong position** — [Thumbnail.tsx:64](</D:/chess code/.worktrees/m5-templates/remotion/src/compositions/Thumbnail.tsx:64>) and [Verdict.tsx:27](</D:/chess code/.worktrees/m5-templates/remotion/src/scenes/Verdict.tsx:27>). Selecting a ply through `show_at_ms + 600/400` allows subsequent moves into the snapshot. With plies 300 ms apart, requesting ply 1 displays ply 3 or 2 respectively, contradicting the arrow or turning-point label. **Fix:** select the completed position by ply explicitly.

3. **Freeze holds an unfinished capture/promotion** — [windows.ts:29](</D:/chess code/.worktrees/m5-templates/remotion/src/fx/windows.ts:29>). At 30 fps, rounding 280 ms gives eight frames, but the board considers frame eight only 267 ms into the move. The six-frame freeze therefore preserves an unfinished state; reproduction leaves the captured pawn visible at 10.8% opacity. **Fix:** start the freeze on the first frame satisfying the board’s completion condition, using shared timing helpers.

4. **Comeback’s `eval_whip` is ignored** — [StudioBoard.tsx:13](</D:/chess code/.worktrees/m5-templates/remotion/src/scenes/StudioBoard.tsx:13>), through [winprob.ts:49](</D:/chess code/.worktrees/m5-templates/remotion/src/ui/winprob.ts:49>). The integration delegates to a helper that recognizes only blunders, ignoring `beats[].fx`. A comeback carrying `eval_whip` produces exactly the ordinary spring animation. **Fix:** drive whip selection from the effect flag and beat timing, respecting the template switch.

5. **Outro captions occupy the reserved end-screen area** — [StudioVideo.tsx:61](</D:/chess code/.worktrees/m5-templates/remotion/src/compositions/StudioVideo.tsx:61>). Global captions remain active during spoken outro narration at `x=1000`, inside the right two-thirds that must stay empty. The layout test omits captions from its outro boxes, so it misses this collision. **Fix:** position outro captions within the left-third region and include them in layout assertions.

Validation: 118 tests passed; TypeScript passed; synthetic 8/10/12-minute timelines remained contiguous.

No files changed. Full renders and Hindi visual checks were not performed; concurrent merge changes were excluded from findings.