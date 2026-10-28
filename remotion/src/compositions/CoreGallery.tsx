// Review-only stills of the core drawing layer (Board, EvalBar, Captions). Not a video template.
import type { FC, ReactNode } from "react";
import { AbsoluteFill, Sequence, type CalculateMetadataFunction } from "remotion";
import { z } from "zod";
import fixture from "../../../spec/fixtures/cc-2026-0001-en/video_spec.json";
import { Board } from "../board/Board";
import { VideoSpec } from "../spec/schema";
import { fontFor } from "../theme/fonts";
import { shortsLayout } from "../theme/layout";
import { tokens } from "../theme/tokens";
import { Captions } from "../ui/Captions";
import { EvalBar } from "../ui/EvalBar";

export const PANELS = [
  "board-bone_slate",
  "board-walnut",
  "board-cool_grey",
  "board-warm_sand",
  "board-black-bottom",
  "eval-states",
  "captions-en",
  "captions-hi",
  "captions-shorts",
  "captions-hi-shorts",
] as const;
export const GalleryProps = z.object({ panel: z.enum(PANELS) });
export type GalleryProps = z.infer<typeof GalleryProps>;

export const calculateGalleryMetadata: CalculateMetadataFunction<GalleryProps> = ({ props }) =>
  props.panel.endsWith("shorts") ? { width: 1080, height: 1920 } : { width: 1920, height: 1080 };

const FPS = 30;
const base = VideoSpec.parse(fixture);
const msF = (ms: number): number => Math.round((ms * FPS) / 1000);

// Opera game after 21.Bxb5+ has landed: last-move tint, check on e8, and two demo arrows.
const PLY21 = base.plies.find((p) => p.ply === 21)!;
const REST_FRAME = msF(PLY21.show_at_ms + 600);
const withArrows: VideoSpec = {
  ...base,
  plies: base.plies.map((p) =>
    p.ply === 21
      ? {
          ...p,
          arrows: [
            { from: "b5", to: "d7", color: "best" as const },
            { from: "d8", to: "d1", color: "threat" as const },
          ],
        }
      : p,
  ),
};

/** Renders children as if the timeline were at `frame`. */
const At: FC<{ frame: number; children: ReactNode }> = ({ frame, children }) => (
  <Sequence from={-frame} layout="none">
    {children}
  </Sequence>
);

const Label: FC<{ x: number; y: number; width?: number; children: ReactNode }> = ({ x, y, width, children }) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width,
      color: tokens.color.muted,
      fontFamily: fontFor("en", "ui"),
      fontSize: tokens.size.min,
      lineHeight: 1.3,
    }}
  >
    {children}
  </div>
);

// Studio layout: board 800 at left, vertically centered, 96 margin; eval bar 24 wide, 16 left of the board.
const StudioStub: FC<{ spec: VideoSpec; frame: number; children?: ReactNode }> = ({ spec, frame, children }) => (
  <At frame={frame}>
    <div style={{ position: "absolute", left: 96, top: 140 }}>
      <EvalBar spec={spec} orientation="vertical" length={800} thickness={24} />
    </div>
    <div style={{ position: "absolute", left: 136, top: 140 }}>
      <Board spec={spec} size={800} />
    </div>
    {children}
  </At>
);

const themed = (theme: VideoSpec["board"]["theme"], orientation: "white" | "black" = "white"): VideoSpec => ({
  ...withArrows,
  board: { theme, orientation },
});

type EvalItem = { label: string; cp: number | null; mate: number | null; frame: number; whip?: boolean };
const EVAL_ITEMS: EvalItem[] = [
  { label: "Equal", cp: 0, mate: null, frame: 90 },
  { label: "White ahead", cp: 140, mate: null, frame: 90 },
  { label: "Black ahead", cp: -320, mate: null, frame: 90 },
  { label: "Mate for White", cp: null, mate: 3, frame: 90 },
  { label: "Mate for Black", cp: null, mate: -3, frame: 90 },
  { label: "Blunder, mid-whip", cp: -900, mate: null, frame: 4, whip: true },
];

const evalSpec = (it: EvalItem): VideoSpec => ({
  ...base,
  plies: [
    {
      ...base.plies[0],
      ply: 1,
      show_at_ms: 0,
      eval: (it.mate !== null ? { cp: null, mate: it.mate } : { cp: it.cp!, mate: null }) as VideoSpec["plies"][number]["eval"],
    },
  ],
  beats: it.whip ? [{ ...base.beats[0], type: "blunder", ply: 1 }] : [],
});

