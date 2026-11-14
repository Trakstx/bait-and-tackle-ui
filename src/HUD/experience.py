"""Persistent, per-character/server XP awards and explicitly measured XP progress."""
import datetime as dt
import hashlib,json,math,os,re,sqlite3,threading,time,uuid
from pathlib import Path
from logwatch import identity
STAMP=re.compile(r'^\[([^]]+)\]\s*(.*)$')
GAIN=re.compile(r'^You gain (party )?experience[!.]+$',re.I)
KILL=re.compile(r'^(?:You have slain (.+?)|(.+?) has been slain(?: by .+?)?)[!.]$',re.I)

def database_path(game,runtime):return Path(runtime)/'experience'/ (hashlib.sha256(str(Path(game).resolve()).casefold().encode()).hexdigest()[:20]+'.sqlite3')

def connect(path):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(path,timeout=5,check_same_thread=False);db.row_factory=sqlite3.Row
 db.execute('PRAGMA journal_mode=WAL');db.executescript('''
 CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,name TEXT,server TEXT,path TEXT,game TEXT,file_key TEXT,offset INTEGER,auto TEXT,manual TEXT,last_seen REAL,camp REAL,gap INTEGER DEFAULT 0);
 CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,profile TEXT,kind TEXT,name TEXT,start REAL,end REAL,reason TEXT,game TEXT);
 CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,profile TEXT,source TEXT,auto TEXT,manual TEXT,at REAL,kind TEXT,mob TEXT,own INTEGER DEFAULT 0,party INTEGER DEFAULT 0,kill_id INTEGER,UNIQUE(profile,source));
 CREATE INDEX IF NOT EXISTS event_session ON events(auto,at);
 CREATE INDEX IF NOT EXISTS event_manual ON events(manual,at);
 CREATE TABLE IF NOT EXISTS checkpoints(id INTEGER PRIMARY KEY,session TEXT,at REAL,level INTEGER,percent REAL,awards INTEGER,kills INTEGER);
 ''');
 if 'generation' not in [row[1] for row in db.execute('PRAGMA table_info(profiles)')]:db.execute('ALTER TABLE profiles ADD COLUMN generation INTEGER DEFAULT 0');db.commit()
 return db

