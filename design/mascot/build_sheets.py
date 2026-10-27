"""Builds the three mascot concept sheets (SVG) and renders them to PNG.

Each character is drawn from the same named layers (base, body, head, eye-l/r,
brow-l/r, mouth, arm-l/r, prop) driven by a small Face dict, mirroring the
PoseState the M4 rig will use. Usage: python design/mascot/build_sheets.py
"""
import base64
import math
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHROME = Path.home() / "AppData/Local/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-win64/chrome-headless-shell.exe"

BG, SURFACE, HAIRLINE, TEXT, MUTED = "#0F1115", "#171A21", "#262A33", "#ECEEF2", "#9097A3"
LIGHT = "#E8E2D4"
SANS = "'IBM Plex Sans', 'IBM Plex Sans Devanagari', sans-serif"
STROKE = 4


@dataclass
class Palette:
    body: str
    shade: str
    ink: str
    accent: str


SILHOUETTE = Palette("#000", "#000", "#000", "#000")


@dataclass
class Face:
    open: float = 1.0          # upper lid: 1 open, 0 shut
    px: float = 0.0            # pupil offset, -1..1
    py: float = 0.0
    scale: float = 1.0         # eye size
    pupil: float = 1.0         # pupil size
    brow: float = 0.0          # brow angle, + = angry (inner end down), - = worried
    brow_y: float = 0.0        # brow height, + = raised
    mouth: str = "smile"
    arms: str = "none"
    shut: str = ""             # "", "down" (calm shut), "squeeze"
    sweat: bool = False
    level: float = 0.5         # engine bot: eval-bar mouth fill
    lean: float = 0.0          # body rotation in degrees
    brow_r_y: float = 0.0      # extra raise of the right brow only (skeptical look)
    pop: float = 0.0           # head prop lift in px (crown pops off when shocked)


def attrs(**kw) -> str:
    return " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())


# ---------- shared parts ----------

def eye(cx: float, cy: float, f: Face, p: Palette, uid: str, rx=18, ry=24) -> str:
    rx, ry = rx * f.scale, ry * f.scale
    if f.shut:
        bend = 7 if f.shut == "down" else -3
        d = f"M{cx-rx},{cy} Q{cx},{cy+bend} {cx+rx},{cy}"
        extra = ""
        if f.shut == "squeeze":
            d = f"M{cx-rx},{cy-6} L{cx+rx*0.5},{cy} L{cx-rx},{cy+6}" if uid.endswith("l") else f"M{cx+rx},{cy-6} L{cx-rx*0.5},{cy} L{cx+rx},{cy+6}"
        return f'<g id="eye-{uid}"><path d="{d}" fill="none" stroke="{p.ink}" stroke-width="{STROKE+1}" stroke-linecap="round" stroke-linejoin="round"/>{extra}</g>'
    clip = f"clip-{uid}"
    pr = 8.5 * f.pupil * f.scale
    pxx, pyy = cx + f.px * (rx - pr - 2), cy + f.py * (ry - pr - 2)
    lid_h = 2 * ry * (1 - f.open)
    lid = ""
    if lid_h > 0.5:
        top = cy - ry
        lid = (f'<rect x="{cx-rx-2}" y="{top-2}" width="{2*rx+4}" height="{lid_h+2}" fill="{p.body}"/>'
               f'<line x1="{cx-rx}" y1="{top+lid_h}" x2="{cx+rx}" y2="{top+lid_h}" stroke="{p.ink}" stroke-width="{STROKE-0.5}"/>')
    return (f'<g id="eye-{uid}"><clipPath id="{clip}"><ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/></clipPath>'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{p.body}"/>'
            f'<g clip-path="url(#{clip})"><circle cx="{pxx}" cy="{pyy}" r="{pr}" fill="{p.ink}"/>'
            f'<circle cx="{pxx+pr*0.35}" cy="{pyy-pr*0.4}" r="{max(1.6, pr*0.28)}" fill="{p.body}"/>{lid}</g>'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="{p.ink}" stroke-width="{STROKE-0.5}"/></g>')


def brows(lx: float, rx_: float, y: float, f: Face, p: Palette, color: str | None = None, w=20) -> str:
    c = color or p.ink
    y = y - max(-1.0, min(1.0, f.brow_y)) * 9  # capped so brows never hit the head prop
    out = []
    for side, x in (("l", lx), ("r", rx_)):
        a = f.brow * 18 * (1 if side == "l" else -1)  # inner ends tilt together
        by = y - (f.brow_r_y * 8 if side == "r" else 0)
        out.append(f'<line id="brow-{side}" x1="{x-w/2}" y1="{by}" x2="{x+w/2}" y2="{by}" stroke="{c}" stroke-width="{STROKE+1.5}" '
                   f'stroke-linecap="round" transform="rotate({a} {x} {by})"/>')
    return "".join(out)


def mouth(cx: float, cy: float, kind: str, p: Palette) -> str:
    s = f'stroke="{p.ink}" stroke-width="{STROKE}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    shapes = {
        "smile": f'<path d="M{cx-11},{cy-2} Q{cx},{cy+8} {cx+11},{cy-2}" {s}/>',
        "grin": f'<path d="M{cx-14},{cy-4} Q{cx},{cy+12} {cx+14},{cy-4} Z" fill="{p.ink}" stroke="{p.ink}" stroke-width="{STROKE-1}" stroke-linejoin="round"/>',
        "flat": f'<path d="M{cx-6},{cy+1} L{cx+10},{cy-1}" {s}/>',
        "frown": f'<path d="M{cx-10},{cy+4} Q{cx},{cy-5} {cx+10},{cy+4}" {s}/>',
        "o": f'<ellipse cx="{cx}" cy="{cy+3}" rx="9" ry="12" fill="{p.ink}"/>',
        "smirk": f'<path d="M{cx-9},{cy+1} Q{cx+2},{cy+5} {cx+12},{cy-4}" {s}/>',
        "wavy": f'<path d="M{cx-13},{cy+2} q4,-5 8,0 t8,0 t8,0" {s}/>',
    }
    return f'<g id="mouth">{shapes[kind]}</g>'


