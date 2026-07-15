from datetime import datetime, timezone
from typing import Any
from app.utils import num, clamp, norm

def age_days(item):
    raw=item.get("checked_at") or item.get("last_checked_at")
    if not raw:return None
    try:
        dt=datetime.fromisoformat(str(raw).replace("Z","+00:00")); dt=dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc); return max(0,(datetime.now(timezone.utc)-dt).total_seconds()/86400)
    except ValueError:return None

def rank_places(candidates:list[dict[str,Any]],payload:dict[str,Any],places:list[dict],signals:list[dict],rules:list[dict]):
    max_walk=num(payload.get("max_walk_minutes"),25); budget=int(num(payload.get("budget_level"),3)); context=norm(payload.get("context") or "solo"); city=norm(payload.get("city")); travel=bool(payload.get("is_travel",city not in {"","москва","moscow"}))
    pidx={(norm(x.get("Name")),norm(x.get("City"))):x for x in places}; sidx={}
    for s in signals:sidx.setdefault(str(s.get("PlaceID","")),[]).append(s)
    avoid_closed=any(str(r.get("Active","")).lower() in {"true","1","yes"} and "закрыт" in norm(r.get("Rule")) for r in rules)
    out=[]
    for c in candidates:
        item=dict(c); stored=pidx.get((norm(item.get("name")),norm(item.get("city")))) or pidx.get((norm(item.get("name")),city)); score=50.; reasons=[]; warnings=[]; rejected=False
        if stored:item["place_id"]=stored.get("PlaceID"); item["memory_status"]=stored.get("Status")
        status=norm(item.get("status") or (stored or {}).get("Status"))
        if status in {"closed","закрыто","закрыт"}: score-=200 if avoid_closed else 80; rejected=avoid_closed; warnings.append("место отмечено как закрыто")
        if item.get("open_now") is False:score-=90;warnings.append("сейчас закрыто")
        elif item.get("open_now") is True:score+=12;reasons.append("открыто сейчас")
        walk=num(item.get("walk_minutes"),-1)
        if walk>=0:
            if walk<=max_walk:score+=max(0,12-walk*.3);reasons.append(f"около {walk:.0f} мин пешком")
            else:score-=min(35,(walk-max_walk)*1.5);warnings.append("дальше желаемой зоны")
        price=int(num(item.get("price_level"),0))
        if price>budget:score-=(price-budget)*14;warnings.append("дороже заданного бюджета")
        elif price:score+=5
        rating=num(item.get("rating")); score+=clamp((rating-3.5)*8,-8,12) if rating else 0
        tags={norm(x) for x in item.get("fit_tags",[])}
        if context in tags:score+=14;reasons.append(f"подходит для {context}")
        if context=="solo" and "дорого одному" in tags:score-=20;warnings.append("может быть дороговато одному")
        if travel and item.get("is_chain_in_home_city"):score-=22;warnings.append("сеть доступна в домашнем городе")
        age=age_days(item)
        if age is None:score-=5;warnings.append("нет времени последней проверки")
        elif age<=2:score+=8;reasons.append("проверено недавно")
        elif age>30:score-=18;warnings.append("данные могли устареть")
        elif age>7:score-=6
        conf=norm(item.get("confidence")); score += 6 if conf=="high" else (-8 if conf=="low" else 0)
        if stored:
            for s in sidx.get(str(stored.get("PlaceID")),[]):
                name=norm(s.get("Signal")); positive=norm(s.get("Value")) in {"true","yes","да","liked","favorite","1"}
                if name in {"liked","favorite","понравилось"} and positive:score+=16;reasons.append("понравилось раньше")
                if name in {"not for me","not_for_me","не понравилось"} and positive:score-=35;warnings.append("раньше не понравилось")
                if name in {"expensive solo","дороговато одному"} and context=="solo" and positive:score-=18;warnings.append("сохранён сигнал: дороговато одному")
        item.update(score=round(score,2),rejected=rejected,reasons=reasons,warnings=warnings);out.append(item)
    return sorted(out,key=lambda x:(x["rejected"],-x["score"],num(x.get("walk_minutes"),999)))

def rank_events(candidates,payload):
    budget=num(payload.get("max_price"),10**9);max_travel=num(payload.get("max_travel_minutes"),60);interests={norm(x) for x in payload.get("interests",[])};out=[]
    for c in candidates:
        item=dict(c);score=50.;warnings=[]
        if num(item.get("price"))>budget:score-=30;warnings.append("выше бюджета")
        if num(item.get("travel_minutes"))>max_travel:score-=25;warnings.append("слишком далеко")
        score+=10*len({norm(x) for x in item.get("tags",[])}&interests)
        if item.get("tickets_available") is False:score-=100;warnings.append("билетов нет")
        if item.get("checked_at"):score+=5
        else:warnings.append("актуальность не подтверждена")
        item.update(score=round(score,2),warnings=warnings);out.append(item)
    return sorted(out,key=lambda x:-x["score"])
