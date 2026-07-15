from app.manifest import CAPABILITY_MAP
from app.sheets import REQUIRED_SHEETS

def memory_seed():
    seed={s:[] for s in REQUIRED_SHEETS}
    seed["People"]=[{"PersonID":"P-ANDREW","DisplayName":"Andrew","Role":"owner","Active":True,"Notes":"Основной пользователь"},{"PersonID":"P-KATYA","DisplayName":"Katya","Role":"partner","Active":True,"Notes":"Катя; отдельные оценки совместных посещений"}]
    seed["Cycling_Profiles"]=[{"ProfileID":"CYC-CHILL","Name":"Chill Moscow","Bike":"Stern Motion 4.0","DefaultStart":"ЖК Символ","PaceMinKmh":12,"PaceMaxKmh":15,"DurationMin":60,"DurationMax":80,"TrafficTolerance":"low","SurfacePreference":"asphalt; limited compact ground","AvoidStairs":True,"AvoidRails":True,"Notes":"Спокойная поездка без жести","Active":True}]
    seed["City_Rules"]=[
      {"RuleID":"RUL-1","Scope":"global","Rule":"Не рекомендовать закрытые места без повторной проверки","Priority":100,"Active":True,"Source":"user"},
      {"RuleID":"RUL-2","Scope":"travel","Rule":"В поездках избегать сетей, доступных в Москве","Priority":80,"Active":True,"Source":"user"},
      {"RuleID":"RUL-3","Scope":"solo","Rule":"Не предлагать дорогой ресторан одному без причины","Priority":80,"Active":True,"Source":"user"},
      {"RuleID":"RUL-4","Scope":"history","Rule":"Разделять подтверждённый факт, книжное место и гипотезу","Priority":100,"Active":True,"Source":"user"},
    ]
    for cid,c in CAPABILITY_MAP.items():
        level="BETA"
        for tag in c.get("tags",[]):
            if tag.startswith("maturity:"): level=tag.split(":",1)[1].upper()
        seed["Capability_Maturity"].append({"CapabilityID":cid,"Title":c["title"],"Level":level,"RealTests":0,"SuccessfulTests":0,"CriticalIssues":0,"KnownIssues":0,"AvgAccuracy":0,"AvgPracticalRating":0,"LastValidatedAt":"","PromotionRecommendation":level,"Notes":"Initial v1.0.0 maturity"})
    return seed
