import json

from ..config import load
from ..context import StageError
from .beats import pace

INPUTS = ["script.json", "voice.json", "beats.json", "classified.json", "config/timeline.yaml"]
OUTPUTS = ["timeline.json"]

def layout(segments: list[dict], voice: list[dict], beats: list[dict], plies: list[dict], cfg: dict) -> dict:
    if len(segments) != len(voice): raise ValueError("script and voice segment counts differ")
    narration=[]; cursor=0; gap=cfg.get("segment_gap_ms",300); reaction=cfg.get("reaction_gap_ms",900)
    beat_plies={b["ply"] for b in beats if b.get("intensity",1)>=2}
    for i,(segment,audio) in enumerate(zip(segments,voice)):
        duration=int(audio["duration_ms"]); start=cursor
        words=[{"w":w["w"],"start_ms":start+int(w["start_ms"]),"end_ms":start+int(w["end_ms"])} for w in audio["words"]]
        narration.append({"segment_id":audio.get("segment_id",f"seg-{i:03d}"),"kind":segment["kind"],"ply":segment.get("ply"),"text":segment["text"],"audio":audio["audio"],"start_ms":start,"duration_ms":duration,"words":words})
        cursor=start+duration
        if segment.get("ply") in beat_plies: cursor+=reaction
        elif i<len(segments)-1: cursor+=gap
    plies_show_at={}
    for ply in plies:
        n=ply["ply"]
        relevant=[s for s in narration if s.get("ply")==n and s.get("kind")=="ply"]
        if relevant:
            s=relevant[0]; starts=[w["start_ms"] for w in s["words"]]
            plies_show_at[n]=starts[0] if starts else s["start_ms"]
        else: plies_show_at[n]=n*cfg.get("est_ms_per_ply",4500)
    timed_beats=[{**b,"at_ms":plies_show_at.get(b["ply"], b["ply"]*cfg.get("est_ms_per_ply",4500))} for b in beats]
    timed_beats=pace(timed_beats,plies_show_at,cfg.get("beats",cfg))
    duration=(narration[-1]["start_ms"]+narration[-1]["duration_ms"] if narration else 0)+cfg.get("outro_ms",20000)
    timed_beats=[b for b in timed_beats if b["at_ms"]<duration]
    chapters=[{"title":s["text"][:70],"start_ms":s["start_ms"]} for s in narration if s["kind"] in ("cold_open","chapter","key_moment","verdict")]
    if not chapters: chapters=[{"title":"Opening","start_ms":0}]
    chapters.sort(key=lambda c:c["start_ms"])
    spaced=[]
    for chapter in chapters:
        if chapter["start_ms"]<=duration-cfg.get("chapter_min_ms",10000) and (not spaced or chapter["start_ms"]-spaced[-1]["start_ms"]>=cfg.get("chapter_min_ms",10000)):
            spaced.append(chapter)
    if not spaced or spaced[0]["start_ms"]!=0: spaced.insert(0,{"title":"Opening","start_ms":0})
    step=cfg.get("chapter_min_ms",10000)
    for at in range(step,duration-step+1,step):
        if len(spaced)>=cfg.get("min_chapters",3): break
        if all(abs(at-c["start_ms"])>=step for c in spaced): spaced.append({"title":f"Chapter {len(spaced)+1}","start_ms":at})
    chapters=sorted(spaced,key=lambda c:c["start_ms"])
    if len(chapters)<cfg.get("min_chapters",3): raise ValueError("duration is too short for three chapters at least 10 seconds apart")
    return {"narration":narration,"plies_show_at":plies_show_at,"beats":timed_beats,"chapters":chapters,"duration_ms":duration}

def run(ctx):
    try:
        data={name:json.loads((ctx.spec_dir/name).read_text(encoding="utf-8")) for name in ("script.json","voice.json","beats.json","classified.json")}
        beats=data["beats.json"]
        timeline_cfg=load("timeline",root=ctx.repo_root)
        if ctx.template=="shorts":
            if not beats: raise ValueError("shorts requires at least one beat")
            beats=[max(beats,key=lambda beat:(beat.get("priority",0),beat.get("intensity",0),-beat.get("ply",0)))]
            timeline_cfg=dict(timeline_cfg)
            timeline_cfg["outro_ms"]=0
            gap=timeline_cfg.get("segment_gap_ms",300)
            duration=sum(int(row["duration_ms"]) for row in data["voice.json"])+gap*max(0,len(data["voice.json"])-1)+timeline_cfg.get("outro_ms",20000)
            timeline_cfg["est_ms_per_ply"]=min(timeline_cfg.get("est_ms_per_ply",4500),max(1,(duration-1)//max(1,beats[0]["ply"])))
        result=layout(data["script.json"]["segments"],data["voice.json"],beats,data["classified.json"],timeline_cfg)
        (ctx.spec_dir/"timeline.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    except Exception as exc: raise StageError(ctx.video_id,"timeline",str(exc)) from exc
