import type { FC } from "react";

/** One board square in board units (1 x 1). */
export const Square: FC<{ x: number; y: number; fill: string }> = ({ x, y, fill }) => (
  <rect x={x} y={y} width={1} height={1} fill={fill} />
);
