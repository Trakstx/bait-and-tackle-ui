"""Observed warrior Defensive timers. Kingdom activation text; P99 discipline durations."""
import re,json
class Defensive:
 def __init__(self):self.start=None;self.ends=None;self.reuse=None;self.warned=set();self.remind_until=0;self.last_reminder=-1e30
 def consume(self,text,now,level):
  if re.fullmatch(r'You assume a defensive fighting style\.{1,2}',text):
   self.start=now;self.ends=now+180;self.reuse=now+(15-(level-55))*60 if isinstance(level,int) and 55<=level<=60 else None;self.warned=set();return 'Defensive activated'
  if text.startswith(('You have been slain by ','You died.')) or re.fullmatch(r'You return to your normal fighting style\.',text):
   had=self.ends is not None;self.ends=None
   if had:return 'Defensive ended'
  # Another discipline can change shared readiness; never claim ready from Defensive alone.
  if text.startswith('You assume ') and 'fighting style' in text:self.reuse=None
  if re.match(r'^.+ (?:hits|slashes|crushes|pierces|bashes|kicks|bites|claws) YOU for \d+ points? of damage',text) and (self.ends is None or self.ends<=now) and now-self.last_reminder>=60:
   self.last_reminder=now;self.remind_until=now+12;return 'Tank reminder: Defensive if assigned and ready'
 def tick(self,now):
  if self.ends is not None:
   left=self.ends-now
   for mark in (30,10,0):
    if left<=mark and mark not in self.warned:
     self.warned.add(mark)
     if mark==0:self.ends=None;return 'Defensive ended - tank handoff if assigned'
     return 'Defensive ending in '+str(mark)+' seconds'
 def row(self,now):
  if self.ends and self.ends>now:
   left=self.ends-now;msg='DEFENSIVE ACTIVE';detail='Expires in '+fmt(left)+' - prepare handoff' if left<=30 else 'Active remaining '+fmt(left);duration=180;severity='danger' if left<=10 else 'warn' if left<=30 else 'info'
  elif self.reuse and self.reuse>now:left=self.reuse-now;msg='DEFENSIVE REUSE ~'+fmt(left);detail='Estimate; shared discipline lockouts may change availability';duration=0;severity='warn'
  else:
   left=0;msg='DEFENSIVE - CHECK /disc';detail='Use if assigned to tank; readiness not verified';duration=0;severity='warn' if now<self.remind_until else 'info'
  return dict(id='warrior-defensive',name='Defensive',message=msg,detail=detail,remaining=left,duration=duration,severity=severity,test=False,started=self.start or now,ends=self.ends or now+1)
def fmt(seconds):
 n=max(0,int(seconds+0.999));return str(n//60)+':'+str(n%60).zfill(2)
