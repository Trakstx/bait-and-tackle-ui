import sys, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src/HUD'))
from privileges import require_standard_user

class Tests(unittest.TestCase):
    def test_standard_user_allowed(self):
        with patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=False):
            require_standard_user()
    def test_admin_helper_refused_without_uac(self):
        with patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=True), patch('ctypes.windll.shell32.ShellExecuteW') as shell:
            with self.assertRaisesRegex(RuntimeError,'without administrator rights'): require_standard_user()
            shell.assert_not_called()
    def test_pth_contains_no_external_or_site_entries(self):
        self.assertEqual((ROOT/'src/python314._pth').read_text().splitlines(),['python314.zip','.','DLLs','Lib','..'])

if __name__=='__main__':unittest.main()
