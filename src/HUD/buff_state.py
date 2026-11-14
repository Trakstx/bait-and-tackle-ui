"""Per-character/server checkpoints for observed buff timers, not server buff state."""
import hashlib
import json
from pathlib import Path

class BuffStateStore:
    def __init__(self,directory,log_path):
        identity=str(Path(log_path).resolve()).casefold()
        self.identity=identity
        self.path=Path(directory)/(hashlib.sha256(identity.encode()).hexdigest()+'.json')
    def load(self):
        try:
            if self.path.stat().st_size>1048576:return None
            data=json.loads(self.path.read_text(encoding='utf-8'))
            return data if data.get('version')==1 and data.get('identity')==self.identity else None
        except (OSError,ValueError,TypeError,AttributeError):return None
    def save(self,data):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload=dict(data,version=1,identity=self.identity)
        temporary=self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(payload,allow_nan=False),encoding='utf-8');temporary.replace(self.path)