def arm(points: list[tuple[float, float]], p: Palette, side: str, hand_r=13) -> str:
    (x0, y0), (x1, y1), (x2, y2) = points
    d = f"M{x0},{y0} L{x1},{y1} L{x2},{y2}"  # shoulder, elbow, hand: two segments per spec section 7
    return (f'<g id="arm-{side}"><path d="{d}" fill="none" stroke="{p.ink}" stroke-width="{STROKE+11}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{p.body}" stroke-width="{STROKE+4}" stroke-linecap="round" stroke-linejoin="round"/>'
            + hand(x2, y2, hand_r, p) + '</g>')


def hand(x: float, y: float, r: float, p: Palette) -> str:
    if r < 20:
        sk = f'fill="{p.body}" stroke="{p.ink}" stroke-width="{STROKE-0.5}"'
        return (f'<circle cx="{x}" cy="{y-r*0.75}" r="{r*0.42}" {sk}/>'  # thumb
                f'<ellipse cx="{x}" cy="{y}" rx="{r*0.8}" ry="{r}" {sk}/>')
    # open palm laid over the face: a wide mitten with finger creases, so it never reads as a monocle
    creases = "".join(f'<line x1="{x-r*0.95}" y1="{y+dy}" x2="{x-r*0.35}" y2="{y+dy}" stroke="{p.ink}" stroke-width="{STROKE-1}" stroke-linecap="round"/>'
                      for dy in (-6, 1, 8))
    return (f'<ellipse cx="{x}" cy="{y}" rx="{r*1.3}" ry="{r*0.85}" transform="rotate(-12 {x} {y})" fill="{p.body}" '
            f'stroke="{p.ink}" stroke-width="{STROKE-0.5}"/>' + creases)


def sweat(x: float, y: float, p: Palette, k: float = 1.5) -> str:
    return (f'<path d="M{x},{y} C{x+9*k},{y+12*k} {x+10*k},{y+20*k} {x},{y+22*k} C{x-10*k},{y+20*k} {x-9*k},{y+12*k} {x},{y} Z" '
            f'fill="{p.body}" stroke="{p.ink}" stroke-width="{STROKE-1}" stroke-linejoin="round"/>')


def pawn_base(p: Palette) -> str:
    return (f'<path id="base" d="M28,226 Q28,207 62,205 L178,205 Q212,207 212,226 Q212,247 120,249 Q28,247 28,226 Z" '
            f'fill="{p.shade}" stroke="{p.ink}" stroke-width="{STROKE}" stroke-linejoin="round"/>')


# ---------- characters (local box 240 x 260, ground at y = 249) ----------

PAWN_ARMS = {
    "none": [],
    "facepalm": [("r", [(150, 156), (212, 150), (138, 90)])],
    "clap": [("l", [(92, 154), (56, 196), (106, 172)]), ("r", [(148, 154), (184, 196), (134, 172)])],
    "wave": [("r", [(150, 156), (198, 140), (204, 92)])],
}


