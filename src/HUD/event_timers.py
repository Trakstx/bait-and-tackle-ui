"""Log-only timers. EQTool MIT-derived schedules/patterns; no game input or uploads."""
import datetime as dt,hashlib,json,math,re,threading,time,urllib.request
from pathlib import Path
from collections import deque
from buff_timers import STAMP
DATA=json.loads(Path(__file__).with_name('eqtool_timers.json').read_text())
AOES=[dict(r,regex=re.compile(r['pattern'],re.I)) for r in DATA['aoes']]
SERVERS={'blue':'Blue','green':'Green','red':'Red'}

def validate(data=None):
 c=dict(visible=True,collapsed=False,enabled=True,shared_enabled=True,scout=True,ring8=True,boats=False,raid=True,respawn=False,respawn_seconds=400,zone_respawn=True,warning_seconds=30,sound=True,move_mode=False,x=940,y=150,width=420,height=0,rows=5);c.update(data or {})
 for k,lo,hi in [('respawn_seconds',1,604800),('warning_seconds',0,3600),('x',0,16384),('y',0,16384),('width',240,800),('height',0,800),('rows',1,8)]:
  v=float(c[k])
  if not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Invalid timer '+k)
  c[k]=int(v)
 return {k:(bool(c[k]) if k in ['visible','collapsed','enabled','shared_enabled','scout','ring8','boats','raid','respawn','zone_respawn','sound','move_mode'] else c[k]) for k in ['visible','collapsed','enabled','shared_enabled','scout','ring8','boats','raid','respawn','zone_respawn','respawn_seconds','warning_seconds','sound','move_mode','x','y','width','height','rows']}

def timestamp(value):
 v=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
 if v.tzinfo is None:raise ValueError('Timer time must include timezone.')
 return v.timestamp()

def duration(value):
 parts=str(value).strip().split(':')
 if not 1<=len(parts)<=3 or any(not s.isdigit() for s in parts):raise ValueError('Use seconds, mm:ss, or hh:mm:ss.')
 if len(parts)>1 and any(int(s)>59 for s in parts[1:]):raise ValueError('Minutes/seconds must be below 60.')
 seconds=0
 for s in parts:seconds=seconds*60+int(s)
 if not 1<=seconds<=604800:raise ValueError('Timer must be 1 second to 7 days.')
 return seconds

