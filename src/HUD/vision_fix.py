"""EQTool's pinned graphics fix, with deferred application and reversible backups."""
import hashlib,io,json,shutil,threading,time,urllib.request,zipfile
from pathlib import Path,PurePosixPath
URL='https://raw.githubusercontent.com/smasherprog/EqTool/8ab4501517c4ad10914a91414d8eda1cf80d2e57/EQTool/Files/VisionFix.zip'
SHA256='105d0cf2c746f894ac85937dbfad0fadb627809e763aeabb4e9157fdadc3528d'
class VisionFix:
 def __init__(self,game,runtime):
  self.game=Path(game) if game else None;identity=str(self.game.resolve()).casefold() if self.game else 'unconfigured';self.directory=Path(runtime)/'vision-fix'/hashlib.sha256(identity.encode()).hexdigest()[:20];self.lock=threading.RLock()
 def state(self):
  try:return json.loads((self.directory/'state.json').read_text(encoding='utf-8'))
  except (OSError,ValueError):return {'applied':False,'pending':None,'files':[]}
 def save(self,state):
  self.directory.mkdir(parents=True,exist_ok=True);tmp=self.directory/'state.tmp';tmp.write_text(json.dumps(state,indent=2),encoding='utf-8');tmp.replace(self.directory/'state.json')
 def status(self):
  with self.lock:
   state=self.state();return {k:state.get(k) for k in ['applied','pending','error','updated']}|{'files':len(state.get('files',[])),'backup':str(self.directory/'backups'),'source':'EQTool Night Vision graphics fix','note':'Graphics-file replacement, not an Ultravision spell or character buff. Applies only while EQ is closed.'}
 def archive(self,download=True):
  p=self.directory/'VisionFix.zip'
  if not p.is_file() or (download and hashlib.sha256(p.read_bytes()).hexdigest()!=SHA256):
   if not download:raise ValueError('Night-vision download is missing. Queue the fix again.')
   req=urllib.request.Request(URL,headers={'User-Agent':'Bait-and-Tackle'})
   with urllib.request.urlopen(req,timeout=30) as response:raw=response.read(20971521)
   if len(raw)>20971520 or hashlib.sha256(raw).hexdigest()!=SHA256:raise ValueError('Night-vision package verification failed.')
   self.directory.mkdir(parents=True,exist_ok=True);temp=p.with_suffix('.download');temp.write_bytes(raw);temp.replace(p)
  raw=p.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=SHA256:raise ValueError('Night-vision package checksum mismatch.')
  return zipfile.ZipFile(io.BytesIO(raw))
 def target(self,name):
  parts=PurePosixPath(name).parts
  if not self.game or not parts or parts[0] not in ['RenderEffects','Resources'] or '..' in parts or '\\' in name or ':' in name or PurePosixPath(name).is_absolute() or PurePosixPath(name).suffix not in ['.fxo','.dds','.ini']:raise ValueError('Invalid graphics package path.')
  target=self.game.joinpath(*parts)
  if not target.resolve().is_relative_to(self.game.resolve()):raise ValueError('Graphics target points outside the EQ installation.')
  return target
 def queue(self,mode):
  if mode not in ['apply','revert','cancel']:raise ValueError('Invalid night-vision action.')
  with self.lock:
   state=self.state()
   if mode=='apply':
    if state.get('applied'):return self.status()
    with self.archive() as z:
     entries=[x for x in z.infolist() if not x.is_dir()]
     if len(entries)!=265 or sum(x.file_size for x in entries)>20971520:raise ValueError('Unexpected graphics archive.')
     for entry in entries:self.target(entry.filename)
   if mode=='revert' and not state.get('files'):raise ValueError('No night-vision backup exists to restore.')
   state['pending']=None if mode=='cancel' else mode;state['error']=None;state['updated']=time.time();self.save(state);return self.status()
 def apply_pending(self):
  with self.lock:
   state=self.state();mode=state.get('pending')
   if not mode:return
   try:
    if mode=='apply':
     with self.archive(False) as z:
      if not state.get('files'):
       files=[]
       for entry in z.infolist():
        if entry.is_dir():continue
        target=self.target(entry.filename);backup=self.directory/'backups'/entry.filename;exists=target.is_file();original=target.read_bytes() if exists else None
        if exists:backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(original)
        files.append({'name':entry.filename,'existed':exists,'before':hashlib.sha256(original).hexdigest() if exists else None,'after':hashlib.sha256(z.read(entry)).hexdigest()})
       state['files']=files;self.save(state)
      for row in state['files']:
       target=self.target(row['name']);current=hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
       if current not in [row['before'],row['after']]:raise ValueError('Graphics changed since backup: '+row['name']+'. Existing backup retained.')
       target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix(target.suffix+'.bft-tmp');temp.write_bytes(z.read(row['name']));temp.replace(target)
     state['applied']=True
    else:
     # Validate all backups and detect subsequent modifications before restoring any file.
     for row in state['files']:
      target=self.target(row['name']);backup=self.directory/'backups'/row['name'];current=hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
      if current not in [row['before'],row['after']]:raise ValueError('Another graphics change was found: '+row['name']+'. Restore paused; backup retained.')
      if row['existed'] and (not backup.is_file() or hashlib.sha256(backup.read_bytes()).hexdigest()!=row['before']):raise ValueError('Original backup is missing or damaged: '+row['name'])
     for row in state['files']:
      target=self.target(row['name'])
      if row['existed']:
       temp=target.with_suffix(target.suffix+'.bft-tmp');temp.write_bytes((self.directory/'backups'/row['name']).read_bytes());temp.replace(target)
      elif target.is_file():target.unlink()
     state['applied']=False
    state['pending']=None;state['error']=None;state['updated']=time.time();self.save(state)
   except (OSError,ValueError,KeyError,zipfile.BadZipFile) as exc:
    state['error']=str(exc);state['updated']=time.time();self.save(state)
