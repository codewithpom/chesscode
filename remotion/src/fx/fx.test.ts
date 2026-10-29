import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { boardStateAt, moveDoneFrame } from "../board/boardState";
import { buildPositions } from "../board/positions";
import { VideoSpec, type Beat } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { templateFx } from "../theme/templates";
import { BoardFx, boardMsAt, fxWindows, shakeOffset } from "./index";
import { kingPath } from "./trail";

const fixture = VideoSpec.parse(
  JSON.parse(readFileSync(resolve(__dirname, "../../../spec/fixtures/cc-2026-0001-en/video_spec.json"), "utf8")),
);
const FPS = 30;
const beat = (over: Partial<Beat>): Beat => ({
  beat_id: "b",
  type: "blunder",
  ply: 5,
  at_ms: 10000,
  intensity: 3,
  mascot: { pose: "faint", line: "x" },
  fx: [],
  sfx: null,
  ...over,
});
const AT = msToFrame(10000, FPS);
// 280 ms rounds to 8 frames, but the board counts frame 8 as 267 ms: the move is done on frame 9.
const LAND = moveDoneFrame(10000, FPS);

describe("fxWindows", () => {
  it("uses the plan's frame counts", () => {
    const w = fxWindows(
      [beat({ fx: ["board_shake", "red_flash", "freeze_frame", "replay_move", "gold_glint", "stamp_brilliant", "ghost_arrow", "king_trail", "crown_sparkle", "out_of_theory_label"] })],
      FPS,
    );
    const span = (fx: string) => w.filter((x) => x.fx === fx).map((x) => [x.from, x.to - x.from]);
    expect(span("board_shake")).toEqual([[AT, 6]]);
    expect(span("red_flash")).toEqual([[LAND, 8]]);
    expect(span("freeze_frame")).toEqual([[LAND, 6]]);
    expect(LAND).toBe(AT + 9);
    expect(span("replay_move")).toEqual([[LAND + 6, 9]]); // the move takes until the board calls it done, after the freeze
    expect(span("gold_glint")).toEqual([[LAND, 24]]);
    expect(span("stamp_brilliant")).toEqual([[LAND, 24]]);
    expect(span("ghost_arrow")).toEqual([[LAND, 60]]);
    expect(span("king_trail")).toEqual([[LAND, 90]]);
    expect(span("crown_sparkle")).toEqual([[LAND, 30]]);
    expect(span("out_of_theory_label")).toEqual([[AT, 60]]);
  });

  it("a freeze never holds a capture mid-fade: the board has finished the move on the freeze's first frame", () => {
    // 1.e4 d5 2.exd5: ply 3 is a capture; at 30 fps the old rounding froze on 267 ms with the pawn at 10.8% opacity.
    const positions = buildPositions("1. e4 d5 2. exd5 *");
    const plies = [1, 2, 3].map((ply) => ({ ply, show_at_ms: 10000 + (ply - 1) * 300, arrows: [], highlights: [] }));
    const b = beat({ ply: 3, at_ms: 10600, fx: ["freeze_frame"] });
    const [w] = fxWindows([b], FPS);
    const state = (f: number) => boardStateAt(f, FPS, plies, positions);
    expect(state(w.from).pieces.every((p) => p.opacity === 1)).toBe(true);
    expect(state(w.from - 1).pieces.some((p) => p.opacity < 1)).toBe(true); // one frame earlier it is still fading
    for (let f = w.from; f < w.to; f++) expect(state(f)).toEqual(state(w.from));
  });

  it("freeze_frame has no window below intensity 2 (the mascot does not freeze either)", () => {
    expect(fxWindows([beat({ intensity: 1, fx: ["freeze_frame"] })], FPS)).toEqual([]);
  });

  it("clock effects last until the next ply starts", () => {
    const w = fxWindows([beat({ fx: ["clock_red"] })], FPS, {
      plies: [{ ply: 6, show_at_ms: 16000 }],
    });
    expect(w).toEqual([expect.objectContaining({ fx: "clock_red", from: AT, to: msToFrame(16000, FPS) })]);
  });

  it("eval_whip and move_underline draw themselves: no window", () => {
    expect(fxWindows([beat({ fx: ["eval_whip", "move_underline"] })], FPS)).toEqual([]);
  });

  it("is deterministic", () => {
    const b = [beat({ fx: ["board_shake", "red_flash"] })];
    expect(fxWindows(b, FPS)).toEqual(fxWindows(b, FPS));
  });

  it("a disabled fx produces no window", () => {
    templateFx.shorts.board_shake = false;
    try {
      expect(fxWindows([beat({ fx: ["board_shake", "red_flash"] })], FPS, { template: "shorts" }).map((w) => w.fx)).toEqual(["red_flash"]);
      expect(fxWindows([beat({ fx: ["board_shake"] })], FPS, { template: "studio" })).toHaveLength(1);
    } finally {
      templateFx.shorts.board_shake = true;
    }
  });
});

describe("shakeOffset", () => {
  const w = fxWindows([beat({ fx: ["board_shake"] })], FPS);
  it("is 0 outside its window", () => {
    for (const f of [0, AT - 1, AT + 6, AT + 100]) expect(shakeOffset(f, w)).toEqual({ x: 0, y: 0 });
  });
  it("stays within 6 px and decays", () => {
    const mag = (f: number) => Math.hypot(shakeOffset(f, w).x, shakeOffset(f, w).y);
    for (let f = AT; f < AT + 6; f++) expect(Math.abs(shakeOffset(f, w).x)).toBeLessThanOrEqual(6);
    expect(mag(AT + 5)).toBeLessThan(mag(AT));
  });
});

describe("boardMsAt", () => {
  const w = fxWindows([beat({ fx: ["freeze_frame", "replay_move"] })], FPS);
  it("holds during the freeze, replays the move after it, and is real time elsewhere", () => {
    expect(boardMsAt(LAND + 3, FPS, w, 99999)).toBe(boardMsAt(LAND, FPS, w, 0));
    expect(boardMsAt(LAND + 6, FPS, w, 99999)).toBe(10000); // replay restarts at the ply's own show_at
    expect(boardMsAt(LAND + 6 + 4, FPS, w, 99999)).toBeGreaterThan(10000);
    expect(boardMsAt(LAND + 20, FPS, w, 12345)).toBe(12345);
  });
});

describe("kingPath", () => {
  it("lists the king's squares for its colour, oldest first", () => {
    const states = buildPositions("1. e4 e5 2. Ke2 Ke7 3. Kd3 Kd6 *");
    expect(kingPath(states, 5, "w")).toEqual(["e1", "e2", "d3"]);
    expect(kingPath(states, 4, "b")).toEqual(["e8", "e7"]);
    expect(kingPath(states, 1, "w")).toEqual([]);
  });
});

describe("BoardFx", () => {
  it("is exported", () => {
    expect(BoardFx).toBeTypeOf("function");
    expect(fixture.beats.length).toBeGreaterThan(0);
  });
});
