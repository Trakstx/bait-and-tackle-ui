'use strict';
// Execute the real form-population code with a minimal DOM and injected render failure.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/HUD/settings.js'),'utf8');
const fields=new Map();
function element(id){if(!fields.has(id))fields.set(id,{value:'',checked:false,childNodes:[],replaceChildren(...rows){this.childNodes=rows;},querySelectorAll(){return [...fields.values()];}});return fields.get(id);}
const context=vm.createContext({URLSearchParams,location:{search:''},document:{getElementById:element},buffRegisterRow(){throw Error('injected rendering failure');}});
vm.runInContext(source.slice(0,source.indexOf("$('settings').addEventListener"))+'\n'+source.split('\n').find(s=>s.startsWith('function populateBuffs')),context);
const base={network:{},misc:{},recorder:{enabled:false},dps:{enabled:true,idle_seconds:15,pet_names_by_character:{}},ch:{template:'{slot} CH -- {target}',channel:'any',my_slot:'001',cast_seconds:10,interval_seconds:3,idle_seconds:30,roster:[],enabled:true,sound:false},buffs:{enabled:true,auto_track:true,x:0,y:0,width:200,row_height:25,registry:[]}};
context.profile=base;vm.runInContext('populate(profile)',context);
element('idle').value='123';const unsaved={id:'unsaved buff edit'};element('buff-register').replaceChildren(unsaved);
context.profile={...base,dps:null,recorder:{enabled:true}};
assert.throws(()=>vm.runInContext('populate(profile)',context));
assert.equal(vm.runInContext('loaded.recorder.enabled',context),false);assert.equal(element('idle').value,'123');
context.profile={...base,buffs:{...base.buffs,registry:[{}]},recorder:{enabled:true}};
assert.throws(()=>vm.runInContext('populate(profile)',context),/injected rendering failure/);
assert.equal(vm.runInContext('loaded.recorder.enabled',context),false);assert.equal(element('idle').value,'123');assert.equal(element('buff-register').childNodes[0],unsaved);
context.profile={...base,recorder:{enabled:true}};vm.runInContext('populate(profile)',context);assert.equal(vm.runInContext('loaded.recorder.enabled',context),true);
console.log('PASS: invalid imports and render failures preserve loaded preferences, unsaved controls and existing row handlers; valid form commit is atomic.');
