import contextlib,importlib.util,io,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src/HUD'))
spec=importlib.util.spec_from_file_location('candidate_recover',ROOT/'src/recover.py');recover=importlib.util.module_from_spec(spec);spec.loader.exec_module(recover)
class Tests(unittest.TestCase):
 def test_file_and_directory_journal_arguments(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp') as t:
   root=Path(t);game=root/'game';game.mkdir();(game/'eqgame.exe').write_bytes(b'inert');journal=root/'journal';journal.mkdir();file=journal/'journal.json';file.write_text('{}')
   for argument in (journal,file):
    with patch.object(sys,'argv',['recover.py','--game',str(game),'--journal',str(argument)]),patch.object(recover,'is_game_running',return_value=False),patch.object(recover,'desktop_path',return_value=root/'desktop'),patch.object(recover.FileTransaction,'restore') as restore,contextlib.redirect_stdout(io.StringIO()):recover.main()
    restore.assert_called_once_with(journal,[game,root/'desktop'])
if __name__=='__main__':unittest.main()