def pyaada(f: Face, p: Palette) -> str:
    ink = f'stroke="{p.ink}" stroke-width="{STROKE}" stroke-linejoin="round"'
    arms_back = ""
    arms_front = "".join(arm(pts, p, s, hand_r=22 if f.arms == "facepalm" else 13) for s, pts in PAWN_ARMS[f.arms])
    face = (eye(96, 90, f, p, "l") + eye(144, 90, f, p, "r") + brows(96, 144, 54, f, p) + mouth(120, 126, f.mouth, p))
    crown = (f'<g id="prop-head" transform="translate({112 + f.pop * 0.3},{8 - f.pop}) rotate({13 + f.pop * 0.8})"><path d="M0,32 L0,9 L13,19 L26,0 L39,19 L52,9 L52,32 Z" '
             f'fill="{p.accent}" {ink}/></g>')
    return (f'<g transform="rotate({f.lean} 120 249)">'
            f'<path id="body" d="M88,138 C86,170 62,190 46,210 L194,210 C178,190 154,170 152,138 Z" fill="{p.body}" {ink}/>'
            + pawn_base(p) +
            f'<ellipse id="collar" cx="120" cy="140" rx="45" ry="11" fill="{p.body}" {ink}/>'
            f'<circle id="head" cx="120" cy="84" r="58" fill="{p.body}" {ink}/>'
            + crown + face + (sweat(166, 42, p) if f.sweat else "") + arms_back + arms_front + "</g>")


KNIGHT_ARMS = {
    "none": [],
    "facepalm": [("r", [(150, 170), (214, 160), (146, 84)])],
    "clap": [("l", [(70, 166), (44, 200), (104, 186)]), ("r", [(156, 166), (190, 200), (132, 186)])],
}


def knight(f: Face, p: Palette) -> str:
    ink = f'stroke="{p.ink}" stroke-width="{STROKE}" stroke-linejoin="round"'
    head = ("M64,207 C58,170 54,130 66,96 C74,72 82,52 90,38 L96,14 C104,24 110,32 114,42 "
            "C140,46 170,58 190,80 C204,96 206,116 194,126 C184,134 166,132 152,130 "
            "C150,150 160,180 178,207 Z")
    mane = ("M66,96 C74,72 82,52 90,38 L98,46 L84,58 L94,66 L78,80 L90,88 L72,104 L84,112 L64,126 C60,116 62,104 66,96 Z")
    face = (eye(122, 80, replace(f, scale=f.scale * 0.92), p, "l") + eye(158, 86, replace(f, scale=f.scale * 0.85), p, "r")
            + brows(121, 157, 58, f, p, w=18) + mouth(184, 112, f.mouth, p)
            + f'<circle cx="196" cy="100" r="3.2" fill="{p.ink}"/>')
    arms = "".join(arm(pts, p, s, hand_r=22 if f.arms == "facepalm" else 13) for s, pts in KNIGHT_ARMS.get(f.arms, []))
    return (f'<g transform="rotate({f.lean} 120 249)">' + f'<path id="body" d="{head}" fill="{p.body}" {ink}/>'
            + f'<path id="prop-head" d="{mane}" fill="{p.accent}" {ink}/>' + pawn_base(p) + face
            + (sweat(170, 40, p) if f.sweat else "") + arms + "</g>")


BOT_ARMS = {
    "none": [],
    "facepalm": [("r", [(192, 150), (236, 140), (146, 106)])],
    "clap": [("l", [(50, 150), (24, 200), (106, 188)]), ("r", [(190, 150), (216, 200), (134, 188)])],
}


