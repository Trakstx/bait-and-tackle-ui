import sys,json,tempfile,urllib.request,urllib.error,unittest,time
from pathlib import Path
sys.path.insert(0,str(Path('outputs/Bait-and-Tackle-Package/payload/BFT_HUD').resolve()))
from settings_hub import Hub
from klandicar import Encounter
class Tests(unittest.TestCase):
 def test_authenticated_settings_and_manual_control(self):
  with tempfile.TemporaryDirectory(dir='work') as t:
   h=Hub(Path(t)/'settings.json');h.encounter=Encounter()
   try:
    def call(path,data=None,auth=True):
     req=urllib.request.Request('http://'+h.host+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-BFT-Token':h.token if auth else '', 'Origin':'http://'+h.host,'Content-Type':'application/json'})
     with urllib.request.urlopen(req,timeout=3) as r:return json.load(r)
    with self.assertRaises(urllib.error.HTTPError):call('/api/klandicar',auth=False)
    call('/api/klandicar/config',{'enabled':True,'da_enabled':True,'da_lead':4});self.assertEqual(call('/api/klandicar')['settings']['da_lead'],4)
    self.assertTrue(call('/api/klandicar/arm',{})['active']);self.assertFalse(call('/api/klandicar/stop',{})['active'])
   finally:h.close()
if __name__=='__main__':unittest.main()
