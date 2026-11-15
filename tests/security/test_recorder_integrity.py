import hashlib,io,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src/HUD'))
import recorder,settings_store,itemlookup
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp');self.root=Path(self.temp.name);data=io.BytesIO()
  with zipfile.ZipFile(data,'w') as z:z.writestr('bin/64bit/obs64.exe',b'inert executable fixture');z.writestr('data/vendor.txt',b'verified asset')
  self.raw=data.getvalue();self.sha=hashlib.sha256(self.raw).hexdigest();self.runtime=self.root/'cache';self.runtime.mkdir();self.engine=self.root/'engine'
  self.stack=[patch.object(recorder,'RUNTIME',self.runtime),patch.object(recorder,'SHA256',self.sha),patch.object(recorder,'engine_path',return_value=self.engine/'bin/64bit/obs64.exe')]
  for p in self.stack:p.start();self.addCleanup(p.stop)
  (self.runtime/('obs-'+self.sha+'.zip')).write_bytes(self.raw)
 def tearDown(self):self.temp.cleanup()
 def test_verified_install_and_cached_revalidation(self):
  self.assertTrue(recorder.install_engine().exists());self.assertEqual(recorder.install_engine().read_bytes(),b'inert executable fixture')
  recorder.engine_path().write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'modified'):recorder.install_engine()
 def test_unexpected_plugin_is_rejected(self):
  recorder.install_engine();(self.engine/'bin/64bit/unapproved.dll').write_bytes(b'extra')
  with self.assertRaisesRegex(ValueError,'Unexpected executable'):recorder.install_engine()
 def test_existing_executable_does_not_bypass_missing_archive(self):
  recorder.install_engine();(self.runtime/('obs-'+self.sha+'.zip')).unlink()
  with patch('urllib.request.urlopen',side_effect=OSError('offline')) as network:
   with self.assertRaises(OSError):recorder.install_engine()
   network.assert_called_once()
 def test_optional_item_lookup_is_off_without_consent(self):
  with patch.object(settings_store,'RUNTIME',self.root),patch('urllib.request.urlopen') as network:
   with self.assertRaisesRegex(ValueError,'disabled'):itemlookup.fetch_item(10028,'Peridot')
   network.assert_not_called()
if __name__=='__main__':unittest.main()
