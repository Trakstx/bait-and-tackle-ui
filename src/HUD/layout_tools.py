"""Copy only saved EQ window geometry, preserving character-specific settings."""
from pathlib import Path
import hashlib,json,re,threading,time,uuid

GEOMETRY=re.compile(r'^(?:XPos|YPos|Width|Height)(?:\d{3,5}x\d{3,5})?$',re.I)
SECTION=re.compile(r'^\s*\[([^\]\r\n]+)\]\s*$')
CHARFILE=re.compile(r'^UI_([^_]+)_(.+)\.ini$',re.I)
BFT={'bait_and_fucking_tacle','bait_and_fucking_tackle','bait_and_tackle'}

def read_text(path):
 raw=Path(path).read_bytes()
 try:return raw.decode('utf-8-sig'),'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'utf-8'
 except UnicodeDecodeError:return raw.decode('cp1252'),'cp1252'

def geometry(text):
 result={};section=None
 for line in text.splitlines():
  match=SECTION.fullmatch(line)
  if match:section=match[1];continue
  if section and '=' in line:
   key,value=line.split('=',1);key=key.strip();value=value.strip()
   if GEOMETRY.fullmatch(key) and re.fullmatch(r'-?\d{1,7}',value):result.setdefault(section,{})[key]=value
 return result

def skin(text):
 section=''
 for line in text.splitlines():
  m=SECTION.fullmatch(line)
  if m:section=m[1].casefold()
  elif section=='main' and '=' in line:
   k,v=line.split('=',1)
   if k.strip().casefold()=='uiskin':return v.strip()
 return ''

def merge_geometry(text,layout):
 """Preserve every non-geometry line, including hotkeys and chat configuration."""
 newline='\r\n' if '\r\n' in text else '\n';lines=text.splitlines(keepends=True);out=[];seen_sections=set();seen_keys=set();section=None
 section_lookup={s.casefold():(s,{k.casefold():(k,v) for k,v in keys.items()}) for s,keys in layout.items()}
 def flush():
  if section in section_lookup:
   for key,value in section_lookup[section][1].values():
    if key.casefold() not in seen_keys:
     if out and not out[-1].endswith(('\n','\r')):out[-1]+=newline
     out.append(key+'='+str(value)+newline)
 for line in lines:
  m=SECTION.fullmatch(line.strip())
  if m:
   flush();section=m[1].casefold();seen_sections.add(section);seen_keys=set();out.append(line);continue
  if section in section_lookup and '=' in line:
   key=line.split('=',1)[0].strip();entry=section_lookup[section][1].get(key.casefold())
   if entry:
    seen_keys.add(key.casefold());out.append(line.split('=',1)[0]+'='+str(entry[1])+newline);continue
  out.append(line)
 flush()
 for name,keys in layout.items():
  if name.casefold() not in seen_sections:
   if out and not out[-1].endswith(('\n','\r')):out[-1]+=newline
   out.append(newline+'['+name+']'+newline)
   out.extend(k+'='+str(v)+newline for k,v in keys.items())
 return ''.join(out)

HOTKEY_SECTION=re.compile(r'^(?:HotButtons\d*|Socials|Abilities|CombatSkills|CombatAbilities)$',re.I)
def hotkey_sections(text):
 result={};section=None
 for line in text.splitlines(keepends=True):
  m=SECTION.fullmatch(line.strip())
  if m:section=m[1] if HOTKEY_SECTION.fullmatch(m[1]) else None
  if section:result[section]=result.get(section,'')+line
 return result

def merge_hotkeys(text,sections):
 newline='\r\n' if '\r\n' in text else '\n';out=[];skipping=False
 for line in text.splitlines(keepends=True):
  m=SECTION.fullmatch(line.strip())
  if m:skipping=bool(HOTKEY_SECTION.fullmatch(m[1]))
  if not skipping:out.append(line)
 if out and not out[-1].endswith(('\n','\r')):out[-1]+=newline
 for name,block in sections.items():
  if not HOTKEY_SECTION.fullmatch(name):raise ValueError('Invalid saved hotkey section.')
  out.append(newline+block.rstrip('\r\n')+newline)
 return ''.join(out)

def tick_snapshot(config,now):
 anchor=config.get('tick_anchor',0);phase=(now-anchor)%6 if anchor else None
 return {'remaining':6-phase if phase is not None else None,'fraction':phase/6 if phase is not None else 0,'estimated':True,'synced':bool(anchor)}

