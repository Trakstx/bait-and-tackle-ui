"""Small class-aware log trigger engine; bounded literal/wildcard matching only."""
import fnmatch,hashlib,json,math,re,threading,time,uuid
from pathlib import Path
from collections import deque
from buff_timers import WHO,TITLES,CLASSES,STAMP
from logwatch import identity
P99_CLASSES=CLASSES[:14]
CASTERS=[c for c in P99_CLASSES if c not in ['warrior','monk','rogue']]

def preset(key,name,patterns,message,classes=(),severity='warn',duration=0,cooldown=3):
 return {'id':'preset:'+key,'name':name,'patterns':patterns,'mode':'wildcard','message':message,'classes':list(classes),'severity':severity,'duration_seconds':duration,'cooldown_seconds':cooldown,'sound':severity=='danger','enabled':True,'builtin':True}
PRESETS=[
 preset('enrage','Enrage',['* has become ENRAGED.','* has become ENRAGED!'],'ENRAGE — stop frontal melee',severity='danger'),
 preset('gating','NPC gating',['* begins to cast the gate spell.'],'NPC GATING — interrupt if able',cooldown=5),
 preset('invis','Invisibility fading',['You feel yourself starting to appear.'],'INVISIBILITY FADING',severity='danger'),
 preset('death','Character death',['You have been slain by *!','You died.'],'YOU HAVE DIED',severity='danger'),
 preset('fizzle','Spell fizzle',['Your spell fizzles!'],'SPELL FIZZLED',CASTERS,severity='info',cooldown=2),
 preset('interrupted','Spell interrupted',['Your spell is interrupted.'],'CAST INTERRUPTED',CASTERS),
 preset('mana','Out of mana',['Insufficient Mana to cast this spell!'],'NOT ENOUGH MANA',CASTERS,cooldown=5),
 preset('resist','Target resisted',['Your target resisted the * spell.','Your target resisted the * spell!'],'SPELL RESISTED',CASTERS,cooldown=2),
 preset('charm','Charm break',['Your charm spell has worn off.'],'CHARM BROKE — control your pet',['enchanter','druid','necromancer','bard'],severity='danger'),
 preset('feign','Failed feign death',['{character} has fallen to the ground.','You have fallen to the ground.'],'FEIGN DEATH FAILED',['monk','necromancer','shadow knight'],severity='danger'),
 preset('song','Song interrupted',['Your song is interrupted.','You miss a note, bringing your song to a close!'],'SONG INTERRUPTED',['bard']),
 preset('hide','Hide failed',['You failed to hide yourself!'],'HIDE FAILED',['rogue','ranger','shadow knight','bard'],cooldown=2),
]
PRESET_IDS={r['id'] for r in PRESETS}

def number(value,low,high,label):
 value=float(value)
 if not math.isfinite(value) or not low<=value<=high:raise ValueError(label+' is out of range.')
 return value

def validate_rule(row):
 if not isinstance(row,dict):raise ValueError('Invalid trigger rule.')
 name=str(row.get('name','')).strip();pattern=str(row.get('pattern','')).strip();message=str(row.get('message','')).strip()
 if not name or len(name)>60 or not pattern or len(pattern)>200 or not message or len(message)>180:raise ValueError('Each trigger needs a name (60 chars), match text (200 chars), and message (180 chars).')
 mode=row.get('mode','contains');severity=row.get('severity','warn');classes=row.get('classes',[])
 if mode not in ['contains','exact','wildcard'] or severity not in ['info','warn','danger']:raise ValueError('Invalid match mode or severity.')
 if not isinstance(classes,list) or any(c not in P99_CLASSES for c in classes):raise ValueError('Choose valid P1999 classes.')
 key=str(row.get('id','')).strip()
 if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',key):key=uuid.uuid4().hex
 return {'id':key,'name':name,'pattern':pattern,'message':message,'mode':mode,'severity':severity,'classes':list(dict.fromkeys(classes)), 'enabled':bool(row.get('enabled',True)),'sound':bool(row.get('sound',False)), 'duration_seconds':number(row.get('duration_seconds',0),0,3600,'Timer duration'),'cooldown_seconds':number(row.get('cooldown_seconds',3),0,300,'Repeat cooldown'),'builtin':False}

