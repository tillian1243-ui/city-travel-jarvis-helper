from fastapi.testclient import TestClient
from app.main import app
from app.settings import settings
object.__setattr__(settings,'action_api_key','test-key');object.__setattr__(settings,'writes_enabled',True)
client=TestClient(app);H={'Authorization':'Bearer test-key'}
def test_health():assert client.get('/health').json()['version']=='1.0.5'
def test_auth():assert client.get('/api/jarvis/manifest').status_code==401
def test_manifest():assert client.get('/api/jarvis/manifest',headers=H).json()['plugin_id']=='city-travel-jarvis'
def test_read():assert client.post('/api/jarvis/read',headers=H,json={'contract_version':'0.1.0','request_id':'REQ-API','capability':'city.cockpit','payload':{}}).json()['status']=='ok'
def test_openapi():
 schema=client.get('/openapi.json').json();ops=[]
 for item in schema['paths'].values():
  for method,op in item.items():
   if method.lower() in {'get','post','put','patch','delete'}:
    ops.append(op.get('operationId'));assert all(not(p.get('in')=='header' and p.get('name','').lower()=='authorization') for p in op.get('parameters',[]))
 assert len(ops)==6 and len(set(ops))==6


def test_api_commit_by_preview_id():
 preview=client.post('/api/jarvis/write/preview',headers=H,json={
  'contract_version':'0.1.0','request_id':'REQ-PREVIEW-PID','capability':'city.rule.save',
  'payload':{'rule':'api preview id test'},'context':{'dry_run':False}
 }).json()
 assert preview['status']=='preview_ready'
 committed=client.post('/api/jarvis/write/commit',headers=H,json={
  'contract_version':'0.1.0','request_id':'REQ-COMMIT-PID','capability':'city.rule.save',
  'preview_id':preview['preview_id'],'confirmed':True
 }).json()
 assert committed['status']=='committed'
