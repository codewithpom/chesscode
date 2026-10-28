import json

from ..config import load
from ..context import StageError
from .beats import pace, top_beat

INPUTS = ["script.json", "voice.json", "beats.json", "classified.json", "config/timeline.yaml", "config/beats.yaml"]
OUTPUTS = ["timeline.json"]

def _coverage(segments: list[dict], max_ply: int) -> dict[int, tuple[int, int]]:
    """segment index -> (first, last) ply covered: from its ply up to the next ply segment's ply - 1."""
    marks = [(i, s.get("ply")) for i, s in enumerate(segments) if s["kind"] == "ply"]
    if not marks: raise ValueError("script has no ply segments, so moves cannot be timed to narration")
    plies = [p for _, p in marks]
    if any(not isinstance(p, int) or not 1 <= p <= max_ply for p in plies) or plies != sorted(set(plies)):
        raise ValueError(f"ply segments must have strictly increasing ply numbers within 1..{max_ply}: {plies}")
    return {i: (p, plies[k+1]-1 if k+1 < len(plies) else max_ply) for k, (i, p) in enumerate(marks)}

def _lay(segments: list[dict], voice: list[dict], cover: dict, reaction_plies: set[int], cfg: dict) -> list[dict]:
    narration = []; cursor = 0
    for i, (segment, audio) in enumerate(zip(segments, voice)):
        duration = int(audio["duration_ms"]); start = cursor
        words = [{"w": w["w"], "start_ms": start+int(w["start_ms"]), "end_ms": start+int(w["end_ms"])} for w in audio["words"]]
        narration.append({"segment_id": audio["segment_id"], "kind": segment["kind"], "ply": segment.get("ply"), "text": segment["text"], "audio": audio["audio"], "start_ms": start, "duration_ms": duration, "words": words})
        cursor = start + duration
        if i in cover and reaction_plies & set(range(cover[i][0], cover[i][1]+1)): cursor += cfg["reaction_gap_ms"]
        elif i < len(segments)-1: cursor += cfg["segment_gap_ms"]
    return narration

def _show_at(narration: list[dict], cover: dict) -> dict[int, int]:
    """First covered ply at segment start, the rest at evenly spaced word starts; earlier plies at the first ply segment."""
    show = {p: narration[min(cover)]["start_ms"] for p in range(1, cover[min(cover)][0])}
    for i, (first, last) in cover.items():
        seg = narration[i]; starts = [w["start_ms"] for w in seg["words"]]; count = last-first+1
        show[first] = seg["start_ms"]
        for j in range(1, count): show[first+j] = starts[j*len(starts)//count] if starts else seg["start_ms"]
    return show

def layout(segments: list[dict], voice: list[dict], beats: list[dict], plies: list[dict], cfg: dict) -> dict:
    if len(segments) != len(voice): raise ValueError("script and voice segment counts differ")
    cover = _coverage(segments, max(p["ply"] for p in plies))
    reaction = {b["ply"] for b in beats if b["intensity"] >= 2}
    for _ in range(5):
        narration = _lay(segments, voice, cover, reaction, cfg)
        plies_show_at = _show_at(narration, cover)
        timed_beats = pace([{**b, "at_ms": plies_show_at[b["ply"]]} for b in beats], plies_show_at, cfg["beats"])
        settled = {b["ply"] for b in timed_beats if b["intensity"] >= 2}
        if settled == reaction: break
        reaction = settled
    else: raise ValueError("reaction gaps and beat pacing do not settle")
    duration=(narration[-1]["start_ms"]+narration[-1]["duration_ms"] if narration else 0)+cfg["outro_ms"]
    timed_beats=[b for b in timed_beats if b["at_ms"]<duration]
    chapters=[{"title":s["text"][:70],"start_ms":s["start_ms"]} for s in narration if s["kind"] in ("cold_open","chapter","key_moment","verdict")]
    if not chapters: chapters=[{"title":"Opening","start_ms":0}]
    chapters.sort(key=lambda c:c["start_ms"])
    spaced=[]
    for chapter in chapters:
        if chapter["start_ms"]<=duration-cfg["chapter_min_ms"] and (not spaced or chapter["start_ms"]-spaced[-1]["start_ms"]>=cfg["chapter_min_ms"]):
            spaced.append(chapter)
    if not spaced or spaced[0]["start_ms"]!=0: spaced.insert(0,{"title":"Opening","start_ms":0})
    step=cfg["chapter_min_ms"]
    for at in range(step,duration-step+1,step):
        if len(spaced)>=cfg["min_chapters"]: break
        if all(abs(at-c["start_ms"])>=step for c in spaced): spaced.append({"title":f"Chapter {len(spaced)+1}","start_ms":at})
    chapters=sorted(spaced,key=lambda c:c["start_ms"])
    if len(chapters)<cfg["min_chapters"]: raise ValueError("duration is too short for three chapters at least 10 seconds apart")
    return {"narration":narration,"plies_show_at":plies_show_at,"beats":timed_beats,"chapters":chapters,"duration_ms":duration}

def run(ctx):
    try:
        data={name:json.loads((ctx.spec_dir/name).read_text(encoding="utf-8")) for name in ("script.json","voice.json","beats.json","classified.json")}
        beats=data["beats.json"]
        timeline_cfg={**load("timeline",root=ctx.repo_root),"beats":load("beats",root=ctx.repo_root)}
        if ctx.template=="shorts":
            if not beats: raise ValueError("shorts requires at least one beat")
            beats=[top_beat(beats)]
            timeline_cfg["outro_ms"]=0; timeline_cfg["min_chapters"]=0
        result=layout(data["script.json"]["segments"],data["voice.json"],beats,data["classified.json"],timeline_cfg)
        (ctx.spec_dir/"timeline.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    except Exception as exc: raise StageError(ctx.video_id,"timeline",str(exc)) from exc
