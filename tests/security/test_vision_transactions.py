import sys,tempfile,unittest,shutil,zipfile,hashlib,os
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str((Path(__file__).resolve().parents[2]/'src/HUD')))
from vision_fix import VisionFix
class Tests(unittest.TestCase):
 def setUp(self):
  running=patch('process_check.find_game_processes',return_value=[]);running.start();self.addCleanup(running.stop)
  self.temp=tempfile.TemporaryDirectory(dir=str(Path(__file__).resolve().parents[2]/'.test-tmp'));self.root=Path(self.temp.name).resolve();self.game=self.root/'game';self.game.mkdir();self.fix=VisionFix(self.game,self.root/'runtime');self.fix.directory.mkdir(parents=True);shutil.copy2(os.environ.get('BFT_VISION_FIXTURE','work/EQTool-VisionFix.zip'),self.fix.directory/'VisionFix.zip');self.original=self.game/'RenderEffects/MPL/FinalBlend.fxo';self.original.parent.mkdir(parents=True);self.original.write_bytes(b'original local graphics')
 def tearDown(self):self.temp.cleanup()
 def test_queue_apply_restore_exact_original(self):
  state=self.fix.queue('apply');self.assertEqual(state['pending'],'apply');self.assertFalse(state['applied']);self.assertEqual(self.original.read_bytes(),b'original local graphics');self.fix.apply_pending();self.assertTrue(self.fix.status()['applied']);self.assertEqual(self.fix.status()['files'],265);self.assertNotEqual(self.original.read_bytes(),b'original local graphics');self.fix.queue('revert');self.fix.apply_pending();self.assertFalse(self.fix.status()['applied']);self.assertEqual(self.original.read_bytes(),b'original local graphics');self.assertFalse((self.game/'Resources/Sky/stars.dds').exists())
 def test_changed_graphics_not_overwritten_on_revert(self):
  self.fix.queue('apply');self.fix.apply_pending();self.original.write_bytes(b'another graphics mod');self.fix.queue('revert');self.fix.apply_pending();self.assertTrue(self.fix.status()['error']);self.assertEqual(self.original.read_bytes(),b'another graphics mod')
 def test_cancel_and_invalid_targets(self):
  self.fix.queue('apply');self.fix.queue('cancel');self.fix.apply_pending();self.assertEqual(self.original.read_bytes(),b'original local graphics')
  for path in ['../eqgame.exe','RenderEffects/../../eqgame.exe','Resources/evil.exe','C:/bad.fxo']:
   with self.assertRaises(ValueError):self.fix.target(path)
 def test_corrupt_archive_is_rejected(self):
  (self.fix.directory/'VisionFix.zip').write_bytes(b'not a package')
  with self.assertRaises(ValueError):self.fix.archive(False)
 def test_partial_apply_failure_rolls_back_entire_graphics_set(self):
  self.fix.queue('apply');replace=os.replace;count=[0]
  def fail(source,target):
   if Path(target).is_relative_to(self.game) and Path(source).name.startswith('.bft-stage-'):
    count[0]+=1
    if count[0]==20:raise OSError('injected graphics write failure')
   return replace(source,target)
  with patch('os.replace',side_effect=fail):self.fix.apply_pending()
  self.assertTrue(self.fix.status()['error']);self.assertFalse(self.fix.status()['applied'])
  self.assertEqual(self.original.read_bytes(),b'original local graphics')
  self.assertEqual([p for p in self.game.rglob('*') if p.is_file()],[self.original])
if __name__=='__main__':unittest.main()
