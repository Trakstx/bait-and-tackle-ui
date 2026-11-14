'use strict';
// Browser port of ZlizEQMap calibration. GPL-3.0; see Maps > license.
(()=>{
 const el=id=>document.getElementById(id),token=new URLSearchParams(location.search).get('key');
 let catalog=null,state=null,selected=null,image=null,imageKey='',zoom=1,busy=false,loadSerial=0,lastZone=null;
 const canvas=el('map-canvas'),ctx=canvas.getContext('2d'),viewport=el('map-viewport');
 const request=async path=>{const r=await fetch(path,{headers:{'X-BFT-Token':token}});if(!r.ok)throw Error('Maps could not load. Reopen the dashboard through Ctrl+H.');return r.json();};
 el('map-license').href='/api/maps/license?key='+encodeURIComponent(token);
 function zone(){return catalog?.zones.find(z=>z.id===el('map-zone').value);}
 function marker(){const p=state?.position;return p&&selected&&(p.zone===selected.zone||(!p.zone&&el('map-follow').checked===false))?p:null;}
 function point(p){return {x:selected.zero[0]-p.x*image.naturalWidth/selected.total[0],y:selected.zero[1]-p.y*image.naturalHeight/selected.total[1]};}
 function draw(){
  if(!image||!selected)return;ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0);
  const p=marker();if(!p)return;const q=point(p),inside=q.x>=0&&q.y>=0&&q.x<canvas.width&&q.y<canvas.height;
  if(!inside)return;const stale=state.age>30;ctx.save();ctx.translate(q.x,q.y);ctx.lineWidth=3;ctx.strokeStyle='#081418';ctx.fillStyle=stale?'#ffce76':'#ff304c';
  if(p.heading!==null){ctx.rotate(p.heading*Math.PI/180);ctx.beginPath();ctx.moveTo(0,-13);ctx.lineTo(9,11);ctx.lineTo(0,6);ctx.lineTo(-9,11);ctx.closePath();ctx.stroke();ctx.fill();}
  else{ctx.beginPath();ctx.arc(0,0,9,0,2*Math.PI);ctx.stroke();ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(-5,-5);ctx.lineTo(5,5);ctx.moveTo(-5,5);ctx.lineTo(5,-5);ctx.stroke();}
  ctx.restore();
 }
 function resize(){if(!image)return;canvas.style.width=Math.round(image.naturalWidth*zoom)+'px';canvas.style.height=Math.round(image.naturalHeight*zoom)+'px';}
 function fit(){if(!image)return;zoom=Math.min(1,Math.max(.2,(viewport.clientWidth-8)/image.naturalWidth));resize();}
 function info(){
  const active=state?.zone_name||'Zone not yet logged',p=marker();let text=(state?.character||'Waiting for login')+' | '+active;
  if(p){text+=' | /loc '+p.y.toFixed(1)+', '+p.x.toFixed(1)+', '+p.z.toFixed(1)+' | '+Math.floor(state.age||0)+'s ago';const q=image?point(p):null;if(q&&(q.x<0||q.y<0||q.x>=image.naturalWidth||q.y>=image.naturalHeight))text+=' | Outside this map’s drawn bounds';if(!p.zone)text+=' | Zone selected manually';}
  else text+=' | '+(state?.position?'Browsing another zone':'Type /loc in EQ to update your marker');
  el('map-state').textContent=text;
 }
 function floors(){const z=zone();el('map-floor').replaceChildren();for(const m of z?.maps||[]){const o=document.createElement('option');o.value=m.id;o.textContent=m.description;el('map-floor').append(o);}showMap();}
 function showMap(){
  const z=zone();selected=z?.maps.find(m=>m.id===el('map-floor').value)||null;const serial=++loadSerial;
  image=null;canvas.hidden=true;el('map-empty').hidden=false;el('map-empty').textContent='Loading map…';
  const legend=el('map-legend');legend.replaceChildren();for(const line of selected?.legend||[]){const li=document.createElement('li');li.textContent=line;legend.append(li);}
  const links=el('map-connections');links.replaceChildren();for(const c of z?.connections||[]){const b=document.createElement('button');b.type='button';b.className='secondary';b.textContent=c.name;b.onclick=()=>{el('map-follow').checked=false;el('map-zone').value=c.id;floors();};links.append(b);}
  if(!selected){el('map-empty').textContent='No map is available for this zone.';return;}
  imageKey=selected.id;const next=new Image();next.onload=()=>{if(serial!==loadSerial)return;image=next;canvas.width=next.naturalWidth;canvas.height=next.naturalHeight;canvas.hidden=false;el('map-empty').hidden=true;canvas.setAttribute('aria-label',selected.name+' '+selected.description+' with last logged position');fit();draw();info();};next.onerror=()=>{if(serial===loadSerial)el('map-empty').textContent='Map image is missing. Reinstall the map library.';};next.src='/api/maps/image?id='+encodeURIComponent(imageKey)+'&key='+encodeURIComponent(token);info();
 }
 async function refresh(){
  if(busy)return;busy=true;
  try{
   if(!catalog){catalog=await request('/api/maps/catalog');const select=el('map-zone');select.replaceChildren();let continent='',group=null;for(const z of catalog.zones){if(z.continent!==continent){continent=z.continent;group=document.createElement('optgroup');group.label=continent;select.append(group);}const o=document.createElement('option');o.value=z.id;o.textContent=z.name;group.append(o);}select.value=catalog.zones.some(z=>z.id==='ecommons')?'ecommons':catalog.zones[0]?.id;floors();}
   state=await request('/api/maps/state');if(el('map-follow').checked&&state.zone&&catalog.zones.some(z=>z.id===state.zone)&&(lastZone!==state.zone||el('map-zone').value!==state.zone)){el('map-zone').value=state.zone;floors();}lastZone=state.zone;info();draw();
  }catch(e){el('map-state').textContent=e.message;}finally{busy=false;}
 }
 el('map-zone').onchange=()=>{el('map-follow').checked=false;floors();};el('map-floor').onchange=showMap;el('map-follow').onchange=()=>{lastZone=null;refresh();};
 el('map-plus').onclick=()=>{zoom=Math.min(4,zoom*1.25);resize();};el('map-minus').onclick=()=>{zoom=Math.max(.2,zoom/1.25);resize();};el('map-fit').onclick=fit;
 el('map-center').onclick=()=>{const p=marker();if(!p||!image){el('map-state').textContent='Type /loc in EQ first, then view the matching zone.';return;}const q=point(p);viewport.scrollTo({left:q.x*zoom-viewport.clientWidth/2,top:q.y*zoom-viewport.clientHeight/2,behavior:'smooth'});};
 window.BFTMaps={refresh};if(location.hash==='#maps')refresh();setInterval(()=>{if(location.hash==='#maps'&&!document.hidden)refresh();},1000);
})();
