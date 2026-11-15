import sys,tempfile,unittest,ctypes,os
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str((Path(__file__).resolve().parents[2]/'src/HUD')))
import refresh_helpers as r
class Tests(unittest.TestCase):
 def setUp(self):
  self.log_patch=patch.object(r,'log');self.log_patch.start();self.addCleanup(self.log_patch.stop)
 def test_game_pid_never_targeted(self):
  with patch.object(r,'verified_handle') as verify:
   with self.assertRaises(RuntimeError):r.stop_helpers(42,Path('work/fake'),42)
   verify.assert_not_called()
 def test_only_verified_owner_stopped(self):
  with patch.object(r,'verified_handle',side_effect=[10,20]),patch.object(r,'parent_pid',return_value=123),patch.object(r.k,'OpenMutexW',return_value=44),patch.object(r.k,'TerminateProcess',return_value=True) as stop,patch.object(r.k,'WaitForSingleObject',return_value=0),patch.object(r.k,'CloseHandle'):
   r.stop_helpers(111,Path('work/fake'),999);stop.assert_called_once_with(20,0)
 def test_unverified_managed_parent_does_not_stop_anything(self):
  with patch.object(r,'verified_handle',side_effect=[10,RuntimeError('wrong')]),patch.object(r,'parent_pid',return_value=123),patch.object(r.k,'OpenMutexW',return_value=44),patch.object(r.k,'TerminateProcess') as stop,patch.object(r.k,'CloseHandle'):
   with self.assertRaises(RuntimeError):r.stop_helpers(111,Path('work/fake'),999)
   stop.assert_not_called()
 def test_wrong_runtime_is_rejected(self):
  with patch.object(r.k,'OpenProcess',return_value=10),patch.object(r,'process_path',return_value='C:/Windows/not-bft.exe'),patch.object(r.k,'CloseHandle'):
   with self.assertRaises(RuntimeError):r.verified_handle(123,Path('work/fake/runtime/pythonw.exe'))
 def test_no_game_no_launch(self):
  with patch.object(r,'visible_game_pid',return_value=None),patch.object(r,'find_game_processes',return_value=[]),patch.object(r.subprocess,'Popen') as spawn:
   with self.assertRaises(RuntimeError):r.refresh(Path('work/fake'))
   spawn.assert_not_called()
 def test_visible_verified_game_is_used_without_process_enumeration(self):
  with patch.object(r,'visible_game_pid',return_value=42),patch.object(r,'find_game_processes') as scan:
   self.assertEqual(r.select_game(Path('work/fake/eqgame.exe')),42);scan.assert_not_called()
 def test_one_process_fallback_when_window_is_minimized(self):
  with patch.object(r,'visible_game_pid',return_value=None),patch.object(r,'find_game_processes',return_value=[43]),patch.object(r,'log'):
   self.assertEqual(r.select_game(Path('work/fake/eqgame.exe')),43)
 def test_wrong_install_window_is_not_silently_attached(self):
  with patch.object(r,'visible_game_pid',side_effect=RuntimeError('other install')),patch.object(r,'find_game_processes') as scan:
   with self.assertRaises(RuntimeError):r.select_game(Path('work/fake/eqgame.exe'))
   scan.assert_not_called()
 def test_legacy_python_requires_expected_bft_script(self):
  with patch.object(r.k,'OpenProcess',return_value=10),patch.object(r,'process_path',return_value='C:/Python312/pythonw.exe'),patch.object(r,'helper_script',return_value=Path('work/fake/ch_overlay.py').resolve()),patch.object(r.k,'CloseHandle'):
   self.assertEqual(r.verified_handle(123,Path('work/fake/runtime/pythonw.exe'),Path('work/fake/ch_overlay.py')),10)
 def test_unrelated_legacy_python_script_is_not_accepted(self):
  with patch.object(r.k,'OpenProcess',return_value=10),patch.object(r,'process_path',return_value='C:/Python312/pythonw.exe'),patch.object(r,'helper_script',return_value=Path('work/unrelated.py').resolve()),patch.object(r.k,'CloseHandle'):
   with self.assertRaises(RuntimeError):r.verified_handle(123,Path('work/fake/runtime/pythonw.exe'),Path('work/fake/ch_overlay.py'))
if __name__=='__main__':unittest.main()
