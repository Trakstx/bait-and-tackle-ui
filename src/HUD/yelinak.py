"""Yelinak Ice Breath warning based on local Kingdom v3.0 trigger definitions."""
import re,time
from klandicar import STAMP,CHAT
import datetime
class Yelinak:
 def __init__(self):self.reset();self.zone=None;self.character='';self.role=None
 def reset(self):self.active=False;self.anchor=None;self.last=0
 def consume(self,line,now,zone):
  if zone and zone!='skyshrine':self.reset();self.zone=zone;return
  self.zone=zone;text=line.strip();event=now;m=STAMP.match(text)
  if m:
   try:event=datetime.datetime.strptime(m[1],'%a %b %d %H:%M:%S %Y').timestamp()
   except ValueError:return
   if not -3<=now-event<=5:return
   text=m[2]
  if len(text)>4096 or CHAT.match(text):return
  if text.startswith(('LOADING, PLEASE WAIT','Welcome to EverQuest!','You have been slain by ','You died.')) or re.match(r'^(Lord Yelinak has been slain by |You have slain Lord Yelinak[!.])',text):self.reset();return
  if re.match(r'^Lord Yelinak (?:engages .+!|hits |slashes |crushes |pierces |tries to |begins to cast)',text,re.I) or re.match(r'^.+ Lord Yelinak for \d+ points? of damage[!.]$',text):self.active=True;self.last=now
  if not self.active:return
  if re.fullmatch(r"(?:Shards of magical ice rend you\.  You have taken \d+ points of damage\.|[A-Za-z][A-Za-z`'-]*'s body is cut by shards of magical ice\.|You resist the Ice Breath spell!)",text):
   if self.anchor is None or event-self.anchor>=5:self.anchor=event
   self.last=now
 def snapshot(self,now,cfg):
  if now-self.last>180:self.reset()
  rem=None if self.anchor is None else self.anchor+120-now
  status='unknown' if rem is None or rem < -8 else 'ready' if rem<=0 else 'countdown'
  role=str(self.role or '').lower();eligible=role in ('cleric','bard')
  warning=self.active and cfg.get('yelinak_enabled',True) and status=='countdown' and rem<=cfg.get('ice_lead',10)
  if warning:msg=('DA NOW IF READY / ASSIGNED - ' + (role.upper() if eligible else 'FOLLOW DA CALL') + ' - ICE BREATH ESTIMATED');severity='danger'
  elif status=='unknown':msg='ICE BREATH TIMING UNKNOWN - awaiting observed landing';severity='warn'
  elif status=='ready':msg='ICE BREATH WINDOW OPEN - hold protection / follow raid call';severity='warn'
  elif now-self.anchor<5:msg='ICE BREATH OBSERVED - next window estimated; follow return call';severity='info'
  else:msg='Prepare assigned DA coverage - readiness / group coverage not known';severity='info'
  return dict(active=self.active and cfg.get('yelinak_enabled',True),manual=False,boss='LORD YELINAK',character=self.character,zone=self.zone,message=msg,severity=severity,da_warning=bool(warning),spells=[dict(id='ice',name='Ice Breath / mana drain',remaining=max(0,rem) if status=='countdown' else None,status=status)],note='Kingdom v3.0: 120-second observed cooldown, not guaranteed cast time',sources=['https://wiki.project1999.com/Lord_Yelinak'])
