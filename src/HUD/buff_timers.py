"""P1999 log-only buff tracking with cast context and explicitly labeled inference."""
import datetime as dt
import math
import re
import threading
import time
from collections import deque
from pathlib import Path

CLASSES=['warrior','cleric','paladin','ranger','shadow knight','druid','monk','bard','rogue','shaman','necromancer','wizard','magician','enchanter','beastlord','berserker']
TITLES={'high priest':'cleric','vicar':'cleric','phantasmist':'enchanter','illusionist':'enchanter','virtuoso':'bard','minstrel':'bard','hierophant':'druid','preserver':'druid','prophet':'shaman','oracle':'shaman','arch mage':'magician','conjurer':'magician','warlock':'necromancer','heretic':'necromancer','sorcerer':'wizard','channeler':'wizard','warlord':'warrior','grandmaster':'monk','assassin':'rogue','warder':'ranger','outrider':'ranger','crusader':'paladin','cavalier':'paladin','lord':'paladin','reaver':'shadow knight','dread lord':'shadow knight'}
STAMP=re.compile(r'^\[((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) [^]]+)\]\s*(.*)$')
WHO=re.compile(r'^\[(\d{1,2})\s+([^]]+)\]\s+([A-Za-z][A-Za-z`\'-]*)\b')
OTHER_CAST=re.compile(r"^([A-Za-z][A-Za-z`'-]*) begins to cast a spell\.$")

def spell_key(name):return name.replace('`',"'").replace('\u2019',"'").casefold()

def validate(config):
    c=dict(enabled=True,auto_track=True,infer_shared=True,assumed_level=60,x=1320,y=110,width=200,row_height=25,registry=[])
    c.update(config or {})
    if 'style' not in (config or {}):
        if c['row_height']==36:c['row_height']=25
        if c['width']==300:c['width']=200
    c['style']='native_slots'
    for key,low,high in [('x',0,16384),('y',0,16384),('row_height',25,100),('width',120,600),('assumed_level',1,60)]:
        c[key]=int(c[key])
        if key=='row_height' and c[key]<25:c[key]=25
        if not low<=c[key]<=high:raise ValueError('Invalid buff display position, size, or assumed caster level')
    for key in ['enabled','auto_track','infer_shared']:c[key]=bool(c[key])
    if not isinstance(c['registry'],list) or len(c['registry'])>300:raise ValueError('Buff register is limited to 300 spells')
    rows=[];names=set()
    for row in c['registry']:
        name=str(row.get('name','')).strip();duration=float(row.get('duration_seconds',0))
        if not name or len(name)>120 or spell_key(name) in names:raise ValueError('Buff names must be unique and nonempty')
        if not 1<=duration<=86400:raise ValueError('Buff duration must be 1-86400 seconds')
        names.add(spell_key(name));rows.append({'name':name,'duration_seconds':duration})
    c['registry']=rows
    return {key:c[key] for key in ['enabled','auto_track','infer_shared','assumed_level','x','y','width','row_height','registry','style']}

def spell_catalog(path):
    result={}
    try:source=Path(path).read_text(encoding='utf-8',errors='replace').splitlines()
    except OSError:return result
    for line in source:
        a=line.split('^')
        try:
            if len(a)<145 or int(a[83]) not in (1,2) or not a[1] or not a[6] or int(a[16])==0:continue
            levels={name:int(a[104+i]) for i,name in enumerate(CLASSES) if 1<=int(a[104+i])<=60}
            result.setdefault(a[1],{'name':a[1],'landing':a[6],'worn_off':a[8],'formula':int(a[16]),'ticks':int(a[17]),'icon':int(a[144]),'cast_seconds':int(a[13])/1000,'classes':levels})
        except ValueError:continue
    return result

