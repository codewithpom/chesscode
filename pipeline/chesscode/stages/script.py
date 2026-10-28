import json
import re
import sqlite3
from pathlib import Path

import chess
import yaml
from .. import llm
from ..config import load
from ..context import StageError
from ..san_guard import extract_san, unknown_moves
from .beats import top_beat

INPUTS = ["classified.json", "beats.json", "game.json", "config/models.yaml", "config/qa.yaml", "pipeline/chesscode/prompts/script_system.md"]
OUTPUTS = ["script.json"]
def _text(limit): return {"type":"string","minLength":1,"maxLength":limit}
# Limits mirror the 1.1.0 spec contract: fact <= 120, cold-open hook <= 60, key-moment label <= 40, thumbnail text <= 4 words.
SCHEMA = {"type":"object", "required":["segments","mascot_lines","titles","hook","player_facts","cold_open_hook","thumbnail_text","key_moment_labels"], "properties":{
 "player_facts":{"type":"object","required":["white","black"],"properties":{"white":_text(120),"black":_text(120)}},
 "cold_open_hook":_text(60),"thumbnail_text":{"type":"string","pattern":r"^\S+(?: \S+){0,3}$"},
 "key_moment_labels":{"type":"object","additionalProperties":_text(40)},
 "segments":{"type":"array","items":{"type":"object","required":["kind","ply","text"],"properties":{"kind":{"enum":["cold_open","title","player_intro","ply","chapter","key_moment","verdict","outro"]},"ply":{"type":["integer","null"]},"text":{"type":"string"}}}},
 "mascot_lines":{"type":"object","additionalProperties":{"type":"string"}},"titles":{"type":"array","minItems":3,"maxItems":3,"items":{"type":"string"}},"hook":{"type":"string"}}}

# Hindi is written natively, not translated; chess terms and moves stay English/Latin (joke rule 3, SAN guard).
SHORTS_ADDENDUM = "\nThis is a Short about the single beat named in short_beat (type, ply, move, mascot pose). Tell that moment as a story with a hook; do not recap the rest of the game."
HINDI_ADDENDUM = "\nWrite the narration natively in conversational spoken Hindi (Devanagari) from these facts; never translate an English script. Keep chess terms (fork, pin, blunder, checkmate, rook, knight) in English and write every move in standard SAN with Latin letters."

def select_bank_line(beat_type: str, bank: dict, recent: set[str], language: str) -> str:
    limit=10 if language=="hi" else 8
    for line in bank.get(beat_type,[]):
        if line not in recent and len(line.split())<=limit: return line
    raise StageError("unknown","script",f"no unused {language} fallback line for {beat_type}")

def _specificity(text: str, minutes: float) -> float:
    concrete=set(re.findall(r"\b[a-h][1-8]\b",text))|set(extract_san(text))
    concrete|={word.lower() for word in re.findall(r"\b(?:plan|file|diagonal|passed pawn|king|rook|fork|pin|sacrifice)\b",text,re.I)}
    return len(concrete)/max(minutes,1e-9)

def ensure_specific(output: dict, regenerate, threshold: float, wpm: int) -> dict:
    def score(value):
        words=" ".join(s["text"] for s in value["segments"])
        return _specificity(words,sum(len(s["text"].split()) for s in value["segments"])/wpm)
    if score(output)<threshold: output=regenerate()
    if score(output)<threshold: raise ValueError("script specificity remains below threshold after regeneration")
    return output

def _recent_lines(path: Path, language: str, video_id: str) -> set[str]:
    if not path.exists(): return set()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS line_history (video_id TEXT, language TEXT, line TEXT)")
        # a rerun must not count this video's own earlier lines as recent
        return {row[0] for row in db.execute("SELECT DISTINCT line FROM line_history WHERE language=? AND video_id IN (SELECT video_id FROM line_history WHERE language=? AND video_id!=? GROUP BY video_id ORDER BY MAX(rowid) DESC LIMIT 10)",(language,language,video_id))}