class ExperienceTracker:
 def __init__(self,path,game_id='unmanaged'):
  self.path=Path(path);self.db=connect(path);self.game_id=str(game_id);self.lock=threading.RLock();self.active=None
 def profile(self):return self.db.execute('SELECT * FROM profiles WHERE id=?',(self.active,)).fetchone() if self.active else None
 def new_session(self,kind,name,now):
  key=uuid.uuid4().hex;self.db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?)',(key,self.active,kind,name,now,None,'',self.game_id));self.db.execute('UPDATE profiles SET '+('auto' if kind=='auto' else 'manual')+'=? WHERE id=?',(key,self.active));return key
 def stop_sessions(self,profile,when,reason):
  for key in [profile['manual'],profile['auto']]:
   if key:self.db.execute('UPDATE sessions SET end=MAX(start,?),reason=? WHERE id=? AND end IS NULL',(when,reason,key))
  self.db.execute('UPDATE profiles SET auto=NULL,manual=NULL,camp=NULL WHERE id=?',(profile['id'],))
 def set_character(self,path,now=None):
  now=time.time() if now is None else now;path=Path(path).resolve();key=hashlib.sha256(str(path).casefold().encode()).hexdigest();name,server=identity(path)
  with self.lock,self.db:
   old=self.profile()
   if old and old['id']!=key:self.stop_sessions(old,now,'Character switched')
   self.active=key;stat=path.stat();file_key=str(stat.st_dev)+':'+str(stat.st_ino)
   row=self.profile();resume=bool(row and row['game']==self.game_id and row['file_key']==file_key and 0<=row['offset']<=stat.st_size)
   offset=row['offset'] if resume else stat.st_size
   if row and not resume:self.stop_sessions(row,row['last_seen'] or now,'Previous session ended; recovered from checkpoint')
   if row and not resume:self.db.execute('UPDATE profiles SET generation=generation+1 WHERE id=?',(key,))
   if row:self.db.execute('UPDATE profiles SET name=?,server=?,path=?,game=?,file_key=?,offset=? WHERE id=?',(name,server,str(path),self.game_id,file_key,offset,key))
   else:self.db.execute('INSERT INTO profiles(id,name,server,path,game,file_key,offset,last_seen) VALUES(?,?,?,?,?,?,?,?)',(key,name,server,str(path),self.game_id,file_key,offset,now))
   if not resume:self.new_session('auto','Automatic session',now)
   if resume:
    if stat.st_size-offset>8388608:
     offset=stat.st_size-8388608;self.db.execute('UPDATE profiles SET gap=1 WHERE id=?',(key,))
    with path.open('rb') as f:
     f.seek(offset)
     if offset!=row['offset']:f.readline()
     complete_offset=f.tell()
     while True:
      line=f.readline()
      if not line or not line.endswith(b'\n'):break
      complete_offset=f.tell();self.consume(line.decode('utf-8',errors='replace'),now,complete_offset,file_key,replay=True)
     self.db.execute('UPDATE profiles SET offset=? WHERE id=?',(complete_offset,key))
   self.db.execute('UPDATE profiles SET last_seen=? WHERE id=?',(now,key))
   return self.profile()['offset']
 def consume(self,line,now,offset=None,file_key=None,replay=False):
  text=line.rstrip('\r\n');match=STAMP.match(text);when=now
  if match:
   try:when=dt.datetime.strptime(match[1],'%a %b %d %H:%M:%S %Y').timestamp()
   except ValueError:return
   text=match[2]
   if not replay and (when>now+3 or now-when>30):return
  # Ignore ordinary combat/chat lines without writing the database for each hit.
  if not (GAIN.fullmatch(text) or KILL.fullmatch(text) or text.startswith(('Welcome to EverQuest!','You died.','You have been slain by ','It will take ','You abandon your preparations to camp.'))):return
  with self.lock,self.db:
   p=self.profile()
   if not p:return
   source=(self.game_id+':'+str(p['generation'])+':'+str(file_key or p['file_key'])+':'+str(offset)) if offset is not None else uuid.uuid4().hex
   if self.db.execute('SELECT 1 FROM events WHERE profile=? AND source=?',(self.active,source)).fetchone():return
   gain=GAIN.fullmatch(text);kill=KILL.fullmatch(text);welcome=text.startswith('Welcome to EverQuest!');death=text.startswith(('You died.','You have been slain by '));camp=re.fullmatch(r'It will take (?:you )?about (\d+) (?:more )?seconds to prepare your camp\.',text)
   if p['camp'] and when>p['camp']+2 and not welcome:self.db.execute('UPDATE profiles SET camp=NULL WHERE id=?',(self.active,))
   if text=='You abandon your preparations to camp.':self.db.execute('UPDATE profiles SET camp=NULL WHERE id=?',(self.active,))
   if camp:self.db.execute('UPDATE profiles SET camp=? WHERE id=?',(when+int(camp[1]),self.active))
   if welcome:
    # The first welcome completes startup, rather than making an empty duplicate session.
    session=self.db.execute('SELECT start FROM sessions WHERE id=?',(p['auto'],)).fetchone()
    has_events=p['auto'] and self.db.execute('SELECT 1 FROM events WHERE auto=? LIMIT 1',(p['auto'],)).fetchone()
    if session and (has_events or abs(when-session['start'])>15):self.stop_sessions(p,min(when,p['camp'] or p['last_seen'] or when),'Logged back in');self.new_session('auto','Automatic session',when)
    elif not p['auto']:self.new_session('auto','Automatic session',when)
   if gain or kill or death or welcome:
    p=self.profile()
    if not p['auto']:self.new_session('auto','Automatic session',when);p=self.profile()
    kind='gain' if gain else 'kill' if kill else 'death' if death else 'login';mob=(kill[1] or kill[2]) if kill else None;own=bool(kill and kill[1]);party=bool(gain and gain[1])
    cur=self.db.execute('INSERT INTO events(profile,source,auto,manual,at,kind,mob,own,party) VALUES(?,?,?,?,?,?,?,?,?)',(self.active,source,p['auto'],p['manual'],when,kind,mob,int(own),int(party)));event_id=cur.lastrowid
    if gain:
     candidate=self.db.execute("SELECT k.id,k.mob,g.id previous_gain FROM events k LEFT JOIN events g ON g.kill_id=k.id WHERE k.auto=? AND k.kind='kill' AND ABS(k.at-?)<=3 AND (g.id IS NULL OR ABS(g.at-k.at)>ABS(k.at-?)) ORDER BY ABS(k.at-?),k.id DESC LIMIT 1",(p['auto'],when,when,when)).fetchone()
     if candidate:
      if candidate['previous_gain']:self.db.execute('UPDATE events SET kill_id=NULL,mob=NULL WHERE id=?',(candidate['previous_gain'],))
      self.db.execute('UPDATE events SET kill_id=?,mob=? WHERE id=?',(candidate['id'],candidate['mob'],event_id))
    elif kill:
     candidate=self.db.execute("SELECT id FROM events WHERE auto=? AND kind='gain' AND kill_id IS NULL AND ABS(at-?)<=3 ORDER BY ABS(at-?),id DESC LIMIT 1",(p['auto'],when,when)).fetchone()
     if candidate:self.db.execute('UPDATE events SET kill_id=?,mob=? WHERE id=?',(event_id,mob,candidate['id']))
   self.db.execute('UPDATE profiles SET last_seen=?'+(',offset=?' if offset is not None else '')+' WHERE id=?',((when,offset,self.active) if offset is not None else (when,self.active)))
 def heartbeat(self,now=None,offset=None):
  now=time.time() if now is None else now
  with self.lock,self.db:
   p=self.profile()
   if not p:return
   if p['camp'] and now>p['camp']+3:self.stop_sessions(p,p['camp'],'Observed camp countdown completed')
   if offset is not None:self.db.execute('UPDATE profiles SET offset=MAX(offset,?),last_seen=? WHERE id=?',(offset,now,self.active))
 def counts(self,key):
  row=self.db.execute("SELECT SUM(kind='gain') awards,SUM(kind='gain' AND kill_id IS NOT NULL) kills,SUM(kind='kill' AND own=1) own_kills,SUM(kind='death') deaths FROM events WHERE auto=? OR manual=?",(key,key)).fetchone();return {k:int(row[k] or 0) for k in row.keys()}
 def checkpoint(self,level,percent,now=None):
  now=time.time() if now is None else now;level=int(level);percent=float(percent)
  if not 1<=level<=60 or not math.isfinite(percent) or not 0<=percent<=100:raise ValueError('Enter level 1–60 and XP-bar percentage 0–100.')
  with self.lock,self.db:
   p=self.profile()
   if not p or not p['auto']:raise ValueError('Log into a character with logging enabled first.')
   for key in [p['auto'],p['manual']]:
    if key:
     counts=self.counts(key);self.db.execute('INSERT INTO checkpoints(session,at,level,percent,awards,kills) VALUES(?,?,?,?,?,?)',(key,now,level,percent,counts['awards'],counts['kills']))
 def start_manual(self,name,now=None,level=None,percent=None):
  now=time.time() if now is None else now;name=str(name).strip() or 'Timed session'
  if len(name)>80:raise ValueError('Use a session name up to 80 characters.')
  with self.lock,self.db:
   p=self.profile()
   if not p or not p['auto']:raise ValueError('Log into a character with logging enabled first.')
   if p['manual']:raise ValueError('Stop the current timed session first.')
   key=self.new_session('manual',name,now)
   if level is not None and percent is not None:self.checkpoint(level,percent,now)
   return key
 def stop_manual(self,now=None,level=None,percent=None):
  now=time.time() if now is None else now
  with self.lock,self.db:
   p=self.profile()
   if not p or not p['manual']:raise ValueError('No timed session is running.')
   if level is not None and percent is not None:self.checkpoint(level,percent,now)
   self.db.execute('UPDATE sessions SET end=?,reason=? WHERE id=?',(now,'Stopped manually',p['manual']));self.db.execute('UPDATE profiles SET manual=NULL WHERE id=?',(self.active,))
 def session(self,row,now):
  out=dict(row);out.update(self.counts(row['id']));out['seconds']=max(0,(row['end'] or now)-row['start']);out['kills_per_hour']=out['kills']*3600/out['seconds'] if out['seconds'] else 0
  points=self.db.execute('SELECT * FROM checkpoints WHERE session=? ORDER BY id',(row['id'],)).fetchall();out['checkpoints']=[dict(p) for p in points];out['progress']=None
  if len(points)>1:
   a,b=points[0],points[-1];delta=(b['level']-a['level'])*100+b['percent']-a['percent'];kills=b['kills']-a['kills'];seconds=b['at']-a['at']
   out['progress']={'level_bar_points':delta,'kills':kills,'awards':b['awards']-a['awards'],'per_kill':delta/kills if kills else None,'per_hour':delta*3600/seconds if seconds>0 else None,'start_level':a['level'],'end_level':b['level'],'note':'Manually measured net level-bar points; 100 points per level. This is not raw XP, and averages may include quests, resurrection or death losses.'}
  return out
 def snapshot(self,profile='',session='',now=None,kind='all',page=0):
  now=time.time() if now is None else now
  with self.lock:
   profiles=[dict(r) for r in self.db.execute('SELECT id,name,server,gap FROM profiles ORDER BY name,server')];selected=next((p['id'] for p in profiles if p['id']==profile),None) or self.active or (profiles[0]['id'] if profiles else '')
   page=max(0,min(100000,int(page)));rows=self.db.execute('SELECT * FROM sessions WHERE profile=?'+(" AND kind='manual'" if kind=='manual' else '')+' ORDER BY start DESC,rowid DESC LIMIT 101 OFFSET ?',(selected,page*100)).fetchall();has_more=len(rows)>100;rows=rows[:100];sessions=[self.session(r,now) for r in rows];chosen=next((r for r in sessions if r['id']==session),None) or (sessions[0] if sessions else None)
   events=[]
   if chosen:
    events=[dict(r) for r in self.db.execute("SELECT at,kind,mob,own,party,kill_id FROM events WHERE (auto=? OR manual=?) AND kind IN ('gain','death') ORDER BY id DESC LIMIT 200",(chosen['id'],chosen['id']))]
   p=self.profile();return {'page':page,'has_more':has_more,'characters':profiles,'selected':selected,'active':self.active,'sessions':sessions,'session':chosen,'events':events,'manual_active':p['manual'] if p else None,'auto_active':p['auto'] if p else None,'note':'XP amounts are not in the log. XP-linked kills are inferred by matching an XP award with a death message within 3 seconds; unmatched awards may be quests, resurrection or unobserved kills.'}
 def close(self):self.db.close()

def finish_game(path,game_id,now=None):
 if not Path(path).is_file():return
 db=connect(path);now=time.time() if now is None else now
 try:
  with db:
   db.execute("UPDATE sessions SET end=MAX(start,?),reason='EQ closed' WHERE game=? AND end IS NULL",(now,str(game_id)))
   db.execute('UPDATE profiles SET auto=NULL,manual=NULL,camp=NULL WHERE game=?',(str(game_id),))
 finally:db.close()
