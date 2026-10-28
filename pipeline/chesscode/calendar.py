from datetime import date, datetime, time, timedelta, timezone

from .config import load

_WEEKDAYS={"mon":0,"tue":1,"wed":2,"thu":3,"fri":4,"sat":5,"sun":6}

def assign(games: list[dict], tier: str) -> dict[str,str]:
    cfg=load("calendar"); start=date.fromisoformat(str(cfg["start"])); end=date.fromisoformat(str(cfg["end"]))
    slots=[s for s in cfg["slots"] if s["tier"]==tier]
    selected=[g for g in games if g.get("tier")==tier]
    # Interleave series in first-seen order while preserving each series' game order.
    series_order=list(dict.fromkeys(g.get("series") for g in selected))
    if len(series_order)>1:
        queues={s:[g for g in selected if g.get("series")==s] for s in series_order}
        selected=[queues[s].pop(0) for _ in range(len(selected)//len(series_order)+1) for s in series_order if queues[s]]
    result={}; occupied=set()
    for index,game in enumerate(selected):
        game_no=int(game["game_no"]); year=int(game.get("year",start.year)); series=game.get("series","")
        def slot_for(kind,lang,not_before=None,not_after=None):
            matches=[s for s in slots if s["kind"]==kind and s["lang"] in (lang,"alternating") and s["game"] in ("A" if tier=="floor" else "B","A")]
            for offset in range((end-start).days+1):
                day=start+timedelta(days=offset)
                if not any(day.weekday()==_WEEKDAYS[s["weekday"]] for s in matches): continue
                if not_before and day<not_before or not_after and day>not_after: continue
                for s in matches:
                    if day.weekday()!=_WEEKDAYS[s["weekday"]]: continue
                    dt=datetime.combine(day,time.fromisoformat(s["time"]),timezone.utc)
                    if dt in occupied: continue
                    occupied.add(dt); return dt
            raise ValueError(f"no {tier} {kind} slot for game {game_no} in calendar range")
        en=slot_for("long","en"); hi=slot_for("long","hi",not_before=en.date()+timedelta(days=1))
        for lang,long_dt in (("en",en),("hi",hi)):
            base=f"cc-{year:04d}-{game_no:04d}-{lang}"
            short=slot_for("short",lang,not_before=long_dt.date()-timedelta(days=3),not_after=long_dt.date()-timedelta(days=1))
            result[base]=long_dt.isoformat().replace("+00:00","Z")
            result[f"cc-{year:04d}-{game_no+5000:04d}-{lang}"]=short.isoformat().replace("+00:00","Z")
    return dict(sorted(result.items(),key=lambda item:item[1]))
