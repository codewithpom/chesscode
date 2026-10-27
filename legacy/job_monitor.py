"""job_monitor.py — live web dashboard for ChessCode MCP background jobs.

Runs a FastAPI/uvicorn server (started as a daemon thread from mcp_server.py)
that gives a human a live-updating page per job_id: a stage-based progress
bar, a scrolling log tail, and a completion chime. Replaces LLM-side polling
of get_job_status — the LLM gets the monitor_url once and the human watches
the rest happen in a browser (or an iframe pointed at that URL).

Progress is estimated from the "Step N: Title" banner lines main.py already
logs (see main.py:_banner) — no changes to main.py needed.
"""

import asyncio
import base64
import io
import math
import os
import re
import struct
import wave
from html import escape as _esc

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

PORT = 8765

# Known pipeline stages in order, keyed by the "N" in "Step N: Title".
# hindi/avatar-only stages are included conditionally per job.
BASE_STAGES = [
    ("1", "Stockfish analysis"),
    ("2", "Commentary (English)"),
    ("4", "TTS — English"),
    ("5", "Board frames"),
    ("6", "Render — English"),
    ("8", "Thumbnails"),
]
HINDI_STAGES = [("3", "Commentary (Hindi)"), ("7", "Render — Hindi")]
AVATAR_STAGE = ("4.5", "Talking avatar")
UPLOAD_STAGE = ("9", "YouTube upload")

_STEP_RE = re.compile(r"Step\s+([\d.]+):\s*(.+?)\s*━*\s*$")


def _stage_list(job: dict) -> list[tuple[str, str]]:
    stages = list(BASE_STAGES)
    if job.get("hindi"):
        stages.extend(HINDI_STAGES)
    if job.get("avatar", True):
        stages.append(AVATAR_STAGE)
    if job.get("upload"):
        stages.append(UPLOAD_STAGE)
    stages.sort(key=lambda s: float(s[0]))
    return stages


def _generate_chime() -> bytes:
    """Synthesize a short two-tone chime as a WAV byte string (no deps)."""
    rate = 22050
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for freq, dur in ((880.0, 0.15), (1318.5, 0.25)):
            n = int(rate * dur)
            for i in range(n):
                t = i / rate
                fade = min(1.0, (n - i) / (rate * 0.05), i / (rate * 0.01) + 0.01)
                sample = int(32767 * 0.3 * fade * math.sin(2 * math.pi * freq * t))
                frames += struct.pack("<h", sample)
        w.writeframes(bytes(frames))
    return buf.getvalue()


_CHIME_PATH = os.path.join("assets", "chime.wav")


def _chime_data_uri() -> str:
    if not os.path.exists(_CHIME_PATH):
        os.makedirs(os.path.dirname(_CHIME_PATH), exist_ok=True)
        with open(_CHIME_PATH, "wb") as f:
            f.write(_generate_chime())
    with open(_CHIME_PATH, "rb") as f:
        data = f.read()
    return "data:audio/wav;base64," + base64.b64encode(data).decode("ascii")


def _job_progress(job: dict) -> dict:
    """Read the job's log file, return current status/stage/pct."""
    proc = job["proc"]
    rc = proc.poll()
    status = "running" if rc is None else ("done" if rc == 0 else "failed")

    stages = _stage_list(job)
    total = len(stages)
    stage_num = 0
    stage_name = "Starting…"

    log_path = job["log_path"]
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        last_step = None
        for m in _STEP_RE.finditer(text):
            last_step = m
        if last_step:
            n, title = last_step.group(1), last_step.group(2).strip()
            stage_name = title
            for idx, (sn, _) in enumerate(stages, start=1):
                if sn == n:
                    stage_num = idx
                    break
            else:
                stage_num = 1

    pct = 100 if status == "done" else int(stage_num / total * 100) if total else 0
    return {"status": status, "stage": stage_name, "stage_num": stage_num,
            "total_stages": total, "pct": pct}