# Explicit P1999 family candidates, not arbitrary last entries from the Titanium catalog.
FAMILIES=[
 ['Clarity','Boon of the Clear Mind'],['Clarity II'],['Breeze'],['Visions of Grandeur'],
 ['Quickness','Alacrity','Celerity','Swift like the Wind'],
 ['Symbol of Transal','Symbol of Ryltan','Symbol of Pinzarn','Symbol of Naltron','Symbol of Marzin',"Naltron's Mark","Marzin's Mark"],
 ['Regeneration','Chloroplast','Regrowth','Pack Regeneration','Pack Chloroplast','Regrowth of the Grove'],
 ['Minor Shielding','Lesser Shielding','Shielding','Major Shielding','Greater Shielding','Arch Shielding','Shield of the Magi'],
 ['Aegolism','Blessing of Aegolism'],['Heroism','Heroic Bond'],['Resolution','Resolute Gift'],
 ['Holy Armor','Guard','Armor of Faith','Shield of Words'],
 ['Talisman of Tnarg','Talisman of Altuna','Talisman of Kragg','Harnessing of Spirit'],
 ['See Invisible','Ultravision','Serpent Sight','Chill Sight','Heat Sight','Acumen','Truesight'],
 ['Invisibility','Superior Camouflage','Improved Invisibility','Improved Superior Camouflage'],
 ['Invisibility versus Undead','Invisibility to Undead','Improved Invis vs Undead'],
 ['Shield of Thistles','Shield of Barbs','Shield of Brambles','Shield of Spikes','Shield of Thorns','Legacy of Thorn'],
 ['Spirit of Wolf','Pack Spirit'],['Selo`s Accelerando'],['Dead Man Floating','Dead Men Floating'],
 ['Augmentation','Augment','Inner Fire'],['Focus of Spirit'],['Avatar','Primal Avatar'],['Levitate'],
 ['Lich','Demi Lich','Arch Lich','Call of Bones'],['Skin like Nature','Protection of Nature'],['Natureskin','Protection of the Glades'],
 ['Resist Magic','Resistance to Magic'],['Endure Magic','Group Resist Magic','Psalm of Mystic Shielding'],
 ['Call of the Predator'],['Boon of the Garou','Night`s Dark Terror']]
P99_NAMES={spell_key(name) for family in FAMILIES for name in family}
MERGE_FAMILIES=[['Clarity','Boon of the Clear Mind'],['Aegolism','Blessing of Aegolism'],['Heroism','Heroic Bond'],['Resolution','Resolute Gift'],['Spirit of Wolf','Pack Spirit'],['Dead Man Floating','Dead Men Floating']]

def duration_seconds(spell,level):
    f,cap=int(spell['formula']),int(spell['ticks']);level=max(1,min(60,int(level)))
    if f in (1,6):ticks=min(math.ceil(level/2),cap)
    elif f==2:ticks=min(math.ceil(level*3/5),cap)
    elif f==3:ticks=min(level*30,cap)
    elif f==4:ticks=cap or 50
    elif f==5:ticks=cap or 3
    elif f==7:ticks=min(level,cap)
    elif f==8:ticks=min(level+10,cap)
    elif f==9:ticks=min(level*2+10,cap)
    elif f==10:ticks=min(level*3+10,cap)
    elif f in (11,12,15):ticks=cap
    elif f==50:ticks=72000
    elif f==3600:ticks=cap or 3600
    else:return None
    return ticks*6 if ticks>0 else None

def locked(method):
    def call(self,*args,**kwargs):
        with self.lock:return method(self,*args,**kwargs)
    return call

