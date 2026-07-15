from typing import Any
from fastapi import Depends,FastAPI
from fastapi.openapi.utils import get_openapi
from app import __version__
from app.models import CommitRequest,PluginRequest
from app.security import require_api_key
from app.services import CityService
from app.storage.factory import get_storage
app=FastAPI(title="City & Travel Jarvis Helper",description="Personal city, travel, route and place-memory helper with controlled writes.",version=__version__)
def svc():return CityService(get_storage())
@app.get('/health',operation_id='healthCheck')
def health()->dict[str,Any]:return {'status':'ok','version':__version__}
@app.get('/api/setup/validate',operation_id='validateCitySetup',dependencies=[Depends(require_api_key)])
def validate():return svc().validate_setup()
@app.get('/api/jarvis/manifest',operation_id='getCityPluginManifest',dependencies=[Depends(require_api_key)])
def plugin_manifest():return svc().get_manifest()
@app.post('/api/jarvis/read',operation_id='executeCityReadCapability',dependencies=[Depends(require_api_key)])
def read(r:PluginRequest):return svc().read(r)
@app.post('/api/jarvis/write/preview',operation_id='previewCityWriteCapability',dependencies=[Depends(require_api_key)])
def preview(r:PluginRequest):return svc().preview(r)
@app.post('/api/jarvis/write/commit',operation_id='commitCityWriteCapability',dependencies=[Depends(require_api_key)])
def commit(r:CommitRequest):return svc().commit(r)
def custom_openapi():
 if app.openapi_schema:return app.openapi_schema
 schema=get_openapi(title=app.title,version=app.version,description=app.description,routes=app.routes)
 schema.setdefault('components',{}).setdefault('securitySchemes',{})['bearerAuth']={'type':'http','scheme':'bearer'}
 for path,item in schema.get('paths',{}).items():
  for method,op in item.items():
   if method.lower() not in {'get','post','put','patch','delete'}:continue
   op['parameters']=[p for p in op.get('parameters',[]) if not(p.get('in')=='header' and str(p.get('name','')).lower()=='authorization')]
   if path!='/health':op['security']=[{'bearerAuth':[]}]
 app.openapi_schema=schema;return schema
app.openapi=custom_openapi
