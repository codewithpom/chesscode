// Palette and stroke exactly as the approved sheet (design/mascot/build_sheets.py): body, shade, ink, one accent.
export const P = { body: "#F1E7D3", shade: "#C8B391", ink: "#1D2026", accent: "#6FA8DC" } as const;
export const STROKE = 4;
/** Rounds so equal states print equal markup. */
export const n = (v: number): number => Math.round(v * 1000) / 1000;
export const INK = { stroke: P.ink, strokeWidth: STROKE, strokeLinejoin: "round" } as const;
