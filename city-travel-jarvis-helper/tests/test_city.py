from datetime import datetime,timezone
import pytest
from app.models import PluginRequest,CommitRequest
from app.seed import memory_seed
from app.services import CityService
from app.settings import settings
from app.storage.memory import MemoryStorage
@pytest.fixture
def s():object.__setattr__(settings,'writes_enabled',True);return CityService(MemoryStorage(memory_seed()))
def r(cap,p=None,dry=False):return PluginRequest(request_id='REQ-1000',capability=cap,payload=p or {},context={'dry_run':dry})
def c(s,pv,cap):return s.commit(CommitRequest(request_id='REQ-C',capability=cap,commit_token=pv['commit_token'],confirmed=True))
def test_manifest(s):assert s.get_manifest()['contract_version']=='0.1.0' and len(s.get_manifest()['capabilities'])==29
def test_setup(s):assert s.validate_setup()['ready'] and s.validate_setup()['exports_ready']
def test_unknown(s):assert s.read(r('city.nope'))['error']['code']=='CAPABILITY_NOT_FOUND'
def test_cockpit(s):assert s.read(r('city.cockpit'))['data']['maturity']['stable']>0
def test_place_requires_candidates(s):assert s.read(r('city.place.search'))['status']=='needs_input'
def test_closed_place(s):
 st=s.storage;st.append_rows('Places',[{'PlaceID':'P1','Name':'Ockam','City':'Санкт-Петербург','Status':'CLOSED'}]);out=s.read(r('city.place.search',{'city':'Санкт-Петербург','candidates':[{'name':'Ockam','city':'Санкт-Петербург','open_now':True,'checked_at':datetime.now(timezone.utc).isoformat()}]}));assert out['data']['top'][0]['rejected']
def test_chain_penalty(s):
 out=s.read(r('city.place.search',{'city':'Санкт-Петербург','is_travel':True,'candidates':[{'name':'Chain','city':'Санкт-Петербург','open_now':True,'is_chain_in_home_city':True,'checked_at':datetime.now(timezone.utc).isoformat()},{'name':'Local','city':'Санкт-Петербург','open_now':True,'checked_at':datetime.now(timezone.utc).isoformat()}]}));assert out['data']['top'][0]['name']=='Local'
def test_trip_overlap(s):assert any(x['code']=='ITINERARY_OVERLAP' for x in s.read(r('city.trip.plan',{'days':[{'date':'2026-07-15','items':[{'title':'A','start_time':'10:00','end_time':'12:00'},{'title':'B','start_time':'11:00','end_time':'13:00'}]}]}))['warnings'])
def test_cycling(s):
 out=s.read(r('city.route.cycling',{'distance_km':15,'duration_min':70,'risk_tags':['tram rails']}));assert out['data']['expected_duration_min']==[60,75] and 'трамвайные рельсы' in out['data']['risks']
def test_photowalk(s):assert any(x['code']=='NO_LIGHT_CONTEXT' for x in s.read(r('city.route.photowalk',{'distance_km':4}))['warnings'])
def test_weather(s):assert len(s.read(r('city.weather.adapt',{'forecast':{'precipitation_probability':80,'wind_kmh':30}}))['data']['adaptations'])==2
def test_departure(s):assert s.read(r('city.logistics.departure',{'departure_at':'2026-07-15T18:00:00+03:00','travel_minutes':45,'buffer_minutes':20,'has_luggage':True}))['data']['total_reserved_minutes']==75
def test_place_preview_no_write(s):
 pv=s.preview(r('city.place.save',{'name':'New','city':'Москва'}));assert pv['status']=='preview_ready' and pv['commit_token']==pv['preview']['commit_token'] and pv['preview_id']==pv['preview']['preview_id'] and s.storage.read_rows('Places')==[]
def test_place_commit(s):
 pv=s.preview(r('city.place.save',{'name':'New','city':'Москва'}));assert c(s,pv,'city.place.save')['status']=='committed' and s.storage.read_rows('Places')[0]['Name']=='New'
def test_solo_experience(s):
 pv=s.preview(r('city.experience.record',{'place':{'name':'Cafe','city':'Москва'},'context':'solo','ratings':[{'person':'Andrew','overall_rating':8,'would_return':'YES'}]}));c(s,pv,'city.experience.record');assert s.storage.read_rows('Experience_Ratings')[0]['PersonID']=='P-ANDREW'
def test_couple_verdict(s):
 pv=s.preview(r('city.experience.record',{'place':{'name':'Cafe','city':'Москва'},'context':'couple','ratings':[{'person':'Andrew','overall_rating':9,'would_return':'YES'},{'person':'Katya','overall_rating':8,'would_return':'YES'}]}));c(s,pv,'city.experience.record');assert s.read(r('city.experience.summary'))['data']['experiences'][0]['couple_verdict']=='Оба любим'
def test_trip_save_get(s):
 pv=s.preview(r('city.trip.save',{'title':'SPb','city':'Санкт-Петербург','days':[{'date':'2026-07-15','items':[{'title':'Coffee','start_time':'10:00'}]}]}));cm=c(s,pv,'city.trip.save');tid=cm['data']['entity_ids']['trip_id'];assert s.read(r('city.trip.get',{'trip_id':tid}))['data']['trip']['Title']=='SPb'
def test_route_export(s):
 pv=s.preview(r('city.route.save',{'title':'Loop','route_type':'cycling','points':[{'name':'A','latitude':55.75,'longitude':37.6},{'name':'B','latitude':55.76,'longitude':37.62}]}));rid=c(s,pv,'city.route.save')['data']['entity_ids']['route_id'];ep=s.preview(r('city.route.export',{'route_id':rid,'formats':['gpx','kml','pdf']}));assert len(c(s,ep,'city.route.export')['data']['files'])==3
def test_maturity(s):
 pv=s.preview(r('city.maturity.feedback',{'capability':'city.route.cycling','outcome':'SUCCESS','accuracy_rating':9,'practical_rating':9}));c(s,pv,'city.maturity.feedback');row=next(x for x in s.storage.read_rows('Capability_Maturity') if x['CapabilityID']=='city.route.cycling');assert row['RealTests']==1
def test_dry_run(s):
 pv=s.preview(r('city.rule.save',{'rule':'test'},True));assert c(s,pv,'city.rule.save')['error']['code']=='POLICY_REJECTED'
def test_writes_disabled(s):
 object.__setattr__(settings,'writes_enabled',False);pv=s.preview(r('city.rule.save',{'rule':'test'}));assert c(s,pv,'city.rule.save')['error']['code']=='WRITES_DISABLED';object.__setattr__(settings,'writes_enabled',True)
