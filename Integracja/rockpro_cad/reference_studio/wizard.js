import {ProcessPanel} from './process-panel.js';
import {StructureView} from './structure3d.js';
import {ReviewPanel} from './review-panel.js';
import {icon} from './viewport-ui.js';
import {ConceptView} from './wizard3d.js';
import {PartsPicker} from './parts-picker.js';
import {PlacementEditor} from './placement-editor.js';
import {ClosureEditor} from './closure-editor.js';
import {PlacementView} from './placement3d.js';
const $=id=>document.getElementById(id),token=location.pathname.split('/').filter(Boolean)[0];
let options,draft,storage={id:null,revision:0},step=1,view,timer,serial=0,dirty=false,saving=false,pendingLegacy=null,partsPicker=null,placementEditor=null,placementView=null,closureEditor=null,partsCatalog,processPanel;
const queryDraft=new URLSearchParams(location.search).get('draft');
let requestedDraft=/^[0-9a-f]{32}$/.test(queryDraft??'')?queryDraft:null;
let localKey='rockpro.configurator.recovery.v3'+(requestedDraft?'.'+requestedDraft:'');
let uiKey='rockpro.studio.context.'+token+(requestedDraft?'.'+requestedDraft:'');
function projectLocation(id){
 requestedDraft=id;localKey='rockpro.configurator.recovery.v3'+(id?'.'+id:'');uiKey='rockpro.studio.context.'+token+(id?'.'+id:'');
 const url=new URL(location.href);if(id)url.searchParams.set('draft',id);else url.searchParams.delete('draft');
 try{history.replaceState(null,'',url);}catch{}
 for(const a of document.querySelectorAll('.app-sidebar a')){const link=new URL(a.href);if(id)link.searchParams.set('draft',id);else link.searchParams.delete('draft');a.href=link.href;}
}
const storagePlace=()=>document.body.dataset.storageMode==='browser'?'tej przeglądarce':'lokalnej bazie';
function actionFeedback(message,error=false){$('action-feedback').hidden=false;$('action-feedback').textContent=message;$('action-feedback').classList.toggle('error',error);}
function rememberContext(){
 if(!draft||!view?.model)return;stored();
 try{sessionStorage.setItem(uiKey,JSON.stringify({name:draft.name,project:storage.id,step,position:view.camera.position.toArray(),target:view.controls.target.toArray(),motion:view.values,placement:placementEditor.selected,closure:closureEditor.selected,part:placementEditor.part,closurePart:closureEditor.part,filters:{search:partsPicker.search.value,category:partsPicker.category.value,source:partsPicker.source.value,only:partsPicker.only.checked,favorites:partsPicker.favoritesOnly.checked,sort:partsPicker.sort.value}}));}catch{}
}
function restoreContext(){
 try{const c=JSON.parse(sessionStorage.getItem(uiKey));if(!c||c.name!==draft.name||c.project!==storage.id)return;
  navigate(Number.isInteger(c.step)?c.step:1);
  if(c.part&&draft.hardware.some(r=>r.part_id===c.part)){placementEditor.part=c.part;placementEditor.render();}
  if(c.closurePart&&draft.hardware.some(r=>r.part_id===c.closurePart)){closureEditor.part=c.closurePart;closureEditor.render();}
  if(c.placement)placementEditor.selectGroup(c.placement);if(c.closure)closureEditor.selectGroup(c.closure);
  const vector=a=>Array.isArray(a)&&a.length===3&&a.every(x=>typeof x==='number'&&Number.isFinite(x)&&Math.abs(x)<1e6);
  if(vector(c.position)&&vector(c.target)&&Math.hypot(...c.position.map((x,k)=>x-c.target[k]))>.001){view.camera.position.fromArray(c.position);view.controls.target.fromArray(c.target);view.controls.update();}
  for(let pass=0;pass<draft.covers.length;pass++)for(const [id,value]of Object.entries(c.motion??{})){if(view.values[id]!==undefined&&typeof value==='number'&&value>=0&&value<=100)try{view.setMotion(id,value);}catch{}}motionInputs();
  if(c.filters){partsPicker.search.value=String(c.filters.search??'');partsPicker.category.value=c.filters.category??'';partsPicker.source.value=c.filters.source??'';partsPicker.only.checked=c.filters.only===true;partsPicker.favoritesOnly.checked=c.filters.favorites===true;partsPicker.sort.value=['recommended','frequent','name'].includes(c.filters.sort)?c.filters.sort:'recommended';partsPicker.render();}
 }catch{}
}

