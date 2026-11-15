import sys,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path('outputs/Bait-and-Tackle-Package/payload/BFT_HUD').resolve()))
import deferred_actions as actions
from process_check import process_still_running
class Tests(unittest.TestCase):
 def test_terminated_process_is_not_a_blocker(self):
  k=MagicMock();k.OpenProcess.return_value=123;k.WaitForSingleObject.return_value=0
  self.assertFalse(process_still_running(k,10));k.CloseHandle.assert_called_once_with(123)
 def test_running_or_inaccessible_still_blocks(self):
  k=MagicMock();k.OpenProcess.return_value=123;k.WaitForSingleObject.return_value=258
  self.assertTrue(process_still_running(k,10));k.OpenProcess.return_value=None;self.assertTrue(process_still_running(k,10))
 def test_layout_failure_does_not_skip_vision(self):
  with tempfile.TemporaryDirectory(dir='work') as t,patch.object(actions,'find_game_processes',return_value=[]),patch.object(actions,'VisionFix') as v,patch.object(actions,'LayoutService') as l:
   v.return_value.state.return_value={'applied':True};l.return_value.apply_pending.side_effect=OSError('layout locked')
   events=actions.run(Path(t)/'game',Path(t)/'runtime');v.return_value.apply_pending.assert_called_once();self.assertTrue(events[0]['ok']);self.assertFalse(events[1]['ok'])
 def test_vision_failure_does_not_skip_layouts(self):
  with tempfile.TemporaryDirectory(dir='work') as t,patch.object(actions,'find_game_processes',return_value=[]),patch.object(actions,'VisionFix') as v,patch.object(actions,'LayoutService') as l:
   v.return_value.apply_pending.side_effect=OSError('graphics locked');events=actions.run(t,Path(t)/'runtime');l.return_value.apply_pending.assert_called_once();self.assertFalse(events[0]['ok']);self.assertTrue(events[1]['ok'])
 def test_running_game_defers_and_records_reason(self):
  with tempfile.TemporaryDirectory(dir='work') as t,patch.object(actions,'find_game_processes',return_value=[12]),patch.object(actions,'VisionFix') as v,patch.object(actions,'LayoutService') as l:
   v.return_value.state.return_value={'pending':'apply'};events=actions.run(t,Path(t)/'runtime');v.return_value.apply_pending.assert_not_called();l.assert_not_called();self.assertIn('12',events[0]['blocked'])
 def test_exit_grace_retries_before_applying(self):
  with tempfile.TemporaryDirectory(dir='work') as t,patch.object(actions,'find_game_processes',side_effect=[[12],[]]),patch.object(actions.time,'sleep'),patch.object(actions,'VisionFix') as v,patch.object(actions,'LayoutService'):
   v.return_value.state.return_value={};actions.run(t,Path(t)/'runtime',wait_seconds=5);v.return_value.apply_pending.assert_called_once()
if __name__=='__main__':unittest.main()
