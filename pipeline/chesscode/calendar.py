from datetime import date, datetime, time, timedelta, timezone

from .config import load
from .context import REPO_ROOT

_WEEKDAYS={"mon":0,"tue":1,"wed":2,"thu":3,"fri":4,"sat":5,"sun":6}
_TIERS=("floor","target")

def _order(selected: list[dict]) -> tuple[list[dict], list[dict]]:
    """Series rotate: never more than two games of one series in a row. Returns (ordered, left over)."""
    pending=list(selected); ordered=[]
    while pending:
        last=[g.get("series") for g in ordered[-2:]]
        pick=next((g for g in pending if not last or g.get("series")!=last[-1]),None)
        if pick is None:  # only the previous series remains
            if len(last)==2 and last[0]==last[1]: break
            pick=pending[0]
        ordered.append(pick); pending.remove(pick)
    return ordered,pending

def schedule(games: list[dict], root=REPO_ROOT) -> tuple[dict[str,str], dict[str,str]]:
    """One pass over all tiers, floor first. Returns (video_id -> publish_at, video_id -> reason it has no slot)."""
    cfg=load("calendar",root=root); start=date.fromisoformat(str(cfg["start"])); end=date.fromisoformat(str(cfg["end"]))
    slots=cfg["slots"]; occupied=set(); assigned={}; unassigned={}
    def find(kind,lang,tier,lo,hi,taken):
        """Earliest free slot in [lo, hi]; shorts of the target tier may also use the alternating Friday short."""
        for offset in range((min(hi,end)-max(lo,start)).days+1):
            day=max(lo,start)+timedelta(days=offset)
            for s in slots:
                if s["kind"]!=kind or day.weekday()!=_WEEKDAYS[s["weekday"]]: continue
                if kind=="long" and not (s["tier"]==tier and s["lang"]==lang): continue
                if kind=="short" and not (s["lang"] in (lang,"alternating") and (s["tier"]==tier or (tier=="target" and s["lang"]=="alternating"))): continue
                dt=datetime.combine(day,time.fromisoformat(s["time"]),timezone.utc)
                if dt not in occupied and dt not in taken: return dt
        return None
    iso=lambda dt: dt.isoformat().replace("+00:00","Z")
    for tier in _TIERS:
        ordered,left=_order([g for g in games if g.get("tier")==tier])
        year=lambda game: int(game.get("year",start.year))
        ids=lambda game: [f"cc-{year(game):04d}-{n:04d}-{lang}" for n in (int(game["game_no"]),int(game["game_no"])+5000) for lang in ("en","hi")]
        for game in left:
            for vid in ids(game): unassigned[vid]=f"series rule: no more than two {game.get('series')} games in a row and no other series is left"
        for game in ordered:
            no=int(game["game_no"]); taken=set()
            en=find("long","en",tier,start,end,taken)
            if en: taken.add(en)
            hi=en and find("long","hi",tier,en.date()+timedelta(days=1),end,taken)
            if not hi:
                for vid in ids(game): unassigned[vid]=f"no {tier} long-form slot left before {end}"
                continue
            taken.add(hi)
            for lang,long_dt in (("en",en),("hi",hi)):
                assigned[f"cc-{year(game):04d}-{no:04d}-{lang}"]=iso(long_dt)
                short_id=f"cc-{year(game):04d}-{no+5000:04d}-{lang}"
                short=find("short",lang,tier,long_dt.date()-timedelta(days=3),long_dt.date()-timedelta(days=1),taken)
                if short: taken.add(short); assigned[short_id]=iso(short)
                else: unassigned[short_id]=f"no free {lang} short slot 1 to 3 days before {long_dt.date()}"
            occupied|=taken
    return dict(sorted(assigned.items(),key=lambda item:item[1])),unassigned

def assign(games: list[dict], tier: str, root=REPO_ROOT) -> dict[str,str]:
    """Publish times for the games of one tier, scheduled together with every other tier so no two uploads collide."""
    wanted={g["game_no"] for g in games if g.get("tier")==tier}
    assigned,_=schedule(games,root)
    return {vid:at for vid,at in assigned.items() if int(vid.split("-")[2])%5000 in {n%5000 for n in wanted}}
