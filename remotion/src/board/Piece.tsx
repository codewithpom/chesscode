import type { FC } from "react";
import bB from "../assets/pieces/bB.svg";
import bK from "../assets/pieces/bK.svg";
import bN from "../assets/pieces/bN.svg";
import bP from "../assets/pieces/bP.svg";
import bQ from "../assets/pieces/bQ.svg";
import bR from "../assets/pieces/bR.svg";
import wB from "../assets/pieces/wB.svg";
import wK from "../assets/pieces/wK.svg";
import wN from "../assets/pieces/wN.svg";
import wP from "../assets/pieces/wP.svg";
import wQ from "../assets/pieces/wQ.svg";
import wR from "../assets/pieces/wR.svg";
import type { PieceType } from "./positions";

const SRC: Record<string, string> = { wK, wQ, wR, wB, wN, wP, bK, bQ, bR, bB, bN, bP };

/** Piece in board units; (x, y) is the top-left of its square. Scale pivots on the square center. */
export const Piece: FC<{
  type: PieceType;
  color: "w" | "b";
  x: number;
  y: number;
  opacity: number;
  scale: number;
}> = ({ type, color, x, y, opacity, scale }) => (
  <g opacity={opacity} transform={`translate(${x + 0.5} ${y + 0.5}) scale(${scale}) translate(-0.5 -0.5)`}>
    <image href={SRC[color + type.toUpperCase()]} x={0} y={0} width={1} height={1} />
  </g>
);
