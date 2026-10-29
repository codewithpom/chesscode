"""data/upload_log.csv: one row per state change, last row per video wins; `chesscode ledger check` compares it with YouTube."""
import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .context import REPO_ROOT

COLUMNS = ["video_id", "status", "youtube_id", "publish_at", "title", "qa_passed", "render_seconds", "batch_id", "updated_at"]
STATUSES = {"scheduled", "failed_qa", "failed_upload", "deferred", "rendered"}
LEDGER = REPO_ROOT / "data" / "upload_log.csv"


def read_ledger(path: Path) -> dict[str, dict]:
    path = Path(path)
    if not path.is_file(): return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {r["video_id"]: r for r in csv.DictReader(f)}


def append(path: Path, row: dict) -> None:
    missing = [c for c in COLUMNS if c not in row]
    if missing: raise ValueError(f"ledger row for {row.get('video_id')} lacks column(s): {', '.join(missing)}")
    if row["status"] not in STATUSES: raise ValueError(f"ledger status {row['status']!r} is not one of {sorted(STATUSES)}")
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.is_file() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLUMNS, extrasaction="ignore", lineterminator="\n")
        if new: w.writeheader()
        w.writerow(row)


def youtube_uploads(client) -> dict[str, dict]:
    """ccid -> {youtube_id, publish_at, privacy} for every video in the channel's uploads playlist."""
    playlist = client.channels().list(part="contentDetails", mine=True).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    found, token = {}, None
    while True:
        page = client.playlistItems().list(part="snippet", playlistId=playlist, maxResults=50, pageToken=token).execute()
        for item in page.get("items", []):
            m = re.search(r"^ccid: (\S+)\s*$", item["snippet"].get("description", ""), re.M)
            if m: found[m[1]] = {"youtube_id": item["snippet"]["resourceId"]["videoId"]}
        token = page.get("nextPageToken")
        if not token: break
    by_yt = {v["youtube_id"]: v for v in found.values()}
    ids = list(by_yt)
    for i in range(0, len(ids), 50):
        for v in client.videos().list(part="status", id=",".join(ids[i:i + 50])).execute().get("items", []):
            by_yt[v["id"]].update(publish_at=v["status"].get("publishAt", ""), privacy=v["status"].get("privacyStatus", ""))
    return found


def _utc(text: str) -> datetime | None:
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def check(client, path: Path) -> list[str]:
    rows = read_ledger(path); live = youtube_uploads(client); problems = []
    for vid, r in rows.items():
        if r["status"] != "scheduled": continue
        if vid not in live: problems.append(f"{vid}: missing in Studio (ledger says scheduled as {r['youtube_id']})")
        elif _utc(live[vid].get("publish_at", "")) != _utc(r["publish_at"]):
            problems.append(f"{vid}: different publishAt (ledger {r['publish_at']}, Studio {live[vid].get('publish_at') or 'none'})")
    for vid in live:
        if vid not in rows: problems.append(f"{vid}: missing in ledger (Studio has {live[vid]['youtube_id']})")
    return problems


def collect(artifacts: Path, ledger_path: Path, review_dir: Path, run_url: str) -> str:
    """Append every downloaded result.json to the ledger, write docs/review/<batch_id>.md, return the run-summary table."""
    results = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(artifacts).glob("*/result.json"))]
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    head = "| video | status | publish_at | QA | render min |\n| --- | --- | --- | --- | --- |"
    lines, by_batch = [], {}
    for r in results:
        if not r.get("batch_id"): raise ValueError(f"{r['video_id']}: result.json has no batch_id")
        append(ledger_path, {"video_id": r["video_id"], "status": r["status"], "youtube_id": r["youtube_id"], "publish_at": r["publish_at"], "title": r["title"],
                             "qa_passed": str(r["qa_passed"]).lower(), "render_seconds": r["render_seconds"], "batch_id": r["batch_id"], "updated_at": now})
        note = " (needs repair)" if r.get("needs_repair") else f" ({r['error']})" if r.get("error") else ""
        lines.append(f"| {r['video_id']} | {r['status']}{note} | {r['publish_at']} | {'pass' if r['qa_passed'] else 'FAIL'} | {r['render_seconds'] / 60:.1f} |")
        by_batch.setdefault(r["batch_id"], []).append((r, note))
    for batch_id, rows in by_batch.items():
        Path(review_dir).mkdir(parents=True, exist_ok=True)
        body = [f"# Batch {batch_id}", "", f"Thumbnails and contact sheets: [workflow run]({run_url}) (artifacts `result-<video>`).", "",
                "| video | title | publish_at | status | QA |", "| --- | --- | --- | --- | --- |"]
        body += [f"| {r['video_id']} | {r['title'].replace('|', '/')} | {r['publish_at']} | {r['status']}{n} | {'pass' if r['qa_passed'] else 'FAIL'} |" for r, n in rows]
        (Path(review_dir) / f"{batch_id}.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    return head + "\n" + "\n".join(lines) + "\n"


def main(args: argparse.Namespace) -> int:
    if args.action == "collect":
        print(collect(Path(args.artifacts), LEDGER, REPO_ROOT / "docs" / "review", args.run_url), end="")
        return 0
    from . import auth
    problems = check(auth.youtube_client(), LEDGER)
    for p in problems: print(p)
    print(f"ledger check: {len(problems)} mismatch(es)")
    return 1 if problems else 0
