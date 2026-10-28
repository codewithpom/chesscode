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
