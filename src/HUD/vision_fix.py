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
   state=self.state();return {k:state.get(k) for k in ['applied','pending','error','updated','attempted','blocked']}|{'files':len(state.get('files',[])),'backup':str(self.directory/'backups'),'source':'EQTool Night Vision graphics fix','note':'Graphics-file replacement, not an Ultravision spell or character buff. Applies only while EQ is closed.'}
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
    from process_check import find_game_processes
    from file_transaction import FileTransaction
    if find_game_processes():state['blocked']='Waiting for EverQuest to close.';self.save(state);return
    state['blocked']=None;state['attempted']=time.time()
    recovery=self.directory/'recovery';FileTransaction.recover_pending(recovery,[self.game,self.directory])
    transaction=FileTransaction(recovery,[self.game,self.directory])
    if mode=='apply':
     with self.archive(False) as z:
      entries={e.filename:e for e in z.infolist() if not e.is_dir()}
      if len(entries)!=265:raise ValueError('Unexpected graphics archive.')
      if not state.get('files'):
       files=[]
       for name,entry in entries.items():
        target=self.target(name);exists=target.is_file();before=target.read_bytes() if exists else None
        backup=self.directory/'backups'/name
        if before is not None:backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(before)
        files.append({'name':name,'existed':exists,'before':hashlib.sha256(before).hexdigest() if exists else None,'after':hashlib.sha256(z.read(entry)).hexdigest()})
       state['files']=files;self.save(state)
      for row in state['files']:
       target=self.target(row['name']);raw=z.read(row['name']);current=hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
       if current not in (row['before'],row['after']):raise ValueError('Graphics changed since backup: '+row['name'])
       if hashlib.sha256(raw).hexdigest()!=row['after']:raise ValueError('Graphics state does not match pinned archive.')
       transaction.add(target,raw)
     state['applied']=True
    elif mode=='revert':
     for row in state['files']:
      target=self.target(row['name']);current=hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
      if current not in (row['before'],row['after']):raise ValueError('Graphics changed after installation: '+row['name'])
      raw=(self.directory/'backups'/row['name']).read_bytes() if row['existed'] else None
      if (hashlib.sha256(raw).hexdigest() if raw is not None else None)!=row['before']:raise ValueError('Graphics recovery backup is damaged.')
      transaction.add(target,raw)
     state['applied']=False
    else:raise ValueError('Invalid pending graphics action.')
    state.update(pending=None,error=None,updated=time.time())
    transaction.add(self.directory/'state.json',json.dumps(state,indent=2).encode('utf8'));transaction.commit()
   except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as exc:
    state=self.state();state['error']=str(exc);state['updated']=time.time();self.save(state)


def main():
 import ctypes,os,subprocess,sys
 from process_check import find_game_processes
 game=Path(__file__).resolve().parent.parent
 if not (game/'eqgame.exe').is_file():raise RuntimeError('Run this tool from the installed BFT_HUD folder beside EverQuest.')
 if find_game_processes():raise RuntimeError('EverQuest is still running. Close every EQ session before applying or restoring graphics.')
 if not ctypes.windll.shell32.IsUserAnAdmin():
  if '--elevated' in sys.argv:raise RuntimeError('Administrator access was not granted.')
  args=subprocess.list2cmdline([str(Path(__file__).resolve()),*sys.argv[1:],'--elevated'])
  if ctypes.windll.shell32.ShellExecuteW(None,'runas',sys.executable,args,str(game),1)<=32:raise RuntimeError('Windows did not authorize the graphics repair.')
  return
 runtime=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'BaitAndTackle'
 fix=VisionFix(game,runtime);mode='revert' if '--revert-now' in sys.argv else 'apply'
 fix.queue(mode);fix.apply_pending();state=fix.state()
 if state.get('error') or state.get('pending'):raise RuntimeError(state.get('error') or state.get('blocked') or 'Graphics change remains pending.')
 if mode=='apply' and not state.get('applied'):raise RuntimeError('Graphics repair was not applied.')
 message=('Night-vision graphics verified: '+str(len(state['files']))+' files. You may start EQ now.') if mode=='apply' else 'Original graphics restored. You may start EQ now.'
 ctypes.windll.user32.MessageBoxW(None,message,'Bait & Tackle graphics repair',0x40)

if __name__=='__main__':
 try:main()
 except Exception as exc:
  import ctypes
  ctypes.windll.user32.MessageBoxW(None,str(exc),'Bait & Tackle graphics repair',0x10)
  raise SystemExit(1)
