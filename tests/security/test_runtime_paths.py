import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src/HUD'))
from runtime_paths import install_state
import recorder
class Tests(unittest.TestCase):
 def test_state_is_per_user_and_install(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp') as temp,patch.dict(os.environ,{'LOCALAPPDATA':temp}):
   first=install_state(Path(temp)/'game-a/BFT_HUD');second=install_state(Path(temp)/'game-b/BFT_HUD')
   self.assertNotEqual(first,second);self.assertTrue(first.is_relative_to(Path(temp)/'BaitAndTackle/installs'))
   self.assertEqual(first,install_state(Path(temp)/'game-a/BFT_HUD'))
 def test_recorder_engine_writes_user_cache_not_game(self):
  with patch.object(recorder,'RUNTIME',Path('user-cache')),patch.object(recorder,'BASE',Path('protected-game/BFT_HUD')):
   self.assertTrue(recorder.engine_path().is_relative_to(Path('user-cache')))
   self.assertFalse(recorder.engine_path().is_relative_to(recorder.BASE))
if __name__=='__main__':unittest.main()
