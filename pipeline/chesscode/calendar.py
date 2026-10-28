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
    def find(kind,lang,tier,lo,hi,taken,before_start=False):
        """Earliest free slot in [lo, hi]; only a teaser may fall before the first calendar day (the Friday ahead of week one)."""
        lo=lo if before_start else max(lo,start)
        for offset in range((min(hi,end)-lo).days+1):
            day=lo+timedelta(days=offset)
            for s in slots:
                if s["kind"]!=kind or day.weekday()!=_WEEKDAYS[s["weekday"]]: continue
                if not (s["tier"]==tier and s["lang"]==lang): continue
                dt=datetime.combine(day,time.fromisoformat(s["time"]),timezone.utc)
                if dt not in occupied and dt not in taken: return dt
        return None
    iso=lambda dt: dt.isoformat().replace("+00:00","Z")
    for tier in _TIERS:
        ordered,left=_order([g for g in games if g.get("tier")==tier])
        year=lambda game: int(game.get("year",start.year))
        teasers=any(s["kind"]=="teaser" and s["tier"]==tier for s in slots)
        # Friday teaser Shorts have their own ids, game_no + 6000, so a game keeps both of its 5000-range Shorts
        ids=lambda game: [f"cc-{year(game):04d}-{n:04d}-{lang}" for n in (int(game["game_no"]),int(game["game_no"])+5000) for lang in ("en","hi")]+([f"cc-{year(game):04d}-{int(game['game_no'])+6000:04d}-{lang}" for lang in ("en","hi")] if teasers else [])
        for game in left:
            for vid in ids(game): unassigned[vid]=f"series rule: no more than two {game.get('series')} games in a row and no other series is left"
        for index,game in enumerate(ordered):
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
            if teasers:  # Friday Short alternates EN/HI and teases next week's long-form: EN Tuesday +4 days, HI Thursday +6 days
                lang,long_dt=(("en",en),("hi",hi))[index%2]
                teaser_id=f"cc-{year(game):04d}-{no+6000:04d}-{lang}"
                teaser=find("teaser",lang,tier,long_dt.date()-timedelta(days=6),long_dt.date()-timedelta(days=4),taken,before_start=True)
                if teaser: taken.add(teaser); assigned[teaser_id]=iso(teaser)
                else: unassigned[teaser_id]=f"no free {lang} Friday teaser slot 4 to 6 days before {long_dt.date()}"
            occupied|=taken
    return dict(sorted(assigned.items(),key=lambda item:item[1])),unassigned

def assign(games: list[dict], tier: str, root=REPO_ROOT) -> dict[str,str]:
    """Publish times for the games of one tier, scheduled together with every other tier so no two uploads collide."""
    wanted={g["game_no"] for g in games if g.get("tier")==tier}
    assigned,_=schedule(games,root)
    return {vid:at for vid,at in assigned.items() if int(vid.split("-")[2])%1000 in {n%1000 for n in wanted}}
