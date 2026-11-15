import contextlib,hashlib,importlib.util,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src/HUD'))
spec=importlib.util.spec_from_file_location('bft_candidate_install',ROOT/'src/install.py');installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp');self.root=Path(self.temp.name).resolve();self.game=self.root/'game';self.game.mkdir();(self.game/'eqgame.exe').write_bytes(b'inert fixture')
  self.package=self.root/'package';payload=self.package/'payload';payload.mkdir(parents=True);self.desktop=self.root/'desktop';self.desktop.mkdir()
  files={}
  for name in ['dxgi.dll','ReShade.ini','BFT_Test.ini','BFT_HUD/a.py','BFT_HUD/b.py']:
   p=payload/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('new '+name).encode());files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
  (self.package/'manifest.json').write_text(json.dumps({'files':files}))
  (self.game/'Logs').mkdir();(self.game/'Logs/personal.txt').write_bytes(b'keep private logs')
  p=self.game/'BFT_HUD/a.py';p.parent.mkdir();p.write_bytes(b'old helper')
 def tearDown(self):self.temp.cleanup()
 def run_install(self,*args):
  with patch.object(installer,'ROOT',self.package),patch.object(installer,'is_game_running',return_value=False),patch.object(installer,'desktop_path',return_value=self.desktop),patch.dict(os.environ,{'LOCALAPPDATA':str(self.root/'local')}),patch.object(sys,'argv',['install.py','--game',str(self.game),'--no-shortcut',*args]),patch('builtins.input',return_value=''),contextlib.redirect_stdout(io.StringIO()):installer.main()
 def test_install_then_restore_preserves_unrelated_data(self):
  self.run_install();receipt=json.loads((self.game/'BFT_HUD/package-installed.json').read_text());self.assertEqual((self.game/'BFT_HUD/a.py').read_bytes(),b'new BFT_HUD/a.py')
  self.run_install('--restore',receipt['backup']);self.assertEqual((self.game/'BFT_HUD/a.py').read_bytes(),b'old helper');self.assertFalse((self.game/'BFT_HUD/b.py').exists());self.assertEqual((self.game/'Logs/personal.txt').read_bytes(),b'keep private logs')
 def test_write_failure_rolls_back_install_and_receipt(self):
  replace=os.replace
  def fail(source,target):
   if Path(target)==self.game/'BFT_HUD/b.py' and Path(source).name.startswith('.bft-stage-'):raise OSError('injected installer failure')
   return replace(source,target)
  with patch('os.replace',side_effect=fail):
   with self.assertRaises(OSError):self.run_install()
  self.assertEqual((self.game/'BFT_HUD/a.py').read_bytes(),b'old helper');self.assertFalse((self.game/'dxgi.dll').exists());self.assertFalse((self.game/'BFT_HUD/package-installed.json').exists())
 def test_old_owned_runtime_file_removed_and_recoverable(self):
  old=self.game/'BFT_HUD/runtime/_testold.pyd';old.parent.mkdir();old.write_bytes(b'old test extension')
  receipt=self.game/'BFT_HUD/package-installed.json';receipt.write_text(json.dumps({'files':{'BFT_HUD/runtime/_testold.pyd':hashlib.sha256(old.read_bytes()).hexdigest()}}))
  self.run_install();self.assertFalse(old.exists());data=json.loads(receipt.read_text());self.run_install('--restore',data['backup']);self.assertEqual(old.read_bytes(),b'old test extension')
 def test_payload_escape_rejected(self):
  (self.package/'manifest.json').write_text(json.dumps({'files':{'../outside':'0'*64}}))
  with self.assertRaises(ValueError):self.run_install()
if __name__=='__main__':unittest.main()