def _engine_sans(rows: list[dict]) -> set[str]:
    sans=set()
    for row in rows:
        for key,fen_key in (("before","fen_before"),("after","fen_after")):
            board=chess.Board(row[fen_key])
            for line in row.get(key) or []:
                for uci in line.get("pv",[]):
                    try:
                        move=chess.Move.from_uci(uci)
                        if move not in board.legal_moves: break
                        sans.add(board.san(move)); board.push(move)
                    except (ValueError,chess.IllegalMoveError): break
    return sans

def _at(value, path):
    for key in path: value = value[key]
    return value

def _revised_text(revised: dict, output: dict, path: tuple) -> str:
    if path[0]=="segments":
        parts=revised["segments"]
        if len(parts)==len(output["segments"]): return parts[path[1]]["text"]
        if len(parts)==1: return parts[0]["text"]  # the model returned only the regenerated segment
        raise ValueError(f"regenerated script has {len(parts)} segments, expected {len(output['segments'])} or 1")
    return _at(revised,path)

def guard_san(output: dict, game_sans: set[str], get_engine_sans, regenerate) -> None:
    """Every SAN in every text the script produced must be a game or engine move; fix by regeneration (3 tries)."""
    engine=[None]
    def bad_in(text):
        bad=unknown_moves(text,game_sans,engine[0] or set())
        if bad and engine[0] is None:
            engine[0]=get_engine_sans(); bad=unknown_moves(text,game_sans,engine[0])
        return bad
    places=[("segments",i,"text") for i in range(len(output["segments"]))]+[("titles",i) for i in range(len(output["titles"]))]
    places+=[("hook",),("cold_open_hook",),("thumbnail_text",),("player_facts","white"),("player_facts","black")]+[("key_moment_labels",bid) for bid in output["key_moment_labels"]]
    for path in places:
        for attempt in range(4):
            bad=bad_in(_at(output,path))
            if not bad: break
            if attempt==3: raise ValueError(f"unknown SAN after regeneration in {'.'.join(map(str,path))}: {', '.join(bad)}")
            _at(output,path[:-1])[path[-1]]=_revised_text(regenerate(path,bad),output,path)  # segment kind and ply stay: they drive timing

def _bank_line(ctx, beat_type: str, bank_path: Path, used: set[str]) -> str:
    if not bank_path.is_file(): raise StageError(ctx.video_id,"script",f"line bank missing: {bank_path}")
    try: return select_bank_line(beat_type,yaml.safe_load(bank_path.read_text(encoding="utf-8")) or {},used,ctx.language)
    except StageError as exc: raise StageError(ctx.video_id,"script",exc.reason) from exc

