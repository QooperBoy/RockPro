import {ConceptView} from './wizard3d.js';
const $=id=>document.getElementById(id),token=location.pathname.split('/').filter(Boolean)[0];
let options,draft,storage={id:null,revision:0},step=1,view,timer,serial=0,dirty=false;
const localKey='rockpro.configurator.recovery.v1';
const labels={top:'Wieko górne',front:'Klapa przednia',rear:'Klapa tylna',left:'Pokrywa lewa',right:'Pokrywa prawa'};
function cover(face='top',kind='hinged'){return {id:crypto.randomUUID(),label:labels[face],face,depth_mm:face==='top'?45:40,kind,hinge_edge:'high',requires:[],height_override:false};}
function fresh(){return {schema:'rockpro.configurator/1',name:'Nowa skrzynia',type:'case',subtype:'top',internal_mm:[600,500,350],thickness_mm:9.8,joint_gap_mm:2,cooperation:'independent',covers:[cover()]};}
async function api(endpoint,data){const response=await fetch(endpoint,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-RockPro-Session':token},body:JSON.stringify(data)});const value=await response.json();if(!response.ok)throw Error(value.error||'Błąd połączenia ze Studio');return value;}
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
function stored(){try{localStorage.setItem(localKey,JSON.stringify({draft,storage,dirty}));}catch{status('Brak miejsca na awaryjny zapis w przeglądarce. Użyj zapisu draftu lub eksportu JSON.',true);}}
function saveLabel(){ $('save-state').textContent=(storage.id?`Draft · rewizja ${storage.revision}`:'Nowy draft')+(dirty?' · niezapisane zmiany':' · zapisany w bazie');if(!storage.id&&!dirty)$('save-state').textContent='Jeszcze niezapisany w bazie.';}
function changed(){dirty=true;saveLabel();stored();clearTimeout(timer);const version=++serial;timer=setTimeout(()=>updatePreview(version),220);}
function selectOptions(select,entries,value){select.replaceChildren(...entries.map(([id,label])=>new Option(label,id)));select.value=value;}
function fillSubtypes(type,value){selectOptions($('subtype'),options.types[type].subtypes.map(id=>[id,options.subtypes[id]]),value??options.types[type].subtypes[0]);}
function navigate(value){if(value>step&&step===1&&($('type').value!==draft.type||$('subtype').value!==draft.subtype))$('apply-type').click();if(value>step&&step===2&&Number($('cover-count').value)!==draft.covers.length)$('apply-count').click();step=Math.min(3,Math.max(1,value));editors();for(let i=1;i<=3;i++)$('step-'+i).hidden=i!==step;for(const b of $('steps').children)b.classList.toggle('active',Number(b.dataset.step)===step);$('previous').disabled=step===1;$('next').disabled=step===3;}
function input(label,value,type='text') {const l=document.createElement('label');l.append(document.createTextNode(label));const e=document.createElement('input');e.type=type;e.value=value;l.append(e);return [l,e];}
function select(label,entries,value){const l=document.createElement('label');l.append(document.createTextNode(label));const e=document.createElement('select');selectOptions(e,entries,value);l.append(e);return [l,e];}
function editors(){
 $('type-description').textContent=options.types[draft.type].label+' · '+options.subtypes[draft.subtype]+' · '+draft.covers.length+' pokryw. Układ nie zawiera jeszcze okuć.';
 $('cover-editors').replaceChildren();$('section-editors').replaceChildren();
 for(const [i,c] of draft.covers.entries()){
  const card=document.createElement('div');card.className='cover-card';const h=document.createElement('h3');h.textContent=`Sekcja ${i+1}`;card.append(h);
  const [nl,ni]=input('Nazwa sekcji',c.label);ni.maxLength=100;ni.oninput=()=>{c.label=ni.value;changed();};card.append(nl);
  const [fl,fi]=select('Ściana / płaszczyzna łączenia',Object.entries(options.faces),c.face);fi.onchange=()=>{c.face=fi.value;draft.subtype='custom';$('subtype').value='custom';editors();changed();};card.append(fl);
  const [kl,ki]=select('Sposób otwierania',[['hinged','Na zawiasach — ruch schematyczny'],['removable','Pokrywa zdejmowana']],c.kind);ki.onchange=()=>{c.kind=ki.value;draft.subtype='custom';$('subtype').value='custom';editors();changed();};card.append(kl);
  const [el,ei]=select(c.face==='top'?'Krawędź osi: przód / tył':'Krawędź osi: lewa / prawa w płaszczyźnie',[['low','Początek płaszczyzny'],['high','Koniec płaszczyzny']],c.hinge_edge);ei.disabled=c.kind!=='hinged';ei.onchange=()=>{c.hinge_edge=ei.value;changed();};card.append(el);
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
 $('name').value=draft.name;$('type').value=draft.type;fillSubtypes(draft.type,draft.subtype);$('cover-count').value=draft.covers.length;$('cooperation').value=draft.cooperation;
 ['x','y','z'].forEach((key,i)=>$('dim-'+key).value=draft.internal_mm[i]);$('thickness').value=draft.thickness_mm;$('gap').value=draft.joint_gap_mm;
 $('type-description').textContent=options.types[draft.type].label+' · '+options.subtypes[draft.subtype]+' · '+draft.covers.length+' pokryw. Układ nie zawiera jeszcze okuć.';
 editors();saveLabel();
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
  if(!view)view=new ConceptView($('viewport'));view.setModel(model);window.rockproWizardView=view;motionInputs();
  $('preview-title').textContent=draft.name;$('section-sizes').replaceChildren();$('topology').replaceChildren();
  for(const s of model.sections){const e=document.createElement('div');e.className='section-size';e.textContent=s.label;const detail=document.createElement('span');detail.textContent=s.size_mm.map(x=>Number(x.toFixed(2))).join(' × ')+' mm · '+(s.id==='body'?'korpus':options.faces[s.face]);e.append(detail);$('section-sizes').append(e);}
  for(const j of model.joints){const s=model.sections.find(s=>s.id===j.sections[1]),e=document.createElement('div');e.className='joint';e.textContent='Korpus ↔ '+s.label+' · '+options.faces[j.face]+(s.requires.length?' · po: '+s.requires.map(id=>model.sections.find(x=>x.id===id).label).join(', '):'');$('topology').append(e);}
  const bounds=[0,1,2].map(k=>Math.max(...model.sections.map(s=>s.position_mm[k]+s.size_mm[k]))-Math.min(...model.sections.map(s=>s.position_mm[k])));$('envelope').textContent='Gabaryt zamkniętego schematu: '+bounds.map(x=>Number(x.toFixed(2))).join(' × ')+' mm. Bez okuć, kół i profili.';
  status(model.sections.length+' sekcji · '+model.joints.length+' złączy · wnętrze '+draft.internal_mm.join(' × ')+' mm. Schemat poprawny.');
 }catch(e){if(version===serial)status('Nieaktualny podgląd — popraw dane: '+e.message,true);}
}
async function refreshList(){const rows=await api('wizard/drafts');selectOptions($('saved'),[['','Wybierz draft…'],...rows.map(r=>[r.id,r.name+' · rew. '+r.revision])],storage.id??'');}
function selectionPending(){return $('type').value!==draft.type||$('subtype').value!==draft.subtype||Number($('cover-count').value)!==draft.covers.length;}
async function save(asNew=false){
 if(selectionPending()){status('Najpierw zastosuj wybrany podtyp lub liczbę pokryw (albo przejdź Dalej).',true);return;}
 $('save').disabled=$('save-copy').disabled=true;
 const version=serial,sent=structuredClone(draft);
 try{const saved=await api('wizard/save',{draft:sent,id:asNew?null:storage.id,expected_revision:asNew?0:storage.revision});storage={id:saved.id,revision:saved.revision};dirty=version!==serial;saveLabel();stored();await refreshList();status('Zapisano draft w lokalnej bazie · rewizja '+saved.revision+(dirty?' · kolejne zmiany nadal niezapisane.':'.'));}
 catch(e){status(e.message,true);}finally{$('save').disabled=$('save-copy').disabled=false;}
}
async function load(saved){draft=saved.draft;storage={id:saved.id??null,revision:saved.revision??0};dirty=!storage.id;clearTimeout(timer);serial++;fill();stored();await updatePreview();}
async function init(){
 options=await api('wizard/options');selectOptions($('type'),Object.entries(options.types).map(([id,t])=>[id,t.label]),'case');
 draft=fresh();try{const recovery=JSON.parse(localStorage.getItem(localKey));if(recovery?.draft){await api('wizard/preview',recovery.draft);draft=recovery.draft;storage=recovery.storage;dirty=recovery.dirty;}}catch{}
 fill();await updatePreview();await refreshList();
 $('type').onchange=()=>fillSubtypes($('type').value);
 $('apply-type').onclick=()=>{const type=$('type').value,sub=$('subtype').value;draft.type=type;draft.subtype=sub;
  draft.covers=sub==='two_covers'?[cover('top'),cover('front','removable')]:sub==='double_front'?[cover('front'),cover('front')]:[cover(['front'].includes(sub)?'front':'top',sub==='hood'?'removable':'hinged')];
  if(sub==='hood')draft.covers[0].depth_mm=Math.max(2*draft.thickness_mm,draft.internal_mm[2]*.8);
  if(sub==='double_front'){draft.covers[0].hinge_edge='low';draft.covers[0].label='Drzwi lewe';draft.covers[1].label='Drzwi prawe';}
  draft.cooperation='independent';fill();changed();};
 $('apply-count').onclick=()=>{const n=Number($('cover-count').value);while(draft.covers.length<n)draft.covers.push(cover(['top','front','rear','left'][draft.covers.length]));draft.covers=draft.covers.slice(0,n);const ids=new Set(draft.covers.map(c=>c.id));for(const c of draft.covers)c.requires=c.requires.filter(id=>ids.has(id));draft.subtype='custom';fill();changed();};
 $('cooperation').onchange=()=>{draft.cooperation=$('cooperation').value;for(const c of draft.covers)c.requires=[];editors();changed();};
 $('name').oninput=()=>{draft.name=$('name').value;changed();};
 for(const [i,k] of ['x','y','z'].entries())$('dim-'+k).oninput=()=>{draft.internal_mm[i]=$('dim-'+k).value===''?null:Number($('dim-'+k).value);changed();};
 for(const [id,key]of[['thickness','thickness_mm'],['gap','joint_gap_mm']])$(id).oninput=()=>{draft[key]=$(id).value===''?null:Number($(id).value);changed();};
 for(const b of $('steps').children)b.onclick=()=>navigate(Number(b.dataset.step));$('previous').onclick=()=>navigate(step-1);$('next').onclick=()=>navigate(step+1);
 const mayReplace=()=>!dirty||confirm('Masz niezapisane zmiany. Zastąpić bieżący draft?');
 $('save').onclick=()=>save();$('save-copy').onclick=()=>save(true);$('load').onclick=async()=>{if(!$('saved').value||!mayReplace())return;try{const item=await api('wizard/drafts/'+$('saved').value);await load(item);}catch(e){status(e.message,true);}};
 $('new').onclick=()=>{if(mayReplace())load({draft:fresh()});};
 $('fit').onclick=()=>view?.fit();for(const [id,v]of[['open-all',100],['close-all',0]])$(id).onclick=()=>{view?.all(v);if(view)motionInputs();};
 $('export').onclick=async()=>{try{if(selectionPending())throw Error('Najpierw zastosuj podtyp lub liczbę pokryw.');await api('wizard/preview',draft);const url=URL.createObjectURL(new Blob([JSON.stringify(draft,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='RockPro_koncepcja.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){status(e.message,true);}};
 $('import').onclick=()=>$('file').click();$('file').onchange=async()=>{try{const f=$('file').files[0];if(!f)return;if(f.size>32768)throw Error('Maksymalny rozmiar draftu to 32 KB');const value=JSON.parse(await f.text());await api('wizard/preview',value);if(!mayReplace())return;await load({draft:value});status('Wczytano JSON jako nowy draft. Zapisz go, aby zachować w bazie.');}catch(e){status(e.message,true);}finally{$('file').value='';}};
 window.rockproWizard={getDraft:()=>structuredClone(draft),getStorage:()=>({...storage}),preview:()=>updatePreview(),load,save,navigate};
}
init().catch(e=>status('Nie można uruchomić kreatora: '+e.message,true));
