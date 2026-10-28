// Shorts (1080 x 1920) layout, approved deviation from docs/SPEC.md section 6: the 960 board of the
// spec cannot fit with captions and the eval bar above it, so the board is 864. ShortsVideo uses these.
export type Box = { x: number; y: number; w: number; h: number };

const BOARD = 864;
const SQUARE = BOARD / 8;
const COORD_GAP = 0.1; // board units, same as Board.tsx
const COORD_SIZE = 0.28;

const board: Box = { x: 48, y: 262, w: BOARD, h: BOARD }; // y 262-1126

export const shortsLayout = {
  width: 1080,
  height: 1920,
  /** Eval label is 28 px (the minimum size) so it fits its 28 px box. */
  evalLabelSize: 28,
  boxes: {
    captions: { x: 48, y: 72, w: BOARD, h: 114 }, // one line at 88 px, y 72-186
    evalLabel: { x: 828, y: 194, w: 84, h: 28 }, // 5 characters, right-aligned to the bar
    evalBar: { x: 48, y: 230, w: BOARD, h: 16 },
    board,
    // Ranks right of the board, files under it (muted text drawn by Board).
    rankLabels: { x: board.x + BOARD, y: board.y, w: Math.ceil(SQUARE * (COORD_GAP + COORD_SIZE)) + 4, h: BOARD },
    fileLabels: { x: board.x, y: board.y + BOARD, w: BOARD, h: Math.ceil(SQUARE * (COORD_GAP + COORD_SIZE)) + 4 },
    mascot: { x: 48, y: 1126, w: BOARD, h: 454 }, // y 1126-1580 (file labels sit at its top edge)
  },
} as const satisfies { width: number; height: number; evalLabelSize: number; boxes: Record<string, Box> };

/** YouTube Shorts UI covers the right 120 px and the bottom 340 px: nothing important there. */
export const youtubeShortsUi = {
  rightZoneX: shortsLayout.width - 120,
  bottomZoneY: shortsLayout.height - 340,
} as const;

// Studio (1920 x 1080) layout, docs/SPEC.md section 6: 8 px grid, 96 px outer margins, board 800 x 800
// vertically centred, eval bar 24 px wide 16 px left of it. Right column from x = 1000 to 1824.
// Vertical stack of the column: label slot, player cards, move list (9 rows of 40), then the mascot
// (right, beside the move list's lower rows) and captions (bottom, full width) which never meet.
const SB = 800;
const SB_X = 136;
const SB_Y = 140;
const SQ = SB / 8;
const COL_X = 1000;
const COL_W = 824;
const ROW = 40;
export const studioLayout = {
  width: 1920,
  height: 1080,
  moveRowHeight: ROW,
  moveRows: 9,
  boxes: {
    evalBar: { x: 96, y: SB_Y, w: 24, h: SB },
    /** Label sits above the bar (EvalBar draws it 8 px above, 40 px tall). */
    evalLabel: { x: 96, y: SB_Y - 48, w: 120, h: 40 },
    board: { x: SB_X, y: SB_Y, w: SB, h: SB },
    rankLabels: { x: SB_X + SB, y: SB_Y, w: Math.ceil(SQ * (COORD_GAP + COORD_SIZE)) + 4, h: SB },
    fileLabels: { x: SB_X, y: SB_Y + SB, w: SB, h: Math.ceil(SQ * (COORD_GAP + COORD_SIZE)) + 4 },
    /** Chapter cards and key-moment labels: top-left of the right column, two lines at most. */
    label: { x: COL_X, y: 96, w: COL_W, h: 88 },
    /** Two stacked rows of 56 px; the player at the top of the board is the top row. */
    cards: { x: COL_X, y: 200, w: COL_W, h: 120 },
    moveList: { x: COL_X, y: 336, w: 440, h: ROW * 9 },
    /** Mascot speech bubble zone, right of the move list and above the mascot. */
    bubble: { x: 1464, y: 336, w: 360, h: 264 },
    mascot: { x: 1624, y: 616, w: 200, h: 200 },
    /** Bottom aligned at the 96 px margin; two lines of 56 px captions fit. */
    captions: { x: COL_X, y: 822, w: COL_W, h: 162 },
  },
} as const satisfies { width: number; height: number; moveRowHeight: number; moveRows: number; boxes: Record<string, Box> };