def engine_bot(f: Face, p: Palette) -> str:
    ink = f'stroke="{p.ink}" stroke-width="{STROKE}" stroke-linejoin="round"'
    w, h = 18 * f.scale, 24 * f.scale * (f.open if not f.shut else 0.18)
    eyes = ""
    for side, cx in (("l", 98), ("r", 142)):
        ex, ey = cx + f.px * 8, 108 + f.py * 6
        eyes += f'<rect id="eye-{side}" x="{ex-w/2}" y="{ey-h/2}" width="{w}" height="{max(h, 4)}" rx="{min(5, w/3)}" fill="{p.body}"/>'
    fill_w = 76 * max(0.0, min(1.0, f.level))
    bar = (f'<g id="mouth"><rect x="82" y="141" width="76" height="12" rx="6" fill="none" stroke="{p.body}" stroke-width="2.5"/>'
           f'<rect x="82" y="141" width="{fill_w}" height="12" rx="6" fill="{p.accent}"/></g>')
    arms = "".join(arm(pts, p, s, hand_r=22 if f.arms == "facepalm" else 13) for s, pts in BOT_ARMS.get(f.arms, []))
    feet = "".join(f'<rect x="{x}" y="200" width="34" height="18" rx="8" fill="{p.shade}" {ink}/>' for x in (70, 136))
    return (f'<g transform="rotate({f.lean} 120 249)">' + feet
            + f'<line x1="120" y1="62" x2="120" y2="34" stroke="{p.ink}" stroke-width="{STROKE+1}" stroke-linecap="round"/>'
            + f'<circle id="prop-head" cx="120" cy="28" r="9" fill="{p.accent}" {ink}/>'
            + f'<rect id="body" x="48" y="60" width="144" height="146" rx="24" fill="{p.body}" {ink}/>'
            + f'<rect id="head" x="64" y="76" width="112" height="90" rx="14" fill="{p.ink}"/>'
            + eyes + brows(98, 142, 90, f, p, color=p.body, w=16) + bar
            + (sweat(196, 54, p) if f.sweat else "") + arms + "</g>")


# ---------- concepts ----------

@dataclass
class Concept:
    slug: str
    name: str
    native: str
    line: str
    draw: object
    palette: Palette
    swatch_names: tuple
    expressions: list = field(default_factory=list)
    note: str = ""
    view: str = "Front, neutral"


EXPR = ["neutral", "side_eye", "facepalm", "shocked", "slow_clap", "sweating"]
PAWN_FACES = {
    "neutral": Face(mouth="smile"),
    "side_eye": Face(open=0.5, px=1.0, brow=0.6, brow_y=-0.4, brow_r_y=1.2, mouth="flat"),
    "facepalm": Face(shut="down", brow=-0.8, brow_y=0.4, mouth="frown", arms="facepalm", lean=-4),
    "shocked": Face(scale=1.18, pupil=0.55, brow_y=1.0, mouth="o", lean=3, pop=14),
    "slow_clap": Face(open=0.7, py=-0.4, brow=-0.3, brow_y=0.4, mouth="smirk", arms="clap"),
    "sweating": Face(pupil=0.7, px=-0.5, brow=-0.9, brow_y=0.5, mouth="wavy", sweat=True),
}
BOT_FACES = {**PAWN_FACES,
             "neutral": replace(PAWN_FACES["neutral"], level=0.5),
             "side_eye": replace(PAWN_FACES["side_eye"], level=0.38),
             "facepalm": replace(PAWN_FACES["facepalm"], level=0.06),
             "shocked": replace(PAWN_FACES["shocked"], level=1.0, open=1.0),
             "slow_clap": replace(PAWN_FACES["slow_clap"], level=0.82),
             "sweating": replace(PAWN_FACES["sweating"], level=0.2)}

CONCEPTS = [
    Concept("pyaada", "Pyaada", "प्यादा", "A pawn who is sure he deserves to be promoted. He made the crown himself.",
            pyaada, Palette("#F1E7D3", "#C8B391", "#1D2026", "#6FA8DC"), ("body", "shade", "ink", "paper crown"),
            note="Running gag: wants promotion, distrusts the h-pawn, thinks every rook lift is too aggressive."),
    Concept("knight", "Ghoda", "घोड़ा", "A tiny knight who refuses to move in anything but an L, even across the screen.",
            knight, Palette("#F1E7D3", "#C8B391", "#1D2026", "#4FB6C8"), ("body", "shade", "ink", "mane"),
            note="Entrances and exits are two squares then one: the L-move is the walk cycle.", view="Three-quarter, neutral"),
    Concept("engine-bot", "Bot", "बॉट", "A small engine whose mouth is an eval bar. It fills when it is happy and drains when you blunder.",
            engine_bot, Palette("#E4E8EC", "#A9B2BC", "#1D2026", "#A98BE0"), ("body", "shade", "ink", "eval fill"),
            note="The mouth is the eval bar: mood = fill level, so the face doubles as a second eval display."),
]

# ---------- sheet ----------

W, H, M = 2400, 1600, 96


def text(x, y, s, size, color=TEXT, weight=400, anchor="start") -> str:
    return (f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}">{s}</text>')


def place(c: Concept, f: Face, p: Palette, x: float, y: float, height: float) -> str:
    s = height / 250
    return f'<g transform="translate({x - 120 * s},{y - 249 * s}) scale({s})">{c.draw(f, p)}</g>'


