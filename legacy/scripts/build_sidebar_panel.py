"""Composite the mascot art asset into the 308x1080 sidebar decorative panel.

Idempotent: always rebuilds from assets/sidebar/mascot.png (the extracted mascot,
no baked-in text) rather than the previous panel, so it can be re-run safely to
retune spacing/fonts without needing the original ChatGPT-generated source art.
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASCOT = os.path.join(ROOT, "assets", "sidebar", "mascot.png")
OUT = os.path.join(ROOT, "assets", "sidebar", "decorative_panel.png")
ACCENT = (245, 166, 35)
BG = (10, 10, 20)
CARD = (20, 20, 34)
CARD_BORDER = (48, 48, 68)

W, H = 308, 1080
PAD = 10

panel = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(panel)

x0, x1 = PAD, W - PAD
draw.rounded_rectangle([x0, 8, x1, H - 8], radius=16, fill=CARD, outline=CARD_BORDER, width=1)

mascot = Image.open(MASCOT).convert("RGB")
mw = W - 2 * PAD - 40
scale = mw / mascot.width
mh = round(mascot.height * scale)
mascot = mascot.resize((mw, mh), Image.LANCZOS)
mascot_y0 = 40
panel.paste(mascot, ((W - mw) // 2, mascot_y0))
mascot_bottom = mascot_y0 + mh

font_title = ImageFont.load_default(size=44)
font_row = ImageFont.load_default(size=19)

title_y = mascot_bottom + 16
bbox = draw.textbbox((0, 0), "ChessCode", font=font_title)
tw = bbox[2] - bbox[0]
draw.text(((W - tw) // 2, title_y), "ChessCode", fill=(255, 255, 255), font=font_title)

line_y = title_y + 68
draw.line([(x0 + 30, line_y), (x1 - 30, line_y)], fill=ACCENT, width=2)

rows = ["Learn Chess", "Think Deeper", "Play Better"]
row_h = 44
content_bottom = H - 8 - 20
remaining = content_bottom - (line_y + 24)
gap = remaining // len(rows)
row_y = line_y + 24 + (gap - row_h) // 2
for label in rows:
    pill_x0, pill_x1 = x0 + 24, x1 - 24
    draw.rounded_rectangle([pill_x0, row_y, pill_x1, row_y + row_h], radius=22,
                           fill=(22, 18, 10), outline=(80, 60, 20), width=1)
    draw.ellipse([pill_x0 + 12, row_y + 12, pill_x0 + 32, row_y + 32], fill=ACCENT)
    draw.text((pill_x0 + 46, row_y + 12), label, fill=(225, 225, 232), font=font_row)
    row_y += gap

panel.save(OUT)
print(f"saved {OUT} ({panel.size})")