def validate(data=None):
 c=dict(enabled=True,sound_enabled=False,move_mode=False,x=500,y=160,width=420,rows=4,class_overrides={},preset_overrides={},custom=[]);c.update(data or {})
 overrides=c['class_overrides'];preset_overrides=c['preset_overrides'];custom=c['custom']
 if not isinstance(overrides,dict) or len(overrides)>200 or any(not re.fullmatch(r'[a-f0-9]{64}',k) or v not in P99_CLASSES for k,v in overrides.items()):raise ValueError('Invalid character class override.')
 if not isinstance(preset_overrides,dict) or any(k not in PRESET_IDS or not isinstance(v,bool) for k,v in preset_overrides.items()):raise ValueError('Invalid preset selection.')
 if not isinstance(custom,list) or len(custom)>100:raise ValueError('Use up to 100 custom triggers.')
 rules=[validate_rule(row) for row in custom]
 if len({r['id'] for r in rules})!=len(rules):raise ValueError('Custom trigger IDs must be unique.')
 return {'enabled':bool(c['enabled']),'sound_enabled':bool(c['sound_enabled']),'speech_style':'natural','speech_voice':str(c.get('speech_voice',''))[:200],'audio_mode':str(c.get('audio_mode','speech')) if c.get('audio_mode','speech') in ('speech','beep') else 'speech','speech_volume':int(number(c.get('speech_volume',80),0,100,'Speech volume')),'speech_rate':int(number(c.get('speech_rate',0),-10,10,'Speech rate')),'move_mode':bool(c['move_mode']), 'x':int(number(c['x'],0,16384,'Panel X')),'y':int(number(c['y'],0,16384,'Panel Y')),'width':int(number(c['width'],240,800,'Panel width')),'rows':int(number(c['rows'],1,8,'Visible alerts')),'class_overrides':dict(overrides),'preset_overrides':dict(preset_overrides),'custom':rules}

def render(text,character,kind,line):
 return text.replace('{character}',character).replace('{class}',kind or 'Unknown class').replace('{line}',line)[:220]

def matches(rule,text,character):
 patterns=rule.get('patterns',[rule.get('pattern','')])
 for pattern in patterns:
  pattern=pattern.replace('{character}',character)
  if rule['mode']=='contains' and pattern.casefold() in text.casefold():return True
  if rule['mode']=='exact' and pattern.casefold()==text.casefold():return True
  if rule['mode']=='wildcard' and fnmatch.fnmatchcase(text.casefold(),pattern.casefold()):return True
 return False

