'use strict';
(()=>{
 const el=id=>document.getElementById(id),token=new URLSearchParams(location.search).get('key');let busy=false,page=0;
 const api=async(path,body)=>{const r=await fetch(path,{method:body?'POST':'GET',headers:{'X-BFT-Token':token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const v=await r.json();if(!r.ok)throw Error(v.error||'Experience tracker unavailable.');return v;};
 const stamp=t=>new Date(t*1000).toLocaleString(),duration=s=>Math.floor(s/3600)+'h '+Math.floor(s%3600/60)+'m '+Math.floor(s%60)+'s';
 function options(select,rows,label){const old=select.value;select.replaceChildren();for(const row of rows){const option=document.createElement('option');option.value=row.id;option.textContent=label(row);select.append(option);}if(rows.some(r=>r.id===old))select.value=old;}
 async function refresh(reset=false){if(busy)return;busy=true;try{
  const char=el('xp-character').value,session=reset?'':el('xp-session').value,data=await api('/api/experience?character='+encodeURIComponent(char)+'&session='+encodeURIComponent(session)+'&kind='+el('xp-kind').value+'&page='+page);
  options(el('xp-character'),data.characters,c=>c.name+' · '+c.server+(c.id===data.active?' (active)':'')+(c.gap?' · log gap':''));el('xp-character').value=data.selected||'';
  options(el('xp-session'),data.sessions,s=>(s.kind==='manual'?s.name:'Automatic')+' · '+stamp(s.start)+(s.end?'':' · running'));if(data.session)el('xp-session').value=data.session.id;
  el('xp-newer').disabled=page===0;el('xp-older').disabled=!data.has_more;
  const live=!!data.active&&data.active===data.selected;el('xp-start').disabled=!live||!!data.manual_active||!data.auto_active;el('xp-stop').disabled=!live||!data.manual_active;el('xp-checkpoint').disabled=!live||!data.auto_active;
  const cards=el('xp-cards');cards.replaceChildren();const s=data.session;
  function card(title,value){const div=document.createElement('div');div.className='xp-card';const num=document.createElement('strong');num.textContent=value;const label=document.createElement('small');label.textContent=title;div.append(num,label);cards.append(div);}
  if(s){card('XP awards',s.awards);card('XP-linked kills (inferred)',s.kills);card('Your killing blows',s.own_kills);card('Unmatched XP awards',s.awards-s.kills);card('XP-linked kills / hour',s.kills_per_hour.toFixed(1));card('Session time',duration(s.seconds));card('Deaths',s.deaths);
   if(s.progress){const p=s.progress;card('Measured level-bar points',p.level_bar_points.toFixed(2));card('Net points / linked kill',p.per_kill===null?'—':p.per_kill.toFixed(3));el('xp-progress').textContent=p.note+' Measured between '+stamp(s.checkpoints[0].at)+' and '+stamp(s.checkpoints.at(-1).at)+'.';}
   else{card('XP amount','Unknown');el('xp-progress').textContent='Add two XP-bar checkpoints to measure progress. Kill counts do not reveal how much XP each mob awarded.';}
  }else el('xp-progress').textContent='No saved XP sessions yet. Enable /log on and play a character through Bait & Tackle.';
  const out=el('xp-events');out.replaceChildren();for(const e of data.events){const tr=document.createElement('tr');for(const text of [stamp(e.at),e.kind==='death'?'Character death':e.mob?e.mob+(e.party?' · party XP':'')+' (inferred match)':'XP award · mob unknown',e.kind==='death'?'Not reported':'Not reported by P1999']){const td=document.createElement('td');td.textContent=text;tr.append(td);}out.append(tr);}
  el('xp-note').textContent=data.note;
 }catch(e){el('xp-action-state').textContent=e.message;}finally{busy=false;}}
 function measurement(required=false){const level=el('xp-level').value,percent=el('xp-percent').value;if(!level&&!percent&&!required)return {};if(!level||percent==='')throw Error('Enter both your current level and XP-bar percentage.');return {level:Number(level),percent:Number(percent)};}
 async function action(kind){try{const body=measurement(kind==='checkpoint');if(kind==='start')body.name=el('xp-name').value;await api('/api/experience/'+kind,body);el('xp-action-state').textContent=kind==='start'?'Timed session started alongside automatic tracking.':kind==='stop'?'Timed session stopped and saved.':'XP-bar checkpoint saved.';el('xp-level').value='';el('xp-percent').value='';page=0;await refresh(true);}catch(e){el('xp-action-state').textContent=e.message;}}
 el('xp-start').onclick=()=>action('start');el('xp-stop').onclick=()=>action('stop');el('xp-checkpoint').onclick=()=>action('checkpoint');
 el('xp-character').onchange=()=>{page=0;el('xp-session').replaceChildren();refresh(true);};el('xp-kind').onchange=()=>{page=0;el('xp-session').replaceChildren();refresh(true);};el('xp-session').onchange=()=>refresh();el('xp-newer').onclick=()=>{page=Math.max(0,page-1);refresh(true);};el('xp-older').onclick=()=>{page++;refresh(true);};
 window.BFTExperience={refresh};if(location.hash==='#experience')refresh();setInterval(()=>{if(location.hash==='#experience'&&!document.hidden)refresh();},5000);
})();
