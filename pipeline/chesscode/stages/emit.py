import json
from pathlib import Path

import chess
import chess.pgn
import jsonschema

from ..context import StageError

INPUTS=["game.json","classified.json","beats.json","script.json","timeline.json","metadata.json",str(Path(__file__).resolve().parents[3]/"spec/video_spec.schema.json")]
OUTPUTS=["video_spec.json"]
_THEMES={"legendary_games":"bone_slate","indian_chess_heroes":"walnut","opening_explained":"cool_grey","blunder_hall_of_fame":"warm_sand"}
_POSES={"blunder":"facepalm","mistake":"side_eye","brilliant":"slow_clap","missed_win":"screaming","comeback":"shocked","long_think":"checks_watch","time_scramble":"sweating","king_walk":"binoculars","promotion":"jealous","checkmate":"mic_drop","resign":"bow","opening_exit":"thinking"}
_FX={"blunder":["board_shake","red_flash","replay_move"],"mistake":["move_underline"],"brilliant":["gold_glint","stamp_brilliant"],"missed_win":["ghost_arrow"],"comeback":["eval_whip"],"long_think":["clock_pulse"],"time_scramble":["clock_red"],"king_walk":["king_trail"],"promotion":["crown_sparkle"],"checkmate":["freeze_frame"],"resign":["freeze_frame"],"opening_exit":["out_of_theory_label"]}

def _read(ctx,name): return json.loads((ctx.spec_dir/name).read_text(encoding="utf-8"))

def assemble(ctx) -> dict:
    game=_read(ctx,"game.json"); rows=_read(ctx,"classified.json"); beats=_read(ctx,"beats.json"); script=_read(ctx,"script.json"); timeline=_read(ctx,"timeline.json"); metadata=_read(ctx,"metadata.json")
    pgn_path=ctx.spec_dir/"game.pgn"
    pgn=pgn_path.read_text(encoding="utf-8") if pgn_path.exists() else game.get("pgn","")
    parsed=chess.pgn.read_game(__import__("io").StringIO(pgn)) if pgn else None
    headers=parsed.headers if parsed else {}
    def player(color):
        key="White" if color==chess.WHITE else "Black"; name=headers.get(key,"Unknown")
        try: rating=int(headers.get(key+"Elo"))
        except (TypeError,ValueError): rating=None
        return {"name":name,"rating":rating,"title":headers.get(key+"Title") or None,"country":game.get(key.lower()+"_country")}
    result=headers.get("Result",game.get("result","1/2-1/2"))
    orientation="white" if result=="1/2-1/2" else "white" if result=="1-0" else "black"
    game_obj={"source":game["source"],"source_id":game["source_id"],"white":player(chess.WHITE),"black":player(chess.BLACK),"event":headers.get("Event","Unknown event"),"date":headers.get("Date","????.??.??").replace(".","-"),"result":result,"eco":headers.get("ECO","A00"),"opening":headers.get("Opening","Unknown opening"),"pgn":pgn}
    spec_plies=[]
    for row in rows:
        n=row["ply"]; fen=row["fen_after"]
        spec_plies.append({"ply":n,"san":row["san"],"uci":row["uci"],"fen_after":fen,"eval":row.get("eval",{"cp":None,"mate":None}),"best_uci":row.get("best_uci",row["uci"]),"class":row.get("class","best"),"clock_ms":row.get("clock_ms"),"show_at_ms":timeline["plies_show_at"][str(n)] if str(n) in timeline["plies_show_at"] else timeline["plies_show_at"].get(n,0),"arrows":[],"highlights":[{"square":chess.square_name(sq),"kind":"last_move"} for sq in (chess.Move.from_uci(row["uci"]).from_square,chess.Move.from_uci(row["uci"]).to_square)]})
    line_map=script.get("mascot_lines",{})
    spec_beats=[]
    for i,b in enumerate(timeline.get("beats",beats)):
        bid=b.get("beat_id",f"b-{i+1:02d}"); kind=b["type"]
        line=line_map.get(bid)
        if not line: raise ValueError(f"missing mascot line for beat {bid}")
        spec_beats.append({"beat_id":bid,"type":kind,"ply":b["ply"],"at_ms":b["at_ms"],"intensity":b.get("intensity",1),"mascot":{"pose":_POSES[kind],"line":line},"fx":_FX[kind],"sfx":None})
    return {"spec_version":"1.0.0","video_id":ctx.video_id,"pair_id":"-".join(ctx.video_id.split("-")[:3]),"language":ctx.language,"template":ctx.template,"series":game["series"],"board":{"orientation":orientation,"theme":_THEMES[game["series"]]},"format":{"width":1080,"height":1920,"fps":30} if ctx.template=="shorts" else {"width":1920,"height":1080,"fps":30},"duration_ms":timeline["duration_ms"],"game":game_obj,"plies":spec_plies,"narration":timeline["narration"],"beats":spec_beats,"chapters":timeline["chapters"],"music":{"track":"music/bed_calm_01.mp3","volume":0.12,"duck_under_voice":0.06},"youtube":metadata}

def validate(spec: dict) -> None:
    root=Path(__file__).resolve().parents[3]
    schema=json.loads((root/"spec/video_spec.schema.json").read_text(encoding="utf-8"))
    errors=[f"{'.'.join(map(str,error.absolute_path)) or '$'}: {error.message}" for error in jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).iter_errors(spec)]
    vid=spec.get("video_id"); pair=spec.get("pair_id"); lang=spec.get("language")
    if vid != f"{pair}-{lang}": errors.append("video_id: must equal pair_id-language")
    if spec.get("template")=="shorts":
        if spec.get("format")!={"width":1080,"height":1920,"fps":30}: errors.append("format: shorts must be 1080x1920 at 30 fps")
        if spec.get("duration_ms",0)>175000: errors.append("duration_ms: shorts maximum is 175000")
    narration=spec.get("narration",[])
    for a,b in zip(narration,narration[1:]):
        if a.get("start_ms",0)+a.get("duration_ms",0)>b.get("start_ms",0): errors.append(f"narration.{b.get('segment_id','?')}: overlaps previous segment")
    if [p.get("ply") for p in spec.get("plies",[])] != list(range(1,len(spec.get("plies",[]))+1)): errors.append("plies: ply numbers must be 1..n")
    if errors: raise StageError(spec.get("video_id","unknown"),"emit","\n".join(errors))

def run(ctx):
    try:
        spec=assemble(ctx); validate(spec)
        (ctx.spec_dir/"video_spec.json").write_text(json.dumps(spec,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    except StageError: raise
    except Exception as exc: raise StageError(ctx.video_id,"emit",str(exc)) from exc
