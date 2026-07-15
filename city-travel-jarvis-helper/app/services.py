import base64
import logging
from datetime import datetime,timedelta,timezone
from typing import Any
from fastapi import HTTPException
from app import __version__
from app.manifest import CAPABILITY_MAP,READ_CAPABILITIES,WRITE_CAPABILITIES,manifest
from app.maturity import update_metrics
from app.preview_store import preview_store
from app.route_exports import build_gpx,build_kml,build_pdf
from app.scoring import rank_events,rank_places
from app.settings import settings
from app.sheets import REQUIRED_SHEETS
from app.token_service import create_token,read_token
from app.utils import now_iso,new_id,digest,norm,num,haversine
READ_IDS={x['id'] for x in READ_CAPABILITIES};WRITE_IDS={x['id'] for x in WRITE_CAPABILITIES}
logger=logging.getLogger(__name__)

class CityService:
 def __init__(self,storage):self.storage=storage
 def response(self,rid,status,**kw):
  return {'contract_version':'0.1.0','request_id':rid,'trace_id':kw.get('trace_id'),'plugin_id':'city-travel-jarvis','plugin_version':__version__,'status':status,'summary':kw.get('summary'),'data':kw.get('data',{}),'warnings':kw.get('warnings',[]),'sources':kw.get('sources',[]),'freshness':kw.get('freshness'),'questions':kw.get('questions',[]),'preview':kw.get('preview'),'error':kw.get('error')}
 def get_manifest(self):return manifest()
 def validate_setup(self):
  checks=[]
  for sheet in REQUIRED_SHEETS:
   try:self.storage.read_rows(sheet);checks.append({'sheet':sheet,'status':'ok','detail':'accessible'})
   except Exception as e:checks.append({'sheet':sheet,'status':'error','detail':str(e)})
  ready=all(x['status']=='ok' for x in checks);return {'ready':ready,'sheets_ready':ready,'exports_ready':self.storage.drive_ready(),'writes_enabled':settings.writes_enabled,'storage_mode':settings.storage_mode,'version':__version__,'checks':checks}
 def read(self,request):
  if request.capability not in READ_IDS:return self.response(request.request_id,'error',error={'code':'CAPABILITY_NOT_FOUND','retryable':False})
  try:
   data,warnings,sources=self._read(request.capability,request.payload);status='partial' if warnings else 'ok'
   return self.response(request.request_id,status,trace_id=request.trace_id,summary=f'{request.capability} completed',data=data,warnings=warnings,sources=sources,freshness={'as_of':now_iso(),'note':'Live facts are only as fresh as the sources passed by the GPT.'})
  except ValueError as e:return self.response(request.request_id,'needs_input',summary=str(e),questions=[{'id':'missing_input','question':str(e)}],error={'code':'INVALID_REQUEST','retryable':False})
  except Exception as e:return self.response(request.request_id,'error',summary='City capability failed',error={'code':'UPSTREAM_UNAVAILABLE','message':str(e),'retryable':True})
 def preview(self,request):
  if request.capability not in WRITE_IDS:return self.response(request.request_id,'error',error={'code':'CAPABILITY_NOT_FOUND','retryable':False})
  try:plan=self._plan(request.capability,request.payload)
  except (ValueError,TypeError,AttributeError) as e:return self.response(request.request_id,'needs_input',summary=str(e),questions=[{'id':'invalid_payload','question':str(e)}],error={'code':'INVALID_REQUEST','message':str(e),'retryable':False})
  except Exception as e:
   logger.exception('Write preview failed for capability %s',request.capability)
   return self.response(request.request_id,'error',summary='Не удалось подготовить preview',error={'code':'INTERNAL_ERROR','message':'Внутренняя ошибка City Helper. Проверьте Railway logs по request_id.','exception_type':type(e).__name__,'retryable':True})
  plan.update(capability=request.capability,dry_run=request.context.dry_run,created_at=now_iso());dg=digest(plan);pid=preview_store.put({'plan':plan,'digest':dg})
  token=create_token({'action':'city_write','preview_id':pid,'capability':request.capability,'digest':dg,'dry_run':request.context.dry_run})
  pv={'preview_id':pid,'commit_token':token,'expires_in_seconds':settings.preview_ttl_seconds,'digest':dg,'write_diff':plan.get('diff',{}),'warnings':plan.get('warnings',[]),'requires_separate_confirmation':True,'nothing_written':True}
  response=self.response(request.request_id,'preview_ready',summary=plan['summary'],data={'entity_ids':plan.get('entity_ids',{})},warnings=plan.get('warnings',[]),sources=plan.get('sources',[]),preview=pv)
  # Duplicate the opaque commit state at the top level for GPT Actions reliability.
  # The nested preview object remains the canonical contract representation.
  response.update({'preview_id':pid,'capability':request.capability,'commit_token':token,'expires_in_seconds':settings.preview_ttl_seconds})
  return response
 def commit(self,request):
  if request.capability not in WRITE_IDS:return self.response(request.request_id,'error',error={'code':'CAPABILITY_NOT_FOUND','retryable':False})
  if not settings.writes_enabled:return self.response(request.request_id,'rejected',summary='Writes are disabled',error={'code':'WRITES_DISABLED','retryable':False})
  token=read_token(request.commit_token,'city_write')
  if token.get('capability')!=request.capability:return self.response(request.request_id,'rejected',error={'code':'COMMIT_TOKEN_INVALID','retryable':False})
  if token.get('dry_run'):return self.response(request.request_id,'rejected',error={'code':'POLICY_REJECTED','retryable':False})
  stored=preview_store.get(token['preview_id'])
  if stored['digest']!=token['digest']:raise HTTPException(400,'Preview digest mismatch')
  result=self._apply(stored['plan'],token['preview_id'],stored['digest']);preview_store.consume(token['preview_id'])
  return self.response(request.request_id,'committed',summary=stored['plan']['summary'],data=result,warnings=stored['plan'].get('warnings',[]),sources=stored['plan'].get('sources',[]))

 # READ
 def _read(self,cap,p):
  if cap=='city.cockpit':
   places=self.storage.read_rows('Places');exps=self.storage.read_rows('Place_Experiences');routes=self.storage.read_rows('Routes');trips=self.storage.read_rows('Trips');m=self.storage.read_rows('Capability_Maturity')
   return {'places':len(places),'visited_places':len([x for x in places if str(x.get('Status','')).upper() in {'VISITED','LIKED','FAVORITE'}]),'experiences':len(exps),'routes':len(routes),'active_trips':[x for x in trips if str(x.get('Status','')).upper() in {'ACTIVE','CONFIRMED'}][:5],'maturity':{k:len([x for x in m if str(x.get('Level','')).upper()==k.upper()]) for k in ['stable','beta','advisory']}},[],[]
  if cap=='city.place.search':
   c=p.get('candidates') or []
   if not c:raise ValueError('Передайте результаты актуального веб-поиска в payload.candidates')
   if len(c)>settings.max_candidates:raise ValueError(f'Не более {settings.max_candidates} кандидатов')
   ranked=rank_places(c,p,self.storage.read_rows('Places'),self.storage.read_rows('Place_Signals'),self.storage.read_rows('City_Rules'));warnings=[] if all(x.get('checked_at') for x in c) else [{'code':'SOURCE_STALE','message':'У части мест нет времени проверки'}]
   return {'ranked_candidates':ranked,'top':ranked[:5]},warnings,self.sources(c)
  if cap=='city.place.list':
   rows=self.storage.read_rows('Places');city=norm(p.get('city'));status=norm(p.get('status'));q=norm(p.get('query'));out=[]
   for r in rows:
    if city and norm(r.get('City'))!=city:continue
    if status and norm(r.get('Status'))!=status:continue
    if q and q not in norm(f"{r.get('Name')} {r.get('Type')} {r.get('Address')}"):continue
    out.append(r)
   return {'places':out[:int(num(p.get('limit'),100))],'count':len(out)},[],[]
  if cap=='city.experience.summary':return self.experience_summary(p),[],[]
  if cap=='city.trip.plan':return self.trip_plan(p)
  if cap=='city.trip.get':return self.trip_get(p),[],[]
  if cap=='city.trip.next':return self.trip_next(p),[],[]
  if cap.startswith('city.route.') and cap not in {'city.route.get'}:return self.route_review(p,cap.split('.')[-1])
  if cap=='city.route.get':
   rid=str(p.get('route_id',''));route=next((x for x in self.storage.read_rows('Routes') if str(x.get('RouteID'))==rid),None)
   if not route:raise ValueError('Маршрут не найден')
   pts=[x for x in self.storage.read_rows('Route_Points') if str(x.get('RouteID'))==rid];pts.sort(key=lambda x:int(num(x.get('Sequence'))));return {'route':route,'points':pts},[],[]
  if cap=='city.event.rank':
   c=p.get('candidates') or []
   if not c:raise ValueError('Передайте актуальные события в payload.candidates')
   ranked=rank_events(c,p);warnings=[] if all(x.get('checked_at') for x in c) else [{'code':'SOURCE_STALE','message':'Не все события проверены'}];return {'ranked_events':ranked,'top':ranked[:5]},warnings,self.sources(c)
  if cap=='city.area.compare':
   areas=p.get('areas') or []
   if len(areas)<2:raise ValueError('Передайте минимум два района')
   weights=p.get('weights') or {'transport':1,'food':1,'noise':1,'cost':1,'plan_fit':1};out=[]
   for a in areas:
    total=sum(num(a.get('scores',{}).get(k))*num(w,1) for k,w in weights.items());tw=sum(num(w,1) for w in weights.values());out.append({**a,'weighted_score':round(total/tw,2) if tw else 0})
   out.sort(key=lambda x:-x['weighted_score']);return {'areas':out,'recommended':out[0]},[],self.sources(areas)
  if cap=='city.weather.adapt':
   f=p.get('forecast') or {}
   if not f:raise ValueError('Нужен актуальный forecast')
   a=[];rain=num(f.get('precipitation_probability'));wind=num(f.get('wind_kmh'));temp=num(f.get('temperature_c'),20)
   if rain>=50:a.append('Активировать rain fallback и перенести открытые участки')
   if wind>=25:a.append('Избегать открытых велоучастков и набережных против ветра')
   if temp>=29:a.append('Сократить дневную ходьбу и добавить воду/паузу')
   if temp<=-5:a.append('Сократить непрерывные уличные блоки')
   return {'adaptations':a or ['План можно оставить без существенных изменений'],'plan':p.get('plan',[]),'fallbacks':p.get('fallbacks',[])},[],self.sources([f])
  if cap=='city.logistics.departure':
   if not p.get('departure_at'):raise ValueError('Нужно departure_at')
   d=datetime.fromisoformat(str(p['departure_at']).replace('Z','+00:00'));travel=num(p.get('travel_minutes'));buffer=num(p.get('buffer_minutes'),20);luggage=num(p.get('luggage_extra_minutes'),10 if p.get('has_luggage') else 0);control=num(p.get('control_extra_minutes'));leave=d-timedelta(minutes=travel+buffer+luggage+control)
   return {'leave_at':leave.isoformat(),'departure_at':d.isoformat(),'total_reserved_minutes':travel+buffer+luggage+control,'breakdown':{'travel':travel,'buffer':buffer,'luggage':luggage,'control':control}},[],self.sources([p])
  if cap=='city.maturity.status':
   rows=self.storage.read_rows('Capability_Maturity');cid=p.get('capability');rows=[x for x in rows if not cid or str(x.get('CapabilityID'))==cid];return {'capabilities':rows,'count':len(rows)},[],[]
  raise ValueError('Capability not implemented')
 def experience_summary(self,p):
  places={str(x.get('PlaceID')):x for x in self.storage.read_rows('Places')};ratings=self.storage.read_rows('Experience_Ratings');items=self.storage.read_rows('Experience_Items');out=[]
  for e in self.storage.read_rows('Place_Experiences'):
   er=[x for x in ratings if str(x.get('ExperienceID'))==str(e.get('ExperienceID'))];mp={norm(x.get('PersonID')):x for x in er};a=mp.get('p andrew') or mp.get('p-andrew');k=mp.get('p katya') or mp.get('p-katya');verdict='Solo visit'
   if a and k:
    av=num(a.get('OverallRating'));kv=num(k.get('OverallRating'));ar=norm(a.get('WouldReturn'));kr=norm(k.get('WouldReturn'))
    if abs(av-kv)>=3:verdict='Мнения разошлись'
    elif ar in {'yes','да'} and kr in {'yes','да'} and av>=8 and kv>=8:verdict='Оба любим'
    elif ar in {'yes','да'} and kr in {'yes','да'} and av>=7 and kv>=7:verdict='Оба готовы вернуться'
    elif ar!=kr:verdict='Разный вердикт о возвращении'
    else:verdict='Совместное впечатление'
   out.append({'experience':e,'place':places.get(str(e.get('PlaceID')),{}),'ratings':er,'items':[x for x in items if str(x.get('ExperienceID'))==str(e.get('ExperienceID'))],'couple_verdict':verdict})
  return {'experiences':out,'count':len(out)}
 def trip_plan(self,p):
  days=p.get('days') or []
  if not days:raise ValueError('Передайте хотя бы один день поездки в payload.days')
  warnings=[];normdays=[]
  for day in days:
   items=sorted(day.get('items',[]),key=lambda x:str(x.get('start_time','99:99')));prev=None
   for item in items:
    st=self.minutes(item.get('start_time'));en=self.minutes(item.get('end_time'))
    if st is not None and en is not None and en<st:warnings.append({'code':'INVALID_TIME','message':f"{item.get('title')}: окончание раньше начала"})
    if prev is not None and st is not None and st<prev:warnings.append({'code':'ITINERARY_OVERLAP','message':f"Пересечение около {item.get('title')}"})
    if en is not None:prev=max(prev or en,en)
   if len(items)>8:warnings.append({'code':'OVERLOADED_DAY','message':f"{day.get('date')}: более 8 блоков"})
   if num(day.get('planned_steps'))>25000:warnings.append({'code':'HIGH_WALKING_LOAD','message':f"{day.get('date')}: высокая нагрузка"})
   if not day.get('rain_plan'):warnings.append({'code':'NO_RAIN_FALLBACK','message':f"{day.get('date')}: нет плана на дождь"})
   normdays.append({**day,'items':items})
  return ({'trip':p.get('trip',{}),'days':normdays,'ready_to_save':not any(x['code']=='INVALID_TIME' for x in warnings)},warnings,self.sources([i for d in days for i in d.get('items',[])]))
 def trip_get(self,p):
  tid=str(p.get('trip_id',''));trip=next((x for x in self.storage.read_rows('Trips') if str(x.get('TripID'))==tid),None)
  if not trip:raise ValueError('Поездка не найдена')
  days=[x for x in self.storage.read_rows('Trip_Days') if str(x.get('TripID'))==tid];ids={str(x.get('TripDayID')) for x in days};items=[x for x in self.storage.read_rows('Itinerary_Items') if str(x.get('TripDayID')) in ids];return {'trip':trip,'days':days,'items':items}
 def trip_next(self,p):
  items=p.get('items')
  if items is None and p.get('trip_id'):items=self.trip_get(p)['items']
  if not items:raise ValueError('Нет itinerary items')
  now=datetime.fromisoformat(str(p.get('now') or now_iso()).replace('Z','+00:00'));cur=now.hour*60+now.minute;active=None;up=[]
  for x in sorted(items,key=lambda z:str(z.get('StartTime') or z.get('start_time') or '99:99')):
   st=self.minutes(x.get('StartTime') or x.get('start_time'));en=self.minutes(x.get('EndTime') or x.get('end_time'))
   if st is not None and en is not None and st<=cur<=en:active=x
   elif st is not None and st>cur:up.append(x)
  return {'active':active,'next':up[0] if up else None,'later':up[1:4],'fallbacks':p.get('fallbacks',[])[:3]}
 def route_review(self,p,kind):
  pts=p.get('points') or [];distance=num(p.get('distance_km'))
  if not distance and len(pts)>=2:distance=sum(haversine(num(pts[i-1].get('latitude')),num(pts[i-1].get('longitude')),num(pts[i].get('latitude')),num(pts[i].get('longitude'))) for i in range(1,len(pts)))
  if distance<=0:raise ValueError('Нужна distance_km или минимум две точки с координатами')
  warnings=[];risks=[]
  if kind=='cycling':
   profiles=self.storage.read_rows('Cycling_Profiles');pr=p.get('profile') or (profiles[0] if profiles else {});pmin=num(pr.get('PaceMinKmh') or pr.get('pace_min_kmh'),12);pmax=num(pr.get('PaceMaxKmh') or pr.get('pace_max_kmh'),15);duration=[round(distance/pmax*60),round(distance/pmin*60)];tags={norm(x) for x in p.get('risk_tags',[])}
   mapping={'stairs':'лестницы','tram rails':'трамвайные рельсы','rails':'рельсы','high traffic':'интенсивный трафик','unpaved':'грунт','rail crossing':'железнодорожный переход'}
   risks=[v for k,v in mapping.items() if k in tags]
   req=num(p.get('duration_min'))
   if req and not(duration[0]*.8<=req<=duration[1]*1.25):warnings.append({'code':'PACE_MISMATCH','message':'Дистанция и время не совпадают с комфортным темпом'})
  else:
   speed=num(p.get('pace_kmh'),4.7 if kind=='walking' else 4.0);duration=[round(distance/speed*60)]*2
  if kind=='photowalk' and not p.get('light_context'):warnings.append({'code':'NO_LIGHT_CONTEXT','message':'Не переданы время света/заката'})
  if kind=='literary' and any(norm(x.get('confidence')) in {'low','hypothesis','гипотеза'} for x in pts):warnings.append({'code':'HISTORICAL_UNCERTAINTY','message':'Есть точки с низкой уверенностью'})
  return ({'route_type':kind,'distance_km':round(distance,2),'expected_duration_min':duration,'points_count':len(pts),'risks':risks,'bailout_points':p.get('bailout_points',[]),'novelty_percent':p.get('novelty_percent'),'export_ready':bool(pts and all('latitude' in x and 'longitude' in x for x in pts))},warnings,self.sources(pts))

 # WRITE
 def _plan(self,cap,p):
  if cap=='city.place.save':return self.plan_place(p)
  if cap=='city.place.status':
   pid=str(p.get('place_id',''));place=self.find_place(pid,'','')
   if not place or not p.get('status'):raise ValueError('Нужны существующий place_id и status')
   return self.plan('Изменить статус места',{'place_id':pid},updates=[{'sheet':'Places','key':'PlaceID','value':pid,'updates':{'Status':p['status'],'UpdatedAt':now_iso()}}],diff={'before':place,'after':{**place,'Status':p['status']}})
  if cap=='city.place.preference':
   pid=str(p.get('place_id',''))
   if not self.find_place(pid,'','') or not p.get('signal'):raise ValueError('Нужны существующий place_id и signal')
   row={'SignalID':new_id('SIG'),'PlaceID':pid,'PersonID':p.get('person_id','P-ANDREW'),'Signal':p['signal'],'Value':p.get('value',True),'Confidence':p.get('confidence','high'),'Source':p.get('source','user'),'CreatedAt':now_iso()};return self.plan('Сохранить сигнал о месте',{'place_id':pid,'signal_id':row['SignalID']},append={'Place_Signals':[row]},diff={'signal':row})
  if cap=='city.experience.record':return self.plan_experience(p)
  if cap=='city.trip.save':return self.plan_trip(p)
  if cap=='city.trip.update':return self.plan_trip_update(p)
  if cap=='city.route.save':return self.plan_route(p)
  if cap=='city.route.export':return self.plan_export(p)
  if cap=='city.event.save':
   if not p.get('title') or not p.get('city'):raise ValueError('Для события нужны title и city')
   row={'EventID':p.get('event_id') or new_id('EVT'),'Title':p['title'],'City':p['city'],'Venue':p.get('venue',''),'StartAt':p.get('start_at',''),'EndAt':p.get('end_at',''),'Price':p.get('price',''),'Status':p.get('status','SHORTLISTED'),'SourceURL':p.get('source_url',''),'LastCheckedAt':p.get('checked_at',''),'Confidence':p.get('confidence','medium'),'TripID':p.get('trip_id',''),'Notes':p.get('notes','')};return self.plan(f"Сохранить событие {p['title']}",{'event_id':row['EventID']},append={'Events':[row]},diff={'event':row},sources=self.sources([p]))
  if cap=='city.rule.save':
   if not p.get('rule'):raise ValueError('Нужен текст rule')
   row={'RuleID':new_id('RUL'),'Scope':p.get('scope','global'),'Rule':p['rule'],'Priority':p.get('priority',50),'Active':p.get('active',True),'Source':p.get('source','user'),'CreatedAt':now_iso()};return self.plan('Сохранить правило City Jarvis',{'rule_id':row['RuleID']},append={'City_Rules':[row]},diff={'rule':row})
  if cap=='city.journal.record':
   row={'JournalID':new_id('JRN'),'TripID':p.get('trip_id',''),'Date':p.get('date',now_iso()[:10]),'BestMoment':p.get('best_moment',''),'Overrated':p.get('overrated',''),'Missed':p.get('missed',''),'WouldRepeat':p.get('would_repeat',''),'ActualSteps':p.get('actual_steps',''),'ActualDistanceKm':p.get('actual_distance_km',''),'Notes':p.get('notes',''),'CreatedAt':now_iso()};return self.plan('Сохранить запись журнала',{'journal_id':row['JournalID']},append={'Trip_Journal':[row]},diff={'journal':row})
  if cap=='city.maturity.feedback':return self.plan_maturity(p)
  raise ValueError('Capability not implemented')
 def plan_place(self,p):
  name=str(p.get('name','')).strip();city=str(p.get('city','')).strip()
  if not name or not city:raise ValueError('Для места нужны name и city')
  old=self.find_place(p.get('place_id'),name,city);now=now_iso();fields={'Name':name,'Type':p.get('type','OTHER'),'City':city,'Address':p.get('address',''),'Latitude':p.get('latitude',''),'Longitude':p.get('longitude',''),'Website':p.get('website',''),'Status':p.get('status','WANT_TO_VISIT'),'PriceLevel':p.get('price_level',''),'LastCheckedAt':p.get('checked_at',''),'SourceURL':p.get('source_url',''),'SourceType':p.get('source_type','web'),'Confidence':p.get('confidence','medium'),'UpdatedAt':now}
  if old:
   pid=str(old['PlaceID']);return self.plan(f'Обновить место {name}',{'place_id':pid},updates=[{'sheet':'Places','key':'PlaceID','value':pid,'updates':fields}],diff={'before':old,'after':{**old,**fields}},sources=self.sources([p]))
  pid=new_id('PLC');row={'PlaceID':pid,**fields,'CreatedAt':now};return self.plan(f'Сохранить место {name}',{'place_id':pid},append={'Places':[row]},diff={'place':row},sources=self.sources([p]))
 def normalize_experience_payload(self,p):
  if not isinstance(p,dict):raise ValueError('payload для city.experience.record должен быть объектом')
  out=dict(p);raw_place=out.get('place')
  if isinstance(raw_place,str):place={'name':raw_place.strip(),'city':out.get('city') or settings.home_city}
  elif isinstance(raw_place,dict):place=dict(raw_place)
  elif raw_place is None:place={'name':out.get('place_name') or out.get('name') or '','city':out.get('city') or settings.home_city}
  else:raise ValueError('place должен быть строкой с названием или объектом {name, city}')
  if place.get('name') and not place.get('city'):place['city']=out.get('city') or settings.home_city
  out['place']=place

  raw_ratings=out.get('ratings',[])
  if isinstance(raw_ratings,dict):
   named=[]
   for key,value in raw_ratings.items():
    if norm(key) in {'andrew','andrey','андрей','katya','kate','катя'} and isinstance(value,dict):named.append({'person':key,**value})
   raw_ratings=named or [raw_ratings]
  if not isinstance(raw_ratings,list):raise ValueError('ratings должен быть массивом оценок или объектом оценки')
  ratings=[]
  for raw in raw_ratings:
   if not isinstance(raw,dict):raise ValueError('Каждая оценка в ratings должна быть объектом')
   r=dict(raw)
   if 'overall_rating' not in r:r['overall_rating']=r.get('rating',r.get('score',''))
   if 'would_return' not in r:r['would_return']=r.get('wouldReturn',r.get('return_intent','MAYBE'))
   if 'person' not in r:r['person']=r.get('name','Andrew')
   try:score=float(r.get('overall_rating'))
   except (TypeError,ValueError):raise ValueError('overall_rating должен быть числом от 1 до 10')
   if not 1<=score<=10:raise ValueError('overall_rating должен быть в диапазоне 1–10')
   r['overall_rating']=int(score) if score.is_integer() else score
   wr=str(r.get('would_return','MAYBE')).upper()
   if wr not in {'YES','MAYBE','NO'}:raise ValueError('would_return должен быть YES, MAYBE или NO')
   r['would_return']=wr;ratings.append(r)
  out['ratings']=ratings

  raw_items=out.get('items',[])
  if isinstance(raw_items,(str,dict)):raw_items=[raw_items]
  if not isinstance(raw_items,list):raise ValueError('items должен быть массивом блюд/позиций')
  items=[]
  for raw in raw_items:
   if isinstance(raw,str):i={'name':raw}
   elif isinstance(raw,dict):i=dict(raw)
   else:raise ValueError('Каждый элемент items должен быть строкой или объектом')
   if 'name' not in i:i['name']=i.get('item_name',i.get('title',''))
   if 'would_order_again' not in i and 'wouldOrderAgain' in i:i['would_order_again']=i['wouldOrderAgain']
   items.append(i)
  out['items']=items

  context=str(out.get('context','solo')).lower();out['context']=context
  if context=='solo':
   out['party']='Andrew'
   if any(self.person_id(r.get('person','Andrew'))=='P-KATYA' for r in ratings):raise ValueError('Для solo-визита нельзя добавлять оценку Katya')
  elif context=='couple':out['party']='Andrew, Katya'
  return out
 def plan_experience(self,p):
  p=self.normalize_experience_payload(p);placep=p.get('place') or {};pid=str(p.get('place_id') or placep.get('place_id') or '');place=self.find_place(pid,placep.get('name',''),placep.get('city',''));append={};updates=[];now=now_iso()
  if not place:
   if not placep.get('name') or not placep.get('city'):raise ValueError('Нужно place_id или place.name и place.city')
   pid=new_id('PLC');place={'PlaceID':pid,'Name':placep['name'],'Type':placep.get('type','OTHER'),'City':placep['city'],'Address':placep.get('address',''),'Latitude':placep.get('latitude',''),'Longitude':placep.get('longitude',''),'Website':placep.get('website',''),'Status':'VISITED','PriceLevel':placep.get('price_level',''),'LastCheckedAt':placep.get('checked_at',''),'SourceURL':placep.get('source_url',''),'SourceType':'user','Confidence':'high','CreatedAt':now,'UpdatedAt':now};append['Places']=[place]
  else:pid=str(place['PlaceID']);updates.append({'sheet':'Places','key':'PlaceID','value':pid,'updates':{'Status':'VISITED','UpdatedAt':now}})
  eid=new_id('EXP');exp={'ExperienceID':eid,'PlaceID':pid,'VisitDate':p.get('visit_date',now[:10]),'Context':p.get('context','solo'),'Party':p.get('party','Andrew' if p.get('context','solo')=='solo' else 'Andrew, Katya'),'TripID':p.get('trip_id',''),'SpendAmount':p.get('spend_amount',''),'Currency':p.get('currency','RUB'),'OverallNote':p.get('overall_note',''),'CreatedAt':now};append['Place_Experiences']=[exp]
  ratings=[]
  for r in p.get('ratings',[]):ratings.append({'RatingID':new_id('RAT'),'ExperienceID':eid,'PersonID':r.get('person_id') or self.person_id(r.get('person','Andrew')),'OverallRating':r.get('overall_rating',''),'WouldReturn':str(r.get('would_return','MAYBE')).upper(),'FoodRating':r.get('food_rating',''),'AtmosphereRating':r.get('atmosphere_rating',''),'ServiceRating':r.get('service_rating',''),'ValueRating':r.get('value_rating',''),'BestPart':r.get('best_part',''),'WorstPart':r.get('worst_part',''),'Comment':r.get('comment',''),'CreatedAt':now})
  if not ratings:raise ValueError('Нужна хотя бы одна оценка в ratings')
  append['Experience_Ratings']=ratings
  items=[]
  for i in p.get('items',[]):items.append({'ItemID':new_id('ITM'),'ExperienceID':eid,'PersonID':i.get('person_id') or self.person_id(i.get('person','Andrew')),'ItemName':i.get('name',''),'ItemType':i.get('type','dish'),'Price':i.get('price',''),'Rating':i.get('rating',''),'WouldOrderAgain':i.get('would_order_again',''),'Comment':i.get('comment','')})
  if items:append['Experience_Items']=items
  return self.plan('Записать впечатление о посещении',{'place_id':pid,'experience_id':eid},append=append,updates=updates,diff={'experience':exp,'ratings':ratings,'items':items})
 def plan_trip(self,p):
  if not p.get('title') or not p.get('city'):raise ValueError('Для поездки нужны title и city')
  tid=p.get('trip_id') or new_id('TRP');now=now_iso();trip={'TripID':tid,'Title':p['title'],'City':p['city'],'StartDate':p.get('start_date',''),'EndDate':p.get('end_date',''),'Status':p.get('status','DRAFT'),'BaseArea':p.get('base_area',''),'Lodging':p.get('lodging',''),'Purpose':p.get('purpose',''),'Budget':p.get('budget',''),'Pace':p.get('pace','balanced'),'Party':p.get('party','solo'),'PrimaryMode':p.get('primary_mode','walking'),'Notes':p.get('notes',''),'CreatedAt':now,'UpdatedAt':now};append={'Trips':[trip]};days=[];items=[]
  for day in p.get('days',[]):
   did=day.get('trip_day_id') or new_id('DAY');days.append({'TripDayID':did,'TripID':tid,'Date':day.get('date',''),'Theme':day.get('theme',''),'Status':day.get('status','PLANNED'),'PlannedSteps':day.get('planned_steps',''),'PlannedDistanceKm':day.get('planned_distance_km',''),'RainPlan':day.get('rain_plan',''),'FatiguePlan':day.get('fatigue_plan',''),'Notes':day.get('notes','')})
   for n,i in enumerate(day.get('items',[]),1):items.append(self.itinerary(i,did,n))
  if days:append['Trip_Days']=days
  if items:append['Itinerary_Items']=items
  return self.plan(f"Сохранить поездку {p['title']}",{'trip_id':tid},append=append,diff={'trip':trip,'days':len(days),'items':len(items)})
 def plan_trip_update(self,p):
  tid=str(p.get('trip_id',''));trip=next((x for x in self.storage.read_rows('Trips') if str(x.get('TripID'))==tid),None)
  if not trip:raise ValueError('Поездка не найдена')
  allowed={'Title','City','StartDate','EndDate','Status','BaseArea','Lodging','Purpose','Budget','Pace','Party','PrimaryMode','Notes'};up={k:v for k,v in (p.get('updates') or {}).items() if k in allowed};up['UpdatedAt']=now_iso();updates=[{'sheet':'Trips','key':'TripID','value':tid,'updates':up}]
  for u in p.get('itinerary_updates',[]):
   if u.get('item_id'):updates.append({'sheet':'Itinerary_Items','key':'ItemID','value':u['item_id'],'updates':u.get('updates',{})})
  return self.plan('Обновить активную поездку',{'trip_id':tid},updates=updates,diff={'updates':len(updates)})
 def plan_route(self,p):
  pts=p.get('points') or []
  if not p.get('title') or len(pts)<2:raise ValueError('Для маршрута нужны title и минимум две точки')
  rid=p.get('route_id') or new_id('RTE');dist=num(p.get('distance_km')) or sum(haversine(num(pts[i-1].get('latitude')),num(pts[i-1].get('longitude')),num(pts[i].get('latitude')),num(pts[i].get('longitude'))) for i in range(1,len(pts)))
  route={'RouteID':rid,'Title':p['title'],'RouteType':p.get('route_type','walking'),'City':p.get('city',settings.home_city),'StartName':p.get('start_name',pts[0].get('name','')),'EndName':p.get('end_name',pts[-1].get('name','')),'DistanceKm':round(dist,2),'DurationMin':p.get('duration_min',''),'PaceKmh':p.get('pace_kmh',''),'Difficulty':p.get('difficulty','moderate'),'Mode':p.get('mode','chill'),'Status':p.get('status','SAVED'),'TripID':p.get('trip_id',''),'MapURL':p.get('map_url',''),'GPXURL':'','KMLURL':'','PDFURL':'','NoveltyPercent':p.get('novelty_percent',''),'RiskLevel':p.get('risk_level',''),'SourceSummary':p.get('source_summary',''),'CreatedAt':now_iso()};rows=[]
  for n,x in enumerate(pts,1):
   if 'latitude' not in x or 'longitude' not in x:raise ValueError('Каждая точка должна иметь latitude и longitude')
   rows.append({'RoutePointID':new_id('RTP'),'RouteID':rid,'Sequence':x.get('sequence',n),'Name':x.get('name',''),'Latitude':x['latitude'],'Longitude':x['longitude'],'PointType':x.get('point_type','WAYPOINT'),'PlaceID':x.get('place_id',''),'StopMinutes':x.get('stop_minutes',''),'Notes':x.get('notes','')})
  return self.plan(f"Сохранить маршрут {p['title']}",{'route_id':rid},append={'Routes':[route],'Route_Points':rows},diff={'route':route,'points':len(rows)},sources=self.sources(pts))
 def plan_export(self,p):
  rid=str(p.get('route_id',''));route=next((x for x in self.storage.read_rows('Routes') if str(x.get('RouteID'))==rid),None);pts=[x for x in self.storage.read_rows('Route_Points') if str(x.get('RouteID'))==rid]
  if not route or len(pts)<2:raise ValueError('Маршрут не найден или недостаточно точек')
  rp={'title':route.get('Title'),'points':[{'sequence':x.get('Sequence'),'name':x.get('Name'),'latitude':x.get('Latitude'),'longitude':x.get('Longitude')} for x in pts]};formats=[str(x).lower() for x in p.get('formats',['gpx','kml'])];safe=''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in str(route.get('Title',rid)))[:80];files=[]
  if 'gpx' in formats:files.append(self.file(f'{safe}.gpx','application/gpx+xml',build_gpx(rp),'GPXURL',rid))
  if 'kml' in formats:files.append(self.file(f'{safe}.kml','application/vnd.google-earth.kml+xml',build_kml(rp),'KMLURL',rid))
  if 'pdf' in formats:
   guide=p.get('guide') or {'title':route.get('Title'),'sections':[{'title':'Точки маршрута','items':[{'label':str(x.get('Sequence')),'text':x.get('Name') or 'Точка'} for x in pts]}]};files.append(self.file(f'{safe}.pdf','application/pdf',build_pdf(guide),'PDFURL',rid))
  if not files:raise ValueError('Поддерживаются gpx, kml, pdf')
  warnings=[] if self.storage.drive_ready() else [{'code':'DRIVE_NOT_READY','message':'Для commit нужен GOOGLE_DRIVE_FOLDER_ID'}]
  return self.plan(f"Экспортировать маршрут {route.get('Title')}",{'route_id':rid},files=files,diff={'files':[x['name'] for x in files]},warnings=warnings)
 def plan_maturity(self,p):
  cid=str(p.get('capability',''))
  if cid not in CAPABILITY_MAP:raise ValueError('Неизвестная capability')
  rows=self.storage.read_rows('Capability_Maturity');cur=next((x for x in rows if str(x.get('CapabilityID'))==cid),None) or {'CapabilityID':cid,'Title':CAPABILITY_MAP[cid]['title'],'Level':'BETA','RealTests':0,'SuccessfulTests':0,'CriticalIssues':0,'KnownIssues':0,'AvgAccuracy':0,'AvgPracticalRating':0}
  after=update_metrics(cur,p);after['LastValidatedAt']=p.get('test_date',now_iso());apply=bool(p.get('apply_recommended_promotion',settings.auto_promote_maturity))
  if apply:after['Level']=after.get('PromotionRecommendation',after.get('Level'))
  log={'TestID':new_id('TST'),'CapabilityID':cid,'TestDate':p.get('test_date',now_iso()),'Scenario':p.get('scenario',''),'Outcome':p.get('outcome','SUCCESS'),'AccuracyRating':p.get('accuracy_rating',''),'FreshnessRating':p.get('freshness_rating',''),'PracticalRating':p.get('practical_rating',''),'CriticalIssue':p.get('critical_issue',False),'IssueSummary':p.get('issue_summary',''),'Notes':p.get('notes','')};append={'Maturity_Test_Log':[log]};updates=[]
  if any(str(x.get('CapabilityID'))==cid for x in rows):updates=[{'sheet':'Capability_Maturity','key':'CapabilityID','value':cid,'updates':after}]
  else:append['Capability_Maturity']=[after]
  return self.plan('Записать реальный тест capability',{'test_id':log['TestID'],'capability':cid},append=append,updates=updates,diff={'before':cur,'after':after,'promotion_applied':apply})

 # helpers
 def plan(self,summary,ids,append=None,updates=None,files=None,diff=None,warnings=None,sources=None):return {'summary':summary,'entity_ids':ids,'append':append or {},'updates':updates or [],'files':files or [],'diff':diff or {},'warnings':warnings or [],'sources':sources or []}
 def _apply(self,plan,pid,dg):
  ac=self.storage.append_many(plan.get('append',{}));uc={}
  for u in plan.get('updates',[]):uc[u['sheet']]=uc.get(u['sheet'],0)+self.storage.update_matching_rows(u['sheet'],u['key'],u['value'],u['updates'])
  fr=[];ru={}
  for f in plan.get('files',[]):
   url=self.storage.upload_file(f['name'],f['mime_type'],base64.b64decode(f['content_b64']));fr.append({'name':f['name'],'url':url,'mime_type':f['mime_type']});ru.setdefault(f['route_id'],{})[f['route_field']]=url
  for rid,up in ru.items():uc['Routes']=uc.get('Routes',0)+self.storage.update_matching_rows('Routes','RouteID',rid,up)
  aid=new_id('AUD');self.storage.append_rows('Write_Log',[{'AuditID':aid,'PreviewID':pid,'Capability':plan.get('capability'),'EntityType':','.join(plan.get('entity_ids',{}).keys()),'EntityID':','.join(str(x) for x in plan.get('entity_ids',{}).values()),'Action':'COMMIT','CommittedAt':now_iso(),'Digest':dg,'Summary':plan.get('summary','')}]);ac['Write_Log']=1
  return {'audit_id':aid,'preview_id':pid,'capability':plan.get('capability'),'append_counts':ac,'update_counts':uc,'files':fr,'entity_ids':plan.get('entity_ids',{})}
 def find_place(self,pid,name,city):
  rows=self.storage.read_rows('Places')
  if pid:return next((x for x in rows if str(x.get('PlaceID'))==str(pid)),None)
  return next((x for x in rows if norm(x.get('Name'))==norm(name) and norm(x.get('City'))==norm(city)),None)
 def person_id(self,name):return 'P-KATYA' if norm(name) in {'катя','katya','kate'} else ('P-ANDREW' if norm(name) in {'андрей','andrew','andrey'} else 'P-'+norm(name).replace(' ','-').upper()[:30])
 def itinerary(self,i,did,n):return {'ItemID':i.get('item_id') or new_id('ITI'),'TripDayID':did,'Sequence':i.get('sequence',n),'StartTime':i.get('start_time',''),'EndTime':i.get('end_time',''),'PlaceID':i.get('place_id',''),'EventID':i.get('event_id',''),'ActivityType':i.get('activity_type','OTHER'),'Title':i.get('title',''),'Address':i.get('address',''),'Latitude':i.get('latitude',''),'Longitude':i.get('longitude',''),'TravelMinutesFromPrevious':i.get('travel_minutes_from_previous',''),'Status':i.get('status','PLANNED'),'BookingRef':i.get('booking_ref',''),'SourceURL':i.get('source_url',''),'Notes':i.get('notes','')}
 def file(self,name,mime,content,field,rid):return {'name':name,'mime_type':mime,'content_b64':base64.b64encode(content).decode(),'route_field':field,'route_id':rid}
 def sources(self,items):
  out=[];seen=set()
  for x in items:
   url=x.get('source_url') or x.get('SourceURL')
   if url and url not in seen:seen.add(url);out.append({'url':url,'type':x.get('source_type','web'),'checked_at':x.get('checked_at') or x.get('LastCheckedAt'),'confidence':x.get('confidence','medium')})
  return out
 def minutes(self,v):
  if v in (None,''):return None
  try:h,m=str(v).split(':',1);return int(h)*60+int(m[:2])
  except:return None