let structureView=null,reviewPanel=null;
const labels={top:'Wieko górne',front:'Klapa przednia',rear:'Klapa tylna',left:'Pokrywa lewa',right:'Pokrywa prawa'};
function cover(face='top',kind='hinged'){return {id:crypto.randomUUID(),label:labels[face],face,depth_mm:face==='top'?45:40,kind,hinge_edge:'high',requires:[],height_override:false};}
function fresh(){return {schema:'rockpro.configurator/3',name:'Nowa skrzynia',type:'case',internal_mm:[600,500,350],thickness_mm:9.8,cooperation:'independent',covers:[cover()],hardware:[],placements:[]};}
async function api(endpoint,data){const response=await fetch(endpoint,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-RockPro-Session':token},body:JSON.stringify(data)});const value=await response.json();if(!response.ok)throw Error(value.error||'Błąd połączenia ze Studio');return value;}
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
function stored(){try{localStorage.setItem(localKey,JSON.stringify({draft,storage,dirty}));}catch{status('Brak miejsca na awaryjny zapis w przeglądarce. Użyj zapisu draftu lub eksportu JSON.',true);}}
function saveLabel(){ $('save-state').textContent=(storage.id?`Draft · rewizja ${storage.revision}`:'Nowy draft')+(dirty?' · niezapisane zmiany':' · zapisany w '+storagePlace());if(!storage.id&&!dirty)$('save-state').textContent='Jeszcze niezapisany.';}
function changed(){dirty=true;reviewPanel?.invalidate();document.dispatchEvent(new CustomEvent('rockpro:preview-pending'));placementView?.setEnabled(false);saveLabel();stored();clearTimeout(timer);const version=++serial;timer=setTimeout(()=>{updatePreview(version);if(step===8)reviewPanel?.check();},220);}
function selectOptions(select,entries,value){select.replaceChildren(...entries.map(([id,label])=>new Option(label,id)));select.value=value;}
function processUI(){
 const names=['','Konstrukcja','Wieka i współpraca','Wymiary sekcji','Części i okucia','Uchwyty i ścianki','Zatrzaski i zawiasy','Konstrukcja i podstawa','Kontrola projektu'];
 $('process-caption').textContent='Etap '+step+' z 8 · '+names[step];$('process-progress').value=step;const mobileStep=document.querySelector('.mobile-step');if(mobileStep)mobileStep.value=String(step);
 for(const b of $('steps').children){b.setAttribute('aria-current',Number(b.dataset.step)===step?'step':'false');b.classList.toggle('earlier',Number(b.dataset.step)<step);}
 if(view?.model)view.chrome.setContext(step,view.model);
 document.dispatchEvent(new CustomEvent('rockpro:step-changed',{detail:step}));
}
function navigate(value){placementView?.setPart(null);if(value>step&&step===1&&$('type').value!==draft.type)$('apply-type').click();step=Math.min(8,Math.max(1,value));editors();for(let i=1;i<=8;i++)$('step-'+i).hidden=i!==step;for(const b of $('steps').children)b.classList.toggle('active',Number(b.dataset.step)===step);$('previous').disabled=step===1;$('next').disabled=saving;$('next').textContent=step===8?'Zapisz draft':step===7?'Sprawdź projekt →':'Dalej →';$('download-final').hidden=step<7;processUI();placementView?.setEnabled(step>=5&&step<=7&&JSON.stringify(view?.model?.draft)===JSON.stringify(draft));if(step===8)reviewPanel?.check();}
function goToIssue(issue){
 const group=draft.placements?.find(g=>g.id===issue.group_id);navigate(group?(group.pattern==='closure_line'?6:5):issue.step);
 if(group){if(group.pattern==='closure_line')closureEditor.selectGroup(group.id);else placementEditor.selectGroup(group.id);placementView?.select(group.id);}
 else if(issue.part_id&&draft.hardware.some(r=>r.part_id===issue.part_id)){if(issue.step===5)placementEditor.choosePart(issue.part_id);else if(issue.step===6){closureEditor.part=issue.part_id;closureEditor.defaults=null;closureEditor.render();}}
 document.querySelector('#step-'+issue.step+' h1')?.scrollIntoView({block:'nearest'});
}

function input(label,value,type='text') {const l=document.createElement('label');l.append(document.createTextNode(label));const e=document.createElement('input');e.type=type;e.value=value;l.append(e);return [l,e];}
function select(label,entries,value){const l=document.createElement('label');l.append(document.createTextNode(label));const e=document.createElement('select');e.setAttribute('aria-label',label);selectOptions(e,entries,value);l.append(e);return [l,e];}
function editors(){

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
 $('construction-wheels').checked=draft.construction?.wheels??true;$('construction-stacking').checked=draft.construction?.stacking??true;
 $('name').value=draft.name;$('type').value=draft.type;$('cooperation').value=draft.cooperation;
 ['x','y','z'].forEach((key,i)=>$('dim-'+key).value=draft.internal_mm[i]);$('thickness').value=draft.thickness_mm;

 editors();partsPicker?.setSelection(draft.hardware??[]);saveLabel();
}
function motionInputs(){
 if(!$('motions'))return;
 $('motions').replaceChildren();for(const s of view.model.sections.slice(1)){
  const l=document.createElement('label');l.className='motion';const text=document.createElement('span');text.textContent=s.label;const out=document.createElement('output');out.textContent=Math.round(view.values[s.id])+'%';
  const range=document.createElement('input');range.type='range';range.min=0;range.max=100;range.value=view.values[s.id];range.dataset.section=s.id;range.setAttribute('aria-label','Otwarcie: '+s.label);
  range.oninput=()=>{try{view.setMotion(s.id,Number(range.value));motionInputs();status('Podgląd koncepcji · ruchy prezentacyjne, bez doboru zawiasu.');}catch(e){range.value=view.values[s.id];status(e.message,true);}};
  l.append(text,out,range);$('motions').append(l);
 }
}
async function updatePreview(version=++serial){
 processPanel?.clearLayer();
 try{const model=await api('wizard/preview',draft);if(version!==serial)return;
  if(!view)view=new ConceptView($('viewport'));
  if(!placementView)placementView=new PlacementView(view,hit=>placementEditor.drop(hit),id=>{const g=draft.placements.find(g=>g.id===id);if(g?.pattern==='closure_line'){navigate(6);closureEditor.selectGroup(id);}else placementEditor.selectGroup(id);},message=>status(message),hit=>placementEditor.candidate(hit));
  const sameLayout=view.model&&JSON.stringify(view.model.panels)===JSON.stringify(model.panels)&&JSON.stringify(view.model.sections)===JSON.stringify(model.sections);
  if(sameLayout)view.model=model;else view.setModel(model);window.rockproWizardView=view;motionInputs();
  placementEditor.setModel(model);closureEditor.setModel(model);placementView.setEnabled(step>=5);
  await placementView.update(model,partsCatalog,step===6?closureEditor.selected:placementEditor.selected);if(version!==serial)return;
  if(!structureView)structureView=new StructureView(view);await structureView.update(model,partsCatalog);if(version!==serial)return;window.rockproStructureView=structureView;
  window.rockproPlacementView=placementView;processUI();processPanel?.applyLayer();
  $('placement-summary').textContent=model.placement.instance_count+' wystąpień w koncepcji · '+(draft.placements?.length??0)+' grup'+(model.placement.unresolved_groups.length?' · grupy bez docelowej ścianki: '+model.placement.unresolved_groups.length:'')+'.';
  partsPicker.renderSummary($('hardware-summary'),model.hardware_summary);
  renderConstruction(model);
  document.dispatchEvent(new CustomEvent('rockpro:preview',{detail:model}));
  $('joint-fit-status').textContent=model.hardware_summary.definition_count?'do ustalenia po rozmieszczeniu i potwierdzeniu danych montażowych':'do ustalenia po wyborze okucia';
  $('preview-title').textContent=draft.name;$('preview-title').title=draft.name;$('section-sizes').replaceChildren();
  for(const s of model.sections){const e=document.createElement('div');e.className='section-size';e.textContent=s.label;const detail=document.createElement('span');detail.textContent=s.size_mm.map(x=>Number(x.toFixed(2))).join(' × ')+' mm · '+(s.id==='body'?'korpus':options.faces[s.face]);e.append(detail);$('section-sizes').append(e);}
  status(model.sections.length+' sekcji · '+model.joints.length+' złączy · wnętrze '+draft.internal_mm.join(' × ')+' mm. Schemat poprawny.');
 }catch(e){if(version===serial){placementView?.setEnabled(false);status('Nieaktualny podgląd — popraw dane: '+e.message,true);}}
}
async function refreshList(){const rows=await api('wizard/drafts');selectOptions($('saved'),[['','Wybierz draft…'],...rows.map(r=>[r.id,r.name+' · rew. '+r.revision])],storage.id??'');}
function selectionPending(){return $('type').value!==draft.type;}
async function save(asNew=false){
 if(saving)return null;
 if(step===8&&reviewPanel?.report?.data_valid===false){actionFeedback('Popraw błędy danych wskazane w kontroli przed zapisem. Kopię JSON możesz pobrać w każdej chwili.',true);return null;}
 if(selectionPending()){actionFeedback('Najpierw zastosuj wybrany typ (albo przejdź Dalej).',true);return null;}
 saving=true;$('next').disabled=true;actionFeedback('Zapisywanie projektu…');
 $('save').disabled=$('save-copy').disabled=$('save-top').disabled=true;$('save-top').setAttribute('aria-busy','true');
 const version=serial,sent=structuredClone(draft);
 try{const saved=await api('wizard/save',{draft:sent,id:asNew?null:storage.id,expected_revision:asNew?0:storage.revision});storage={id:saved.id,revision:saved.revision};dirty=version!==serial;projectLocation(saved.id);saveLabel();stored();document.dispatchEvent(new CustomEvent('rockpro:project-saved'));try{await refreshList();}catch{}const message='Zapisano projekt w '+storagePlace()+' · rewizja '+saved.revision+(dirty?' · nowsze zmiany czekają na zapis.':'. Możesz teraz pobrać projekt JSON.');status(message);actionFeedback(message);return saved;}
 catch(e){status(e.message,true);actionFeedback('Nie zapisano projektu: '+e.message+' Możesz pobrać kopię JSON.',true);return null;}finally{saving=false;$('next').disabled=$('save').disabled=$('save-copy').disabled=$('save-top').disabled=false;$('save-top').setAttribute('aria-busy','false');}
}
function showLegacy(value){pendingLegacy=structuredClone(value);$('legacy-notice').hidden=false;status('Archiwalny draft zachowany. Możesz pobrać jego oryginalny JSON lub jawnie utworzyć nowy draft w obecnych typach.',true);}
async function load(saved){
 processPanel?.clearLayer();
 try{await api('wizard/preview',saved.draft);}catch(e){if(['rockpro.configurator/1','rockpro.configurator/2'].includes(saved.draft?.schema)){showLegacy(saved.draft);return false;}throw e;}
 draft=saved.draft;storage={id:saved.id??null,revision:saved.revision??0};dirty=!storage.id;projectLocation(storage.id);reviewPanel?.invalidate();pendingLegacy=null;$('legacy-notice').hidden=true;clearTimeout(timer);serial++;fill();stored();await updatePreview();if(step===8)reviewPanel?.check();processPanel?.refresh();return true;
}
function download(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.hidden=true;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
function exportDraft(){
 try{if(selectionPending())throw Error('Najpierw zastosuj wybrany typ.');if(!draft)throw Error('Projekt nie został jeszcze wczytany.');
  const name=(draft.name||'projekt').replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').slice(0,100);
  download(draft,'RockPro_'+name+'.json');actionFeedback('Rozpoczęto pobieranie projektu JSON. Plik znajdziesz w pobranych plikach przeglądarki.');
 }catch(e){actionFeedback(e.message,true);}
}

function renderConstruction(model){
 const customKit=Boolean(draft.construction?.kit),supported=draft.type==='case';for(const id of ['construction-wheels','construction-stacking','construction-apply'])$(id).disabled=!supported||customKit;
 $('construction-help').textContent=supported?'Zestaw profili i okuć dla skrzyni z jednym górnym wiekiem o wysokości minimum 110 mm.':'Automatyczny zestaw profili jest obecnie dostępny dla T1. Ten projekt możesz zapisać i pobrać; konstrukcja pozostałych typów wymaga dalszego opracowania.';
 if(customKit)$('construction-help').textContent='Zestaw Penn / Adam Hall: narożniki 30 mm i 8 nóżek (1 opakowanie). Bryły uproszczone; profil 30 mm i montaż do doboru. Uchwyty na zdejmowanym wieku wymagają sprawdzenia przenoszenia obciążeń przez zamki.';
 const summary=model.project_summary,table=document.createElement('table');table.className='parts-table';
 for(const row of summary.rows){const tr=document.createElement('tr');for(const text of [row.name,row.part_id.startsWith('plywood')?'Sklejka '+row.material_thickness_mm+' mm':row.part_id,row.quantity+' '+row.unit]){const td=document.createElement('td');td.textContent=text;tr.append(td);}table.append(tr);}
 $('construction-bom').replaceChildren(table);
 $('construction-bom').prepend(Object.assign(document.createElement('p'),{textContent:summary.total_count+' części w projekcie · '+summary.definition_count+' pozycji.'}));
 if(draft.construction?.enabled)$('placement-summary').textContent=summary.total_count+' części w projekcie · konstrukcja i rozmieszczenie okuć.';
}
async function init(){
 $('construction-apply').onclick=()=>{
  if(draft.type!=='case'){status('Ten zestaw obsługuje obecnie skrzynię z jednym górnym wiekiem.',true);return;}
  const wheels=$('construction-wheels').checked,stacking=$('construction-stacking').checked;
  if(stacking&&!wheels){status('Gniazda wymagają kół. Włącz koła albo wyłącz gniazda.',true);return;}
  const ids=['EG-0113','EG-0500/1','EG-0500/2','410429','B1930','B1121',...(wheels?['source-caster-epson']:[]),...(stacking?['W0968Z']:[])];
  for(const id of ids)if(!draft.hardware.some(r=>r.part_id===id))draft.hardware.push({part_id:id,revision:1});
  draft.construction={enabled:true,wheels,stacking};partsPicker.setSelection(draft.hardware);changed();
 };
 $('construction-remove').onclick=()=>{delete draft.construction;changed();};

 options=await api('wizard/options');partsCatalog=await api('wizard/parts');partsPicker=new PartsPicker($('parts-library'),partsCatalog,refs=>{const ids=new Set(refs.map(r=>r.part_id)),affected=(draft.placements??[]).filter(g=>!ids.has(g.part_id)||(g.mate_part_id&&!ids.has(g.mate_part_id)));if(affected.length&&!confirm('Usunięcie części z wyboru usunie także jej grupy rozmieszczenia ('+affected.length+'). Kontynuować?')){partsPicker.setSelection(draft.hardware);return;}draft.placements=(draft.placements??[]).filter(g=>ids.has(g.part_id)&&(!g.mate_part_id||ids.has(g.mate_part_id)));draft.hardware=refs;changed();});selectOptions($('type'),Object.entries(options.types).map(([id,t])=>[id,t.label]),'case');
 placementEditor=new PlacementEditor($('placement-editor'),partsCatalog,()=>draft,changed,id=>placementView?.select(id),id=>placementView?.setPart(id),message=>status(message));
 closureEditor=new ClosureEditor($('closure-editor'),partsCatalog,()=>draft,changed,id=>placementView?.select(id));
 reviewPanel=new ReviewPanel($('review-panel'),()=>structuredClone(draft),goToIssue,report=>{if(step===8)$('next').textContent=report.counts.error?'Zapisz draft z problemami':'Zapisz draft';});
 draft=fresh();let recovered=false;try{const recovery=JSON.parse(localStorage.getItem(localKey));if(recovery?.draft){await api('wizard/preview',recovery.draft);draft=recovery.draft;storage=recovery.storage??{id:null,revision:0};dirty=recovery.dirty;recovered=true;}}catch{}
 if(requestedDraft&&recovered)step=7;
 if(requestedDraft&&!recovered){try{const saved=await api('wizard/drafts/'+requestedDraft);draft=saved.draft;storage={id:saved.id,revision:saved.revision};dirty=false;step=7;}catch(e){actionFeedback('Nie znaleziono projektu pod tym linkiem w '+storagePlace()+'. Wczytaj plik JSON przyciskiem „Import JSON” lub wybierz zapisany projekt. '+e.message,true);document.querySelector('details.storage').open=true;}}
 fill();await updatePreview();try{await refreshList();}catch(e){actionFeedback('Lista zapisanych projektów jest niedostępna: '+e.message+'. Nadal możesz pobrać projekt JSON.',true);}restoreContext();if(requestedDraft)navigate(step);
 window.addEventListener('pagehide',rememberContext);document.addEventListener('rockpro:before-navigation',rememberContext);document.addEventListener('rockpro:navigate-step',e=>navigate(e.detail));
 try{if(!localStorage.getItem(localKey)){const old=JSON.parse(localStorage.getItem('rockpro.configurator.recovery.v2')||localStorage.getItem('rockpro.configurator.recovery.v1'));if(old?.draft)showLegacy(old.draft);}}catch{}
 $('type').onchange=()=>status('Wybrany typ zostanie zastosowany przyciskiem „Zastosuj typ” lub „Dalej”.');
 $('apply-type').onclick=()=>{draft.type=$('type').value;delete draft.construction;draft.covers=options.types[draft.type].covers.map(([face,kind])=>cover(face,kind));draft.cooperation='independent';fill();changed();};
 $('legacy-convert').onclick=async()=>{try{const converted=await api('wizard/convert',pendingLegacy);await load({draft:converted});status('Utworzono nowy, niezapisany draft bez ręcznej szczeliny. Złącza wymagają doboru okucia. Oryginał pozostał zachowany.');}catch(e){status(e.message,true);}};
 $('legacy-export').onclick=()=>download(pendingLegacy,'RockPro_draft_archiwalny.json');
 $('cooperation').onchange=()=>{draft.cooperation=$('cooperation').value;for(const c of draft.covers)c.requires=[];editors();changed();};
 $('name').oninput=()=>{draft.name=$('name').value;changed();};
 for(const [i,k] of ['x','y','z'].entries())$('dim-'+k).oninput=()=>{draft.internal_mm[i]=$('dim-'+k).value===''?null:Number($('dim-'+k).value);changed();};
 for(const [id,key]of[['thickness','thickness_mm']])$(id).oninput=()=>{draft[key]=$(id).value===''?null:Number($(id).value);changed();};
 for(const b of $('steps').children)b.onclick=()=>navigate(Number(b.dataset.step));$('previous').onclick=()=>navigate(step-1);$('next').onclick=async()=>{if(step<8)navigate(step+1);else if(await save()){document.querySelector('details.storage').open=true;$('action-feedback').scrollIntoView({block:'nearest'});}};
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
 $('download-top').prepend(icon('download'));
 for(const b of $('steps').children){const n=b.dataset.step,title=b.querySelector('span');b.replaceChildren(Object.assign(document.createElement('span'),{className:'step-number',textContent:n}),title);}
 $('fit').onclick=()=>view?.chrome.frame();for(const [id,v]of[['open-all',100],['close-all',0]])$(id).onclick=()=>{view?.all(v);if(view)motionInputs();};
 $('export').onclick=$('download-top').onclick=$('download-final').onclick=exportDraft;$('download-top').disabled=false;
 $('import').onclick=()=>$('file').click();$('file').onchange=async()=>{try{const f=$('file').files[0];if(!f)return;if(f.size>32768)throw Error('Maksymalny rozmiar draftu to 32 KB');const value=JSON.parse(await f.text());if(!mayReplace())return;if(await load({draft:value}))status('Wczytano JSON jako nowy draft. Zapisz go, aby zachować w bazie.');}catch(e){status(e.message,true);}finally{$('file').value='';}};
 processPanel=new ProcessPanel($('process-panel'),{api,context:()=>({...storage,dirty}),view:()=>view});window.rockproProcessPanel=processPanel;
 window.rockproWizard={getDraft:()=>structuredClone(draft),getStorage:()=>({...storage}),preview:()=>updatePreview(),load,save,navigate};
}
init().catch(e=>status('Nie można uruchomić kreatora: '+e.message,true));
