import json
import re
import sqlite3
from pathlib import Path

import chess
from .. import llm
from ..config import load
from ..context import StageError
from ..san_guard import unknown_moves

INPUTS = ["classified.json", "beats.json", "game.json", "config/models.yaml", "prompts/script_system.md"]
OUTPUTS = ["script.json"]
SCHEMA = {"type":"object", "required":["segments","mascot_lines","titles","hook"], "properties":{
 "segments":{"type":"array","items":{"type":"object","required":["kind","ply","text"],"properties":{"kind":{"enum":["cold_open","title","player_intro","ply","chapter","key_moment","verdict","outro"]},"ply":{"type":["integer","null"]},"text":{"type":"string"}}}},
 "mascot_lines":{"type":"object","additionalProperties":{"type":"string"}},"titles":{"type":"array","minItems":3,"maxItems":3,"items":{"type":"string"}},"hook":{"type":"string"}}}

def select_bank_line(beat_type: str, bank: dict, recent: set[str], language: str) -> str:
    limit=10 if language=="hi" else 8
    for line in bank.get(beat_type,[]):
        if line not in recent and len(line.split())<=limit: return line
    raise StageError("unknown","script",f"no unused {language} fallback line for {beat_type}")

def _specificity(text: str, minutes: float) -> float:
    concrete=set(re.findall(r"\b[a-h][1-8]\b",text))|set(re.findall(r"(?<![A-Za-z0-9])(?:O-O(?:-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?)(?![A-Za-z0-9])",text))
    concrete|={word.lower() for word in re.findall(r"\b(?:plan|file|diagonal|passed pawn|king|rook|fork|pin|sacrifice)\b",text,re.I)}
    return len(concrete)/max(minutes,1e-9)

def ensure_specific(output: dict, regenerate, threshold: float, wpm: int) -> dict:
    def score(value):
        words=" ".join(s["text"] for s in value["segments"])
        return _specificity(words,sum(len(s["text"].split()) for s in value["segments"])/wpm)
    if score(output)<threshold: output=regenerate()
    if score(output)<threshold: raise ValueError("script specificity remains below threshold after regeneration")
    return output

def _recent_lines(path: Path, language: str) -> set[str]:
    if not path.exists(): return set()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS line_history (video_id TEXT, language TEXT, line TEXT)")
        return {row[0] for row in db.execute("SELECT DISTINCT line FROM line_history WHERE language=? AND video_id IN (SELECT video_id FROM line_history WHERE language=? GROUP BY video_id ORDER BY MAX(rowid) DESC LIMIT 10)",(language,language))}

def run(ctx):
    try:
        facts = {name: json.loads((ctx.spec_dir / name).read_text(encoding="utf-8")) for name in ("game.json", "classified.json", "beats.json")}
        system = (Path(__file__).parent.parent / "prompts" / "script_system.md").read_text(encoding="utf-8")
        if ctx.language=="hi": system += "\nWrite in natural spoken Hindi from these facts. Do not translate or use any English script."
        user = json.dumps({"language":ctx.language,"facts":facts}, ensure_ascii=False)
        output = llm.complete_json("script", system, user, SCHEMA)
        if ctx.template=="shorts" and output["segments"]:
            output["segments"][0].update(kind="cold_open",ply=None)
        rows=facts["classified.json"]
        game_sans={r.get("san","") for r in rows}
        engine_sans=set()
        bad_by_segment=[unknown_moves(segment["text"],game_sans,engine_sans) for segment in output["segments"]]
        if any(bad_by_segment):
            for row in rows:
                for key,fen_key in (("before","fen_before"),("after","fen_after")):
                    board=chess.Board(row[fen_key])
                    for line in row.get(key) or []:
                        for uci in line.get("pv",[]):
                            try:
                                move=chess.Move.from_uci(uci)
                                if move not in board.legal_moves: break
                                engine_sans.add(board.san(move)); board.push(move)
                            except (ValueError,chess.IllegalMoveError): break
        for index,segment in enumerate(output["segments"]):
            for _ in range(3):
                bad=bad_by_segment[index] if _==0 else unknown_moves(segment["text"],game_sans,engine_sans)
                if not bad: break
                prompt=user+"\nRegenerate only this segment and return the full JSON. Unknown SAN: "+", ".join(bad)+". Segment: "+json.dumps(segment,ensure_ascii=False)
                revised=llm.complete_json("script",system,prompt,SCHEMA)
                output["segments"][index]=revised["segments"][index]
                segment=output["segments"][index]
            else: raise StageError(ctx.video_id,"script",f"unknown SAN after regeneration in segment {index}")
        word_count=sum(len(s["text"].split()) for s in output["segments"])
        wpm=140 if ctx.language=="hi" else 150
        minutes=word_count/wpm
        qa=load("qa",root=ctx.repo_root)
        try:
            output=ensure_specific(output,lambda:llm.complete_json("script",system,user+"\nMake the game-specific plans, squares, and moves explicit.",SCHEMA),qa.get("min_specific_tokens_per_min",6),wpm)
        except ValueError as exc: raise StageError(ctx.video_id,"script",str(exc)) from exc
        min_words,max_words=(int(wpm*35/60),int(wpm*59/60)) if ctx.template=="shorts" else (int(wpm*8),int(wpm*12))
        if not min_words<=word_count<=max_words:
            output=llm.complete_json("script",system,user+f"\nTarget a total of {min_words} to {max_words} spoken words.",SCHEMA)
            word_count=sum(len(s["text"].split()) for s in output["segments"])
            if not min_words<=word_count<=max_words: raise StageError(ctx.video_id,"script",f"script length {word_count} words is outside {min_words}..{max_words} after regeneration")
        recent=_recent_lines(ctx.repo_root/"data/line_history.sqlite",ctx.language)
        used=set(recent)
        bank_path=ctx.repo_root/"content/lines"/f"{ctx.language}.yaml"
        for beat in facts["beats.json"]:
            bid=beat.get("beat_id")
            line=output["mascot_lines"].get(bid)
            cap=10 if ctx.language=="hi" else 8
            if not line or len(line.split())>cap or line in used:
                if not bank_path.is_file(): raise StageError(ctx.video_id,"script",f"line bank missing: {bank_path}")
                import yaml
                output["mascot_lines"][bid]=select_bank_line(beat["type"],yaml.safe_load(bank_path.read_text(encoding="utf-8")) or {},used,ctx.language)
            line=output["mascot_lines"].get(bid,"")
            checked=llm.complete_json("checks",system,"Check only this mascot line against the quoted joke rules. Return {\"ok\": boolean}. Line: "+line,{"type":"object","required":["ok"],"properties":{"ok":{"type":"boolean"}}})
            if not checked["ok"]:
                if not bank_path.is_file(): raise StageError(ctx.video_id,"script",f"line bank missing: {bank_path}")
                import yaml
                output["mascot_lines"][bid]=select_bank_line(beat["type"],yaml.safe_load(bank_path.read_text(encoding="utf-8")) or {},used,ctx.language)
            used.add(output["mascot_lines"][bid])
        (ctx.spec_dir / "script.json").write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        history_path=ctx.repo_root/"data/line_history.sqlite"; history_path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(history_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS line_history (video_id TEXT, language TEXT, line TEXT)")
            db.executemany("INSERT INTO line_history VALUES (?, ?, ?)",[(ctx.video_id,ctx.language,line) for line in output["mascot_lines"].values()])
    except Exception as exc:
        if isinstance(exc, StageError): raise
        raise StageError(ctx.video_id, "script", str(exc)) from exc
