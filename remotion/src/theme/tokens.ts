// Design tokens (docs/SPEC.md section 6). Studio palette; other templates change values, not structure.
export const color = {
  bg: "#0F1115",
  surface: "#171A21",
  hairline: "#262A33",
  text: "#ECEEF2",
  muted: "#9097A3",
  // Semantic: move quality only.
  best: "#3DD68C",
  brilliant: "#F2A93B",
  mistake: "#F5A524",
  blunder: "#E8545A",
  // Threat arrows: its own token (same value as blunder for now) so they can diverge.
  threat: "#E8545A",
  // Black share of the eval bar: visibly lighter than the page so the bar reads as a bar.
  evalBlack: "#3A3F4A",
} as const;

export const font = {
  sans: '"IBM Plex Sans", sans-serif',
  condensed: '"IBM Plex Sans Condensed", "IBM Plex Sans", sans-serif',
  mono: '"IBM Plex Mono", monospace',
  devanagari: '"IBM Plex Sans Devanagari", "IBM Plex Sans", sans-serif',
} as const;

// Nothing under 28 px at 1080p (PRODUCT.md accessibility).
export const size = { min: 28, label: 28, body: 32, caption: 56, evalLabel: 40, title: 72 } as const;

/** 8 px grid. */
export const space = (n: number): number => n * 8;

const channel = (v: number): number => {
  const c = v / 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
};
const luminance = (hex: string): number => {
  const n = parseInt(hex.replace("#", ""), 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
};

/** WCAG 2.x contrast ratio of two #rrggbb colors. */
export const contrast = (a: string, b: string): number => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

export const tokens = { color, space, font, size } as const;