class LayoutService:
 def __init__(self,game,directory):
  self.game=Path(game) if game else None
  identity=str(self.game.resolve()).casefold() if self.game else 'unconfigured'
  self.directory=Path(directory)/hashlib.sha256(identity.encode()).hexdigest()[:20];self.lock=threading.RLock()
 def read(self,name,default):
  try:return json.loads((self.directory/name).read_text(encoding='utf-8'))
  except (OSError,ValueError):return default
 def write(self,name,value):
  self.directory.mkdir(parents=True,exist_ok=True);path=self.directory/name;temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2),encoding='utf-8');temp.replace(path)
 def characters(self):
  rows=[]
  if self.game:
   for path in sorted(self.game.glob('UI_*.ini')):
    match=CHARFILE.fullmatch(path.name)
    if not match or path.is_symlink():continue
    try:
     text,_=read_text(path);layout=geometry(text);s=skin(text)
     rows.append({'id':path.name,'character':match[1],'server':match[2],'skin':s,'bft':s.casefold() in BFT,'has_hotkeys':path.with_name(path.name[3:]).is_file(),'windows':len(layout),'updated':path.stat().st_mtime})
    except (OSError,ValueError,UnicodeError):continue
  return rows
 def character_path(self,key):
  row=next((r for r in self.characters() if r['id']==key),None)
  if not row:raise ValueError('Choose a character from this installation.')
  path=self.game/row['id']
  if path.resolve().parent!=self.game.resolve():raise ValueError('Invalid character file.')
  return path,row
 def source(self,kind,key):
  if kind=='character':
   path,row=self.character_path(key)
   if not row['bft']:raise ValueError('Choose a source character using Bait & Tackle.')
   text,_=read_text(path);value=geometry(text)
  elif kind=='template':
   row=next((r for r in self.read('templates.json',[]) if r['id']==key),None)
   if not row:raise ValueError('Template not found.')
   value=row['layout']
  else:raise ValueError('Invalid source type.')
  if not value:raise ValueError('The source has no saved window positions.')
  return value
 def hotkeys(self,kind,key):
  if kind=='character':
   ui,_=self.character_path(key);path=ui.with_name(ui.name[3:])
   if path.is_symlink() or not path.is_file() or path.resolve().parent!=self.game.resolve():raise ValueError('Source has no saved character hotkeys. Turn off Include hotkeys or choose another character.')
   text,_=read_text(path);sections=hotkey_sections(text)
  else:
   template=next((r for r in self.read('templates.json',[]) if r['id']==key),None)
   sections=template.get('hotkeys') if template else None
  if not sections:raise ValueError('Source has no saved hotkeys. Choose a template with hotkeys or turn off Include hotkeys.')
  return sections
 def snapshot(self):
  with self.lock:
   return {'characters':self.characters(),'templates':[dict({k:v for k,v in t.items() if k not in ['layout','hotkeys']},has_hotkeys=bool(t.get('hotkeys'))) for t in self.read('templates.json',[])], 'pending':self.read('pending.json',[]),'results':self.read('results.json',[])[-20:]}
 def validate_request(self,data):
  kind=str(data.get('source_kind','character'));key=str(data.get('source',''));layout=self.source(kind,key)
  targets=data.get('targets',[])
  if not isinstance(targets,list) or len(targets)>200:raise ValueError('Choose up to 200 target characters.')
  targets=list(dict.fromkeys(targets))
  for target in targets:
   self.character_path(target)
   if kind=='character' and target==key:raise ValueError('Source and target must be different characters.')
  name=str(data.get('template_name','')).strip()
  if name and (len(name)>40 or not re.fullmatch(r'[\w \-]+',name)):raise ValueError('Template name: use up to 40 letters, numbers, spaces or hyphens.')
  if not targets and not name:raise ValueError('Choose target characters or enter a template name.')
  if data.get('include_hotkeys',False):self.hotkeys(kind,key)
  return kind,key,layout,targets,name
 def preview(self,data):
  with self.lock:
   kind,key,layout,targets,name=self.validate_request(data);items=[]
   for target in targets:
    path,row=self.character_path(target);text,_=read_text(path);old=geometry(text);changed=0
    for section,keys in layout.items():
     existing=next((v for k,v in old.items() if k.casefold()==section.casefold()),{})
     indexed={k.casefold():v for k,v in existing.items()}
     changed+=sum(indexed.get(k.casefold())!=v for k,v in keys.items())
    items.append({'target':target,'changed_values':changed,'bft':row['bft']})
   resolutions=sorted({m[0] for keys in layout.values() for k in keys for m in [re.findall(r'\d+x\d+',k)] if m})
   return {'windows':len(layout),'values':sum(map(len,layout.values())),'resolutions':resolutions,'targets':items,'template_name':name,'include_hotkeys':bool(data.get('include_hotkeys',False)),'note':'Copies X/Y positions and window sizes, plus hotbars/socials/ability slots only when Include hotkeys is selected. Source is read again after EQ closes to include its final saved layout.'}
 def queue(self,data):
  with self.lock:
   preview=self.preview(data);kind,key,_,targets,name=self.validate_request(data);pending=self.read('pending.json',[])
   if len(pending)>=30:raise ValueError('Too many pending copies. Finish or cancel pending operations first.')
   if name and any(t.get('name',t.get('template_name','')).casefold()==name.casefold() for t in self.read('templates.json',[])+pending):raise ValueError('That template name already exists. Use another name.')
   item={'id':uuid.uuid4().hex,'source_kind':kind,'source':key,'targets':targets,'template_name':name,'include_hotkeys':bool(data.get('include_hotkeys',False)),'queued_at':time.time()}
   pending.append(item);self.write('pending.json',pending);return dict(preview,queued=item)
 def cancel(self,key):
  with self.lock:
   pending=self.read('pending.json',[]);self.write('pending.json',[r for r in pending if r['id']!=key]);return {'cancelled':True}
 def apply_pending(self):
  """Called only by session owner before game starts or after exact EQ PID exits."""
  with self.lock:
   pending=self.read('pending.json',[])
   if not pending:return []
   results=self.read('results.json',[]);remaining=[];completed=[]
   for item in pending:
    try:
     if not re.fullmatch(r'[a-f0-9]{32}',str(item.get('id',''))):raise ValueError('Invalid queued operation ID.')
     layout=self.source(item['source_kind'],item['source']);targets=item['targets'];hotkeys=self.hotkeys(item['source_kind'],item['source']) if item.get('include_hotkeys') else None
     if item['template_name'] and any(t['name'].casefold()==item['template_name'].casefold() and t['id']!=item['id'] for t in self.read('templates.json',[])):raise ValueError('Template name already exists.')
     # Validate every target before beginning this operation.
     paths=[self.character_path(target)[0] for target in targets]
     if hotkeys:
      for path in paths:
       charpath=path.with_name(path.name[3:])
       if charpath.is_symlink() or charpath.resolve().parent!=self.game.resolve():raise ValueError('Invalid target hotkey file.')
     from file_transaction import FileTransaction
     recovery=self.directory/'recovery';FileTransaction.recover_pending(recovery,[self.game,self.directory])
     transaction=FileTransaction(recovery,[self.game,self.directory])
     backup=transaction.directory
     for path in paths:
      text,encoding=read_text(path);new=merge_geometry(text,layout)
      if new!=text:
       transaction.add(path,new.encode(encoding))
      if hotkeys:
       charpath=path.with_name(path.name[3:]);old,codec=read_text(charpath) if charpath.exists() else ('','utf-8');updated=merge_hotkeys(old,hotkeys)
       if updated!=old:transaction.add(charpath,updated.encode(codec))
     if item['template_name']:
      templates=self.read('templates.json',[])
      if not any(t['id']==item['id'] for t in templates):
       if any(t['name'].casefold()==item['template_name'].casefold() for t in templates):raise ValueError('Template name already exists.')
       templates.append({'id':item['id'],'name':item['template_name'],'created_at':time.time(),'source':item['source'],'layout':layout,'hotkeys':hotkeys});transaction.add(self.directory/'templates.json',json.dumps(templates,indent=2).encode('utf8'))
     transaction.commit()
     result={'id':item['id'],'ok':True,'targets':targets,'template_name':item['template_name'],'at':time.time(),'backup':str(backup)};completed.append(result)
    except (OSError,ValueError,KeyError,TypeError,UnicodeError) as exc:
     result={'id':item.get('id',''),'ok':False,'error':str(exc),'at':time.time()};remaining.append(item)
    results.append(result)
   self.write('results.json',results[-100:]);self.write('pending.json',remaining);return completed
