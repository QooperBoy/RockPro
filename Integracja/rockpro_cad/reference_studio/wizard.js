import {icon} from './viewport-ui.js';
import {ConceptView} from './wizard3d.js';
import {PartsPicker} from './parts-picker.js';
import {PlacementEditor} from './placement-editor.js';
import {ClosureEditor} from './closure-editor.js';
import {PlacementView} from './placement3d.js';
const $=id=>document.getElementById(id),token=location.pathname.split('/').filter(Boolean)[0];
let options,draft,storage={id:null,revision:0},step=1,view,timer,serial=0,dirty=false,pendingLegacy=null,partsPicker=null,placementEditor=null,placementView=null,closureEditor=null,partsCatalog;
const localKey='rockpro.configurator.recovery.v3';
const labels={top:'Wieko górne',front:'Klapa przednia',rear:'Klapa tylna',left:'Pokrywa lewa',right:'Pokrywa prawa'};
function cover(face='top',kind='hinged'){return {id:crypto.randomUUID(),label:labels[face],face,depth_mm:face==='top'?45:40,kind,hinge_edge:'high',requires:[],height_override:false};}
function fresh(){return {schema:'rockpro.configurator/3',name:'Nowa skrzynia',type:'case',internal_mm:[600,500,350],thickness_mm:9.8,cooperation:'independent',covers:[cover()],hardware:[],placements:[]};}
async function api(endpoint,data){const response=await fetch(endpoint,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-RockPro-Session':token},body:JSON.stringify(data)});const value=await response.json();if(!response.ok)throw Error(value.error||'Błąd połączenia ze Studio');return value;}
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
function stored(){try{localStorage.setItem(localKey,JSON.stringify({draft,storage,dirty}));}catch{status('Brak miejsca na awaryjny zapis w przeglądarce. Użyj zapisu draftu lub eksportu JSON.',true);}}
function saveLabel(){ $('save-state').textContent=(storage.id?`Draft · rewizja ${storage.revision}`:'Nowy draft')+(dirty?' · niezapisane zmiany':' · zapisany w bazie');if(!storage.id&&!dirty)$('save-state').textContent='Jeszcze niezapisany w bazie.';}
function changed(){dirty=true;placementView?.setEnabled(false);saveLabel();stored();clearTimeout(timer);const version=++serial;timer=setTimeout(()=>updatePreview(version),220);}
function selectOptions(select,entries,value){select.replaceChildren(...entries.map(([id,label])=>new Option(label,id)));select.value=value;}
function processUI(){
 const names=['','Konstrukcja','Wieka i współpraca','Wymiary sekcji','Części i okucia','Uchwyty i ścianki','Zatrzaski i zawiasy'];
 $('process-caption').textContent='Etap '+step+' z 6 · '+names[step];$('process-progress').value=step;
 for(const b of $('steps').children){b.setAttribute('aria-current',Number(b.dataset.step)===step?'step':'false');b.classList.toggle('earlier',Number(b.dataset.step)<step);}
 if(view?.model)view.chrome.setContext(step,view.model);
}
function navigate(value){placementView?.setPart(null);if(value>step&&step===1&&$('type').value!==draft.type)$('apply-type').click();step=Math.min(6,Math.max(1,value));editors();for(let i=1;i<=6;i++)$('step-'+i).hidden=i!==step;for(const b of $('steps').children)b.classList.toggle('active',Number(b.dataset.step)===step);$('previous').disabled=step===1;$('next').disabled=step===6;processUI();placementView?.setEnabled(step>=5&&JSON.stringify(view.model.draft)===JSON.stringify(draft));}

function input(label,value,type='text') {const l=document.createElement('label');l.append(document.createTextNode(label));const e=document.createElement('input');e.type=type;e.value=value;l.append(e);return [l,e];}
function select(label,entries,value){const l=document.createElement('label');l.append(document.createTextNode(label));const e=document.createElement('select');e.setAttribute('aria-label',label);selectOptions(e,entries,value);l.append(e);return [l,e];}
function editors(){
 $('type-description').textContent=options.types[draft.type].description;
 $('cooperation-field').hidden=draft.covers.length===1;
 $('cover-editors').replaceChildren();$('section-editors').replaceChildren();
 for(const [i,c] of draft.covers.entries()){
  const card=document.createElement('div');card.className='cover-card';const h=document.createElement('h3');h.textContent=`Sekcja ${i+1}`;card.append(h);
  const [nl,ni]=input('Nazwa sekcji',c.label);ni.maxLength=100;ni.oninput=()=>{c.label=ni.value;changed();};card.append(nl);
  const face=document.createElement('p');face.className='hint';face.textContent='Płaszczyzna łączenia: '+options.faces[c.face];card.append(face);
  if(draft.type==='cabinet'||draft.type==='case'){
   const modes=draft.type==='case'?[['hinged','Wieko otwierane na zawiasach'],['removable','Wieko zdejmowane']]:[['hinged','Otwierana na zawiasach'],['removable','Powłoka zdejmowana']];
   const [kl,ki]=select('Sposób otwierania',modes,c.kind);ki.onchange=()=>{c.kind=ki.value;editors();changed();};card.append(kl);
  }else{const kind=document.createElement('p');kind.className='hint';kind.textContent=c.kind==='hinged'?'Wieko na zawiasach po jednej stronie':'Pokrywa zdejmowana';card.append(kind);}
  if(c.kind==='hinged'){
   const [el,ei]=select(c.face==='top'?'Strona zawiasów':'Strona zawiasów powłoki przedniej',c.face==='top'?[['low','Przód'],['high','Tył']]:[['low','Lewa'],['high','Prawa']],c.hinge_edge);ei.onchange=()=>{c.hinge_edge=ei.value;changed();};card.append(el);
  }
  if(draft.cooperation==='custom'){
   const [rl,ri]=select('Otwórz dopiero po',[['','Bez poprzednika'],...draft.covers.filter(x=>x.id!==c.id).map(x=>[x.id,x.label])],c.requires[0]??'');ri.onchange=()=>{c.requires=ri.value?[ri.value]:[];changed();};card.append(rl);
  }
  $('cover-editors').append(card);
  const [dl,di]=input(c.label+' — '+(c.face==='top'?'wysokość pokrywy':'głębokość pokrywy')+' [mm]',c.depth_mm,'number');di.min=2*draft.thickness_mm;di.max=3000;di.step='any';di.dataset.cover=c.id;di.oninput=()=>{c.depth_mm=di.value===''?null:Number(di.value);changed();};$('section-editors').append(dl);
  if(c.face==='top'&&c.kind==='hinged'){
   const l=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.checked=c.height_override;check.onchange=()=>{c.height_override=check.checked;changed();};l.className='override';l.append(check,document.createTextNode('Odstępstwo konstruktora: zezwalam na wieko wyższe niż 15% korpusu'));$('section-editors').append(l);
  }
 }
}
function fill(){
 draft.hardware??=[];draft.placements??=[];
 $('name').value=draft.name;$('type').value=draft.type;$('cooperation').value=draft.cooperation;
 ['x','y','z'].forEach((key,i)=>$('dim-'+key).value=draft.internal_mm[i]);$('thickness').value=draft.thickness_mm;
 $('type-description').textContent=options.types[draft.type].description;
 editors();partsPicker?.setSelection(draft.hardware??[]);saveLabel();
}
function motionInputs(){
 $('motions').replaceChildren();for(const s of view.model.sections.slice(1)){
  const l=document.createElement('label');l.className='motion';const text=document.createElement('span');text.textContent=s.label;const out=document.createElement('output');out.textContent=Math.round(view.values[s.id])+'%';
  const range=document.createElement('input');range.type='range';range.min=0;range.max=100;range.value=view.values[s.id];range.dataset.section=s.id;range.setAttribute('aria-label','Otwarcie: '+s.label);
  range.oninput=()=>{try{view.setMotion(s.id,Number(range.value));motionInputs();status('Podgląd koncepcji · ruchy prezentacyjne, bez doboru zawiasu.');}catch(e){range.value=view.values[s.id];status(e.message,true);}};
  l.append(text,out,range);$('motions').append(l);
 }
}
async function updatePreview(version=++serial){
 try{const model=await api('wizard/preview',draft);if(version!==serial)return;
  if(!view)view=new ConceptView($('viewport'));
  if(!placementView)placementView=new PlacementView(view,hit=>placementEditor.drop(hit),id=>{const g=draft.placements.find(g=>g.id===id);if(g?.pattern==='closure_line'){navigate(6);closureEditor.selectGroup(id);}else placementEditor.selectGroup(id);},message=>status(message),hit=>placementEditor.candidate(hit));
  const sameLayout=view.model&&JSON.stringify(view.model.panels)===JSON.stringify(model.panels)&&JSON.stringify(view.model.sections)===JSON.stringify(model.sections);
  if(sameLayout)view.model=model;else view.setModel(model);window.rockproWizardView=view;motionInputs();
  placementEditor.setModel(model);closureEditor.setModel(model);placementView.setEnabled(step>=5);
  await placementView.update(model,partsCatalog,step===6?closureEditor.selected:placementEditor.selected);if(version!==serial)return;
  window.rockproPlacementView=placementView;processUI();
  $('placement-summary').textContent=model.placement.instance_count+' wystąpień w koncepcji · '+(draft.placements?.length??0)+' grup'+(model.placement.unresolved_groups.length?' · grupy bez docelowej ścianki: '+model.placement.unresolved_groups.length:'')+'.';
  partsPicker.renderSummary($('hardware-summary'),model.hardware_summary);
  $('joint-fit-status').textContent=model.hardware_summary.definition_count?'do ustalenia po rozmieszczeniu i potwierdzeniu danych montażowych':'do ustalenia po wyborze okucia';
  $('preview-title').textContent=draft.name;$('section-sizes').replaceChildren();$('topology').replaceChildren();
  for(const s of model.sections){const e=document.createElement('div');e.className='section-size';e.textContent=s.label;const detail=document.createElement('span');detail.textContent=s.size_mm.map(x=>Number(x.toFixed(2))).join(' × ')+' mm · '+(s.id==='body'?'korpus':options.faces[s.face]);e.append(detail);$('section-sizes').append(e);}
  for(const j of model.joints){const s=model.sections.find(s=>s.id===j.sections[1]),e=document.createElement('div');e.className='joint';e.textContent='Korpus ↔ '+s.label+' · '+options.faces[j.face]+' · szczelina i docięcie sklejki: wymagają danych montażowych'+(s.requires.length?' · po: '+s.requires.map(id=>model.sections.find(x=>x.id===id).label).join(', '):'');$('topology').append(e);}
  const bounds=[0,1,2].map(k=>Math.max(...model.sections.map(s=>s.position_mm[k]+s.size_mm[k]))-Math.min(...model.sections.map(s=>s.position_mm[k])));$('envelope').textContent='Gabaryt zamkniętego schematu: '+bounds.map(x=>Number(x.toFixed(2))).join(' × ')+' mm. Nominalny gabaryt bez okuć, kół i profili; dopasowanie złączy nie powiększa tych wymiarów.';
  status(model.sections.length+' sekcji · '+model.joints.length+' złączy · wnętrze '+draft.internal_mm.join(' × ')+' mm. Schemat poprawny.');
 }catch(e){if(version===serial){placementView?.setEnabled(false);status('Nieaktualny podgląd — popraw dane: '+e.message,true);}}
}
async function refreshList(){const rows=await api('wizard/drafts');selectOptions($('saved'),[['','Wybierz draft…'],...rows.map(r=>[r.id,r.name+' · rew. '+r.revision])],storage.id??'');}
function selectionPending(){return $('type').value!==draft.type;}
async function save(asNew=false){
 if(selectionPending()){status('Najpierw zastosuj wybrany typ (albo przejdź Dalej).',true);return;}
 $('save').disabled=$('save-copy').disabled=$('save-top').disabled=true;$('save-top').setAttribute('aria-busy','true');
 const version=serial,sent=structuredClone(draft);
 try{const saved=await api('wizard/save',{draft:sent,id:asNew?null:storage.id,expected_revision:asNew?0:storage.revision});storage={id:saved.id,revision:saved.revision};dirty=version!==serial;saveLabel();stored();await refreshList();status('Zapisano draft w lokalnej bazie · rewizja '+saved.revision+(dirty?' · kolejne zmiany nadal niezapisane.':'.'));}
 catch(e){status(e.message,true);}finally{$('save').disabled=$('save-copy').disabled=$('save-top').disabled=false;$('save-top').setAttribute('aria-busy','false');}
}
function showLegacy(value){pendingLegacy=structuredClone(value);$('legacy-notice').hidden=false;status('Archiwalny draft zachowany. Możesz pobrać jego oryginalny JSON lub jawnie utworzyć nowy draft w obecnych typach.',true);}
async function load(saved){
 try{await api('wizard/preview',saved.draft);}catch(e){if(['rockpro.configurator/1','rockpro.configurator/2'].includes(saved.draft?.schema)){showLegacy(saved.draft);return false;}throw e;}
 draft=saved.draft;storage={id:saved.id??null,revision:saved.revision??0};dirty=!storage.id;pendingLegacy=null;$('legacy-notice').hidden=true;clearTimeout(timer);serial++;fill();stored();await updatePreview();return true;
}
function download(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

async function init(){
 options=await api('wizard/options');partsCatalog=await api('wizard/parts');partsPicker=new PartsPicker($('parts-library'),partsCatalog,refs=>{const ids=new Set(refs.map(r=>r.part_id)),affected=(draft.placements??[]).filter(g=>!ids.has(g.part_id)||(g.mate_part_id&&!ids.has(g.mate_part_id)));if(affected.length&&!confirm('Usunięcie części z wyboru usunie także jej grupy rozmieszczenia ('+affected.length+'). Kontynuować?')){partsPicker.setSelection(draft.hardware);return;}draft.placements=(draft.placements??[]).filter(g=>ids.has(g.part_id)&&(!g.mate_part_id||ids.has(g.mate_part_id)));draft.hardware=refs;changed();});selectOptions($('type'),Object.entries(options.types).map(([id,t])=>[id,t.label]),'case');
 placementEditor=new PlacementEditor($('placement-editor'),partsCatalog,()=>draft,changed,id=>placementView?.select(id),id=>placementView?.setPart(id),message=>status(message));
 closureEditor=new ClosureEditor($('closure-editor'),partsCatalog,()=>draft,changed,id=>placementView?.select(id));
 draft=fresh();try{const recovery=JSON.parse(localStorage.getItem(localKey));if(recovery?.draft){await api('wizard/preview',recovery.draft);draft=recovery.draft;storage=recovery.storage;dirty=recovery.dirty;}}catch{}
 fill();await updatePreview();await refreshList();
 try{if(!localStorage.getItem(localKey)){const old=JSON.parse(localStorage.getItem('rockpro.configurator.recovery.v2')||localStorage.getItem('rockpro.configurator.recovery.v1'));if(old?.draft)showLegacy(old.draft);}}catch{}
 $('type').onchange=()=>status('Wybrany typ zostanie zastosowany przyciskiem „Zastosuj typ” lub „Dalej”.');
 $('apply-type').onclick=()=>{draft.type=$('type').value;draft.covers=options.types[draft.type].covers.map(([face,kind])=>cover(face,kind));draft.cooperation='independent';fill();changed();};
 $('legacy-convert').onclick=async()=>{try{const converted=await api('wizard/convert',pendingLegacy);await load({draft:converted});status('Utworzono nowy, niezapisany draft bez ręcznej szczeliny. Złącza wymagają doboru okucia. Oryginał pozostał zachowany.');}catch(e){status(e.message,true);}};
 $('legacy-export').onclick=()=>download(pendingLegacy,'RockPro_draft_archiwalny.json');
 $('cooperation').onchange=()=>{draft.cooperation=$('cooperation').value;for(const c of draft.covers)c.requires=[];editors();changed();};
 $('name').oninput=()=>{draft.name=$('name').value;changed();};
 for(const [i,k] of ['x','y','z'].entries())$('dim-'+k).oninput=()=>{draft.internal_mm[i]=$('dim-'+k).value===''?null:Number($('dim-'+k).value);changed();};
 for(const [id,key]of[['thickness','thickness_mm']])$(id).oninput=()=>{draft[key]=$(id).value===''?null:Number($(id).value);changed();};
 for(const b of $('steps').children)b.onclick=()=>navigate(Number(b.dataset.step));$('previous').onclick=()=>navigate(step-1);$('next').onclick=()=>navigate(step+1);
 const mayReplace=()=>!dirty||confirm('Masz niezapisane zmiany. Zastąpić bieżący draft?');
 $('save').onclick=()=>save();$('save-copy').onclick=()=>save(true);$('load').onclick=async()=>{if(!$('saved').value||!mayReplace())return;try{const item=await api('wizard/drafts/'+$('saved').value);await load(item);}catch(e){status(e.message,true);}};
 const startClean=async()=>{
  if(!mayReplace())return;
  placementView?.cancelDrag();placementView?.setPart(null);
  placementEditor.selected=placementEditor.part=placementEditor.defaults=null;
  closureEditor.selected=closureEditor.part=closureEditor.defaults=null;
  partsPicker.search.value=partsPicker.category.value=partsPicker.source.value='';partsPicker.only.checked=false;
  await load({draft:fresh()});navigate(1);status('Nowa czysta skrzynia — części i rozmieszczenie wyczyszczone. Zapisane projekty pozostają w bazie.');
 };
 $('new').onclick=$('new-clean').onclick=startClean;
 document.addEventListener('rockpro:stop-placement',()=>{placementView?.cancelDrag();placementView?.setPart(null);});
 $('save-top').prepend(icon('save'));$('save-top').onclick=()=>$('save').click();
 for(const b of $('steps').children){const n=b.dataset.step,title=b.querySelector('span');b.replaceChildren(Object.assign(document.createElement('span'),{className:'step-number',textContent:n}),title);}
 $('fit').onclick=()=>view?.chrome.frame();for(const [id,v]of[['open-all',100],['close-all',0]])$(id).onclick=()=>{view?.all(v);if(view)motionInputs();};
 $('export').onclick=async()=>{try{if(selectionPending())throw Error('Najpierw zastosuj wybrany typ.');await api('wizard/preview',draft);download(draft,'RockPro_koncepcja.json');}catch(e){status(e.message,true);}};
 $('import').onclick=()=>$('file').click();$('file').onchange=async()=>{try{const f=$('file').files[0];if(!f)return;if(f.size>32768)throw Error('Maksymalny rozmiar draftu to 32 KB');const value=JSON.parse(await f.text());if(!mayReplace())return;if(await load({draft:value}))status('Wczytano JSON jako nowy draft. Zapisz go, aby zachować w bazie.');}catch(e){status(e.message,true);}finally{$('file').value='';}};
 window.rockproWizard={getDraft:()=>structuredClone(draft),getStorage:()=>({...storage}),preview:()=>updatePreview(),load,save,navigate};
}
init().catch(e=>status('Nie można uruchomić kreatora: '+e.message,true));
