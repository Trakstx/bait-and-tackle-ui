"""Managed OBS replay buffer: EQ window + process audio only; saved clips are never pruned."""
import configparser,ctypes,hashlib,json,math,os,queue,secrets,shutil,subprocess,threading,time,urllib.request,zipfile
from pathlib import Path
VERSION='33.0.1'
URL='https://github.com/obsproject/obs-studio/releases/download/33.0.1/OBS-Studio-33.0.1-Windows-x64.zip'
SHA256='0d9436451c2d772b33428e3fdae9776f071895c335de17283176306fb72651d3'
BASE=Path(__file__).resolve().parent
RUNTIME=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'BaitAndTackle/recorder'

def validate(data=None):
 d=data or {};folder=str(d.get('folder',str(Path.home()/'Videos/BaitAndTackle'))).strip()
 if not Path(folder).is_absolute() or folder.startswith(('\\\\','//')) or '\n' in folder or '\r' in folder:raise ValueError('Choose an absolute local folder for saved incidents.')
 return {'enabled':bool(d.get('enabled',False)),'folder':folder,'seconds':300,'fps':15,'bitrate':3000,'audio_bitrate':96}

def engine_path():return BASE/'recorder-engine/bin/64bit/obs64.exe'

def install_engine(report=lambda s:None):
 exe=engine_path()
 if exe.is_file():return exe
 report('Downloading official portable recorder engine (one-time, about 224 MB).');RUNTIME.mkdir(parents=True,exist_ok=True);archive=RUNTIME/'obs-download.zip'
 req=urllib.request.Request(URL,headers={'User-Agent':'BaitAndTackle-recorder/1.0'})
 digest=hashlib.sha256();size=0
 with urllib.request.urlopen(req,timeout=30) as response,archive.open('wb') as out:
  while True:
   chunk=response.read(1024*1024)
   if not chunk:break
   size+=len(chunk)
   if size>350*1024*1024:raise ValueError('Recorder download exceeded its size limit.')
   digest.update(chunk);out.write(chunk)
 if digest.hexdigest()!=SHA256:raise ValueError('Recorder download checksum did not match the pinned official release.')
 report('Installing isolated recorder engine.');root=BASE/'recorder-engine';root.mkdir(exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for item in z.infolist():
   target=(root/item.filename).resolve()
   if not target.is_relative_to(root.resolve()):raise ValueError('Unsafe recorder archive path.')
  z.extractall(root)
 archive.unlink();return exe

def encoder():
 try:
  from ctypes import wintypes as W
  class Display(ctypes.Structure):_fields_=[('cb',W.DWORD),('name',W.WCHAR*32),('description',W.WCHAR*128),('flags',W.DWORD),('id',W.WCHAR*128),('key',W.WCHAR*128)]
  u=ctypes.WinDLL('user32');u.EnumDisplayDevicesW.argtypes=[W.LPCWSTR,W.DWORD,ctypes.POINTER(Display),W.DWORD]
  names=[]
  for i in range(12):
   row=Display();row.cb=ctypes.sizeof(row)
   if u.EnumDisplayDevicesW(None,i,ctypes.byref(row),0):names.append(row.description.lower())
  if any('nvidia' in n for n in names):return 'obs_nvenc_h264_tex'
  if any('radeon' in n or 'amd' in n for n in names):return 'h264_texture_amf'
  if any('intel' in n for n in names):return 'obs_qsv11_v2'
 except OSError:pass
 return 'obs_x264'

def prepare(config,root,ipc,width=1680,height=1050):
 config=validate(config);root=Path(root);ipc=Path(ipc);ipc.mkdir(parents=True,exist_ok=True);folder=Path(config['folder']);folder.mkdir(parents=True,exist_ok=True)
 if shutil.disk_usage(folder).free<512*1024*1024:raise ValueError('Keep at least 512 MB free in the incident folder.')
 base=root/'config/obs-studio';profile=base/'basic/profiles/BFT';scenes=base/'basic/scenes';profile.mkdir(parents=True,exist_ok=True);scenes.mkdir(parents=True,exist_ok=True)
 (root/'portable_mode.txt').write_text('')
 user='[General]\nEnableAutoUpdates=false\nFirstRun=true\n[Basic]\nProfile=BFT\nProfileDir=BFT\nSceneCollection=BFT Evidence\nSceneCollectionFile=BFT\nConfigOnNewProfile=false\n[BasicWindow]\nPreviewEnabled=false\nSysTrayEnabled=true\nSysTrayWhenStarted=true\n'
 (base/'global.ini').write_text(user);(base/'user.ini').write_text(user)
 width=max(640,min(1920,int(width)//2*2));height=max(360,min(1200,int(height)//2*2));enc=encoder()
 text=f'''[General]
Name=BFT
[Video]
BaseCX={width}
BaseCY={height}
OutputCX={width}
OutputCY={height}
FPSType=1
FPSInt=15
ScaleType=bilinear
[Audio]
SampleRate=48000
ChannelSetup=Stereo
[Output]
Mode=Advanced
FilenameFormatting=BFT-%CCYY-%MM-%DD-%hh-%mm-%ss
OverwriteIfExists=false
[SimpleOutput]
RecRBPrefix=Incident
[AdvOut]
RecType=Standard
RecFilePath={folder.as_posix()}
RecFormat2=mkv
RecEncoder={enc}
Encoder={enc}
RecTracks=1
TrackIndex=1
RecRB=true
RecRBTime=300
RecRBSize=160
Track1Bitrate=96
ApplyServiceSettings=false
[Hotkeys]
ReplayBuffer.Save={{"bindings":[{{"control":true,"shift":true,"key":"OBS_KEY_F9"}}]}}
'''
 (profile/'basic.ini').write_text(text,encoding='utf-8')
 settings={'rate_control':'CBR','bitrate':3000,'max_bitrate':3000,'keyint_sec':2,'preset':'p1' if 'nvenc' in enc else 'ultrafast','tune':'ll','multipass':'disabled','lookahead':False,'psycho_aq':False,'bf':0,'profile':'high'}
 for name in ['recordEncoder.json','streamEncoder.json']:(profile/name).write_text(json.dumps(settings))
 (profile/'service.json').write_text(json.dumps({'type':'rtmp_custom','settings':{'server':'','key':''}}))
 plugin=base/'plugin_config/obs-websocket';plugin.mkdir(parents=True,exist_ok=True);(plugin/'config.json').write_text(json.dumps({'first_load':False,'server_enabled':False,'auth_required':True,'server_password':secrets.token_urlsafe(32),'alerts_enabled':False}))
 collection={'name':'BFT Evidence','current_scene':'BFT Evidence','current_program_scene':'BFT Evidence','scene_order':[{'name':'BFT Evidence'}],'sources':[{'name':'BFT Evidence','id':'scene','settings':{'items':[]}}],'modules':{'scripts-tool':[{'path':(BASE/'recorder_control.lua').as_posix(),'settings':{'command_path':(ipc/'command.txt').as_posix(),'status_path':(ipc/'status.txt').as_posix()}}]}}
 (scenes/'BFT.json').write_text(json.dumps(collection));return enc

class OwnedProcess:
 def __init__(self,args,cwd):
  from session_lifecycle import HelperJob,k
  self.k=k;self.job=HelperJob();self.pid=self.job.start(args,cwd);self.handle=k.OpenProcess(0x101001,False,self.pid)
  if not self.handle:self.job.close();raise OSError('Recorder process could not be monitored.')
 def poll(self):return None if self.handle and self.k.WaitForSingleObject(self.handle,0)==258 else 0
 def wait(self,timeout):
  if self.k.WaitForSingleObject(self.handle,int(timeout*1000))==258:raise subprocess.TimeoutExpired('owned recorder',timeout)
  return 0
 def terminate(self):self.job.close()
 def close(self):
  self.job.close()
  if self.handle:self.k.CloseHandle(self.handle);self.handle=None

class Recorder:
 def __init__(self,config=None,runtime=RUNTIME,game=None):
  self.config=validate(config);self.runtime=Path(runtime);self.game=Path(game) if game else None;self.lock=threading.RLock();self.commands=queue.Queue(maxsize=8);self.process=None;self.ipc=None;self.closed=False;self.started=0;self.pending_save=None;self.last_save=0;self.seen_clip='';self.state={'active':False,'message':'Recorder off.','last_clip':'','encoder':'','capture_width':0,'capture_height':0};self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
  if self.config['enabled']:self.action('start')
 def configure(self,config):
  new=validate(config)
  with self.lock:
   if self.process and new['folder']!=self.config['folder']:raise ValueError('Stop the recorder before changing the incident folder.')
   self.config=new
 def action(self,action):
  if action not in ['start','stop','save']:raise ValueError('Unknown recorder action.')
  if action=='save':
   with self.lock:
    if not self.state['active']:raise ValueError('Start the rolling buffer before saving an incident.')
    if self.pending_save or time.time()-self.last_save<3:raise ValueError('The previous incident is still saving. Try again shortly.')
    self.pending_save=time.time();self.last_save=time.time()
  try:self.commands.put_nowait(action)
  except queue.Full:
   if action=='save':self.pending_save=None
   raise ValueError('Recorder is busy. Please wait.')
 def message(self,text):
  with self.lock:self.state['message']=text
 def issue(self,action):
  if self.ipc:
   temp=self.ipc/'command.tmp';temp.write_text(secrets.token_hex(8)+'\n'+action+'\n');temp.replace(self.ipc/'command.txt')
 def launch(self):
  if self.process and self.process.poll() is None:return
  exe=install_engine(self.message);self.ipc=self.runtime/('session-'+secrets.token_hex(8));width,height=1680,1050
  # Query only the OS client rectangle; no game memory is opened.
  try:
   from ctypes import wintypes as W
   u=ctypes.WinDLL('user32');u.FindWindowW.argtypes=[W.LPCWSTR,W.LPCWSTR];u.FindWindowW.restype=W.HWND;u.GetClientRect.argtypes=[W.HWND,ctypes.POINTER(W.RECT)];rect=W.RECT();h=u.FindWindowW(None,'EverQuest')
   if h and u.GetClientRect(h,ctypes.byref(rect)):width,height=rect.right,rect.bottom
  except OSError:pass
  self.state['encoder']=prepare(self.config,exe.parents[2],self.ipc,width,height);self.message('Starting EQ-only replay buffer.');self.started=0;self.seen_clip=''
  self.process=OwnedProcess([str(exe),'--portable','--multi','--disable-updater','--profile','BFT','--collection','BFT Evidence','--minimize-to-tray'],exe.parent)
  self.issue('start');self.launch_at=time.time()
 def stop(self):
  self.issue('stop')
  if self.process:
   # Only the exact child process object created by this controller is terminated.
   try:self.process.wait(timeout=1)
   except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=5)
   self.process.close();self.process=None
  self.state['active']=False;self.started=0;self.message('Recorder off. Saved incidents are kept.')
 def poll(self):
  if not self.process:return
  if self.process.poll() is not None:self.state['active']=False;self.message('Recorder stopped unexpectedly. Check the isolated OBS log.');self.process.close();self.process=None;return
  try:
   path=self.ipc/'status.txt'
   if time.time()-path.stat().st_mtime>8:return
   lines=path.read_text(encoding='utf-8').splitlines()
   if len(lines)<6:return
   active=lines[1]=='active';was=self.state['active'];self.state.update(active=active,capture_width=int(lines[4]),capture_height=int(lines[5]))
   if active and not was:self.started=time.time()
   if lines[3]:self.message(lines[3])
   elif active:self.message('Rolling last five minutes of EQ + game audio. No microphone. Old buffer stays in RAM.' if int(lines[4]) else 'Buffer is running, but EQ is not captured yet. Restore the EQ window.')
   elif time.time()-self.launch_at>20:self.message('Recorder initialized, but replay is not active. Check the isolated OBS log.')
   clip=lines[2]
   if clip and clip!=self.seen_clip:
    file=Path(clip).resolve();folder=Path(self.config['folder']).resolve()
    if file.is_relative_to(folder) and file.is_file():
     self.seen_clip=clip;self.state['last_clip']=str(file);self.pending_save=None
     note=file.with_suffix('.json');note.write_text(json.dumps({'saved_at':time.time(),'capture':'EverQuest window + EQ process audio','microphone':False,'rolling_seconds':300,'file':file.name},indent=2))
     self.message('Incident saved. This clip will not be automatically deleted.')
  except (OSError,ValueError):pass
  if self.pending_save and time.time()-self.pending_save>30:self.pending_save=None;self.message('Save did not complete within 30 seconds. Check free disk space and recorder log.')
 def run(self):
  while not self.closed:
   try:
    action=self.commands.get(timeout=.5)
    if action=='start':self.launch()
    elif action=='stop':self.stop()
    elif action=='save':self.issue('save');self.message('Saving the last five minutes...')
   except queue.Empty:pass
   except Exception as e:self.message(str(e));self.pending_save=None;self.state['active']=False
   with self.lock:self.poll()
  self.stop()
 def snapshot(self):
  with self.lock:
   clips=[];folder=Path(self.config['folder'])
   try:
    for f in sorted(folder.glob('Incident BFT-*.mkv'),key=lambda p:p.stat().st_mtime,reverse=True)[:30]:clips.append({'name':f.name,'bytes':f.stat().st_size,'saved':f.stat().st_mtime})
   except OSError:pass
   return dict(self.state,settings=dict(self.config),buffer_seconds=min(300,int(time.time()-self.started)) if self.started and self.state['active'] else 0,saving=bool(self.pending_save),clips=clips,engine_installed=engine_path().is_file())
 def close(self):self.closed=True;self.thread.join(timeout=8)
