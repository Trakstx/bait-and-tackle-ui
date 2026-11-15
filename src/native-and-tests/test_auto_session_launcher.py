import sys,os,tempfile,importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from contextlib import ExitStack
sys.path.insert(0,str(Path('outputs/Bait-and-Tackle-Package/payload/BFT_HUD').resolve()))
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir='work');root=Path(self.temp.name).resolve();self.game=root/'game';self.base=self.game/'BFT_HUD';self.base.mkdir(parents=True);(self.game/'Logs').mkdir();(self.game/'eqgame.exe').write_text('test');(self.base/'config.json').write_text(json.dumps({'auto_detect':True}))
  with patch.dict(os.environ,{'LOCALAPPDATA':str(root)}):
   spec=importlib.util.spec_from_file_location('launch_test',Path('outputs/Bait-and-Tackle-Package/payload/BFT_HUD/launcher.py'));self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
  self.m.base=self.base;self.m.game=self.game;self.stack=ExitStack();self.addCleanup(self.stack.close);self.addCleanup(self.temp.cleanup)
  for obj,name,value in [(self.m.k,'CreateMutexW',MagicMock(return_value=123)),(self.m.k,'OpenProcess',MagicMock(return_value=321)),(self.m.k,'WaitForSingleObject',MagicMock(side_effect=[258,0])),(self.m.k,'CloseHandle',MagicMock()),(self.m.atexit,'register',MagicMock()),(self.m.ctypes,'get_last_error',MagicMock(return_value=0)),(self.m,'process_path',MagicMock(return_value=str(self.game/'eqgame.exe'))),(self.m,'HelperJob',MagicMock()),(self.m,'find_game_processes',MagicMock(return_value=[])),(self.m.subprocess,'Popen',MagicMock()),(self.m.ctypes.windll.shell32,'ShellExecuteW',MagicMock())]:self.stack.enter_context(patch.object(obj,name,value))
  self.stack.enter_context(patch.dict(os.environ,{},clear=False))
  self.stack.enter_context(patch.object(self.m,'apply_layouts',MagicMock()))
  import game_window
  self.window=self.stack.enter_context(patch.object(game_window,'game_window',return_value={'hwnd':777,'pid':4321,'path_verified':False}))
 def run_args(self,*args):
  with patch.object(sys,'argv',['launcher.py',*args]):self.m.main()
 def test_exact_attach_starts_helpers_without_game_or_uac(self):
  self.run_args('--attach-only','--game-pid','4321');self.m.apply_layouts.assert_called_once_with(wait_seconds=5);self.m.subprocess.Popen.assert_not_called();self.m.ctypes.windll.shell32.ShellExecuteW.assert_not_called();self.assertEqual(self.m.HelperJob.return_value.start.call_count,2);self.m.HelperJob.return_value.close.assert_called_once();self.m.k.WaitForSingleObject.assert_any_call(321,0xffffffff)
 def test_attach_never_starts_eq_if_absent(self):
  self.window.return_value=None;self.run_args('--attach-only');self.m.subprocess.Popen.assert_not_called();self.m.HelperJob.assert_not_called()
 def test_wrong_pid_path_rejected(self):
  self.window.side_effect=RuntimeError('Different EQ installation')
  with self.assertRaises(RuntimeError):self.run_args('--game-pid','4321')
  self.m.HelperJob.assert_not_called()
 def test_exited_eq_does_not_restart(self):
  self.m.k.OpenProcess.return_value=None;self.window.return_value=None
  with self.assertRaises(RuntimeError):self.run_args('--game-pid','4321')
  self.m.subprocess.Popen.assert_not_called();self.m.HelperJob.return_value.start.assert_not_called()
 def test_duplicate_session_no_extra_helpers(self):
  self.m.ctypes.get_last_error.return_value=183;self.run_args('--game-pid','4321');self.m.HelperJob.assert_not_called()
 def test_denied_wait_handle_uses_window_lifecycle(self):
  import game_window
  self.m.k.OpenProcess.return_value=None;self.window.side_effect=[{'hwnd':777,'pid':4321,'path_verified':False},None,None]
  with patch.object(game_window,'window_alive',return_value=False),patch.object(self.m.time,'monotonic',side_effect=[0,4]),patch.object(self.m.time,'sleep'):
   self.run_args('--game-pid','4321')
  self.assertEqual(self.m.HelperJob.return_value.start.call_count,2);self.m.HelperJob.return_value.close.assert_called_once();self.m.k.OpenProcess.assert_called_once_with(0x100000,False,4321)
 def test_xp_failure_still_applies_deferred_work(self):
  import experience
  with patch.object(experience,'finish_game',side_effect=RuntimeError('XP cleanup failed')):
   self.run_args('--game-pid','4321')
  self.m.apply_layouts.assert_called_once_with(wait_seconds=5)
 def test_invalid_pid_rejected(self):
  with self.assertRaises(ValueError):self.run_args('--game-pid','0')
unittest.main()

