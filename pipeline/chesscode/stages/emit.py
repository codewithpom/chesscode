import csv
import io
import json
import math
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import chess
import chess.pgn
import imageio_ffmpeg
import jsonschema

from ..config import load
from ..context import StageError
from ..winprob import win_pct
from .beats import _FX, top_beat

INPUTS=["game.json","game.pgn","classified.json","beats.json","script.json","timeline.json","metadata.json","spec/video_spec.schema.json","config/music.yaml","config/beats.yaml","content/openings"]
OUTPUTS=["video_spec.json"]
_THEMES={"legendary_games":"bone_slate","indian_chess_heroes":"walnut","opening_explained":"cool_grey","blunder_hall_of_fame":"warm_sand"}
_RESULTS=("1-0","0-1","1/2-1/2")
SPEC_VERSION="1.1.0"
_UTC_Z=re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z")

def _read(ctx,name): return json.loads((ctx.spec_dir/name).read_text(encoding="utf-8"))

def _need(mapping,key,where):
    value=mapping.get(key)
    # python-chess fills absent PGN tags with "?" and "????.??.??"
    if value in (None,"","?","????.??.??"): raise ValueError(f"missing {where} {key}")
    return value

def arrows(row: dict) -> list[dict]:
    """Best-move arrow where the played move cost something; a missed win is drawn as the missed move."""
    if row["class"] not in ("mistake","blunder","missed_win") or row["best_uci"]==row["uci"]: return []
    best=chess.Move.from_uci(row["best_uci"])
    return [{"from":chess.square_name(best.from_square),"to":chess.square_name(best.to_square),"color":"missed" if row["class"]=="missed_win" else "best"}]

def highlights(row: dict) -> list[dict]:
    move=chess.Move.from_uci(row["uci"]); board=chess.Board(row["fen_after"])
    marks=[{"square":chess.square_name(sq),"kind":"last_move"} for sq in (move.from_square,move.to_square)]
    if board.is_check(): marks.append({"square":chess.square_name(board.king(board.turn)),"kind":"check"})
    return marks

def _opening_name(eco: str, fens_after: list[str], directory: Path) -> str:
    """Name from the openings table: the deepest game position that ends an entry with this ECO, else the shortest (broadest) name listed for the ECO."""
    by_epd={}; broadest=None
    for path in sorted(Path(directory).glob("*.tsv")):
        with path.open(encoding="utf-8",newline="") as f:
            for entry in csv.DictReader(f,delimiter="\t"):
                if entry["eco"]!=eco: continue
                line=chess.pgn.read_game(io.StringIO(entry["pgn"])); board=line.board()
                for node in line.mainline(): board.push(node.move)
                by_epd[board.epd()]=entry["name"]
                if broadest is None or len(entry["name"])<len(broadest): broadest=entry["name"]
    for fen in reversed(fens_after):
        name=by_epd.get(chess.Board(fen).epd())
        if name: return name
    if broadest: return broadest
    raise ValueError(f"no opening name for ECO {eco}: add an Opening header to the PGN")

def prepare_music(ctx,duration_ms: int) -> dict:
    """Copy the configured track into the spec folder; a placeholder is generated as a silent bed and marked for QA."""
    cfg=load("music",root=ctx.repo_root); track=cfg["tracks"][cfg["track"]]
    name=Path(track["file"]).name; target=ctx.spec_dir/"music"/name; marker=target.with_name(name+".placeholder")
    target.parent.mkdir(parents=True,exist_ok=True)
    if track["placeholder"]:
        result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-y","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t",f"{duration_ms/1000+1:.3f}","-c:a","libmp3lame","-b:a","32k",str(target)],capture_output=True,text=True,check=False)
        if result.returncode: raise ValueError(f"ffmpeg could not generate the placeholder music bed: {result.stderr.strip()[-200:]}")
        marker.write_text("silent placeholder bed: replace with licensed music (config/music.yaml) before publishing\n",encoding="utf-8")
    else:
        source=ctx.repo_root/track["file"]
        if not source.is_file(): raise ValueError(f"music file missing: {source}")
        shutil.copyfile(source,target); marker.unlink(missing_ok=True)
    return {"track":f"music/{name}","volume":track["volume"],"duck_under_voice":track["duck_under_voice"]}

