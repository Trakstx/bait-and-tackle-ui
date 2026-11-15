"""Log-only Klandicar prompts. Recast floors are NOT guaranteed NPC schedules."""
import datetime,math,re,threading,time
SOURCES=['https://wiki.project1999.com/Klandicar','https://wiki.project1999.com/Silver_Breath','https://wiki.project1999.com/Dragon_Roar']
SPELLS={'roar':('Dragon Roar',36.0),'breath':('Silver Breath',12.0)}
STAMP=re.compile(r'^\[([^]]+)\]\s*(.*)$')
CHAT=re.compile(r"^(?:You|[A-Za-z][A-Za-z`'-]*) (?:say|says|tell|tells|shout|shouts|auction|auctions|say out of character|says out of character)\b.*'",re.I)
def validate(data=None):
 d=data or {};lead=float(d.get('da_lead',3))
 if not math.isfinite(lead) or not 1<=lead<=10:raise ValueError('DA lead must be 1-10 seconds')
 ice=float(d.get('ice_lead',10))
 if not math.isfinite(ice) or not 1<=ice<=30:raise ValueError('Ice Breath lead must be 1-30 seconds')
 return {'yelinak_enabled':bool(d.get('yelinak_enabled',True)),'ice_lead':ice,'enabled':bool(d.get('enabled',True)),'da_enabled':bool(d.get('da_enabled',True)),'da_lead':lead}
class Encounter:
 def __init__(self,config=None):
  from yelinak import Yelinak
  self.yelinak=Yelinak()
  self.lock=threading.RLock();self.config=validate(config);self.character='';self.zone=None;self.active=False;self.manual=False;self.last_activity=0;self.seen={};self.notice=None;self.fear=False;self.enraged=False
 def configure(self,data):
  with self.lock:
   self.config=validate(data)
   if not self.config['enabled']:self.reset()
 def reset(self):
  self.yelinak.reset()
  self.active=False;self.manual=False;self.seen={};self.notice=None;self.fear=False;self.enraged=False;self.last_activity=0
 def set_character(self,name):
  with self.lock:
   if name!=self.character:self.reset();self.zone=None;self.character=name;self.yelinak.character=name
 def arm(self,now=None):
  with self.lock:
   if not self.config['enabled']:raise ValueError('Enable Klandicar alerts first')
   if self.zone and self.zone!='westwastes':raise ValueError('Klandicar alerts are for Western Wastes')
   self.reset();self.active=True;self.manual=True;self.last_activity=time.time() if now is None else now
 def disarm(self):
  with self.lock:self.reset()
 def consume(self,line,now,zone=None):
  self.yelinak.consume(line,now,zone)
  if self.yelinak.active:return
  text=line.strip();event=now;m=STAMP.match(text)
  if m:
   try:event=datetime.datetime.strptime(m[1],'%a %b %d %H:%M:%S %Y').timestamp()
   except ValueError:return
   if now-event>5 or event-now>3:return
   text=m[2]
  if len(text)>4096:return
  with self.lock:
   if zone!=self.zone and zone is not None:
    self.zone=zone
    if zone!='westwastes':self.reset()
   if text.startswith(('LOADING, PLEASE WAIT','Welcome to EverQuest!')):self.reset();self.zone=None;return
   if not self.config['enabled'] or (self.zone and self.zone!='westwastes') or CHAT.match(text):return
   if re.match(r'^(?:Klandicar has been slain by |You have slain Klandicar[!.]|You have been slain by |You died\.)',text,re.I):self.reset();return
   # Require actual named encounter activity, never a chat mention.
   named=bool(re.match(r'^Klandicar (?:hits|slashes|crushes|pierces|bashes|kicks|bites|claws|tries to |begins to cast|has become ENRAGED|is no longer enraged|goes on a RAMPAGE|rampages)',text,re.I) or re.match(r'^(?:You|[A-Za-z][A-Za-z`-]*) .+? Klandicar for \d+ points? of damage[!.]$',text,re.I))
   if named:
    self.active=True;self.last_activity=now
   if not self.active:return
   if re.match(r'^Klandicar has become ENRAGED[!.]',text,re.I):self.enraged=True;self.notice=('ENRAGE: STOP FRONTAL MELEE - follow tank calls',now+12,'danger')
   elif re.match(r'^Klandicar is no longer enraged[!.]',text,re.I):self.enraged=False;self.notice=('Enrage ended - resume only on raid call',now+5,'info')
   elif re.match(r'^Klandicar (?:goes on a RAMPAGE|rampages)[!.]',text,re.I):self.notice=('RAMPAGE: heal assigned ramp tank; hold assigned positions',now+5,'warn')
   kind=None
   if text in ('You flee in terror.','You resist the Dragon Roar spell!'):kind='roar';self.fear=text=='You flee in terror.'
   if text=='You are no longer afraid.':self.fear=False
   if text=='You feel your skin freeze.' or text=='You resist the Silver Breath spell!' or re.match(r"^[A-Za-z][A-Za-z`'-]*'?s skin freezes\.$",text):kind='breath'
   if kind and event-self.seen.get(kind,-1000)>=3:
    self.seen[kind]=event;self.last_activity=now
    if kind=='breath':self.notice=('SILVER BREATH: check top buff; refresh junk buff if dispelled',now+7,'warn')
    else:self.notice=('FEAR LANDED: wait for control; follow raid recovery plan' if self.fear else 'Dragon Roar resisted - next recast window estimated',now+5,'warn')
 def snapshot(self,now):
  with self.lock:
   ys=self.yelinak.snapshot(now,self.config)
   if ys['active']:return ys
   if self.active and not self.manual and now-self.last_activity>120:self.reset()
   rows=[]
   for key,(name,interval) in SPELLS.items():
    anchor=self.seen.get(key);remaining=anchor+interval-now if anchor is not None else None
    status='unknown' if remaining is None or remaining < -8 else ('ready' if remaining<=0 else 'countdown')
    rows.append({'id':key,'name':name,'remaining':max(0,remaining) if status=='countdown' else None,'status':status,'observed_at':anchor,'interval':interval})
   roar=rows[0];warning=self.active and self.config['da_enabled'] and roar['status']=='countdown' and roar['remaining']<=self.config['da_lead']
   if self.fear:message='FEARED: control unavailable - follow raid recovery plan';severity='danger'
   elif self.enraged:message='ENRAGE: STOP FRONTAL MELEE - follow tank calls';severity='danger'
   elif warning:message='DA NOW IF READY - ESTIMATED FEAR WINDOW';severity='danger'
   elif roar['status']=='ready':message='FEAR WINDOW OPEN - timing uncertain; follow raid call';severity='warn'
   elif self.notice and now<self.notice[1]:message=self.notice[0];severity=self.notice[2]
   elif roar['status']=='unknown':message='FEAR TIMING UNKNOWN - waiting for observed Roar';severity='warn'
   else:message='Prepare fear protection / positioning; DA readiness is not known';severity='info'
   return {'active':self.active and self.config['enabled'],'manual':self.manual,'character':self.character,'zone':self.zone,'message':message,'severity':severity,'da_warning':bool(warning),'spells':rows,'note':'Log observations + spell recast floors; NOT guaranteed cast times. No automatic casting.','sources':SOURCES}
