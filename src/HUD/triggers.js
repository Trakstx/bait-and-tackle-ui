'use strict';

(()=>{

 const el=id=>document.getElementById(id),key=new URLSearchParams(location.search).get('key');let config=null,state=null,editing=crypto.randomUUID(),dirty=false,busy=false,presetSignature='',profileSeen=null;

 const api=async(path,body)=>{const r=await fetch(path,{method:body?'POST':'GET',headers:{'X-BFT-Token':key,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const v=await r.json();if(!r.ok)throw Error(v.error||'Class alerts could not load.');return v;};

 const title=s=>s.replace(/\b\w/g,c=>c.toUpperCase());

 function mark(){dirty=true;el('trigger-status').textContent='Unsaved alert changes. Save alerts live to apply.';}

 function populate(){el('trigger-invulnerability').checked=config.invulnerability_enabled??true;el('trigger-da-source').value=config.invulnerability_sources?.[state.profile_key]||'auto';for(const [id,field] of [['trigger-enabled','enabled'],['trigger-sound','sound_enabled']])el(id).checked=config[field];for(const [id,field] of [['trigger-x','x'],['trigger-y','y'],['trigger-width','width'],['trigger-rows','rows'],['trigger-volume','speech_volume'],['trigger-rate','speech_rate']])el(id).value=config[field];el('trigger-audio-mode').value=config.audio_mode;el('trigger-voice').value=config.speech_voice||'';el('trigger-class').value=config.class_overrides[state.profile_key]||'';presets();customList();}

 function presets(){

  if(!state||!config)return;const out=el('trigger-presets');const kind=el('trigger-class').value||state.detected_class;const signature=JSON.stringify([kind,el('trigger-all').checked,config.preset_overrides]);if(signature===presetSignature)return;presetSignature=signature;out.replaceChildren();

  for(const rule of state.presets){if(!el('trigger-all').checked&&rule.classes.length&&!rule.classes.includes(kind))continue;const label=document.createElement('label');label.className='check';const check=document.createElement('input');check.type='checkbox';check.checked=config.preset_overrides[rule.id]??true;check.onchange=()=>{config.preset_overrides[rule.id]=check.checked;mark();};const text=document.createElement('span');text.textContent=rule.name;const hint=document.createElement('small');hint.textContent=rule.classes.length?(kind&&rule.classes.includes(kind)?title(kind)+' preset':rule.classes.map(title).join(', ')):'Shared alert';hint.title=rule.classes.map(title).join(', ');text.append(hint);label.append(check,text);out.append(label);}

 }

 function customList(){const out=el('trigger-custom');out.replaceChildren();for(const r of config.custom){const row=document.createElement('div');row.className='trigger-list-row';const text=document.createElement('span');text.textContent=r.name+' Â· '+(r.enabled?'enabled':'disabled')+' Â· '+(r.classes.length?r.classes.map(title).join(', '):'all classes');const edit=document.createElement('button');edit.type='button';edit.className='secondary';edit.textContent='Edit';edit.onclick=()=>editRule(r);const del=document.createElement('button');del.type='button';del.className='secondary';del.textContent='Remove';del.onclick=()=>{config.custom=config.custom.filter(x=>x.id!==r.id);customList();mark();};row.append(text,edit,del);out.append(row);}if(!config.custom.length)out.textContent='No custom triggers yet.';}

 function editRule(rule=null){editing=rule?.id||crypto.randomUUID();el('trigger-editor-title').textContent=rule?'Edit '+rule.name:'New trigger';for(const [id,value] of Object.entries({'rule-name':rule?.name||'','rule-pattern':rule?.pattern||'','rule-message':rule?.message||'','rule-mode':rule?.mode||'contains','rule-severity':rule?.severity||'warn','rule-duration':rule?.duration_seconds||0,'rule-cooldown':rule?.cooldown_seconds??3}))el(id).value=value;el('rule-enabled').checked=rule?.enabled??true;el('rule-sound').checked=rule?.sound||false;for(const box of el('rule-classes').querySelectorAll('input'))box.checked=rule?.classes.includes(box.value)||false;el('rule-test-result').textContent='';}

 function draft(){return {id:editing,name:el('rule-name').value.trim(),pattern:el('rule-pattern').value.trim(),message:el('rule-message').value.trim(),mode:el('rule-mode').value,severity:el('rule-severity').value,duration_seconds:Number(el('rule-duration').value),cooldown_seconds:Number(el('rule-cooldown').value),enabled:el('rule-enabled').checked,sound:el('rule-sound').checked,classes:Array.from(el('rule-classes').querySelectorAll('input:checked')).map(x=>x.value)};}

 function collect(){const value=structuredClone(config);value.invulnerability_enabled=el('trigger-invulnerability').checked;value.invulnerability_sources=value.invulnerability_sources||{};if(state.profile_key)value.invulnerability_sources[state.profile_key]=el('trigger-da-source').value;value.speech_style='natural';value.audio_mode=el('trigger-audio-mode').value;value.speech_voice=el('trigger-voice').value;value.enabled=el('trigger-enabled').checked;value.sound_enabled=el('trigger-sound').checked;for(const [id,field] of [['trigger-x','x'],['trigger-y','y'],['trigger-width','width'],['trigger-rows','rows'],['trigger-volume','speech_volume'],['trigger-rate','speech_rate']])value[field]=Number(el(id).value);if(state.profile_key){if(el('trigger-class').value)value.class_overrides[state.profile_key]=el('trigger-class').value;else delete value.class_overrides[state.profile_key];}return value;}

 async function save(mode=null){try{const value=collect();if(mode!==null)value.move_mode=mode;if(mode===true)value.enabled=true;config=await api('/api/triggers/config',value);loaded.triggers=config;dirty=false;populate();el('trigger-status').textContent=mode===true?'Placement enabled. Return to EQ and drag the alert panel header; release to save.':'Saved. Alerts updated live; no EQ restart needed.';}catch(e){el('trigger-status').textContent=e.message;}}

 async function refresh(){if(busy)return;busy=true;try{state=await api('/api/triggers');if(config&&profileSeen!==state.profile_key){el('trigger-da-source').value=config.invulnerability_sources?.[state.profile_key]||'auto';el('trigger-class').value=config.class_overrides[state.profile_key]||'';}profileSeen=state.profile_key;if(!config){config=(await api('/api/settings')).triggers;for(const c of state.classes){for(const id of ['trigger-class','rule-test-class']){const o=document.createElement('option');o.value=c;o.textContent=title(c);el(id).append(o);}const label=document.createElement('label');label.className='check';const box=document.createElement('input');box.type='checkbox';box.value=c;label.append(box,document.createTextNode(title(c)));el('rule-classes').append(label);}populate();}

  const audio=await api('/api/triggers/audio');for(const name of audio.voices||[]){if(!Array.from(el('trigger-voice').options).some(o=>o.value===name)){const option=document.createElement('option');option.value=name;option.textContent=name;el('trigger-voice').append(option);}}if(!dirty)el('trigger-voice').value=config.speech_voice||'';el('trigger-audio-state').textContent=audio.error?'Speech unavailable: '+audio.error:audio.ready?'Voice ready'+(audio.last_spoken?' Â· Last spoken: '+audio.last_spoken:''):'Uses your default Windows voice, offline. Test voice to check audio.';

  el('trigger-character').textContent=state.character+(state.server?' Â· '+state.server:'')+' Â· '+(state.class?title(state.class):'Class unknown')+(state.level?' '+state.level:'')+' Â· '+state.class_source;

  el('trigger-class').disabled=!state.profile_key;el('trigger-move').disabled=!state.profile_key;

  if(!dirty){const latest=(await api('/api/settings')).triggers;if(latest.x!==config.x||latest.y!==config.y||latest.move_mode!==config.move_mode){config=latest;loaded.triggers=config;populate();}}

  const recent=el('trigger-recent');recent.replaceChildren();for(const row of state.recent.slice(0,12)){const p=document.createElement('p');p.textContent=new Date(row.started*1000).toLocaleTimeString()+' Â· '+(row.test?'TEST Â· ':'')+row.message;recent.append(p);}if(!state.recent.length)recent.textContent='Waiting for a matching live log message.';presets();

 }catch(e){el('trigger-status').textContent=e.message;}finally{busy=false;}}

 el('trigger-save').onclick=()=>save();el('trigger-move').onclick=()=>save(true);el('trigger-place').onclick=()=>save(false);el('trigger-all').onchange=presets;el('trigger-class').onchange=()=>{mark();presets();};for(const id of ['trigger-invulnerability','trigger-da-source','trigger-enabled','trigger-sound','trigger-x','trigger-y','trigger-width','trigger-rows','trigger-volume','trigger-rate','trigger-audio-mode','trigger-voice'])el(id).oninput=mark;

 el('trigger-new').onclick=()=>editRule();el('rule-add').onclick=()=>{const r=draft();if(!r.name||!r.pattern||!r.message){el('rule-test-result').textContent='Enter a name, match text and alert message.';return;}const i=config.custom.findIndex(x=>x.id===r.id);if(i<0)config.custom.push(r);else config.custom[i]=r;customList();mark();el('rule-test-result').textContent='Rule added to your draft. Save alerts live to activate it.';};

 async function test(show,speak=false){try{const value=await api('/api/triggers/test',{rule:draft(),sample:el('rule-sample').value,class:el('rule-test-class').value||null,show,speak,config:collect()});el('rule-test-result').textContent=(value.matched?'MATCH: '+value.message:'No match.')+(value.eligible?' Â· Eligible for this class.':' Â· This class would not activate this rule.')+(show&&value.matched?' Test preview queued; return to EQ to view it.':'');}catch(e){el('rule-test-result').textContent=e.message;}}

 el('trigger-voice-test').onclick=async()=>{try{await api('/api/triggers/audio/test',{config:collect()});el('trigger-audio-state').textContent='Voice test queued. Audio uses the Windows default output device.';}catch(e){el('trigger-audio-state').textContent=e.message;}};el('rule-speak').onclick=()=>test(false,true);

 el('rule-test').onclick=()=>test(false);el('rule-preview').onclick=()=>test(true);window.BFTTriggers={refresh};if(location.hash==='#triggers')refresh();setInterval(()=>{if(location.hash==='#triggers'&&!document.hidden)refresh();},2000);

})();

