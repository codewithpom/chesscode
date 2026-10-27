"""token_setup.py — Tiny local page to save API keys into the project's .env.

Run:  python token_setup.py     then open  http://127.0.0.1:8777

Stdlib only (no deps). Binds to localhost only — nothing is exposed to the
network. Submitted values are upserted into ./.env (existing lines/comments are
preserved; a matching KEY= line is updated in place, otherwise appended). Blank
fields are ignored, so you can set just the Lichess token and leave the rest.
config.py auto-loads .env, so a new render picks the values up immediately.
"""

import html
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

HOST, PORT = "127.0.0.1", 8777
ENV_PATH = Path(__file__).parent / ".env"

# Fields shown on the page. (env key, label, help, is_secret)
FIELDS = [
    ("LICHESS_TOKEN",      "Lichess API token",
     "lichess.org → Preferences → API access tokens (no scopes needed). Raises Opening-Explorer rate limits.", True),
    ("ANTHROPIC_API_KEY",  "Anthropic (Claude) API key",
     "Optional — enables LLM-written commentary.", True),
    ("ELEVENLABS_API_KEY", "ElevenLabs API key",
     "Optional — premium TTS voice (Kokoro is the free default).", True),
    ("YOUTUBE_API_KEY",    "YouTube Data API key",
     "Optional — powers the channel-stats ribbon.", True),
    ("YOUTUBE_CHANNEL_ID", "YouTube channel ID",
     "Optional — your channel ID for the stats ribbon.", False),
]


def _read_env_lines():
    if ENV_PATH.exists():
        return ENV_PATH.read_text(encoding="utf-8").splitlines()
    return []


def _current_values():
    """Map of key -> raw value currently set in .env (non-commented)."""
    vals = {}
    for line in _read_env_lines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


def _upsert_env(updates: dict):
    """Update-or-append each key in .env, preserving other lines/comments."""
    lines = _read_env_lines()
    remaining = dict(updates)
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k = s.partition("=")[0].strip()
        if k in remaining:
            lines[i] = f"{k}={remaining.pop(k)}"
    for k, v in remaining.items():
        lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mask(v: str) -> str:
    if not v:
        return ""
    if len(v) <= 6:
        return "•" * len(v)
    return v[:3] + "•" * (len(v) - 6) + v[-3:]


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ChessCode · API keys</title><style>
  :root {{ --bg:#0c0c16; --panel:#161624; --border:#2d2d3e; --accent:#f5a623;
           --text:#e8e8ee; --muted:#9e9eb2; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
    font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif; }}
  .wrap {{ max-width:640px; margin:40px auto; padding:0 20px; }}
  h1 {{ font-size:26px; margin:0 0 4px; }}
  h1 span {{ color:var(--accent); }}
  p.sub {{ color:var(--muted); margin:0 0 24px; }}
  .card {{ background:var(--panel); border:1px solid var(--border);
    border-radius:14px; padding:22px; }}
  .field {{ margin-bottom:20px; }}
  label {{ display:block; font-weight:600; margin-bottom:4px; }}
  .hint {{ color:var(--muted); font-size:13px; margin-bottom:8px; }}
  .cur {{ color:var(--accent); font-size:12px; }}
  input {{ width:100%; padding:11px 13px; border-radius:9px;
    border:1px solid var(--border); background:#0f0f1c; color:var(--text);
    font-size:14px; font-family:ui-monospace,monospace; }}
  input:focus {{ outline:none; border-color:var(--accent); }}
  button {{ background:var(--accent); color:#1a1200; border:none;
    padding:12px 22px; border-radius:9px; font-size:15px; font-weight:700;
    cursor:pointer; }}
  button:hover {{ filter:brightness(1.07); }}
  .ok {{ background:#16351f; border:1px solid #2f7d3f; color:#9fe0b0;
    padding:12px 14px; border-radius:9px; margin-bottom:20px; }}
  .note {{ color:var(--muted); font-size:12px; margin-top:18px; }}
</style></head><body><div class="wrap">
  <h1>Chess<span>Code</span> · API keys</h1>
  <p class="sub">Saved to <code>.env</code> on this machine only. Blank fields are left unchanged.</p>
  {banner}
  <form method="POST" action="/save"><div class="card">
    {fields}
    <button type="submit">Save to .env</button>
  </div></form>
  <p class="note">Local only (127.0.0.1). Nothing leaves your computer. Close this
  tab and stop the script (Ctrl+C) when done.</p>
</div></body></html>"""


def _render(banner=""):
    blocks = []
    cur = _current_values()
    for key, label, hint, secret in FIELDS:
        set_note = (f'<div class="cur">currently set: {html.escape(_mask(cur[key]))}</div>'
                    if cur.get(key) else "")
        ph = "leave blank to keep current" if cur.get(key) else "not set"
        blocks.append(f"""<div class="field">
          <label for="{key}">{html.escape(label)}</label>
          <div class="hint">{html.escape(hint)}</div>
          {set_note}
          <input type="{'password' if secret else 'text'}" id="{key}" name="{key}"
                 placeholder="{ph}" autocomplete="off" spellcheck="false">
        </div>""")
    return PAGE.format(banner=banner, fields="\n".join(blocks))


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, code=200):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(_render())
        else:
            self._send("<p>Not found</p>", 404)

    def do_POST(self):
        if self.path != "/save":
            self._send("<p>Not found</p>", 404)
            return
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        updates = {}
        for key, *_ in FIELDS:
            v = (form.get(key, [""])[0] or "").strip()
            if v:
                updates[key] = v
        if updates:
            _upsert_env(updates)
            saved = ", ".join(sorted(updates))
            banner = f'<div class="ok">✓ Saved {html.escape(saved)} to .env. Re-run a render to use it.</div>'
        else:
            banner = '<div class="ok">Nothing submitted — no changes.</div>'
        self._send(_render(banner))

    def log_message(self, *a):
        pass  # quiet


def main():
    httpd = HTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"ChessCode key setup → {url}")
    print(f"Writing to: {ENV_PATH}")
    print("Ctrl+C to stop.")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
