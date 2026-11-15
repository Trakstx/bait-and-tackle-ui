'use strict';

const key=new URLSearchParams(location.search).get('key');

const $=id=>document.getElementById(id);let loaded;

function status(text,kind=''){ $('status').textContent=text;$('status').className=kind; }

async function api(path,data){const r=await fetch(path,{method:data?'POST':'GET',headers:{'X-BFT-Token':key,'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});const value=await r.json();if(!r.ok)throw Error(value.error||'Could not save settings');return value;}

function populate(v){loaded=v;$('tick-enabled').checked=v.misc?.tick_enabled||false;$('dps-enabled').checked=v.dps.enabled;$('idle').value=v.dps.idle_seconds;$('pets').value=Object.entries(v.dps.pet_names_by_character).map(([name,pets])=>name+': '+pets.join(', ')).join('\n');for(const k of ['template','channel','my_slot','cast_seconds','interval_seconds','idle_seconds'])$(k).value=v.ch[k];$('roster').value=v.ch.roster.join(', ');$('enabled').checked=v.ch.enabled;$('sound').checked=v.ch.sound;populateBuffs(v.buffs);}

function collect(){const pets={};for(const line of $('pets').value.split('\n').filter(x=>x.trim())){const i=line.indexOf(':');if(i<1)throw Error('Use Character: Petname for each pet entry.');const name=line.slice(0,i).trim();if(Object.hasOwn(pets,name))throw Error('Duplicate character in pet settings.');pets[name]=line.slice(i+1).split(',').map(x=>x.trim()).filter(Boolean);}return {klandicar:loaded?.klandicar||{},recorder:loaded?.recorder||{},aggro:loaded?.aggro||{},timers:loaded?.timers||{},triggers:loaded?.triggers||{},misc:{tick_enabled:$('tick-enabled').checked,tick_anchor:loaded?.misc?.tick_anchor||0},buffs:collectBuffs(),dps:{enabled:$('dps-enabled').checked,idle_seconds:Number($('idle').value),pet_names_by_character:pets},ch:{enabled:$('enabled').checked,template:$('template').value,channel:$('channel').value,roster:$('roster').value.split(',').map(x=>x.trim()).filter(Boolean),my_slot:$('my_slot').value,cast_seconds:Number($('cast_seconds').value),interval_seconds:Number($('interval_seconds').value),idle_seconds:Number($('idle_seconds').value),sound:$('sound').checked}};}

$('settings').addEventListener('input',e=>{if(e.target.id?.startsWith('trigger-')||e.target.id?.startsWith('rule-')||e.target.closest('#trigger-presets')||e.target.closest('#rule-classes')||e.target.id?.startsWith('xp-')||e.target.id?.startsWith('layout-')||e.target.closest('#layout-targets'))return;status('Unsaved changes.');});

$('settings').addEventListener('submit',async e=>{e.preventDefault();$('save').disabled=true;try{populate(await api('/api/settings',collect()));status('Saved. CH updates now; DPS updates when its reader is running the latest version.','success');}catch(e){status(e.message,'error');}finally{$('save').disabled=false;}});

$('test').onclick=async()=>{try{const v=await api('/api/test',{ch:collect().ch,sample:$('sample').value});$('match').textContent=v.matched?`Matched â€” slot ${v.slot} â†’ ${v.target}`:'No match. Check the format, channel and chain order.';$('match').className=v.matched?'success':'error';}catch(e){$('match').textContent=e.message;$('match').className='error';}};

$('export').onclick=()=>{try{const blob=new Blob([JSON.stringify(collect(),null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='Bait-and-Tackle-settings.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}catch(e){status(e.message,'error');}};

$('import').onclick=()=>$('file').click();$('file').onchange=async()=>{try{const file=$('file').files[0];if(!file)return;if(file.size>65536)throw Error('Profile is too large.');const value=JSON.parse(await file.text());populate(value);status('Profile loaded. Review and Save to apply.');}catch(e){status('Could not import profile: '+e.message,'error');}};

api('/api/settings').then(v=>{populate(v);status('Settings ready.');}).catch(e=>status(e.message,'error'));



let currentPage='dps',bankData=[],buffCatalogReady=false;

function cell(row,value){const td=document.createElement('td');td.textContent=String(value??'');row.append(td);}

function messageRow(body,text,columns){body.replaceChildren();const tr=document.createElement('tr');const td=document.createElement('td');td.colSpan=columns;td.textContent=text;tr.append(td);body.append(tr);}

async function loadHistory(){try{const data=await api('/api/history?character='+encodeURIComponent($('history-character').value));const select=$('history-character');select.replaceChildren();for(const c of data.characters){const o=document.createElement('option');o.value=c.id;o.textContent=c.name;select.append(o);}select.value=data.selected;const body=$('fight-rows');body.replaceChildren();for(const f of data.fights){const tr=document.createElement('tr');cell(tr,new Date(Number(f.start)*1000).toLocaleString());cell(tr,(f.targets||[]).join(', '));cell(tr,Number(f.damage||0).toLocaleString());cell(tr,Number(f.dps||0).toFixed(1));cell(tr,Number(f.duration||0).toFixed(0)+'s');cell(tr,Number(f.incoming||0).toLocaleString());body.append(tr);}if(!data.fights.length)messageRow(body,'No completed fights for this character.',6);$('history-state').textContent='Updates every 15 seconds while this tab is open.';}catch(e){$('history-state').textContent=e.message;}}


const openBankBags=new Set(),seenBankCharacters=new Set();
let bankView='grid';
function wikiUrl(name){return 'https://wiki.project1999.com/'+encodeURIComponent(String(name).trim().replace(/ /g,'_'));}
function wikiLink(name,label=name){const link=document.createElement('a');link.href=wikiUrl(name);link.target='_blank';link.rel='noopener noreferrer';link.textContent=label;link.title='Open '+name+' on Project 1999 Wiki';return link;}
function bankRegister(snapshot,query){
    const wrap=document.createElement('div');wrap.className='table-wrap bank-register';const table=document.createElement('table'),head=document.createElement('thead'),row=document.createElement('tr');
    for(const text of ['Item','Quantity','Location']){const th=document.createElement('th');th.textContent=text;row.append(th);}head.append(row);table.append(head);const body=document.createElement('tbody');
    const items=snapshot.items.filter(i=>i.id&&i.count>0).filter(i=>(i.name+' Bank '+i.bank+' slot '+i.slot).toLowerCase().includes(query)).sort((a,b)=>a.name.localeCompare(b.name)||a.bank-b.bank||a.slot-b.slot);
    for(const item of items){const tr=document.createElement('tr'),name=document.createElement('td');name.append(wikiLink(item.name));tr.append(name);cell(tr,item.count);const bag=snapshot.items.find(i=>i.bank===item.bank&&!i.slot);cell(tr,'Bank '+item.bank+(item.slot?' / '+(bag?.name||'bag')+' / slot '+item.slot:''));body.append(tr);}
    if(!items.length)messageRow(body,'No matching bank items.',3);table.append(body);wrap.append(table);return wrap;
}
function bankItemSlot(item,location,query,linked=true){
    const slot=document.createElement('div');slot.className='eq-slot';
    const empty=!item||!item.id||item.count<=0;
    slot.setAttribute('role','img');slot.setAttribute('aria-label',empty?'Empty '+location:item.name+', quantity '+item.count+', '+location);
    slot.title=empty?'Empty - '+location:item.name+'\nQuantity: '+item.count+'\n'+location+'\nItem ID: '+item.id;
    slot.draggable=false;
    if(empty){slot.classList.add('empty');return slot;}
    const fallback=document.createElement('span');fallback.className='eq-fallback';fallback.textContent=item.name.split(/\s+/).map(x=>x[0]).join('').slice(0,3);slot.append(fallback);
    const image=document.createElement('img');image.alt='';image.draggable=false;image.loading='lazy';image.src='/api/item-icon?id='+encodeURIComponent(item.id)+'&name='+encodeURIComponent(item.name)+'&key='+encodeURIComponent(key);image.onload=()=>fallback.hidden=true;image.onerror=()=>image.remove();slot.append(image);
    if(item.count>1){const count=document.createElement('span');count.className='eq-count';count.textContent=item.count;slot.append(count);}
    if(query){const matched=(item.name+' '+location).toLowerCase().includes(query);slot.classList.add(matched?'bank-match':'bank-dim');}
    if(!linked)return slot;
    const link=wikiLink(item.name,'');link.className='eq-item-link';link.setAttribute('aria-label','Open '+item.name+' on Project 1999 Wiki');link.append(slot);return link;
}
function showBank(){
    const out=$('bank-results');out.replaceChildren();const snapshot=bankData.find(x=>x.character===$('bank-character').value)||bankData[0];
    if(!snapshot){out.textContent='No inventory export found. Run /outputfile inventory in EverQuest.';return;}
    const query=$('bank-search').value.trim().toLowerCase(),slots=snapshot.slots||[];
    $('bank-grid-button').setAttribute('aria-pressed',bankView==='grid'?'true':'false');$('bank-register-button').setAttribute('aria-pressed',bankView==='register'?'true':'false');
    if(!seenBankCharacters.has(snapshot.character)){seenBankCharacters.add(snapshot.character);const first=slots.find(x=>x.capacity>0);if(first)openBankBags.add(snapshot.character+':'+first.number);}
    const stamp=document.createElement('p');stamp.className='bank-snapshot';stamp.textContent=snapshot.character+' | Exported '+new Date(snapshot.updated*1000).toLocaleString()+' | Saved snapshot, not live. Server is not recorded in this export.';out.append(stamp);
    if(bankView==='register'){out.append(bankRegister(snapshot,query));return;}
    const layout=document.createElement('div');layout.className='eq-bank-layout';
    const vault=document.createElement('div');vault.className='eq-window eq-vault';
    const title=document.createElement('h3');title.textContent='BANK';vault.append(title);
    const grid=document.createElement('div');grid.className='eq-vault-grid';
    for(const bank of slots){
        const frame=document.createElement('div');frame.className='eq-bank-position';const button=document.createElement('button');button.type='button';button.className='eq-slot-button';button.draggable=false;
        const id=snapshot.character+':'+bank.number;const opened=openBankBags.has(id);
        button.setAttribute('aria-label','Bank '+bank.number+': '+bank.item.name+(bank.capacity?', '+bank.capacity+' slots. Click to '+(opened?'close':'open')+' bag.':''));
        if(bank.capacity){button.setAttribute('aria-expanded',opened?'true':'false');button.classList.toggle('bag-open',opened);button.onclick=()=>{if(openBankBags.has(id))openBankBags.delete(id);else openBankBags.add(id);showBank();};}
        else if(bank.item.id>0){button.onclick=()=>window.open(wikiUrl(bank.item.name),'_blank','noopener,noreferrer');}
        else button.disabled=true;
        button.append(bankItemSlot(bank.item,'Bank '+bank.number,query,false));frame.append(button);const number=document.createElement('small');number.textContent=bank.number;frame.append(number);if(bank.item.id>0){const link=wikiLink(bank.item.name,'Wiki');link.className='bank-wiki-link';frame.append(link);}grid.append(frame);
    }
    vault.append(grid);const hint=document.createElement('p');hint.textContent='Click a bag to inspect its contents. Items cannot be moved.';vault.append(hint);layout.append(vault);
    const bags=document.createElement('div');bags.className='eq-bags';let visible=0;
    for(const bank of slots){
        const id=snapshot.character+':'+bank.number;
        const searchHit=query&&bank.contents.some(x=>x.id&&(x.name+' Bank '+bank.number+' slot '+x.slot).toLowerCase().includes(query));
        if(!bank.capacity||(!openBankBags.has(id)&&!searchHit))continue;
        visible++;const bag=document.createElement('div');bag.className='eq-window eq-bag';const heading=document.createElement('h4');heading.append(wikiLink(bank.item.name));bag.append(heading);
        const caption=document.createElement('p');caption.textContent='Bank '+bank.number+' - '+bank.capacity+' slots';bag.append(caption);
        const contents=document.createElement('div');contents.className='eq-bag-grid';
        for(const item of bank.contents)contents.append(bankItemSlot(item,'Bank '+bank.number+' / slot '+item.slot,query));
        bag.append(contents);bags.append(bag);
    }
    if(!visible){const help=document.createElement('p');help.className='bank-empty-help';help.textContent='Select a bank bag to open its saved contents.';bags.append(help);}
    layout.append(bags);out.append(layout);
}
async function loadBank(){try{
    const data=await api('/api/bank');bankData=data.characters;
    const select=$('bank-character'),selected=select.value;select.replaceChildren();
    for(const c of bankData){const option=document.createElement('option');option.value=c.character;option.textContent=c.character;select.append(option);}
    const fallback=bankData.find(c=>c.character===data.active)||bankData.reduce((best,c)=>!best||c.updated>best.updated?c:best,null);
    select.value=bankData.some(c=>c.character===selected)?selected:(fallback?.character||'');
    showBank();$('bank-state').textContent='Exact exported slots and bag sizes. Click items for the P1999 Wiki. Search highlights matching items without changing their positions. Icons load on demand and are cached locally.';
}catch(e){$('bank-state').textContent=e.message;}}
function choosePage(){const requested=location.hash.slice(1);currentPage=['dps','ch','aggro','history','bank','buffs','maps','misc','experience','triggers','timers','recorder','updates','klandicar'].includes(requested)?requested:'dps';for(const panel of document.querySelectorAll('[data-panel]'))panel.hidden=panel.id!==currentPage;for(const link of document.querySelectorAll('[data-page]')){const active=link.dataset.page===currentPage;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}document.querySelector('form footer').hidden=['bank','history','maps','experience','triggers','timers','recorder','updates','klandicar'].includes(currentPage);if(currentPage==='aggro')loadAggro();if(currentPage==='history')loadHistory();if(currentPage==='bank')loadBank();if(currentPage==='buffs')loadBuffs();if(currentPage==='maps')window.BFTMaps?.refresh();if(currentPage==='misc')window.BFTMisc?.refresh();if(currentPage==='experience')window.BFTExperience?.refresh();if(currentPage==='triggers')window.BFTTriggers?.refresh();if(currentPage==='timers')window.BFTTimers?.refresh();if(currentPage==='recorder')window.BFTRecorder?.refresh();}

$('history-character').onchange=loadHistory;$('bank-character').onchange=showBank;$('bank-search').oninput=showBank;window.addEventListener('hashchange',choosePage);choosePage();setInterval(()=>{if(document.hidden)return;if(currentPage==='aggro')loadAggro();if(currentPage==='history')loadHistory();if(currentPage==='bank')loadBank();if(currentPage==='buffs')loadBuffs();if(currentPage==='maps')window.BFTMaps?.refresh();},15000);


$('bank-grid-button').onclick=()=>{bankView='grid';showBank();};$('bank-register-button').onclick=()=>{bankView='register';showBank();};

function buffRegisterRow(row={name:'',duration_seconds:60}){
 const tr=document.createElement('tr');tr.className='buff-config-row';
 for(const field of ['name','duration_seconds']){const td=document.createElement('td'),input=document.createElement('input');input.dataset.buffField=field;input.value=row[field];if(field==='name'){input.type='text';input.setAttribute('list','buff-spells');input.maxLength=120;input.required=true;}else{input.type='number';input.min=1;input.max=86400;input.required=true;}td.append(input);tr.append(td);}
 const td=document.createElement('td'),remove=document.createElement('button');remove.type='button';remove.className='secondary';remove.textContent='Remove';remove.onclick=()=>{tr.remove();status('Unsaved changes.');};td.append(remove);tr.append(td);$('buff-register').append(tr);
}
function populateBuffs(config){config=config||{enabled:true,auto_track:true,x:1320,y:110,width:200,row_height:25,registry:[]};$('buffs-enabled').checked=config.enabled;$('buff-auto').checked=config.auto_track;$('buff-infer').checked=config.infer_shared!==false;$('buff-assumed-level').value=config.assumed_level||60;$('buff-width').value=config.width;$('buff-x').value=config.x;$('buff-y').value=config.y;$('buff-spacing').value=config.row_height;$('buff-register').replaceChildren();for(const row of config.registry)buffRegisterRow(row);}
function collectBuffs(){return {style:'native_slots',enabled:$('buffs-enabled').checked,auto_track:$('buff-auto').checked,infer_shared:$('buff-infer').checked,assumed_level:Number($('buff-assumed-level').value),width:Number($('buff-width').value),x:Number($('buff-x').value),y:Number($('buff-y').value),row_height:Number($('buff-spacing').value),registry:Array.from(document.querySelectorAll('.buff-config-row')).map(row=>{const read=field=>row.querySelector('[data-buff-field="'+field+'"]').value;return {name:read('name').trim(),duration_seconds:Number(read('duration_seconds'))};})};}

async function loadBuffs(){try{if(!buffCatalogReady){const data=await api('/api/buff-catalog');$('buff-spells').replaceChildren();for(const name of data.spells){const option=document.createElement('option');option.value=name;$('buff-spells').append(option);}buffCatalogReady=true;}const data=await api('/api/buffs');$('buff-state').textContent=data.note;const out=$('buff-active');out.replaceChildren();for(const timer of data.timers){const row=document.createElement('div');row.className='buff-dashboard-row';const image=document.createElement('img');image.src='/api/spell-icon?id='+encodeURIComponent(timer.icon)+'&key='+encodeURIComponent(key);image.alt='';image.width=32;image.height=32;image.onerror=()=>image.remove();row.append(image);const label=document.createElement('span');const stamp=s=>Math.floor(s/60)+':'+String(s%60).padStart(2,'0');label.textContent=timer.name+' - '+(timer.remaining===null?'unknown duration':'~'+(timer.minimum_remaining!==timer.remaining?stamp(timer.minimum_remaining)+' - ':'')+stamp(timer.remaining));row.append(label);const detail=document.createElement('small');detail.textContent=(timer.uncertain?'UNVERIFIED SAVED EFFECT: ':timer.identity==='inferred'?'ASSUMED SPELL: ':'')+(timer.reason||'');row.append(detail);const dismiss=document.createElement('button');dismiss.type='button';dismiss.textContent='Dismiss';dismiss.title='Remove this local timer only';dismiss.onclick=async()=>{try{await api('/api/buffs/dismiss',{name:timer.spell});await loadBuffs();}catch(e){$('buff-state').textContent=e.message;}};row.append(dismiss);out.append(row);}if(!data.timers.length)out.textContent='No usable observed buff landings yet.';for(const event of data.unresolved||[]){const p=document.createElement('p');p.textContent='Unresolved: '+event.message+' | '+event.candidates.join(', ');out.append(p);}}catch(e){$('buff-state').textContent=e.message;}}
$('add-buff').onclick=()=>{buffRegisterRow();status('Unsaved changes.');};

async function loadAggro(){try{const s=await api('/api/aggro');const prefs=(await api('/api/settings')).aggro;loaded.aggro=prefs;$('aggro-enabled').checked=prefs.enabled;const fresh=s.updated&&Date.now()/1000-s.updated<5;const gear=s.gear_status==='READY'?'Inventory export current':s.gear_status==='STALE'?'Run /outputfile inventory: export is stale':'Run /outputfile inventory';$('aggro-status').textContent=(s.character||'Waiting for character')+' · '+gear+(fresh?'':' · Combat reader not current');const lines=[];for(const [hand,item] of Object.entries(s.equipment||{})){const resolved=s.resolved_items?.[hand];lines.push(hand+': '+item.name+(resolved?' · '+(resolved.damage||0)+' damage / '+(resolved.delay||0)+' delay':' · resolving stats'));}if(s.estimate)lines.push('Estimated melee hate: '+Math.round(s.estimate[0])+' – '+Math.round(s.estimate[1])+' (partial)');if(s.target)lines.push('Target: '+s.target.name);if(s.profile)lines.push('Profile: '+(s.profile.class||'unknown class')+' '+(s.profile.level||'unknown level'));for(const value of Object.values(s.lookup_errors||{}))lines.push('Lookup: '+value);$('aggro-details').textContent=lines.join('\n');}catch(e){$('aggro-status').textContent=e.message;}}
$('aggro-enabled').onchange=async()=>{try{const v=await api('/api/aggro/config',{enabled:$('aggro-enabled').checked});loaded.aggro=v;$('aggro-save-state').textContent='Saved live.';}catch(e){$('aggro-save-state').textContent=e.message;}};