def panel(x, y, w, h, fill=SURFACE) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{HAIRLINE}" stroke-width="2"/>'


def sheet(c: Concept) -> str:
    faces = BOT_FACES if c.slug == "engine-bot" else PAWN_FACES
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{BG}"/>',
           text(M, 136, f'{c.name} <tspan font-family="IBM Plex Sans Devanagari">{c.native}</tspan>', 72, weight=600),
           text(M, 190, c.line, 32, MUTED)]
    # hero
    hx, hy, hw, hh = M, 240, 760, 940
    out += [panel(hx, hy, hw, hh), place(c, faces["neutral"], c.palette, hx + hw / 2, hy + hh - 110, 700),
            text(hx + 32, hy + hh - 36, c.view, 28, MUTED)]
    # expressions
    cw, ch, gap, ex0 = 448, 458, 24, 904
    for i, name in enumerate(EXPR):
        cx, cy = ex0 + (i % 3) * (cw + gap), 240 + (i // 3) * (ch + gap)
        out += [panel(cx, cy, cw, ch), place(c, faces[name], c.palette, cx + cw / 2, cy + ch - 76, 300),
                text(cx + 28, cy + ch - 26, name.replace("_", " ").capitalize(), 28, MUTED)]
    # silhouettes on light at 120 and 240 px; colour at real Studio size (200 px) on the video background
    sy, bh = 1204, 300
    out += [panel(M, sy, 470, bh, LIGHT),
            place(c, faces["neutral"], SILHOUETTE, M + 90, sy + 196, 120),
            place(c, faces["neutral"], SILHOUETTE, M + 320, sy + 258, 240),
            text(M + 90, sy + 254, "120 px", 28, "#3A3F47", anchor="middle"),
            text(M + 440, sy + 286, "240 px", 28, "#3A3F47", anchor="end"),
            panel(M + 486, sy, 274, bh, BG),
            place(c, faces["neutral"], c.palette, M + 486 + 137, sy + 230, 200),
            text(M + 486 + 137, sy + 282, "200 px", 28, MUTED, anchor="middle")]
    # palette + note
    px0 = ex0
    out.append(panel(px0, sy, 1392, bh))
    for i, (hexv, label) in enumerate(zip((c.palette.body, c.palette.shade, c.palette.ink, c.palette.accent), c.swatch_names)):
        x = px0 + 32 + i * 196
        out += [f'<rect x="{x}" y="{sy + 32}" width="160" height="120" rx="10" fill="{hexv}" stroke="#4A505B" stroke-width="2"/>',
                text(x, sy + 192, label.capitalize(), 28),
                text(x, sy + 232, hexv.upper(), 28, MUTED)]
    note_x = px0 + 32 + 4 * 196 + 16
    for j, line in enumerate(wrap(c.note, 34)):
        out.append(text(note_x, sy + 64 + j * 40, line, 28, MUTED))
    out.append("</svg>")
    return "\n".join(out)


def wrap(s: str, n: int) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur]


def font_css() -> str:
    faces = [("IBM Plex Sans", 400, "IBMPlexSans-Regular"), ("IBM Plex Sans", 600, "IBMPlexSans-SemiBold"),
             ("IBM Plex Sans Devanagari", 400, "IBMPlexSansDevanagari-Regular"),
             ("IBM Plex Sans Devanagari", 600, "IBMPlexSansDevanagari-SemiBold")]
    return "".join(
        f"@font-face{{font-family:'{fam}';font-weight:{wt};src:url(data:font/woff2;base64,"
        f"{base64.b64encode((HERE / 'fonts' / (f + '.woff2')).read_bytes()).decode()}) format('woff2');}}"
        for fam, wt, f in faces)


def render_png(svg: str, out: Path, w=W, h=H) -> None:
    html = HERE / f".{out.stem}.render.html"
    html.write_text(f"<!doctype html><meta charset=utf-8><style>{font_css()}html,body{{margin:0;background:{BG}}}</style>{svg}",
                    encoding="utf8")
    subprocess.run([str(CHROME), "--headless", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}",
                    "--virtual-time-budget=3000", f"--screenshot={out}", html.as_uri()],
                   check=True, capture_output=True)
    html.unlink()


def main() -> None:
    for c in CONCEPTS:
        svg = sheet(c)
        (HERE / f"{c.slug}.svg").write_text(svg, encoding="utf8")
        render_png(svg, HERE / f"{c.slug}.png")
        print("wrote", c.slug)


if __name__ == "__main__":
    main()