class Timers:
 def __init__(self,config=None,state_dir=None):
  self.lock=threading.RLock();self.config=validate(config);self.state_dir=Path(state_dir) if state_dir else None;self.server='';self.character='Waiting for login';self.zone=None;self.local={};self.remote={};self.audio=deque(maxlen=8);self.last={};self.fetched=0;self.error='Waiting for character/server detection.';self.next_fetch=0;self.fetching=False;self.closed=False;self.thread=None
 def configure(self,c):
  with self.lock:
   self.config=validate(c)
   if not self.config['sound'] or not self.config['enabled']:self.audio.clear()
 def path(self):return self.state_dir/(self.server+'.json') if self.state_dir and self.server else None
 def save(self):
  p=self.path()
  if p:
   try:p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps({'local':self.local,'remote':self.remote,'fetched':self.fetched}));tmp.replace(p)
   except OSError:pass
 def set_character(self,name,server):
  server=SERVERS.get(str(server).casefold(),'')
  with self.lock:
   self.character=name;self.zone=None;self.audio.clear();self.last.clear()
   if server==self.server:return
   self.server=server;self.local={};self.remote={};self.fetched=0;self.next_fetch=0;self.error='Waiting for shared estimates.'
   p=self.path()
   if p:
    try:
     v=json.loads(p.read_text());now=time.time()
     for field in ['local','remote']:
      rows=v.get(field,{})
      if isinstance(rows,dict):setattr(self,field,{str(k):r for k,r in list(rows.items())[:100] if isinstance(r,dict) and isinstance(r.get('ends'),(int,float)) and now-120<r['ends']<now+604800 and all(k in r for k in ['id','name','detail','duration','started','source','category'])})
     self.fetched=float(v.get('fetched',0))
    except (OSError,ValueError,TypeError):pass
 def start(self,name,seconds,now=None,key=None,source='Manual',category='custom',detail='Estimated countdown'):
  now=time.time() if now is None else now;seconds=duration(seconds);name=' '.join(str(name).split())[:80] or 'Custom timer';key=key or 'custom:'+hashlib.sha256(name.encode()).hexdigest()[:16]
  with self.lock:
   self.local[key]=dict(id=key,name=name,message=name,detail=detail,duration=seconds,started=now,ends=now+seconds,source=source,category=category,warned=False,finished=False,test=False,severity='info')
   if len(self.local)>100:self.local.pop(next(iter(self.local)))
   self.save()
  return key
 def remove(self,key):
  with self.lock:self.local.pop(str(key),None);self.save()
 def consume(self,line,now,zone=None):
  match=STAMP.match(line);text=match[2] if match else line.strip()
  if match:
   try:when=dt.datetime.strptime(match[1],'%a %b %d %H:%M:%S %Y').timestamp()
   except ValueError:return
   if now-when>15 or when>now+3:return
  if len(text)>4096:return
  with self.lock:
   self.zone=zone
   if not self.config['enabled']:return
   # Only explicit timer commands in your own chat can create a custom countdown.
   chat=re.match(r"^You (?:say|tell|shout|auction)[^']*'((?:StartTimer|PigTimer)-[^']+)'\s*$",text,re.I)
   if chat:
    cmd=re.fullmatch(r'(?:StartTimer|PigTimer)-([\d:]+)(?:-([^\s]{1,80}))?',chat[1],re.I)
    if cmd:
     try:self.start((cmd[2] or 'Custom timer').replace('_',' '),cmd[1],now,source='Own log command')
     except ValueError:pass
   slain=re.match(r'^(.+?) has been slain by .+?[!.]$',text)
   if slain:
    npc=slain[1]
    if npc.casefold()=='scout charisa':self.start('Scout Charisa',36000,now,key='scout-local',source='Observed death',category='scout',detail='10-hour estimate from your log')
    if npc in DATA['kael']:self.start('Next Kael faction pull',1680,now,key='kael',source='Observed death',category='raid',detail='28-minute estimate; EQTool schedule')
    if self.config['respawn'] and zone:self.start(npc,self.config['respawn_seconds'],now,key='spawn:'+str(now),source='Observed death',category='respawn',detail=zone+' · configured respawn estimate')
   if self.config['raid']:
    if text=="Seneschal Aldikar shouts, TROOPS, TAKE YOUR POSITIONS!" and now-self.last.get('ringwar',0)>10:
     self.last['ringwar']=now;total=0
     for wave in range(1,4):
      if wave==2:total+=6
      for round in range(1,8):
       total+=210;self.start(f'Ring War wave {wave} round {round}',total,now,key=f'ringwar:{wave}:{round}',source='Observed Ring War start',category='raid')
      total+=300+(6 if wave==3 else 0);self.start(f'Ring War wave {wave} break',total,now,key=f'ringwar:{wave}:break',source='Observed Ring War start',category='raid')
     self.start('Narandi the Wretched',5530,now,key='ringwar:narandi',source='Observed Ring War start',category='raid')
    events=[]
    if re.search(r'You flee in terror\.|You resist the Dragon Roar spell!',text):events.append(('dragon-roar','Dragon Roar',36))
    if zone=='fearplane':
     m=re.match(r"^(Fright|Dread) says,? '([^' ]+)'",text)
     if m:events.append(('dt:'+m[1],'Death Touch: '+m[2],45))
    if zone=='kael' and "Who dares defile my temple?! Come forth and face me!" in text:events.append(('aow','Avatar of War lockout',1200))
    for r in AOES:
     if zone==r['zone'] and r['regex'].search(text):events.append(('aoe:'+r['zone']+':'+r['name'],r['name'],r['seconds']))
    for key,name,seconds in events:
     if now-self.last.get(key,0)<3:continue
     self.last[key]=now;self.start(name,seconds,now,key,source='Observed log',category='raid',detail='EQTool encounter estimate · '+str(zone or 'zone unknown'))
   if self.config['boats']:
    for b in DATA['boats']:
     if b['announcement'] and b['announcement'] in text:
      self.add_boat(b,now,now,'Local announcement',self.local);self.save()
 def add_boat(self,b,seen,now,source,out):
  for dest in DATA['boats']:
   if dest['boat']!=b['boat']:continue
   left=(dest['offset']-(now-seen)%b['trip'])%b['trip'];key='boat:'+dest['boat']+':'+dest['start']
   out[key]=dict(id=key,name=dest['name'],message=dest['name'],detail='Estimated arrival · observed '+dt.datetime.fromtimestamp(seen).strftime('%b %d %H:%M'),duration=b['trip'],started=now-(b['trip']-left),ends=now+left,source=source,category='boats',test=False,severity='info',cycle=b['trip'],anchor=seen,offset=dest['offset'])
 def fetch_shared(self,server):
  result={};now=time.time();error='';fetched=0
  try:
   def get(path):
    req=urllib.request.Request('https://pigparse.azurewebsites.net/api/'+path+'/'+server,headers={'User-Agent':'BaitAndTackle/1.0 (read-only timers)'})
    with urllib.request.urlopen(req,timeout=8) as r:
     body=r.read(262145)
     if len(body)>262144:raise ValueError('Timer response too large.')
     rows=json.loads(body)
     if not isinstance(rows,list):raise ValueError('Invalid timer feed.')
     return rows[:100]
   for r in get('rolltimer/timers'):
    name=r.get('name');end=timestamp(r['dateTime']);guess=bool(r.get('guess'))
    if name=='Scout Charisa':category='scout';seconds=36000;label='Scout Charisa';key='scout-shared'
    elif name=='Quake':
     category='ring8';seconds=86400;label='Ring 8 roll';key='ring8-shared';end=end-1800;end+=max(0,math.floor((now-end)/86400)+1)*86400;guess=True
    else:continue
    result[key]=dict(id=key,name=label,message=label,detail='Shared estimate'+(' · uncertain' if guess or end<=now else '')+' · EQTool/PigParse',started=end-seconds,ends=end,duration=seconds,source='Shared feed',category=category,test=False,severity='info',guess=guess)
   fetched=now
   if self.config['boats']:
    for r in get('boat/serverActivity'):
     enum=['BarrelBarge','BloatedBelly','MaidensVoyage','NroIcecladBoat'];boat=r.get('boat');boat=enum[boat] if isinstance(boat,int) and 0<=boat<4 else boat
     b=next((b for b in DATA['boats'] if b['boat']==boat and b['start']==r.get('startPoint')),None)
     if b:self.add_boat(b,timestamp(r['lastSeen']),now,'Shared feed',result)
  except (OSError,ValueError,TypeError,KeyError,OverflowError) as e:error='Shared feed unavailable: '+str(e)[:140]
  with self.lock:
   if self.server==server and not self.closed:
    if fetched:self.remote=result;self.fetched=fetched;self.save()
    self.error=error
   self.fetching=False
 def tick(self,now):
  with self.lock:
   if not self.closed and self.config['enabled'] and self.config['shared_enabled'] and self.server and now>=self.next_fetch and not self.fetching:
    self.next_fetch=now+90;self.fetching=True;self.thread=threading.Thread(target=self.fetch_shared,args=(self.server,),daemon=True);self.thread.start()
   changed=False
   for key,r in list(self.local.items()):
    if r['category']=='boats':continue
    left=r['ends']-now
    if self.config['enabled'] and self.config['sound']:
     if 0<left<=self.config['warning_seconds'] and not r.get('warned'):
      r['warned']=True;changed=True;self.audio.append({'text':r['name']+' in '+str(math.ceil(left))+' seconds.','severity':'warn'})
     if -10<left<=0 and not r.get('finished'):
      r['finished']=True;changed=True;self.audio.append({'text':r['name']+' timer finished.','severity':'info'})
    if left < -120:self.local.pop(key);changed=True
   if changed:self.save()
 def take_audio(self):
  with self.lock:rows=list(self.audio);self.audio.clear();return rows
 def snapshot(self,now):
  with self.lock:
   rows=[];source=dict(self.remote) if self.config['shared_enabled'] else {};source.update(self.local)
   if 'scout-local' in source:source.pop('scout-shared',None)
   for raw in source.values():
    r=dict(raw);category=r['category']
    if category in ['scout','ring8','boats','raid','respawn'] and not self.config[category]:continue
    if category=='boats':r['ends']=now+(r['offset']-(now-r['anchor'])%r['cycle'])%r['cycle']
    left=r['ends']-now
    if left< -120 and category not in ['scout','ring8']:continue
    r.update(remaining=max(0,left),status='Unknown / overdue' if left<=0 and category in ['scout','ring8'] else 'Due' if left<=0 else 'Running',severity='warn' if left<=self.config['warning_seconds'] else 'info')
    r['message']=r['name'];r['detail']=r['status']+' · '+r['detail'];rows.append(r)
   rows.sort(key=lambda r:(r['remaining']>0,r['remaining'],r['name']))
   return {'alerts':rows,'class':'Timers','character':self.character,'server':self.server,'zone':self.zone,'fetched':self.fetched,'stale':now-self.fetched>180,'error':self.error,'catalog':[{'name':r['name'],'zone':r['zone'],'seconds':r['seconds']} for r in DATA['aoes']]}
 def close(self):
  with self.lock:self.closed=True;self.save()
