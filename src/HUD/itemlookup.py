"""Automatic public item-ID lookup. No preset weapon catalog.

Lucy is a live-EQ source: its displayed damage bonus is deliberately NOT used.
Retrieved base stats are marked unverified for the P99 era.
"""
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
import html
import json
import re
import time
import urllib.request

KINDS = {'1H Slashing':'1hs','1H Piercing':'1hp','Piercing':'1hp',
         '1H Blunt':'1hb','2H Slashing':'2hs','2H Piercing':'2hp',
         '2H Blunt':'2hb','Hand to Hand':'h2h','Hand To Hand':'h2h'}

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=0; self.text=[]; self.links=[]; self.current_link=None
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.skip+=1
        if tag=='a': self.current_link=dict(attrs).get('href')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag=='a': self.current_link=None
    def handle_data(self,data):
        if self.skip or not data.strip(): return
        data=data.strip(); self.text.append(data)
        if self.current_link: self.links.append((data,self.current_link))

def normalized(name):
    return ' '.join(html.unescape(name).replace('`',"'").casefold().split())

def parse_item(document,item_id,expected_name):
    p=VisibleText();p.feed(document)
    titles=[s for s in p.text if s.startswith('Item Details for ') and s.endswith(' :: Lucy')]
    if len(titles)!=1: raise ValueError('Item page format not recognized')
    name=titles[0][len('Item Details for '):-len(' :: Lucy')]
    if normalized(name)!=normalized(expected_name): raise ValueError('Item ID/name mismatch')
    # Scope to the actual item card, excluding navigation and raw/live bonus fields.
    starts=[i for i,s in enumerate(p.text) if s==name]
    if not starts: raise ValueError('Missing item card')
    body='\n'.join(p.text[starts[-1]:starts[-1]+35])
    skill=re.search(r'Skill:\s*([^\n]+?)\s+Atk Delay:\s*(\d+)',body)
    damage=re.search(r'\bDMG:\s*(\d+)',body)
    result={'id':int(item_id),'name':name,'source':f'https://lucy.allakhazam.com/item.html?id={int(item_id)}',
            'retrieved':time.time(),'era_verified':False,'type':'unknown','effects':[]}
    if skill:
        kind=KINDS.get(skill[1].strip())
        if not kind or not damage: raise ValueError('Unsupported weapon skill or missing damage')
        result.update(type=kind,damage=int(damage[1]),delay=int(skill[2]))
        if not 0<result['damage']<10000 or not 0<result['delay']<1000: raise ValueError('Invalid weapon stats')
    elif re.search(r'(?:Percussion|Wind|Stringed|Brass|Singing).*Instrument|Instrument.*(?:Percussion|Wind|Stringed|Brass)',body,re.I):
        result['type']='instrument'
    elif 'Slot:' in body:
        result['type']='nonweapon'
    else: raise ValueError('Missing item slot information')
    effect_names=[]
    for i,s in enumerate(p.text):
        if s=='Effect:' and i+1<len(p.text): effect_names.append(p.text[i+1])
    for name in dict.fromkeys(effect_names):
        links=[url for text,url in p.links if text==name and 'spell' in url]
        result['effects'].append({'name':name,'url':links[0] if links else None})
    return result

def fetch_item(item_id,expected_name):
    item_id=int(item_id)
    if not 0<item_id<10000000: raise ValueError('Invalid item ID')
    url=f'https://lucy.allakhazam.com/item.html?id={item_id}'
    req=urllib.request.Request(url,headers={'User-Agent':'BaitAndTackle/0.4 (user-requested inventory item lookup)'})
    with urllib.request.urlopen(req,timeout=10) as response:
        if response.geturl().split('/')[2] != 'lucy.allakhazam.com': raise ValueError('Unexpected redirect')
        body=response.read(2_000_001)
    if len(body)>2_000_000: raise ValueError('Item response too large')
    return parse_item(body.decode('utf-8',errors='replace'),item_id,expected_name)

class ItemResolver:
    def __init__(self,cache_file,fetcher=fetch_item):
        self.path=Path(cache_file);self.fetcher=fetcher
        try:self.cache=json.loads(self.path.read_text())
        except (OSError,ValueError):self.cache={}
        if not isinstance(self.cache,dict):self.cache={}
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='BFT-item-lookup')
        self.pending={};self.retry_after={};self.errors={}
    def resolve(self,item,now=None):
        now=time.time() if now is None else now
        key=str(int(item['id']))
        if key=='0':return {'id':0,'name':'Empty','type':'none','era_verified':True}
        if key in self.pending and self.pending[key].done():
            future=self.pending.pop(key)
            try:
                value=future.result()
                if normalized(value['name'])!=normalized(item['name']):raise ValueError('Lookup name changed')
                self.cache[key]=value;self.errors.pop(key,None)
                self.path.parent.mkdir(parents=True,exist_ok=True)
                temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(self.cache,indent=2));temp.replace(self.path)
            except Exception as error:
                self.errors[key]=str(error);self.retry_after[key]=now+60
        value=self.cache.get(key)
        valid=isinstance(value,dict) and value.get('id')==int(key) and normalized(value.get('name',''))==normalized(item['name'])
        if valid and now-value.get('retrieved',0)<7*86400:return value
        if key not in self.pending and now>=self.retry_after.get(key,0):
            self.pending[key]=self.pool.submit(self.fetcher,int(key),item['name'])
        # A stale cache is not silently reused as current data.
        return None
    def close(self):
        self.pool.shutdown(wait=False,cancel_futures=True)
