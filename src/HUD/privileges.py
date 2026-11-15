"""Never run the everyday helper stack with an administrator token."""
import ctypes

def require_standard_user():
    if ctypes.windll.shell32.IsUserAnAdmin():
        raise RuntimeError('Bait & Tackle helpers must run without administrator rights. '
                           'Close this helper and open Play Bait and Tackle.exe normally. '
                           'EQ can request its own permission separately.')
