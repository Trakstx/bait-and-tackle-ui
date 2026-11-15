import sys,tempfile,unittest,json,urllib.request,urllib.error,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str((Path(__file__).resolve().parents[2]/'src/HUD')))
import settings_store
from settings_hub import Hub
from class_triggers import TriggerEngine
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parents[2]/'.test-tmp'));self.root=Path(self.temp.name).resolve();self.r=patch.object(settings_store,'RUNTIME',self.root/'runtime');self.r.start();self.hub=Hub(self.root/'settings.json',game=self.root);self.hub.trigger_engine=TriggerEngine();self.hub.trigger_engine.character='Healer';self.hub.trigger_engine.detected='cleric';self.hub.trigger_engine.profile_key='a'*64
 def tearDown(self):self.hub.close();self.r.stop();self.temp.cleanup()
 def req(self,path,body=None,auth=True,origin=True):
  headers={'Content-Type':'application/json'}
  if auth:headers['X-BFT-Token']=self.hub.token
  if origin:headers['Origin']='http://'+self.hub.host
  return urllib.request.urlopen(urllib.request.Request('http://'+self.hub.host+path,headers=headers,data=json.dumps(body).encode() if body is not None else None),timeout=3)
 def rule(self):return {'id':'mine','name':'Casting','pattern':'You begin casting Complete Heal.','mode':'exact','message':'Heal started {character}','classes':['cleric'],'duration_seconds':10}
 def test_live_config_preserves_other_settings(self):
  settings_store.save({'dps':{'idle_seconds':22}},self.hub.path)
  with self.req('/api/triggers/config',{'custom':[self.rule()],'class_overrides':{'a'*64:'cleric'}}) as r:self.assertEqual(json.load(r)['custom'][0]['name'],'Casting')
  self.assertEqual(settings_store.load(self.hub.path)['dps']['idle_seconds'],22);self.hub.trigger_engine.consume('You begin casting Complete Heal.',time.time());self.assertTrue(self.hub.trigger_engine.active)
 def test_test_endpoint_no_live_side_effects_and_preview(self):
  body={'rule':self.rule(),'sample':'You begin casting Complete Heal.'}
  with self.req('/api/triggers/test',body) as r:self.assertTrue(json.load(r)['eligible'])
  self.assertFalse(self.hub.trigger_engine.active);body['show']=True
  with self.req('/api/triggers/test',body) as r:self.assertTrue(json.load(r)['matched'])
  self.assertTrue(self.hub.trigger_engine.active[0]['test']);self.assertFalse(self.hub.trigger_engine.last_fire)
 def test_mutations_require_token_and_origin(self):
  for route in ['/api/triggers/config','/api/triggers/test']:
   for kwargs in [{'auth':False},{'origin':False}]:
    with self.assertRaises(urllib.error.HTTPError) as e:self.req(route,{},**kwargs)
    self.assertEqual(e.exception.code,403)
 def test_presets_and_script(self):
  with self.req('/api/triggers') as r:self.assertEqual(json.load(r)['class'],'cleric')
  with self.req('/triggers.js') as r:self.assertIn(b'BFTTriggers',r.read())
if __name__=='__main__':unittest.main()
