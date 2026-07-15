from typing import Any
from app.utils import num

def recommend(row: dict[str, Any]) -> str:
    level=str(row.get("Level","ADVISORY")).upper(); tests=int(num(row.get("RealTests"))); ok=int(num(row.get("SuccessfulTests"))); critical=int(num(row.get("CriticalIssues"))); acc=num(row.get("AvgAccuracy")); practical=num(row.get("AvgPracticalRating")); rate=ok/tests if tests else 0
    if critical:return level
    if level=="ADVISORY" and tests>=3 and rate>=.67 and practical>=6.5:return "BETA"
    if level=="BETA" and tests>=10 and rate>=.8 and acc>=8 and practical>=8:return "STABLE"
    return level

def update_metrics(row: dict[str, Any], f: dict[str, Any]) -> dict[str, Any]:
    tests=int(num(row.get("RealTests"))); new=tests+1; success=int(num(row.get("SuccessfulTests")))+(1 if str(f.get("outcome","SUCCESS")).upper() in {"SUCCESS","PARTIAL_SUCCESS"} else 0)
    acc=num(f.get("accuracy_rating")); pr=num(f.get("practical_rating")); olda=num(row.get("AvgAccuracy")); oldp=num(row.get("AvgPracticalRating"))
    out={**row,"RealTests":new,"SuccessfulTests":success,"CriticalIssues":int(num(row.get("CriticalIssues")))+(1 if f.get("critical_issue") else 0),"KnownIssues":int(num(row.get("KnownIssues")))+(1 if f.get("issue_summary") else 0),"AvgAccuracy":round(((olda*tests)+acc)/new,2) if acc else olda,"AvgPracticalRating":round(((oldp*tests)+pr)/new,2) if pr else oldp}
    out["PromotionRecommendation"]=recommend(out); return out
