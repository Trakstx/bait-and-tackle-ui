"""Staged file sets with external backups, durable journals and conflict-aware recovery."""
import hashlib,json,os,stat,tempfile,uuid
from pathlib import Path

def digest(data):return hashlib.sha256(data).hexdigest() if data is not None else None
def checked(path,roots):
    path=Path(os.path.abspath(path));roots=[Path(r).resolve() for r in roots]
    if not any(path.is_relative_to(r) for r in roots):raise ValueError('Transaction path escapes approved roots.')
    for component in [path,*path.parents]:
        try:info=component.lstat()
        except FileNotFoundError:continue
        if getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024) or component.is_symlink():raise ValueError('Transaction paths cannot use links/junctions.')
    return path
def write_atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.bft-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

class FileTransaction:
    def __init__(self,backups,roots):
        self.roots=[Path(p).resolve() for p in roots];self.directory=Path(backups).resolve()/uuid.uuid4().hex
        if any(self.directory.is_relative_to(r) for r in self.roots[:1]):raise ValueError('Recovery backups must be outside the game root.')
        self.entries=[];self.targets=set()
    def add(self,path,data):
        path=checked(path,self.roots)
        if path in self.targets:raise ValueError('Duplicate transaction target.')
        if data is not None and not isinstance(data,bytes):raise TypeError('Transaction content must be bytes.')
        self.targets.add(path);self.entries.append((path,data))
    def commit(self):
        self.directory.mkdir(parents=True)
        journal={'schema':1,'state':'preparing','entries':[]};staged=[]
        def save():write_atomic(self.directory/'journal.json',json.dumps(journal,indent=2).encode())
        try:
            for index,(path,data) in enumerate(self.entries):
                checked(path,self.roots);before=path.read_bytes() if path.exists() else None
                if before is not None:write_atomic(self.directory/str(index),before)
                journal['entries'].append({'target':str(path),'blob':str(index),'before':digest(before),'after':digest(data)})
                if data is not None:
                    path.parent.mkdir(parents=True,exist_ok=True)
                    fd,name=tempfile.mkstemp(prefix='.bft-stage-',dir=path.parent)
                    with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
                    staged.append(Path(name))
                else:staged.append(None)
            journal['state']='applying';save()
            for (path,data),temp,row in zip(self.entries,staged,journal['entries']):
                checked(path,self.roots)
                if digest(path.read_bytes() if path.exists() else None)!=row['before']:raise ValueError('File changed during transaction: '+path.name)
                if data is None:
                    if path.exists():path.unlink()
                else:os.replace(temp,path)
                if digest(path.read_bytes() if path.exists() else None)!=row['after']:raise OSError('Post-write verification failed: '+path.name)
            journal['state']='committed';save()
        except BaseException:
            if journal['state']=='applying':self.restore(self.directory,self.roots)
            else:journal['state']='aborted';save()
            raise
        finally:
            for path in staged:
                if path and path.exists():path.unlink()
        return self.directory
    @staticmethod
    def restore(directory,roots):
        directory=Path(directory).resolve();journal=json.loads((directory/'journal.json').read_text())
        if journal.get('schema')!=1 or not isinstance(journal.get('entries'),list):raise ValueError('Invalid recovery journal.')
        plan=[]
        for index,row in enumerate(journal['entries']):
            path=checked(row['target'],roots)
            if row['blob']!=str(index):raise ValueError('Invalid backup entry.')
            before=(directory/str(index)).read_bytes() if row['before'] is not None else None
            if digest(before)!=row['before']:raise ValueError('Recovery backup is damaged.')
            current=digest(path.read_bytes() if path.exists() else None)
            if current not in (row['before'],row['after']):raise ValueError('Recovery paused: file modified after this operation: '+path.name)
            plan.append((path,before))
        journal['state']='restoring';write_atomic(directory/'journal.json',json.dumps(journal,indent=2).encode())
        for path,data in reversed(plan):
            checked(path,roots)
            if data is None:
                if path.exists():path.unlink()
            else:write_atomic(path,data)
        journal['state']='rolled_back';write_atomic(directory/'journal.json',json.dumps(journal,indent=2).encode())
    @staticmethod
    def recover_pending(backups,roots):
        for file in Path(backups).glob('*/journal.json'):
            if json.loads(file.read_text()).get('state') in ('applying','restoring'):FileTransaction.restore(file.parent,roots)
