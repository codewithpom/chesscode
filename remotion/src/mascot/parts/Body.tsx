import { INK, P } from "./kit";

export const Body: React.FC = () => (
  <>
    <path id="body" d="M88,138 C86,170 62,190 46,210 L194,210 C178,190 154,170 152,138 Z" fill={P.body} {...INK} />
    <ellipse id="collar" cx={120} cy={140} rx={45} ry={11} fill={P.body} {...INK} />
  </>
);

export const Head: React.FC = () => <circle id="head" cx={120} cy={84} r={58} fill={P.body} {...INK} />;
