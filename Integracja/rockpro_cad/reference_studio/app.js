const $=id=>document.getElementById(id);
import {WorkstationView} from './workstation3d.js';
const token=location.pathname.split('/').filter(Boolean)[0];
let catalog, selected, variant, view='closed';
const drafts=new Map();
const previewDrafts=new Map();let workstation=null,mode3d=false,controlsBuilt=false;
const fields=['x','y','z','cover','opening','transport','notes','shelf-count','shelf-travel'];
function remember(){if(variant)drafts.set(variant.id,Object.fromEntries(fields.map(id=>[id,$(id).value])));}
function restore(){const d=drafts.get(variant.id)||{};for(const id of fields)$(id).value=d[id]??(['opening','transport'].includes(id)?'source_unconfirmed':'');}
function showResult(text,error=false){$('result').textContent=text;$('result').classList.toggle('error',error);}
function showImage(){
 const source=variant.images[view];
 $('reference-image').hidden=!source;
 if(source)$('reference-image').src=source;
 for(const v of ['closed','inside']){$(v).disabled=!variant.images[v];$(v).classList.toggle('active',view===v);}
}
function refreshPreviewControls(){
 if(!workstation?.loaded)return;
 ['preview-x','preview-y','preview-z'].forEach((id,k)=>{
  const input=$(id),base=1000*(workstation.model.baseline_bounds[k+3]-workstation.model.baseline_bounds[k]);
  input.min=Math.ceil(base*.8);input.max=Math.floor(base*1.4);input.value=Number(workstation.dimensions[k].toFixed(3));
 });
 $('show-covers').checked=workstation.coverVisible;
 workstation.travels.forEach((value,i)=>{const input=$('slide-'+i);if(input){input.value=value;$('travel-'+i).textContent=Math.round(value)+' mm';}});
}
function buildPreviewControls(){
 if(controlsBuilt)return;controlsBuilt=true;
 workstation.model.shelves.forEach((s,i)=>{
  const label=document.createElement('label');label.className='shelf-slider';const caption=document.createElement('span');caption.textContent=s.label;
  const output=document.createElement('output');output.id='travel-'+i;output.textContent='0 mm';
  const input=document.createElement('input');input.type='range';input.id='slide-'+i;input.min=0;input.max=500;input.step=1;input.value=0;input.setAttribute('aria-label',s.label+' — wysuw');
  input.oninput=()=>{workstation.setTravel(i,Number(input.value));output.textContent=input.value+' mm';};label.append(caption,output,input);$('shelf-sliders').append(label);
 });
 ['preview-x','preview-y','preview-z'].forEach((id,k)=>$(id).onchange=()=>{
  if(!$(id).reportValidity())return;const values=[...workstation.dimensions];values[k]=Number($(id).value);workstation.setDimensions(values);
 });
 $('show-covers').onchange=e=>{workstation.coverVisible=e.target.checked;workstation.apply();};
 $('fit-view').onclick=()=>workstation.fit();
 $('reset-view').onclick=()=>{workstation.restore({source_sha256:workstation.model.source_sha256,external_mm:[0,1,2].map(k=>1000*(workstation.model.baseline_bounds[k+3]-workstation.model.baseline_bounds[k])),shelf_travel_mm:[0,0,0,0],covers_visible:false});refreshPreviewControls();workstation.fit();};
 for(const [id,amount] of [['extend-all',350],['close-all',0]])$(id).onclick=()=>{workstation.travels=[amount,amount,amount,amount];workstation.apply();refreshPreviewControls();};
}
async function show3d(){
 mode3d=true;$('interactive').hidden=false;$('image-wrap').hidden=true;$('three').classList.add('active');
 $('closed').classList.remove('active');$('inside').classList.remove('active');
 try{
  if(!workstation)workstation=new WorkstationView($('viewport'),$('mesh-status'),()=>previewDrafts.set('M04',workstation.state()));
  await workstation.load();buildPreviewControls();refreshPreviewControls();workstation.resize();
 }catch(e){$('mesh-status').textContent='Nie udało się wczytać 3D: '+e.message;}
}
function selectVariant(id){
 remember();variant=selected.variants.find(v=>v.id===id);
 $('variant').value=variant.id;$('name').textContent=variant.label;
 $('part-count').textContent=`· ${variant.part_count} wystąpień części`;
 $('groups').replaceChildren(...variant.groups.map(g=>{const li=document.createElement('li');li.textContent=g.label||'(bez nazwy)';const code=document.createElement('code');code.textContent=g.path;li.append(code);return li;}));
 if(!variant.images[view])view=Object.keys(variant.images)[0];
 showImage();restore();
 const supported=variant.id==='M04'&&Boolean(catalog.workstation_preview);$('three').disabled=!supported;
 $('interactive').hidden=true;$('image-wrap').hidden=false;$('three').classList.remove('active');mode3d=false;
 if(supported)show3d();
 showResult('Szkic tego wariantu. Eksport JSON pozwala zachować wymagania po zamknięciu aplikacji. Wymiary podglądu 3D i wymaganego wnętrza są rozdzielone.');
}
function selectFamily(id){
 remember();selected=catalog.families.find(f=>f.id===id);variant=null;
 for(const button of $('families').children)button.classList.toggle('active',button.dataset.id===id);
 $('description').textContent=selected.description;
 $('shelf-fields').hidden=selected.id!=='workstation';
 for(const id of ['shelf-count','shelf-travel'])$(id).disabled=selected.id!=='workstation';
 $('controls').replaceChildren(...selected.controls.map(c=>{const el=document.createElement('span');el.textContent=c;return el;}));
 $('questions').textContent=selected.questions.join(' ');
 $('notes').placeholder=selected.controls.join('; ')+'…';
 $('variant').replaceChildren(...selected.variants.map(v=>new Option(v.label,v.id)));
 selectVariant(selected.variants[0].id);
}
function number(id){return $(id).value.trim()===''?null:Number($(id).value);}
function getDraft(){const draft={schema:'rockpro.concept-draft/1',catalog_binding:catalog.binding,
 family_id:selected.id,variant_id:variant.id,internal_mm:['x','y','z'].map(number),
 cover_height_mm:number('cover'),opening:$('opening').value,transport:$('transport').value,notes:$('notes').value,
 sliding_shelves:selected.id==='workstation'?{count:number('shelf-count'),requested_travel_mm:number('shelf-travel')}:null};
 if(variant.id==='M04'&&workstation?.loaded)draft.preview=workstation.state();return draft;}