const EvalStates: FC = () => (
  <>
    {EVAL_ITEMS.map((it, i) => (
      <div key={it.label}>
        <div style={{ position: "absolute", left: 96 + i * 290, top: 200 }}>
          <At frame={it.frame}>
            <EvalBar spec={evalSpec(it)} orientation="vertical" length={500} thickness={24} />
          </At>
        </div>
        <Label x={96 + i * 290} y={730} width={260}>
          {it.label}
        </Label>
      </div>
    ))}
    <div style={{ position: "absolute", left: 96, top: 900 }}>
      <At frame={90}>
        <EvalBar spec={evalSpec(EVAL_ITEMS[1])} orientation="horizontal" length={800} thickness={24} />
      </At>
    </div>
    <Label x={1000} y={888}>
      Horizontal, as on Shorts
    </Label>
  </>
);

// Hindi sample with English chess terms: 4 s of evenly timed words, then a conjunct/matra stress
// segment (क्ष त्र ष्ठ कृ ज़्या) timed fast enough that all five words share one long-form page.
const HI_WORDS = "सोलहवें move पर queen b8 पर, check. Black को लेना ही पड़ा.".split(" ");
const HI_STEP = Math.floor(4000 / HI_WORDS.length);
const HI_STRESS = "क्षति त्रुटि श्रेष्ठ कृपया ज़्यादा".split(" ");
const HI_STRESS_AT = 4500;
const HI_STRESS_STEP = 220;
const hiSpec: VideoSpec = {
  ...base,
  language: "hi",
  narration: [
    {
      segment_id: "hi-sample",
      kind: "ply",
      ply: 31,
      text: HI_WORDS.join(" "),
      audio: "audio/none.mp3",
      start_ms: 0,
      duration_ms: 4000,
      words: HI_WORDS.map((w, i) => ({ w, start_ms: i * HI_STEP, end_ms: (i + 1) * HI_STEP - 40 })),
    },
    {
      segment_id: "hi-stress",
      kind: "ply",
      ply: 31,
      text: HI_STRESS.join(" "),
      audio: "audio/none.mp3",
      start_ms: HI_STRESS_AT,
      duration_ms: HI_STRESS.length * HI_STRESS_STEP,
      words: HI_STRESS.map((w, i) => ({
        w,
        start_ms: HI_STRESS_AT + i * HI_STRESS_STEP,
        end_ms: HI_STRESS_AT + (i + 1) * HI_STRESS_STEP - 20,
      })),
    },
  ],
};

export const CoreGallery: FC<GalleryProps> = ({ panel }) => {
  let body: ReactNode;
  if (panel === "board-black-bottom") {
    body = (
      <>
        <StudioStub spec={themed("bone_slate", "black")} frame={REST_FRAME} />
        <Label x={1000} y={140}>
          Black at the bottom
        </Label>
      </>
    );
  } else if (panel.startsWith("board-")) {
    const theme = panel.slice("board-".length) as VideoSpec["board"]["theme"];
    body = (
      <>
        <StudioStub spec={themed(theme)} frame={REST_FRAME} />
        <Label x={1000} y={140}>
          Board theme: {theme}
        </Label>
      </>
    );
  } else if (panel === "eval-states") {
    body = <EvalStates />;
  } else if (panel === "captions-en") {
    body = (
      <StudioStub spec={themed("bone_slate")} frame={msF(7100)}>
        <Captions spec={base} mode="long" />
      </StudioStub>
    );
  } else if (panel === "captions-hi") {
    body = (
      <StudioStub spec={{ ...themed("bone_slate"), language: "hi" }} frame={msF(HI_STRESS_AT + 600)}>
        <Captions spec={hiSpec} mode="long" />
      </StudioStub>
    );
  } else {
    // Shorts: approved layout (theme/layout.ts): captions, eval label + thin bar, 864 board, mascot zone below.
    const hindi = panel === "captions-hi-shorts";
    const s = hindi ? { ...themed("bone_slate"), language: "hi" as const } : themed("bone_slate");
    const { evalBar, board } = shortsLayout.boxes;
    body = (
      <At frame={msF(hindi ? HI_STRESS_AT + 600 : 7100)}>
        <Captions spec={hindi ? hiSpec : base} mode="shorts" />
        <div style={{ position: "absolute", left: evalBar.x, top: evalBar.y }}>
          <EvalBar
            spec={s}
            orientation="horizontal"
            length={evalBar.w}
            thickness={evalBar.h}
            labelSize={shortsLayout.evalLabelSize}
          />
        </div>
        <div style={{ position: "absolute", left: board.x, top: board.y }}>
          <Board spec={s} size={board.w} />
        </div>
      </At>
    );
  }
  return <AbsoluteFill style={{ backgroundColor: tokens.color.bg }}>{body}</AbsoluteFill>;
};