class TriggerEngine:
 def __init__(self,config=None,profile_dir=None):
  from warrior_defensive import Defensive
  self.defensive=Defensive()
  self.lock=threading.RLock();self.profile_dir=Path(profile_dir) if profile_dir else None;self.config=validate(config);self.character='Waiting for login';self.server='';self.profile_key='';self.detected=None;self.level=None;self.active=[];self.last_fire={};self.recent=deque(maxlen=30);self.sound_pending=False;self.audio_pending=deque(maxlen=4);self.zone='';self._class=None
 def configure(self,config):
  with self.lock:
   old=self.current_class();self.config=validate(config)
   if old!=self.current_class():self.active.clear();self.last_fire.clear();self.audio_pending.clear()
   if not self.config['enabled']:self.active.clear();self.sound_pending=False
 def current_class(self):return self.config['class_overrides'].get(self.profile_key) or self.detected
 def profile_path(self):return self.profile_dir/(self.profile_key+'.json') if self.profile_dir and self.profile_key else None
 def learn(self,text):
  match=WHO.match(text)
  if not match or match[3].casefold()!=self.character.casefold():return False
  kind=TITLES.get(match[2].casefold(),match[2].casefold());level=int(match[1])
  if kind not in P99_CLASSES or not 1<=level<=60:return False
  old=self.current_class();self.detected=kind;self.level=level
  if old!=self.current_class():self.active.clear();self.last_fire.clear();self.audio_pending.clear()
  path=self.profile_path()
  if path:
   try:path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp');temp.write_text(json.dumps({'class':kind,'level':level}),encoding='utf-8');temp.replace(path)
   except OSError:pass
  return True
 def set_character(self,path):
  path=Path(path)
  with self.lock:
   from warrior_defensive import Defensive
   self.defensive=Defensive()
   self.character,self.server=identity(path);self.profile_key=hashlib.sha256(str(path.resolve()).casefold().encode()).hexdigest();self.detected=None;self.level=None;self.active.clear();self.last_fire.clear();self.audio_pending.clear();self.recent.clear();self.sound_pending=False;self.audio_pending=deque(maxlen=4);self.zone=''
   saved=self.profile_path()
   if saved:
    try:
     value=json.loads(saved.read_text(encoding='utf-8'))
     if value.get('class') in P99_CLASSES:self.detected=value['class'];self.level=value.get('level')
    except (OSError,ValueError,AttributeError):pass
   try:
    with path.open('rb') as source:source.seek(max(0,path.stat().st_size-1048576));tail=source.read().decode('utf-8',errors='replace')
    for line in tail.splitlines():
     match=STAMP.match(line)
     if match:self.learn(match[2])
   except OSError:pass
 def rules(self):
  return [dict(r,enabled=self.config['preset_overrides'].get(r['id'],r['enabled'])) for r in PRESETS]+self.config['custom']
 def eligible(self,rule):return rule['enabled'] and (not rule['classes'] or self.current_class() in rule['classes'])
 def fire(self,rule,line,now,preview=False,kind=None):
  row={'id':rule['id'],'name':rule['name'],'message':render(rule['message'],self.character,kind or self.current_class(),line),'detail':line[:220],'severity':rule['severity'],'started':now,'ends':now+(rule['duration_seconds'] if rule['duration_seconds']>0 else 5),'duration':rule['duration_seconds'],'test':preview}
  self.active=[r for r in self.active if r['id']!=row['id']];self.active.append(row);self.active=self.active[-20:];self.recent.appendleft(dict(row))
  if not preview and self.config['sound_enabled']:
   self.sound_pending=True;self.audio_pending.append(dict(text=row['message'],severity=row['severity']))
 def consume(self,line,now):
  text=line.rstrip('\r\n');stamp=STAMP.match(text)
  if stamp:
   import datetime as dt
   try:when=dt.datetime.strptime(stamp[1],'%a %b %d %H:%M:%S %Y').timestamp()
   except ValueError:return
   if when>now+3 or now-when>15:return
   text=stamp[2]
  if len(text)>4096:return
  with self.lock:
   if self.learn(text):return
   if text.startswith(('LOADING, PLEASE WAIT','Welcome to EverQuest!')):self.active.clear();self.last_fire.clear();self.audio_pending.clear();self.sound_pending=False;self.audio_pending=deque(maxlen=4);return
   if not self.config['enabled']:return
   if self.current_class()=='warrior':
    notice=self.defensive.consume(text,now,self.level)
    if notice and self.config['sound_enabled']:self.audio_pending.append(dict(text=notice,severity='warn'))
   for rule in self.rules():
    if self.eligible(rule) and matches(rule,text,self.character) and now-self.last_fire.get(rule['id'],-1e30)>=rule['cooldown_seconds']:
     self.last_fire[rule['id']]=now;self.fire(rule,text,now)
 def test(self,data,now=None):
  now=time.time() if now is None else now;rule=validate_rule(data['rule']);line=str(data.get('sample',''))[:4096];kind=data.get('class') or self.current_class()
  if kind is not None and kind not in P99_CLASSES:raise ValueError('Invalid test class.')
  match=STAMP.match(line)
  if match:line=match[2]
  hit=matches(rule,line,self.character);eligible=rule['enabled'] and (not rule['classes'] or kind in rule['classes'])
  if data.get('show') and hit:
   with self.lock:self.fire(dict(rule,id='preview:'+rule['id']),line,now,preview=True,kind=kind)
  return {'matched':hit,'eligible':eligible,'message':render(rule['message'],self.character,kind,line) if hit else '', 'class':kind,'note':'Test only. Does not run game commands or change live trigger cooldowns.'}
 def take_audio(self):
  with self.lock:
   rows=list(self.audio_pending) if self.config['enabled'] and self.config['sound_enabled'] else [];self.audio_pending.clear();self.sound_pending=False;return rows
 def take_sound(self):
  with self.lock:value=self.sound_pending;self.sound_pending=False;self.audio_pending=deque(maxlen=4);return value
 def snapshot(self,now):
  with self.lock:
   self.active=[r for r in self.active if r['ends']>now];kind=self.current_class()
   defensive_rows=[]
   if kind=='warrior' and self.config['enabled'] and (self.level is None or self.level>=55):
    notice=self.defensive.tick(now)
    if notice and self.config['sound_enabled']:self.audio_pending.append(dict(text=notice,severity='warn'))
    defensive_rows=[self.defensive.row(now)]
   return {'character':self.character,'server':self.server,'profile_key':self.profile_key,'class':kind,'detected_class':self.detected,'level':self.level,'class_source':'Manual override' if self.profile_key in self.config['class_overrides'] else 'Own /who log record' if self.detected else 'Unknown — run /who or choose a class override','alerts':defensive_rows+[dict(r,remaining=max(0,r['ends']-now)) for r in reversed(self.active)],'recent':list(self.recent),'presets':[dict(r,eligible=self.eligible(r)) for r in self.rules() if r.get('builtin')],'classes':P99_CLASSES}