async function validate(draft){
 const response=await fetch('validate',{method:'POST',headers:{'Content-Type':'application/json','X-RockPro-Session':token},body:JSON.stringify(draft)});
 const receipt=await response.json();if(!response.ok)throw Error(receipt.error||'Nie można sprawdzić szkicu');return receipt;
}
async function exportDraft(){
 try{if(!$('draft-form').reportValidity())return;const draft=getDraft();const r=await validate(draft);
 const url=URL.createObjectURL(new Blob([JSON.stringify(draft,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`RockPro_${variant.id}_szkic.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);showResult('Wyeksportowano szkic. '+r.message);
 }catch(e){showResult(e.message,true);}
}
async function importDraft(file){
 try{if(file.size>32768)throw Error('Plik szkicu jest zbyt duży');const draft=JSON.parse(await file.text());await validate(draft);
 selectFamily(draft.family_id);selectVariant(draft.variant_id);
 ['x','y','z'].forEach((id,i)=>$(id).value=draft.internal_mm[i]);$('cover').value=draft.cover_height_mm??'';
 for(const id of ['opening','transport','notes'])$(id).value=draft[id];
 $('shelf-count').value=draft.sliding_shelves?.count??'';$('shelf-travel').value=draft.sliding_shelves?.requested_travel_mm??'';
 if(draft.preview){await workstation?.load();workstation?.restore(draft.preview);refreshPreviewControls();}
 remember();showResult('Wczytano szkic i sprawdzono jego powiązanie z katalogiem.');
 }catch(e){showResult(e.message,true);}finally{$('file').value='';}
}
async function init(){
 const response=await fetch('catalog.json');if(!response.ok)throw Error('Brak katalogu wzorców');catalog=await response.json();
 $('summary').textContent=`${catalog.family_count} kandydatów rodzin · ${catalog.reference_count} modeli · ${catalog.part_count} wystąpień części`;
 for(const f of catalog.families){const button=document.createElement('button');button.className='family';button.dataset.id=f.id;const box=document.createElement('span');const title=document.createElement('b');title.textContent=f.label;const sub=document.createElement('small');sub.textContent=f.variants.map(v=>v.id).join(' / ')+' · '+f.variants.length+' wzorzec / wariant';box.append(title,sub);button.append(box);button.onclick=()=>selectFamily(f.id);$('families').append(button);}
 $('variant').onchange=e=>selectVariant(e.target.value);
 for(const v of ['closed','inside'])$(v).onclick=()=>{mode3d=false;$('interactive').hidden=true;$('image-wrap').hidden=false;$('three').classList.remove('active');view=v;showImage();};
 $('three').onclick=show3d;
 for(const id of fields)$(id).addEventListener('input',()=>{remember();showResult('Szkic zmieniony — sprawdź go ponownie przed eksportem.');});
 $('draft-form').onsubmit=async e=>{e.preventDefault();try{const r=await validate(getDraft());showResult(r.message+'\nDo CAD brakuje: '+r.missing.join('; '));}catch(error){showResult(error.message,true);}};
 $('export').onclick=exportDraft;$('import').onclick=()=>$('file').click();$('file').onchange=()=>{if($('file').files[0])importDraft($('file').files[0]);};
 const requested=location.hash.slice(1);
 selectFamily(catalog.families.some(f=>f.id===requested)?requested:catalog.families[0].id);window.rockproStudio={getDraft,selectFamily,importDraft};
}
init().catch(error=>showResult(error.message,true));