def crop_origin(uci: str) -> str:
    """Lower-left of the 4x4 window (files a-e, ranks 1-5, White's view) holding both squares, centred on the move.
    A move wider than four squares cannot fit, so the window then keeps the destination in view."""
    def axis(a,b):
        lo,hi=max(max(a,b)-3,0),min(min(a,b),4)
        return max(lo,min(hi,(a+b)//2-1)) if lo<=hi else max(0,min(4,b-1))
    a,b=chess.parse_square(uci[:2]),chess.parse_square(uci[2:4])
    return "abcde"[axis(chess.square_file(a),chess.square_file(b))]+str(axis(chess.square_rank(a),chess.square_rank(b))+1)

def verdict(rows: list[dict], result: str) -> dict:
    """Turning point = largest win% swing against the eventual loser (draws: largest absolute swing); Lichess accuracy per side, book plies included."""
    pct=lambda s: win_pct(s["cp"],s["mate"])
    swing={}; accuracy={"white":[],"black":[]}
    for row in rows:
        before,after=pct(row["before"][0]),pct(row["eval"]); white=row["ply"]%2==1
        swing[row["ply"]]={"1-0":after-before,"0-1":before-after}.get(result,abs(after-before))
        loss=before-after if white else after-before
        accuracy["white" if white else "black"].append(max(0.0,min(100.0,103.1668*math.exp(-0.04354*loss)-3.1669)))
    if not all(accuracy.values()): raise ValueError("verdict needs plies from both sides")
    return {"turning_point_ply":max(swing,key=swing.get),"accuracy":{side:round(sum(v)/len(v),2) for side,v in accuracy.items()}}

def key_moments(rows: list[dict], beats: list[dict], narration: list[dict], labels: dict) -> list[dict]:
    """One per beat of intensity >= 2, timed by its key_moment narration segment (carrying the beat's ply); ordered by start."""
    by_ply={r["ply"]:r for r in rows}; moments=[]
    for beat in beats:
        if beat["intensity"]<2: continue
        ply=beat["ply"]
        segs=[n for n in narration if n["kind"]=="key_moment" and n.get("ply")==ply]
        if len(segs)!=1: raise ValueError(f"beat {beat['beat_id']} needs exactly one key_moment narration segment at ply {ply}, found {len(segs)}")
        seg=segs[0]
        line=by_ply[ply]["before"][0].get("pv",[])[:8]
        if not line: raise ValueError(f"engine has no line before ply {ply}")
        moments.append({"beat_id":beat["beat_id"],"ply":ply,"start_ms":seg["start_ms"],"duration_ms":seg["duration_ms"],"label":_need(labels,beat["beat_id"],"script key_moment_labels"),"line":line})
    return sorted(moments,key=lambda k:k["start_ms"])

def assemble(ctx) -> dict:
    game=_read(ctx,"game.json"); rows=_read(ctx,"classified.json"); script=_read(ctx,"script.json"); timeline=_read(ctx,"timeline.json"); metadata=_read(ctx,"metadata.json")
    pgn=(ctx.spec_dir/"game.pgn").read_text(encoding="utf-8")
    parsed=chess.pgn.read_game(io.StringIO(pgn))
    if parsed is None: raise ValueError("game.pgn holds no game")
    headers=parsed.headers
    def player(color):
        key="White" if color==chess.WHITE else "Black"; name=_need(headers,key,"PGN header")
        elo=headers.get(key+"Elo","")
        return {"name":name,"rating":int(elo) if elo not in ("","?") else None,"title":headers.get(key+"Title") or None,"country":game[key.lower()+"_country"],"fact":_need(script.get("player_facts") or {},key.lower(),"script player_facts")}
    result=_need(headers,"Result","PGN header")
    if result not in _RESULTS: raise ValueError(f"PGN Result {result!r} is not a finished game")
    eco=_need(headers,"ECO","PGN header")
    opening=headers.get("Opening") or _opening_name(eco,[r["fen_after"] for r in rows],ctx.repo_root/"content/openings")
    game_obj={"source":_need(game,"source","game.json"),"source_id":_need(game,"source_id","game.json"),"white":player(chess.WHITE),"black":player(chess.BLACK),"event":_need(headers,"Event","PGN header"),"date":_need(headers,"Date","PGN header").replace(".","-"),"result":result,"eco":eco,"opening":opening,"pgn":pgn}
    show=timeline["plies_show_at"]
    spec_plies=[]
    for row in rows:
        n=row["ply"]
        if str(n) not in show: raise ValueError(f"missing show_at_ms for ply {n}")
        spec_plies.append({"ply":n,"san":row["san"],"uci":row["uci"],"fen_after":row["fen_after"],"eval":row["eval"],"best_uci":row["best_uci"],"class":row["class"],"clock_ms":row["clock_ms"],"show_at_ms":show[str(n)],"arrows":arrows(row),"highlights":highlights(row)})
    sfx=load("beats",root=ctx.repo_root)["sfx"]
    spec_beats=[]
    for b in timeline["beats"]:
        bid=b["beat_id"]; kind=b["type"]
        line=script["mascot_lines"].get(bid)
        if not line: raise ValueError(f"missing mascot line for beat {bid}")
        spec_beats.append({"beat_id":bid,"type":kind,"ply":b["ply"],"at_ms":b["at_ms"],"intensity":b["intensity"],"mascot":{"pose":b["pose"],"line":line},"fx":_FX[kind],"sfx":sfx[kind]})
    series=_need(game,"series","game.json")
    if not timeline["beats"]: raise ValueError("no beats: cannot choose a cold open or thumbnail ply")
    top=top_beat(timeline["beats"]); by_ply={r["ply"]:r for r in rows}
    cold_open={"ply_from":max(1,top["ply"]-2),"ply_to":top["ply"],"hook":_need(script,"cold_open_hook","script.json")}
    moments=[] if ctx.template=="shorts" else key_moments(rows,timeline["beats"],timeline["narration"],_need(script,"key_moment_labels","script.json"))
    thumbnail={"text":_need(script,"thumbnail_text","script.json"),"ply":top["ply"],"crop_origin":crop_origin(by_ply[top["ply"]]["uci"]),"pose":top["pose"]}
    return {"spec_version":SPEC_VERSION,"video_id":ctx.video_id,"pair_id":"-".join(ctx.video_id.split("-")[:3]),"language":ctx.language,"template":ctx.template,"series":series,"board":{"orientation":"black" if result=="0-1" else "white","theme":_THEMES[series]},"format":{"width":1080,"height":1920,"fps":30} if ctx.template=="shorts" else {"width":1920,"height":1080,"fps":30},"duration_ms":timeline["duration_ms"],"game":game_obj,"plies":spec_plies,"narration":timeline["narration"],"beats":spec_beats,"chapters":timeline["chapters"],"cold_open":cold_open,"key_moments":moments,"verdict":verdict(rows,result),"thumbnail":thumbnail,"music":prepare_music(ctx,timeline["duration_ms"]),"youtube":{k:v for k,v in metadata.items() if k!="chapters"}}  # chapters live at the top level

def validate(spec: dict) -> None:
    root=Path(__file__).resolve().parents[3]
    schema=json.loads((root/"spec/video_spec.schema.json").read_text(encoding="utf-8"))
    errors=[f"{'.'.join(map(str,error.absolute_path)) or '$'}: {error.message}" for error in jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).iter_errors(spec)]
    vid=spec.get("video_id");pair=spec.get("pair_id");lang=spec.get("language")
    if vid != f"{pair}-{lang}": errors.append("video_id: must equal pair_id-language")
    publish=spec.get("youtube",{}).get("publish_at")
    try:
        if not _UTC_Z.fullmatch(publish): raise ValueError
        datetime.fromisoformat(publish.replace("Z","+00:00"))
    except (TypeError,ValueError): errors.append(f"youtube.publish_at: {publish!r} is not an ISO-8601 UTC timestamp ending in Z")
    if spec.get("template")=="shorts":
        if spec.get("format")!={"width":1080,"height":1920,"fps":30}: errors.append("format: shorts must be 1080x1920 at 30 fps")
        if spec.get("duration_ms",0)>59000: errors.append("duration_ms: shorts maximum is 59000")
        if len(spec.get("beats",[]))!=1: errors.append("beats: shorts require exactly one beat")
    narration=spec.get("narration",[])
    for a,b in zip(narration,narration[1:]):
        if a.get("start_ms",0)+a.get("duration_ms",0)>b.get("start_ms",0): errors.append(f"narration.{b.get('segment_id','?')}: overlaps previous segment")
    beats=sorted(spec.get("beats",[]),key=lambda b:b.get("at_ms",0))
    for a,b in zip(beats,beats[1:]):
        if a.get("mascot",{}).get("pose")==b.get("mascot",{}).get("pose"): errors.append(f"beats.{b.get('beat_id','?')}: mascot pose {b['mascot']['pose']} repeats the previous beat")
    if [p.get("ply") for p in spec.get("plies",[])] != list(range(1,len(spec.get("plies",[]))+1)): errors.append("plies: ply numbers must be 1..n")
    n=len(spec.get("plies",[])); ok=lambda p: isinstance(p,int) and 1<=p<=n
    cold=spec.get("cold_open") or {}
    if not (ok(cold.get("ply_from")) and ok(cold.get("ply_to")) and cold["ply_from"]<=cold["ply_to"]): errors.append("cold_open: ply_from..ply_to must be a forward range of existing plies")
    for i,k in enumerate(spec.get("key_moments",[])):
        # spec section 5: KeyMoment scenes run 15 to 40 s and never overlap each other (same rule as the Zod superRefine)
        if not 15000<=k.get("duration_ms",0)<=40000: errors.append(f"key_moments.{i}.duration_ms: must be 15000-40000 ms")
        prev=spec["key_moments"][i-1] if i else None
        if prev and k.get("start_ms",0)<prev.get("start_ms",0)+prev.get("duration_ms",0): errors.append(f"key_moments.{i}.start_ms: overlaps previous key moment")
        if not ok(k.get("ply")): errors.append(f"key_moments.{i}.ply: no such ply")
        if not any(b.get("beat_id")==k.get("beat_id") for b in spec.get("beats",[])): errors.append(f"key_moments.{i}.beat_id: must reference a beat")
    if not ok((spec.get("verdict") or {}).get("turning_point_ply")): errors.append("verdict.turning_point_ply: no such ply")
    thumb=spec.get("thumbnail") or {}
    if not ok(thumb.get("ply")): errors.append("thumbnail.ply: no such ply")
    if thumb.get("text") and str(thumb["text"]).lower()==str(spec.get("youtube",{}).get("title","")).lower(): errors.append("thumbnail.text: must not repeat the title")
    if errors: raise StageError(spec.get("video_id","unknown"),"emit","\n".join(errors))

def run(ctx):
    try:
        spec=assemble(ctx); validate(spec)
        (ctx.spec_dir/"video_spec.json").write_text(json.dumps(spec,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    except StageError: raise
    except KeyError as exc: raise StageError(ctx.video_id,"emit",f"missing required value: {exc}") from exc
    except Exception as exc: raise StageError(ctx.video_id,"emit",str(exc)) from exc
