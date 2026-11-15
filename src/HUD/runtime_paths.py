"""Per-user, per-install writable helper state; the game folder is not a cache."""
import hashlib, os
from pathlib import Path

def install_state(base):
    root=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'BaitAndTackle'
    key=hashlib.sha256(str(Path(base).resolve()).casefold().encode()).hexdigest()[:20]
    destination=root/'installs'/key
    destination.mkdir(parents=True,exist_ok=True)
    return destination
