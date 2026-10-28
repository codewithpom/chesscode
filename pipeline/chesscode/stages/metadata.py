import json
import re

from ..calendar import assign
from ..context import StageError

INPUTS=["game.json","script.json","timeline.json","content/games.yaml","config/calendar.yaml"]
OUTPUTS=["metadata.json"]
_SERIES={"legendary_games":"Legendary Games","indian_chess_heroes":"Indian Chess Heroes","opening_explained":"Opening Explained","blunder_hall_of_fame":"Blunder Hall of Fame"}

def build_description(hook: str, chapters: list[dict], game: dict, series_name: str, credits: list[str], video_id: str) -> str:
    game_facts=game.get("game",game)
    lines=[hook,""]
    chapters=[*chapters]
    if chapters and chapters[0].get("start_ms")!=0: chapters.insert(0,{"title":"Opening","start_ms":0})
    for chapter in chapters:
        ms=int(chapter["start_ms"]); lines.append(f"{ms//60000:02d}:{(ms//1000)%60:02d} {chapter['title']}")
    names=game_facts.get("white",{}).get("name","White")+" vs "+game_facts.get("black",{}).get("name","Black")
    facts=[names,game_facts.get("event",""),str(game_facts.get("date","")),game_facts.get("opening","") ,f"Result: {game_facts.get('result','')}"]
    if game_facts.get("source")=="lichess": facts.append("Game source: Lichess")
    lines.extend(["", " · ".join(x for x in facts if x), f"{series_name} chess analysis. Subscribe for more games."])
    lines.extend(credits)
    if video_id.rsplit("-",1)[0].split("-")[-1].isdigit() and int(video_id.rsplit("-",1)[0].split("-")[-1])>=5000: lines.append("#Shorts")
    lines.extend(["",f"ccid: {video_id}"])
    text="\n".join(lines)
    if len(text)>5000: raise ValueError("description exceeds 5000 characters")
    return text

def pick_title(titles: list[str], scorer) -> str:
    valid=[t for t in titles if len(t)<=70 and not any(re.fullmatch(r"[A-Z]{3,}",word.strip(".,!?;:'\"()[]")) for word in t.split())]
    if not valid: raise ValueError("no title meets the 70-character and capitalization rules")
    choice=scorer(valid)
    return choice if choice in valid else valid[0]

def run(ctx):
    try:
        read=lambda name:json.loads((ctx.spec_dir/name).read_text(encoding="utf-8"))
        game=read("game.json"); script=read("script.json"); timeline=read("timeline.json")
        import yaml
        games=yaml.safe_load((ctx.repo_root/"content/games.yaml").read_text(encoding="utf-8")) or []
        schedule=assign(games,game.get("tier","floor")); publish=schedule.get(ctx.video_id)
        if not publish: raise ValueError(f"calendar has no slot for {ctx.video_id}")
        title=pick_title(script["titles"],lambda valid:valid[0]); series=_SERIES[game["series"]]
        description=build_description(script["hook"],timeline["chapters"],game,series,[],ctx.video_id)
        result={"title":title,"description":description,"tags":["chess",series.lower()],"playlist":series,"publish_at":publish,"default_language":ctx.language,"made_for_kids":False,"contains_synthetic_media":False,"thumbnail":"thumb.png","chapters":timeline["chapters"]}
        (ctx.spec_dir/"metadata.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    except Exception as exc: raise StageError(ctx.video_id,"metadata",str(exc)) from exc
