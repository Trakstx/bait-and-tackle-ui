"""ZlizEQMap format adapter and log-only map state for the unified dashboard.

Calibration format / coordinate conversion based on almx/ZlizEQMap (GPL-3.0).
See maps/ATTRIBUTION.txt and maps/LICENSE-ZlizEQMap.txt.
"""
import datetime as dt
import math
from pathlib import Path
import re
import threading

STAMP=re.compile(r'^\[((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) [^]]+)\]\s*(.*)$')
NUMBER=r'([+-]?(?:\d+(?:\.\d*)?|\.\d+))'
LOCATION=re.compile(r'^Your Location is '+NUMBER+r',\s*'+NUMBER+r',\s*'+NUMBER+r'\.?$',re.I)
DIRECTIONS={'north':0,'northeast':45,'east':90,'southeast':135,'south':180,'southwest':225,'west':270,'northwest':315}
def normalize(name):return re.sub(r'[^a-z0-9]','',name.casefold())
class MapCatalog:
 def __init__(self,root=None):
  self.root=Path(root) if root else Path(__file__).with_name('maps');self.maps={};self.zones={};self.aliases={}
  names={};connections={}
  for file,target in [('ZoneData-Project1999.txt',names),('ZoneConnections.txt',connections)]:
   path=self.root/'ZoneData'/file
   if not path.is_file():continue
   for line in path.read_text(encoding='utf-8-sig').splitlines():
    if line.strip() and not line.startswith('//') and '=' in line:
     k,v=line.split('=',1);target[k]=v
  for path in (self.root/'ZoneData').glob('*/*.txt'):
   match=re.fullmatch(r'(.+?)(\d)',path.stem)
   if not match or match[1] not in names:continue
   short,floor=match[1],int(match[2]);lines=path.read_text(encoding='utf-8-sig').splitlines()
   try:parts=lines[0].split('|');zero=[int(parts[0]),int(parts[1])];total=[int(parts[2]),int(parts[3])]
   except (ValueError,IndexError):continue
   if 0 in total:continue
   image=next((self.root/'ZoneMaps'/path.parent.name/(path.stem+'.'+ext) for ext in ['jpg','gif','png'] if (self.root/'ZoneMaps'/path.parent.name/(path.stem+'.'+ext)).is_file()),None)
   if image is None:continue
   key=short+':'+str(floor)
   row={'id':key,'zone':short,'name':names[short],'floor':floor,'description':parts[4] if len(parts)>4 else 'Map '+str(floor),'continent':path.parent.name[2:],'zero':zero,'total':total,'legend':lines[1:]}
   self.maps[key]=(row,image);self.zones.setdefault(short,{'id':short,'name':names[short],'continent':path.parent.name[2:],'maps':[],'connections':[]})['maps'].append(row)
  for short,zone in self.zones.items():
   zone['maps'].sort(key=lambda r:r['floor']);zone['connections']=[{'id':s,'name':self.zones[s]['name']} for s in connections.get(short,'').split(',') if s in self.zones]
   self.aliases[normalize(short)]=short;self.aliases[normalize(zone['name'])]=short
   self.aliases[normalize(re.sub(r'^(?:The |the )','',zone['name']))]=short
 def resolve(self,name):return self.aliases.get(normalize(name))
 def catalog(self):return {'zones':sorted(self.zones.values(),key=lambda z:(z['continent'],z['name'])),'source':'ZlizEQMap / EQAtlas','license':'GPL-3.0'}
 def image(self,key):
  if key not in self.maps:raise ValueError('Unknown map')
  path=self.maps[key][1];return path.read_bytes(),{'.jpg':'image/jpeg','.png':'image/png','.gif':'image/gif'}[path.suffix]

class MapTracker:
 def __init__(self,catalog):self.catalog=catalog;self.lock=threading.RLock();self.character='Waiting for login';self.zone=None;self.zone_name=None;self.position=None;self.heading=None;self.heading_at=0
 def set_character(self,name,path=None):
  with self.lock:
   self.character=name;self.zone=None;self.zone_name=None;self.position=None;self.heading=None;self.heading_at=0
   if path:
    try:
     with Path(path).open('rb') as f:
      f.seek(max(0,Path(path).stat().st_size-2097152));raw=f.read()
     complete=raw[:raw.rfind(b'\n')+1] if b'\n' in raw else b''
     for line in complete.decode('utf-8',errors='replace').splitlines():self.consume(line,0)
    except OSError:pass
 def consume(self,line,now):
  with self.lock:
   text=line.rstrip('\r\n');match=STAMP.match(text)
   if match:
    text=match[2]
    try:now=dt.datetime.strptime(match[1],'%a %b %d %H:%M:%S %Y').timestamp()
    except ValueError:return
   if text.startswith('Welcome to EverQuest!') or text.startswith('LOADING, PLEASE WAIT'):
    self.zone=None;self.zone_name=None;self.position=None;self.heading=None;return
   if text.startswith('You have entered ') and text.endswith('.'):
    name=text[len('You have entered '):-1]
    if name=='an Arena (PvP) area':return
    self.zone_name=name;self.zone=self.catalog.resolve(name);self.position=None;self.heading=None;return
   if text.startswith('You think you are heading ') and text.endswith('.'):
    self.heading=DIRECTIONS.get(text[len('You think you are heading '):-1].replace(' ','').casefold());self.heading_at=now;return
   match=LOCATION.fullmatch(text)
   if match:
    y,x,z=map(float,match.groups())
    if not all(math.isfinite(v) and abs(v)<1e8 for v in [y,x,z]):return
    self.position={'y':y,'x':x,'z':z,'at':now,'zone':self.zone,'heading':self.heading if 0<=now-self.heading_at<=2 else None}
 def snapshot(self,now):
  with self.lock:
   return {'character':self.character,'zone':self.zone,'zone_name':self.zone_name,'position':dict(self.position) if self.position else None,'age':max(0,now-self.position['at']) if self.position else None,'note':'Position updates only when /loc appears in your EQ log.'}
