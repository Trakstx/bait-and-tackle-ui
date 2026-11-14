"""Read-only bank snapshots from EQ's user-requested inventory exports."""
import csv
import datetime as dt
import html
import re
from pathlib import Path

LOCATION = re.compile(r'^Bank(\d+)(?:-Slot(\d+))?$', re.I)

def read_export(path, include_empty=False):
    path = Path(path)
    with path.open(encoding='utf-8-sig', errors='replace', newline='') as source:
        reader = csv.DictReader(source, delimiter='\t')
        if not {'Location','Name','ID','Count'}.issubset(reader.fieldnames or []):
            raise ValueError('Not an EverQuest inventory export')
        items = []
        for row in reader:
            location = row.get('Location') or ''
            match = LOCATION.fullmatch(location)
            if not match: continue
            try:
                item_id, count = int(row['ID']), int(row['Count'])
            except (TypeError, ValueError): raise ValueError('Incomplete bank row')
            if (item_id <= 0 or count <= 0) and not include_empty: continue
            try: capacity = max(0,int(row.get('Slots') or 0))
            except (TypeError,ValueError): capacity = 0
            items.append({'location':location, 'name':row.get('Name') or 'Unknown item',
                'id':item_id, 'count':count, 'capacity':capacity, 'bank':int(match[1]),
                'slot':int(match[2]) if match[2] else 0})
    return sorted(items, key=lambda x:(x['bank'], x['slot']))

NAV = '<nav aria-label="Reports"><a href="latest.html">Combat history</a><a href="bank.html">Bank</a></nav>'

def render(snapshots):
    esc = lambda x: html.escape(str(x), quote=True)
    sections = []
    for entry in sorted(snapshots, key=lambda x:x['character'].casefold()):
        name=entry['character']; items=entry['items']
        when=dt.datetime.fromtimestamp(entry['mtime']).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
        age=max(0, (dt.datetime.now().timestamp()-entry['mtime'])/86400)
        age_label='today' if age<1 else f'{int(age)} days ago'
        rows=''
        for item in items:
            group=next((x['name'] for x in items if x['bank']==item['bank'] and not x['slot']), '')
            where=f"Bank {item['bank']}"+(f" / {group} / slot {item['slot']}" if item['slot'] else '')
            rows+=f'<tr><td>{esc(item["name"])}</td><td>{item["count"]}</td><td>{esc(where)}</td></tr>'
        if not rows: rows='<tr><td colspan="3">No bank items in this export.</td></tr>'
        sections.append(f'<section data-character="{esc(name)}"><h2>{esc(name)}</h2><p>Exported {esc(when)} ({esc(age_label)}). Server is not identified by this export.</p><table><thead><tr><th>Item</th><th>Quantity</th><th>Location</th></tr></thead><tbody>{rows}</tbody></table></section>')
    body=''.join(sections) or '<p>No inventory exports found. In EverQuest, run <code>/outputfile inventory</code>.</p>'
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="15"><title>Bait &amp; Tackle — Bank</title>
<style>body{background:#08191d;color:#e3e9e4;font:15px system-ui;margin:32px}h1,h2,th,a{color:#d3b362}nav{display:flex;gap:24px;margin-bottom:24px}p,small{color:#a6bdbc}input,select{padding:10px;background:#10262a;color:#e3e9e4;border:1px solid #497076;border-radius:5px;margin:8px}input{min-width:260px}table{border-collapse:collapse;width:100%;background:#10262a;margin-bottom:28px}th,td{text-align:left;padding:10px;border-bottom:1px solid #294347}section[hidden],tr[hidden]{display:none}code{color:#e3c67e}</style>'''+NAV+'''<h1>BAIT &amp; TACKLE · BANK</h1><p>Read-only saved inventory exports. This is not a live bank connection. Run <code>/outputfile inventory</code> after bank changes to update your snapshot. Exports can be created away from a banker.</p><p>The helper checks for changed exports while the updated launcher is running. This page refreshes every 15 seconds. No item movement or game commands are available here.</p><label>Character <select id="character"><option value="">All characters</option>'''+''.join(f'<option>{esc(x["character"])}</option>' for x in sorted(snapshots,key=lambda x:x['character'].casefold()))+'''</select></label><label>Find an item <input id="search" type="search" placeholder="Search item or bag name"></label>'''+body+'''
<script>const q=document.getElementById('search'),c=document.getElementById('character');function filter(){const text=q.value.toLowerCase();for(const section of document.querySelectorAll('section')){section.hidden=Boolean(c.value&&section.dataset.character!==c.value);for(const row of section.querySelectorAll('tbody tr'))row.hidden=!row.textContent.toLowerCase().includes(text);}try{sessionStorage.setItem('bank-search',q.value);sessionStorage.setItem('bank-character',c.value);}catch(e){}}try{q.value=sessionStorage.getItem('bank-search')||'';c.value=sessionStorage.getItem('bank-character')||'';}catch(e){}q.oninput=filter;c.onchange=filter;filter();</script></html>'''

class BankIndex:
    def __init__(self, game, destination):
        self.game=Path(game); self.destination=Path(destination); self.fingerprint=None
    def refresh(self):
        exports=sorted(self.game.glob('*-Inventory.txt'))
        files=[]
        for path in exports:
            try:
                stat=path.stat();files.append((path,stat.st_mtime_ns,stat.st_size))
            except OSError: continue
        fingerprint=tuple((str(p),stamp,size) for p,stamp,size in files)
        if fingerprint==self.fingerprint and self.destination.is_file(): return False
        snapshots=[]
        for path,stamp,size in files:
            try:
                items=read_export(path)
                # Never commit a snapshot while the client is changing its export.
                stat=path.stat()
                if (stat.st_mtime_ns,stat.st_size)!=(stamp,size):return False
                snapshots.append({'character':path.name[:-len('-Inventory.txt')], 'mtime':stamp/1e9,'items':items})
            except (OSError,ValueError): continue
        self.destination.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.destination.with_suffix('.tmp')
        temporary.write_text(render(snapshots),encoding='utf-8');temporary.replace(self.destination)
        self.fingerprint=fingerprint
        return True


def bank_layout(path):
    rows=read_export(path, include_empty=True)
    top={x['bank']:x for x in rows if not x['slot']}
    numbers=set(range(1,9)) | {n for n,item in top.items() if n>8 and item['id']>0}
    result=[]
    for number in sorted(numbers):
        parent=top.get(number,{'id':0,'name':'Empty','count':0,'capacity':0,'bank':number,'slot':0,'location':f'Bank{number}'})
        children={x['slot']:x for x in rows if x['bank']==number and x['slot']}
        # Ordinary items also have a Slots value in Titanium exports. Only child
        # rows establish a container; never turn a sword into a five-slot bag.
        if parent['id']<=0:children={}
        capacity=parent['capacity'] if children and 0<parent['capacity']<=10 else (max(children) if children else 0)
        contents=[]
        for slot in range(1,capacity+1):
            contents.append(children.get(slot,{'id':0,'name':'Empty','count':0,'bank':number,'slot':slot,'location':f'Bank{number}-Slot{slot}'}))
        result.append({'number':number,'item':parent,'capacity':capacity,'contents':contents})
    return result