def run(ctx):
    try:
        facts = {name: json.loads((ctx.spec_dir / name).read_text(encoding="utf-8")) for name in ("game.json", "classified.json", "beats.json")}
        system = (Path(__file__).parent.parent / "prompts" / "script_system.md").read_text(encoding="utf-8")
        if ctx.language=="hi": system += HINDI_ADDENDUM
        request = {"language":ctx.language,"facts":facts}
        if ctx.template=="shorts":
            if not facts["beats.json"]: raise StageError(ctx.video_id,"script","a Short needs at least one beat")
            beat=top_beat(facts["beats.json"])  # the timeline cuts the same beat
            facts["beats.json"]=[beat]
            san=next(r["san"] for r in facts["classified.json"] if r["ply"]==beat["ply"])
            request["short_beat"]={"beat_id":beat["beat_id"],"type":beat["type"],"ply":beat["ply"],"san":san,"pose":beat["pose"]}
            system += SHORTS_ADDENDUM
        user = json.dumps(request, ensure_ascii=False)
        output = llm.complete_json("script", system, user, SCHEMA)
        rows=facts["classified.json"]
        game_sans={r.get("san","") for r in rows}
        wpm=140 if ctx.language=="hi" else 150
        qa=load("qa",root=ctx.repo_root)
        try:
            output=ensure_specific(output,lambda:llm.complete_json("script",system,user+"\nMake the game-specific plans, squares, and moves explicit.",SCHEMA),qa.get("min_specific_tokens_per_min",6),wpm)
        except ValueError as exc: raise StageError(ctx.video_id,"script",str(exc)) from exc
        word_count=sum(len(s["text"].split()) for s in output["segments"])
        min_words,max_words=(int(wpm*35/60),int(wpm*59/60)) if ctx.template=="shorts" else (int(wpm*8),int(wpm*12))
        if not min_words<=word_count<=max_words:
            output=llm.complete_json("script",system,user+f"\nTarget a total of {min_words} to {max_words} spoken words.",SCHEMA)
            word_count=sum(len(s["text"].split()) for s in output["segments"])
            if not min_words<=word_count<=max_words: raise StageError(ctx.video_id,"script",f"script length {word_count} words is outside {min_words}..{max_words} after regeneration")
        if ctx.template=="shorts" and output["segments"]:
            output["segments"][0].update(kind="cold_open",ply=None)
        # the SAN guard runs last: the regenerations above replace the whole output
        def regenerate(path,bad):
            part=_at(output,path[:2]) if path[0]=="segments" else _at(output,path)
            where=" ".join(map(str,path[:2] if path[0]=="segments" else path))
            return llm.complete_json("script",system,user+f"\nRegenerate only the {where} and return the full JSON. Unknown SAN: "+", ".join(bad)+". Current: "+json.dumps(part,ensure_ascii=False),SCHEMA)
        try: guard_san(output,game_sans,lambda:_engine_sans(rows),regenerate)
        except ValueError as exc: raise StageError(ctx.video_id,"script",str(exc)) from exc
        if output["thumbnail_text"].lower() in {title.lower() for title in output["titles"]}: raise StageError(ctx.video_id,"script","thumbnail_text repeats a title")
        if ctx.template!="shorts":
            missing=[b["beat_id"] for b in facts["beats.json"] if b["intensity"]>=2 and b["beat_id"] not in output["key_moment_labels"]]
            if missing: raise StageError(ctx.video_id,"script",f"key_moment_labels missing for beats: {', '.join(missing)}")
        used=_recent_lines(ctx.repo_root/"data/line_history.sqlite",ctx.language,ctx.video_id)
        bank_path=ctx.repo_root/"content/lines"/f"{ctx.language}.yaml"
        cap=10 if ctx.language=="hi" else 8
        engine_sans=_engine_sans(rows)
        for beat in facts["beats.json"]:
            bid=beat["beat_id"]
            line=output["mascot_lines"].get(bid)
            if not line or len(line.split())>cap or line in used or unknown_moves(line,game_sans,engine_sans):
                line=output["mascot_lines"][bid]=_bank_line(ctx,beat["type"],bank_path,used)
            checked=llm.complete_json("checks",system,"Check only this mascot line against the quoted joke rules. Return {\"ok\": boolean}. Line: "+line,{"type":"object","required":["ok"],"properties":{"ok":{"type":"boolean"}}})
            if not checked["ok"]: output["mascot_lines"][bid]=_bank_line(ctx,beat["type"],bank_path,used)
            used.add(output["mascot_lines"][bid])
        bad=[m for line in output["mascot_lines"].values() for m in unknown_moves(line,game_sans,engine_sans)]
        if bad: raise StageError(ctx.video_id,"script",f"unknown SAN in mascot line: {', '.join(bad)}")
        (ctx.spec_dir / "script.json").write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        history_path=ctx.repo_root/"data/line_history.sqlite"; history_path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(history_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS line_history (video_id TEXT, language TEXT, line TEXT)")
            db.execute("DELETE FROM line_history WHERE video_id=?",(ctx.video_id,))
            db.executemany("INSERT INTO line_history VALUES (?, ?, ?)",[(ctx.video_id,ctx.language,line) for line in output["mascot_lines"].values()])
    except Exception as exc:
        if isinstance(exc, StageError): raise
        raise StageError(ctx.video_id, "script", str(exc)) from exc