def create_app(jobs: dict) -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        import json as _json
        running_count = sum(1 for j in jobs.values() if j.get("proc") and j["proc"].poll() is None)
        completed_count = sum(1 for j in jobs.values() if j.get("proc") and j["proc"].poll() is not None)
        return {
            "status": "ok",
            "timestamp": _json.dumps({"now": str(__import__("datetime").datetime.now())}, default=str),
            "total_jobs": len(jobs),
            "running_jobs": running_count,
            "completed_jobs": completed_count,
        }

    @app.get("/metrics")
    async def metrics():
        """Prometheus-compatible metrics endpoint."""
        running_count = sum(1 for j in jobs.values() if j.get("proc") and j["proc"].poll() is None)
        completed_count = sum(1 for j in jobs.values() if j.get("proc") and j["proc"].poll() is not None)
        return f"""# HELP chesscode_jobs_running Number of running jobs
# TYPE chesscode_jobs_running gauge
chesscode_jobs_running {running_count}

# HELP chesscode_jobs_total Total jobs seen
# TYPE chesscode_jobs_total counter
chesscode_jobs_total {len(jobs)}

# HELP chesscode_jobs_completed Completed jobs
# TYPE chesscode_jobs_completed counter
chesscode_jobs_completed {completed_count}
"""

    @app.get("/", response_class=HTMLResponse)
    async def index():
        rows = []
        for job_id, job in jobs.items():
            prog = _job_progress(job)
            rows.append(
                f'<tr><td><a href="/job/{_esc(job_id)}">{_esc(job_id)}</a></td>'
                f'<td>{_esc(job.get("title") or "")}</td>'
                f'<td>{_esc(prog["status"])}</td>'
                f'<td>{prog["pct"]}%</td></tr>'
            )
        body = "".join(rows) or '<tr><td colspan="4">No jobs yet</td></tr>'
        return f"""<!doctype html><html><head><title>ChessCode Jobs</title>
<style>body{{font-family:system-ui,sans-serif;background:#111;color:#eee;padding:2rem}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:.5rem;border-bottom:1px solid #333}}
a{{color:#6cf}}</style></head><body>
<h1>ChessCode Jobs</h1>
<table><tr><th>Job ID</th><th>Title</th><th>Status</th><th>Progress</th></tr>{body}</table>
</body></html>"""

    @app.get("/job/{job_id}", response_class=HTMLResponse)
    async def job_page(job_id: str):
        job = jobs.get(job_id)
        if not job:
            return HTMLResponse(f"<h1>Unknown job_id: {_esc(job_id)}</h1>", status_code=404)
        title = _esc(job.get("title") or job_id)
        chime_uri = _chime_data_uri()
        return f"""<!doctype html><html><head><title>{title}</title>
<style>
body{{font-family:system-ui,sans-serif;background:#111;color:#eee;padding:2rem;max-width:900px;margin:0 auto}}
#bar-outer{{background:#333;border-radius:6px;overflow:hidden;height:28px;margin:1rem 0}}
#bar-inner{{background:#3b82f6;height:100%;width:0%;transition:width .3s;
  display:flex;align-items:center;justify-content:center;color:#fff;font-size:.85rem;white-space:nowrap}}
#bar-inner.done{{background:#22c55e}}
#bar-inner.failed{{background:#ef4444}}
#stage{{font-size:1.1rem;margin-bottom:.25rem}}
#log{{background:#000;color:#9f9;font-family:Consolas,monospace;font-size:.8rem;
  padding:1rem;height:400px;overflow-y:auto;border-radius:6px;white-space:pre-wrap}}
</style></head><body>
<h1>{title}</h1>
<div id="stage">Connecting…</div>
<div id="bar-outer"><div id="bar-inner"></div></div>
<div id="log"></div>
<audio id="chime" src="{chime_uri}"></audio>
<script>
const barInner = document.getElementById('bar-inner');
const stageEl = document.getElementById('stage');
const logEl = document.getElementById('log');
const chime = document.getElementById('chime');
const es = new EventSource('/job/{job_id}/events');
es.addEventListener('progress', (e) => {{
  const d = JSON.parse(e.data);
  barInner.style.width = d.pct + '%';
  barInner.textContent = d.pct + '%';
  stageEl.textContent = `[${{d.status}}] Step ${{d.stage_num}}/${{d.total_stages}}: ${{d.stage}}`;
  if (d.new_log) {{
    logEl.textContent += d.new_log;
    logEl.scrollTop = logEl.scrollHeight;
  }}
}});
es.addEventListener('done', (e) => {{
  const d = JSON.parse(e.data);
  barInner.classList.add(d.status === 'failed' ? 'failed' : 'done');
  barInner.style.width = '100%';
  stageEl.textContent = d.status === 'failed' ? 'Failed' : 'Done!';
  chime.play().catch(() => {{}});
  es.close();
}});
</script>
</body></html>"""

    @app.get("/job/{job_id}/events")
    async def job_events(job_id: str):
        job = jobs.get(job_id)
        if not job:
            async def not_found():
                yield "event: done\ndata: {\"status\": \"failed\"}\n\n"
            return StreamingResponse(not_found(), media_type="text/event-stream")

        async def stream():
            offset = 0
            while True:
                prog = _job_progress(job)
                new_log = ""
                log_path = job["log_path"]
                if os.path.exists(log_path):
                    with open(log_path, encoding="utf-8", errors="replace") as f:
                        f.seek(offset)
                        new_log = f.read()
                        offset = f.tell()
                payload = {**prog, "new_log": new_log}
                import json as _json
                if prog["status"] == "running":
                    yield f"event: progress\ndata: {_json.dumps(payload)}\n\n"
                    await asyncio.sleep(1)
                else:
                    yield f"event: progress\ndata: {_json.dumps(payload)}\n\n"
                    yield f"event: done\ndata: {_json.dumps(prog)}\n\n"
                    break

        return StreamingResponse(stream(), media_type="text/event-stream")

    return app


def start_monitor_server(jobs: dict) -> None:
    """Run the monitor server (blocking) — call from a daemon thread."""
    import uvicorn
    app = create_app(jobs)
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