class BuffTimers:
    def __init__(self,catalog,config=None,state_dir=None):
        self.lock=threading.RLock();self.catalog=catalog;self.by_key={spell_key(s['name']):s for s in catalog.values()};self.by_message={}
        for spell in catalog.values():self.by_message.setdefault(spell['landing'],[]).append(spell)
        self.active={};self.pending=None;self.zoning=None;self.other_casts=deque(maxlen=40);self.players={};self.character='';self.events=deque(maxlen=12)
        self.state_dir=Path(state_dir) if state_dir else None;self.store=None;self.log_path=None;self.log_offset=None;self.last_event=0;self.camp_deadline=None;self.offline_at=None
        self.note='Waiting for observed buff landings. Existing buffs have unknown remaining time.';self.configure(config or {})
    @locked
    def configure(self,config):self.config=validate(config)
    def learn_player(self,text):
        match=WHO.match(text)
        if not match:return False
        level=int(match[1]);kind=match[2].casefold();kind=TITLES.get(kind,kind)
        if not 1<=level<=60 or kind not in CLASSES:return False
        self.players[match[3].casefold()]={'name':match[3],'level':level,'class':kind};return True
    def _freeze_camp(self,now):
        if self.camp_deadline is not None and now>=self.camp_deadline and self.last_event<=self.camp_deadline+2:
            self.offline_at=max(self.camp_deadline,self.last_event)
    def _mark_uncertain(self):
        for row in self.active.values():
            row['expires']=None;row['uncertain']=True;row['restored']=True
            row['reason']='Saved effect; offline duration or presence is unverified. Recast or dismiss to reconcile.'
    @locked
    def save_state(self,now=None,log_offset=None):
        if self.store is None:return
        now=time.time() if now is None else now
        if log_offset is not None:self.log_offset=int(log_offset)
        self.snapshot(now)
        try:
            stat=self.log_path.stat() if self.log_path else None
            self.store.save({'character':self.character,'saved_at':now,'last_event':self.last_event,'camp_deadline':self.camp_deadline,
                'offline_at':self.offline_at,'log_offset':self.log_offset,'file_id':[stat.st_dev,stat.st_ino] if stat else None,
                'active':list(self.active.values()),'players':self.players})
        except (OSError,ValueError,TypeError):self.note='Buff checkpoint could not be saved; current timers still run.'
    def _load_state(self,data,current):
        if not isinstance(data,dict):return False
        rows=data.get('active',[])
        if not isinstance(rows,list) or len(rows)>300:return False
        try:
            saved=float(data['saved_at']);last=float(data.get('last_event',saved))
            if not math.isfinite(saved) or not math.isfinite(last) or saved>current+5:return False
            self.last_event=last
            for key in ['camp_deadline','offline_at']:
                value=data.get(key)
                setattr(self,key,float(value) if value is not None and math.isfinite(float(value)) else None)
            occupied=set()
            for source in rows:
                spell=self.by_key.get(spell_key(str(source.get('name',''))))
                if not spell:continue
                row=dict(source)
                for key in ['expires','duration','started']:
                    value=row.get(key)
                    if value is not None and (not isinstance(value,(int,float)) or not math.isfinite(value)):raise ValueError('Invalid saved timer')
                if not row.get('duration') and row.get('expires') is not None:raise ValueError('Invalid saved duration')
                slot=row.get('display_slot')
                if not isinstance(slot,int) or not 1<=slot<=15 or slot in occupied:slot=next((n for n in range(1,16) if n not in occupied),None)
                if slot:occupied.add(slot)
                row.update(name=spell['name'],icon=spell.get('icon',0),worn_off=spell['worn_off'],display_slot=slot,restored=True)
                row.setdefault('identity','matched');row.setdefault('reason','Restored from a saved observation');row.setdefault('caster',None)
                self.active[spell_key(spell['name'])]=row
            self.players={name:profile for name,profile in data.get('players',{}).items() if isinstance(profile,dict) and profile.get('class') in CLASSES and isinstance(profile.get('level'),int) and 1<=profile['level']<=60}
            self._freeze_camp(current)
            if self.offline_at is None and current-saved>10:self._mark_uncertain()
            return True
        except (ValueError,TypeError,KeyError,AttributeError):
            self.active.clear();self.players.clear();self.camp_deadline=None;self.offline_at=None;return False
    @locked
    def set_character(self,name,log_path=None,now=None):
        current=time.time() if now is None else now
        if self.store is not None:self.save_state(current)
        self.character=name;self.active.clear();self.pending=None;self.zoning=None;self.other_casts.clear();self.players.clear();self.events.clear()
        self.camp_deadline=None;self.offline_at=None;self.last_event=0;self.log_offset=None;self.log_path=Path(log_path) if log_path else None;self.store=None
        saved=None;loaded=False
        if self.state_dir and self.log_path:
            from buff_state import BuffStateStore
            self.store=BuffStateStore(self.state_dir,self.log_path);saved=self.store.load();loaded=self._load_state(saved,current)
        if self.log_path:
            try:
                stat=self.log_path.stat()
                with self.log_path.open('rb') as source:
                    source.seek(max(0,stat.st_size-1048576));raw=source.read();partial=raw.rsplit(b'\n',1)[-1] if raw else b'';complete=raw[:-len(partial)] if partial else raw;tail=complete.decode('utf-8',errors='replace').splitlines()
                for line in tail:
                    match=STAMP.match(line)
                    if match:self.learn_player(match[2])
                offset=saved.get('log_offset') if loaded else None
                if isinstance(offset,int) and 0<=offset<=stat.st_size and saved.get('file_id')==[stat.st_dev,stat.st_ino] and stat.st_size-offset<=1048576:
                    with self.log_path.open('rb') as source:
                        source.seek(offset);raw=source.read();partial=raw.rsplit(b'\n',1)[-1] if raw else b'';complete=raw[:-len(partial)] if partial else raw;replay=complete.decode('utf-8',errors='replace').splitlines()
                else:
                    replay=tail
                    if loaded:self._mark_uncertain()
                for line in replay:
                    match=STAMP.match(line)
                    if not match:continue
                    try:event_time=dt.datetime.strptime(match[1],'%a %b %d %H:%M:%S %Y').timestamp()
                    except ValueError:continue
                    if 0<=current-event_time<=86400 or loaded:self.consume(line,event_time)
                self.log_offset=stat.st_size-len(partial)
                self.snapshot(current)
                if loaded:self.note='Saved effects restored for '+name+'. Unknown entries need confirmation; display slots are our own order.'
            except OSError:
                if loaded:self._mark_uncertain()
    @locked
    def dismiss(self,name):
        self.active.pop(spell_key(name),None);self.save_state()
    def cast_matches(self,spell,start,land):
        elapsed=land-start;cast=float(spell.get('cast_seconds',0))
        return max(0,cast-1.5)<=elapsed<=cast+3
    def curated(self,candidates):
        curated=[s for s in candidates if spell_key(s['name']) in P99_NAMES]
        if curated:return curated
        return [s for s in candidates if s.get('classes') and not s['name'].startswith(('GM ','NPC'))]
    @locked
    def consume(self,line,now):
        match=STAMP.match(line.rstrip('\r\n'));text=line.rstrip('\r\n');when=now
        if match:
            try:when=dt.datetime.strptime(match[1],'%a %b %d %H:%M:%S %Y').timestamp()
            except ValueError:return False
            text=match[2]
        if when>now+2 or now-when>15:return False
        if text.startswith('Welcome to EverQuest!'):
            self._freeze_camp(when)
            if self.offline_at is not None:
                delay=max(0,when-self.offline_at)
                for row in self.active.values():
                    if row['expires'] is not None:row['expires']+=delay
                    row['restored']=True
                    row['reason']=row.get('reason','')+'; resumed after observed camp countdown'
                self.note='Restored saved buff estimates after camping.'
            elif self.active:
                self._mark_uncertain();self.note='Saved effects restored with unknown remaining time: no reliable camp completion was observed.'
            self.offline_at=None;self.camp_deadline=None;self.pending=None;self.zoning=None;self.other_casts.clear();self.last_event=when;return True
        # New activity past the expected camp finish invalidates a presumed camp.
        if self.camp_deadline is not None and when>self.camp_deadline+2:
            self.camp_deadline=None;self.offline_at=None
        self.last_event=max(self.last_event,when)
        if self.learn_player(text):return False
        camp=re.fullmatch(r'It will take (?:you )?about (\d+) (?:more )?seconds to prepare your camp\.',text)
        if camp:
            self.camp_deadline=when+int(camp[1]);self.offline_at=None;self.note='Camp countdown observed; buffs continue counting down until camp completes.';return True
        if text=='You abandon your preparations to camp.':
            self.camp_deadline=None;self.offline_at=None;self.note='Camp canceled; buff timers continue.';return True
        if text.startswith(('You have been slain by ','You died.')):
            self.active.clear();self.pending=None;self.zoning=None;self.camp_deadline=None;self.offline_at=None;self.other_casts.clear();self.note='Observed timers cleared after death.';return True
        if text.startswith('LOADING, PLEASE WAIT'):
            if self.zoning is None:
                self.snapshot(when)  # Do not revive an already expired effect.
                self.zoning=when
            self.pending=None;self.other_casts.clear();self.note='Zoning: observed buff countdowns are paused.';return True
        if text.startswith('You have entered '):
            if self.zoning is not None:
                delay=when-self.zoning
                if 0<=delay<=120:
                    for row in self.active.values():
                        if row['expires'] is not None:row['expires']+=delay
                        row['zone_pause_seconds']=row.get('zone_pause_seconds',0)+delay
                    self.note='Buff timers resumed after zoning.'
                else:self.note='Long or incomplete zone transition: timers kept on elapsed time; duration may be uncertain.'
                self.zoning=None
            self.pending=None;self.other_casts.clear();return True
        if text.startswith('You begin casting ') and text.endswith('.'):
            self.pending=(spell_key(text[len('You begin casting '):-1]),when);return False
        if text.startswith(('Your spell is interrupted','Your spell fizzles','Your target resisted','Your spell did not take hold','You try to cast a spell on')):
            self.pending=None;return False
        other=OTHER_CAST.match(text)
        if other:self.other_casts.append((other[1].casefold(),when));return False
        removed=False
        for key,timer in list(self.active.items()):
            if (timer['worn_off'] and text==timer['worn_off']) or text.casefold()==('Your '+timer['name']+' spell has worn off.').casefold():
                del self.active[key];removed=True
        if removed:return True
        registered={spell_key(r['name']):r for r in self.config['registry']}
        all_candidates=self.by_message.get(text,[])
        candidates=[s for s in all_candidates if self.config['auto_track'] or spell_key(s['name']) in registered]
        if not candidates:return False
        chosen=None;player=None;identity='matched';reason='Unique landing message';fixed=None
        # Explicit named self casts outrank all inference and item defaults.
        if self.pending:
            own=[s for s in candidates if spell_key(s['name'])==self.pending[0] and self.cast_matches(s,self.pending[1],when)]
            if len(own)==1:chosen=own[0];player=self.players.get(self.character.casefold());reason='Named self cast and timed landing'
        if chosen is None:
            configured=[s for s in candidates if spell_key(s['name']) in registered]
            if len(configured)==1:chosen=configured[0];reason='Register selection'
        if chosen is None and text=='Your feet feel quick.':
            chosen=next((s for s in candidates if s['name']=='JourneymanBoots'),None)
            if chosen:fixed=1080;identity='default';reason='User-approved JBoots default: 18 minutes'
        eligible=self.curated(candidates)
        # Associate nearby cast timing with a known /who class/level profile.
        if chosen is None:
            evidence=[]
            for caster,start in self.other_casts:
                known=self.players.get(caster)
                if not known:continue
                for spell in eligible:
                    minimum=spell.get('classes',{}).get(known['class'])
                    if minimum and known['level']>=minimum and self.cast_matches(spell,start,when):
                        error=abs((when-start)-spell.get('cast_seconds',0));evidence.append((error,-minimum,spell,known))
            if evidence:
                evidence.sort(key=lambda row:(row[0],row[1],row[2]['name']))
                _,_,chosen,player=evidence[0];identity='inferred';reason='Nearby cast timing and logged caster class/level'
        if chosen is None:
            if len(eligible)==1:chosen=eligible[0];reason='Unique P1999/player spell candidate'
            elif len(candidates)==1:chosen=candidates[0]
            elif eligible and self.config['infer_shared']:
                # Favor equivalent effects, otherwise a useful top-rank P1999 default.
                signatures={(s.get('icon'),duration_seconds(s,self.config['assumed_level'])) for s in eligible}
                if len(signatures)==1:
                    chosen=eligible[0];reason='Equivalent effect family';identity='family'
                elif all(spell_key(s['name']) in P99_NAMES for s in eligible):
                    rank=lambda s:max(s.get('classes',{}).values(),default=0)
                    chosen=max(eligible,key=lambda s:(rank(s),s['name']));identity='inferred';reason='Typical P1999 family rank; spell identity is assumed'
        if chosen is None:
            self.note='Unresolved buff message: '+text;self.events.append({'message':text,'candidates':[s['name'] for s in eligible or candidates]});return False
        spell=chosen;override=registered.get(spell_key(spell['name']))
        if fixed is None and spell['name']=='JourneymanBoots':fixed=1080
        level=player['level'] if player else self.config['assumed_level'];level_source='logged caster level' if player else 'assumed caster level'
        if override:seconds=override['duration_seconds'];reason+='; duration override'
        elif fixed is not None:seconds=fixed
        else:seconds=duration_seconds(spell,level)
        if not override and fixed is None:reason+=f'; {level_source} {level}'
        self.snapshot(when)
        # Mutually exclusive members of a curated family share one displayed effect.
        family=next((group for group in MERGE_FAMILIES if spell_key(spell['name']) in {spell_key(n) for n in group}),None)
        old=self.active.get(spell_key(spell['name']))
        if family:
            keys={spell_key(n) for n in family}
            for key,row in list(self.active.items()):
                if key in keys:
                    if old is None:old=row
                    del self.active[key]
        occupied={r['display_slot'] for r in self.active.values()}
        slot=old['display_slot'] if old else next((n for n in range(1,16) if n not in occupied),None)
        self.active[spell_key(spell['name'])]={'display_slot':slot,'name':spell['name'],'icon':spell.get('icon',0),'worn_off':spell['worn_off'],
            'display_name':('Illusion' if identity=='family' and text=='You feel different.' else spell['name']),
            'expires':when+seconds if seconds else None,'duration':seconds,'started':when,'identity':identity,'reason':reason,'caster':player['name'] if player else None}
        if reason.startswith('Named self cast'):self.pending=None
        self.note=reason;return True
    @locked
    def snapshot(self,now):
        # Pause at the loading event, bounded so a missing arrival cannot freeze forever.
        if self.camp_deadline is not None and now>=self.camp_deadline+3:self._freeze_camp(now)
        clock=self.offline_at if self.offline_at is not None else (self.zoning if self.zoning is not None and 0<=now-self.zoning<=120 else now)
        for key,row in list(self.active.items()):
            if row['expires'] is not None and row['expires']<=clock:del self.active[key]
        timers=[]
        for row in self.active.values():
            remaining=max(0,math.ceil(row['expires']-clock)) if row['expires'] is not None else None
            timers.append({'name':row.get('display_name',row['name']),'spell':row['name'],'icon':row['icon'],'display_slot':row['display_slot'],'remaining':remaining,'minimum_remaining':remaining,
                'fraction':max(0,min(1,(row['expires']-clock)/row['duration'])) if row['duration'] and row['expires'] is not None else None,'estimated':True,
                'identity':row['identity'],'reason':row['reason'],'caster':row['caster'],'zone_pause_seconds':row.get('zone_pause_seconds',0),'restored':row.get('restored',False),'uncertain':row.get('uncertain',False)})
        timers.sort(key=lambda row:(row['display_slot'] or 99,row['name']))
        return {'note':self.note,'character':self.character,'profile':self.players.get(self.character.casefold()),'timers':timers,'unresolved':list(self.events),'zoning':self.zoning is not None,'camped':self.offline_at is not None}
