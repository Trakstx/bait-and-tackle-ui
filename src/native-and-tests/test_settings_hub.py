import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.request
import urllib.error
module_dir = Path(__file__).resolve().parents[1]/'HUD'
sys.path.insert(0,str(module_dir))
import settings_store as store
from settings_hub import Hub

class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.path=Path(self.temp.name)/'settings.json';self.hub=Hub(self.path)
    def tearDown(self):self.hub.close();self.temp.cleanup()
    def request(self,path,body=None,auth=True,origin=True):
        headers={}
        if auth:headers['X-BFT-Token']=self.hub.token
        if origin:headers['Origin']='http://'+self.hub.host
        if body is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request('http://'+self.hub.host+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        return urllib.request.urlopen(req,timeout=3)
    def test_page_and_csp(self):
        with urllib.request.urlopen(self.hub.url,timeout=3) as r:
            self.assertIn(b'DPS meter',r.read());self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy'])
    def test_get_requires_token(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/settings',auth=False)
        self.assertEqual(e.exception.code,403)
    def test_save_rejects_cross_origin(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/settings',store.validate({}),origin=False)
        self.assertEqual(e.exception.code,403);self.assertFalse(self.path.exists())
    def test_shared_save_and_apply(self):
        v=store.validate({});v['dps']['idle_seconds']=25;v['dps']['pet_names_by_character']={'Tester':['Fluffy']};v['ch']['template']='GG {slot} CH -- {target}'
        with self.request('/api/settings',v) as r:self.assertEqual(json.load(r)['dps']['idle_seconds'],25)
        self.assertEqual(store.load(self.path)['ch']['template'],v['ch']['template'])
        class Meter:pass
        m=Meter();store.apply_dps(m,'Tester',store.load(self.path));self.assertEqual(m.idle_seconds,25);self.assertEqual(m.pet_names,{'fluffy'})
    def test_invalid_save_preserves_existing(self):
        store.save({},self.path);before=self.path.read_bytes()
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/settings',{'dps':{'idle_seconds':float('nan')}})
        self.assertEqual(e.exception.code,400);self.assertEqual(self.path.read_bytes(),before)
    def test_announcement_preview(self):
        with self.request('/api/test',{'ch':store.validate({})['ch'],'sample':"Cleric shouts, '001 CH -- Tank'"}) as r:
            self.assertEqual(json.load(r),{'matched':True,'slot':'001','target':'Tank'})
    def test_legacy_migration(self):
        (self.path.parent/'ch_chain.json').write_text(json.dumps({'my_slot':'AAA'}))
        self.assertEqual(store.load(self.path)['ch']['my_slot'],'AAA')
    def test_settings_no_fake_aggro(self):
        self.assertEqual(store.validate({'aggro':{'enabled':True}})['aggro'],{'available':False})

if __name__=='__main__':unittest.main()
