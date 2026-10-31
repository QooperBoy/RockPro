// Read-only process overlay. Geometry editing and part quantities are untouched.
const ORIGIN={standard:'Standard / skrypt',ai:'Interwencja AI',manual:'Konstruktor',unknown:'Nieustalone'};
const STAGE={hardware:'Okucia',handles:'Uchwyty',structure:'Konstrukcja',native:'Wykonanie CAD',source:'Przygotowanie',plywood:'Sklejka',profiles:'Profile',corners:'Narożniki',closures:'Zamki i zawiasy',wheels:'Podwozie',checks:'Kontrola',save:'Zapis'};
const EXECUTOR={sdk:'SDK',python:'Python',agent:'Agent AI',constructor:'Konstruktor',unknown:'Nieustalone'};
const COLORS={standard:0x38a679,ai:0xb58aff,manual:0xe6a643,unknown:0x89969d};
const STATE={running:'W toku',completed:'Zakończony',partial:'Częściowy',failed:'Błąd',success:'OK',skipped:'Pominięto',requested:'Oczekuje',resolved:'Rozwiązano'};
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const occurrenceId=o=>o.userData.processOccurrenceId??o.userData.occurrence?.id??(o.userData.mountFace?'panel/'+o.userData.mountFace.key:null);
export class ProcessPanel{
 constructor(host,{api,context,view}){
  this.host=host;this.api=api;this.context=context;this.view=view;this.originals=[];this.report=null;this.serial=0;
  host.classList.add('process-panel');const summary=el('summary','Przebieg wykonania · SDK / AI');host.append(summary);
  this.body=el('div',undefined,'process-body');host.append(this.body);
  const tools=el('div',undefined,'process-tools');this.choose=el('select');this.choose.setAttribute('aria-label','Historia przebiegów projektu');
  this.refreshButton=el('button','Odśwież');this.refreshButton.type='button';this.exportButton=el('button','Pobierz log JSON');this.exportButton.type='button';
  this.startButton=el('button','Przygotuj pomiar');this.startButton.type='button';
  this.copyButton=el('button','Kopiuj ID przebiegu');this.copyButton.type='button';
  this.importButton=el('button','Wczytaj log JSON');this.importButton.type='button';this.file=el('input');this.file.type='file';this.file.accept='.json,application/json';this.file.hidden=true;
  tools.append(this.choose,this.refreshButton,this.startButton,this.copyButton,this.exportButton,this.importButton,this.file);this.body.append(tools);
  this.message=el('p',undefined,'hint');this.cards=el('div',undefined,'process-cards');this.body.append(this.message,this.cards);
  const filters=el('div',undefined,'process-tools');this.filter=el('select');this.filter.setAttribute('aria-label','Filtr pochodzenia operacji');
  for(const [id,title] of [['all','Wszystkie operacje'],...Object.entries(ORIGIN)]){const o=el('option',title);o.value=id;this.filter.append(o);}
  this.search=el('input');this.search.placeholder='Szukaj części, etapu lub operacji';this.search.setAttribute('aria-label',this.search.placeholder);
  const label=el('label',undefined,'process-layer');this.layer=el('input');this.layer.type='checkbox';label.append(this.layer,document.createTextNode('Kolory pochodzenia w 3D'));
  filters.append(this.filter,this.search,label);this.body.append(filters);
  this.legend=el('p','Zielony: standard · fioletowy: AI · bursztynowy: konstruktor · szary: brak danych.','hint');this.body.append(this.legend);
  this.interventions=el('div');this.rows=el('div',undefined,'process-rows');this.body.append(this.interventions,this.rows);
  this.body.append(el('p','Liczymy zakończone operacje robocze, nie nadrzędne etapy. SDK to wykonawca; AI to pochodzenie decyzji. Dane pochodzą z rejestru wykonawcy, nie stanowią odbioru geometrii.','hint'));
  this.choose.onchange=()=>this.load(this.choose.value);this.refreshButton.onclick=()=>this.refresh();
  this.filter.onchange=this.search.oninput=()=>{this.renderRows();this.applyLayer();};this.layer.onchange=()=>this.applyLayer();
  this.exportButton.onclick=()=>this.download();this.importButton.onclick=()=>this.file.click();this.file.onchange=()=>this.importFile();
  this.startButton.onclick=async()=>{try{const c=this.context();if(!c.id||c.dirty)throw Error('Najpierw zapisz bieżący draft.');const r=await this.api('process',{action:'create',draft_id:c.id,revision:c.revision,label:'Wykonanie CAD · '+new Date().toLocaleString('pl-PL')});this.choose.value='';await this.refresh();this.choose.value=r.id;await this.load(r.id);this.message.textContent='Pomiar przygotowany. ID: '+r.id+'. Sam pomiar nie uruchamia CAD; wykonawca musi otrzymać to ID.';}catch(e){this.message.textContent=e.message;}};
  this.copyButton.onclick=async()=>{try{if(this.report){await navigator.clipboard.writeText(this.report.id);this.message.textContent='Skopiowano ID przebiegu: '+this.report.id;}}catch{this.message.textContent='ID przebiegu: '+this.report?.id;}};
  host.addEventListener('toggle',()=>{if(host.open)this.refresh();});document.addEventListener('rockpro:project-saved',()=>this.refresh());
  this.interval=setInterval(()=>{if(host.open&&document.visibilityState==='visible')this.refresh();},4000);
  this.refresh();
  if(location.hash==='#process-panel')host.open=true;
 }
 clearLayer(){for(const [mesh,material] of this.originals){const current=Array.isArray(mesh.material)?mesh.material:[mesh.material];for(const m of current)m?.dispose();mesh.material=material;}this.originals=[];}
 current(){const c=this.context();return this.report&&this.report.binding.draft_id===c.id&&this.report.binding.draft_revision===c.revision&&!c.dirty;}
 async refresh(){
  const serial=++this.serial,c=this.context();if(!c.id){this.report=null;this.choose.replaceChildren();this.render();this.message.textContent='Zapisz draft, aby powiązać przebieg z jego rewizją.';return;}
  try{const rows=await this.api('process/runs/'+c.id);if(serial!==this.serial)return;
   const selected=rows.some(r=>r.id===this.choose.value)?this.choose.value:rows[0]?.id;this.choose.replaceChildren();
   for(const r of rows){const o=el('option',`${r.mode==='simulation'?'SYMULACJA · ':''}${r.label} · rew. ${r.binding.draft_revision} · ${STATE[r.state]??r.state}`);o.value=r.id;this.choose.append(o);}
   if(selected){this.choose.value=selected;await this.load(selected);}else{this.report=null;this.render();}
  }catch(e){if(serial!==this.serial)return;this.report=null;this.render();this.message.textContent='Nie odczytano historii: '+e.message;}
 }
 async load(id){if(!id)return;const serial=++this.serial;try{const r=await this.api('process/run/'+id);if(serial!==this.serial)return;this.report=r;this.render();}catch(e){this.message.textContent=e.message;}}
 render(){
  this.clearLayer();this.cards.replaceChildren();this.rows.replaceChildren();this.interventions.replaceChildren();this.exportButton.disabled=this.copyButton.disabled=!this.report;this.startButton.hidden=document.body.dataset.storageMode==='browser';
  if(!this.report){this.message.textContent='Brak zarejestrowanych przebiegów. Nie odtwarzamy udziału AI ze starych modeli ani z samej liczby części.';return;}
  const r=this.report,s=r.summary,current=this.current();
  this.message.textContent=`${r.mode==='simulation'?'SYMULACJA — przykład, nie wykonanie CAD. ':''}Rewizja ${r.binding.draft_revision} · ${STATE[r.state]??r.state}. ${current?'Dotyczy zapisanej wersji projektu.':'Historia starszej lub innej wersji — kolory 3D wyłączone.'}`;
  for(const [value,label] of [[s.completed,'Zakończone operacje'],[s.by_origin.standard,'Standard / skrypt'],[s.by_origin.ai,'Z udziałem AI'],[s.interventions,'Interwencje AI'],[s.by_origin.manual,'Konstruktor'],[s.by_origin.unknown,'Nieustalone']]){
   const card=el('div',undefined,'process-card');card.append(el('strong',String(value)),el('span',label));this.cards.append(card);
  }
  this.cards.append(el('p',`${s.failed} błędnych · ${s.running} w toku · ${s.retry_attempts} ponowień. Wykonawcy zakończonych operacji: SDK ${s.by_executor.sdk}, Python ${s.by_executor.python}, agent ${s.by_executor.agent}, konstruktor ${s.by_executor.constructor}, nieustalone ${s.by_executor.unknown}. Udział standardu: ${s.percent.standard===null?'brak danych':s.percent.standard+'%'}; AI: ${s.percent.ai===null?'brak danych':s.percent.ai+'%'}.`,'hint'));
  this.interventions.append(el('h3','Interwencje i nowe elementy'));
  if(s.coarse_jobs_without_details)this.interventions.append(el('p',`${s.coarse_jobs_without_details} wywołań SDK ma tylko pomiar całego etapu. Brak szczegółowych operacji — nie dopisujemy ich do licznika. Pozostałe liczby obejmują tylko zarejestrowane zdarzenia.`,'hint'));
  if(!s.intervention_rows.length)this.interventions.append(el('p','Brak zapisanych interwencji.','hint'));
  for(const i of s.intervention_rows){const row=el('article',undefined,'process-intervention');row.append(el('strong',i.label||i.operation_id),el('p',i.reason),el('small',`${i.part_id??'Bez SKU'} · ${STAGE[i.stage]??i.stage} · ${STATE[i.status]??i.status}${i.duration_ms==null?'':` · ${(i.duration_ms/1000).toFixed(2)} s`}`));this.interventions.append(row);}
  if(s.spans?.length){const spans=el('details');spans.append(el('summary','Czasy etapów SDK — poza licznikiem operacji'));for(const e of s.spans)spans.append(el('p',`${e.label??e.operation_id} · ${STATE[e.status]??e.status} · ${e.duration_ms==null?'brak pomiaru':(e.duration_ms/1000).toFixed(2)+' s'}`,'hint'));this.interventions.append(spans);}
  this.renderRows();this.applyLayer();
 }
 filtered(){const term=this.search.value.toLocaleLowerCase();return(this.report?.summary.operations??[]).filter(e=>(this.filter.value==='all'||e.origin===this.filter.value)&&[e.label,e.operation_id,e.stage,e.part_id,e.occurrence_id].join(' ').toLocaleLowerCase().includes(term));}
 renderRows(){
  this.rows.replaceChildren();const rows=this.filtered();this.rows.append(el('p',`${rows.length} operacji w filtrze · pokazano pierwsze ${Math.min(100,rows.length)}. Pełna historia jest w JSON. Próby nie są liczone jako dodatkowe ukończone operacje.`,'hint'));
  const table=el('table'),head=el('thead'),tr=el('tr');for(const title of ['Etap / operacja','Część / wystąpienie','Pochodzenie','Wykonawca','Wynik / czas'])tr.append(el('th',title));head.append(tr);table.append(head);const body=el('tbody');
  for(const e of rows.slice(0,100)){const row=el('tr');for(const value of [`${STAGE[e.stage]??e.stage} · ${e.label??e.operation_id}`,[e.part_id,e.occurrence_id].filter(Boolean).join(' · ')||'—',ORIGIN[e.origin],EXECUTOR[e.executor],`${STATE[e.status]??e.status} · ${e.duration_ms==null?'brak pomiaru':e.duration_ms.toFixed(1)+' ms'} · próba ${e.attempt}`])row.append(el('td',value));body.append(row);}table.append(body);this.rows.append(table);
 }
 applyLayer(){
  this.clearLayer();if(!this.layer.checked||!this.current())return;const view=this.view();if(!view?.root)return;
  const origins=new Map();for(const e of this.filtered()){if(e.status!=='success'||!e.occurrence_id)continue;const old=origins.get(e.occurrence_id);origins.set(e.occurrence_id,old==='ai'?'ai':e.origin);}
  let matches=0;view.root.traverse(group=>{const id=occurrenceId(group);if(!id)return;if(origins.has(id))matches++;const origin=origins.get(id)??'unknown';group.traverse(mesh=>{if(!mesh.isMesh||!mesh.material||mesh.userData.pickProxy)return;const original=mesh.material;
   const tint=m=>{const copy=m.clone();copy.color?.setHex(COLORS[origin]);if(copy.emissive){copy.emissive.setHex(COLORS[origin]);copy.emissiveIntensity=.15;}return copy;};mesh.material=Array.isArray(original)?original.map(tint):tint(original);this.originals.push([mesh,original]);});});
  this.legend.textContent=`Zielony: standard · fioletowy: AI · bursztynowy: konstruktor · szary: nieustalone lub bez zdarzeń. Dopasowano ${matches} obiektów podglądu; ${[...origins.keys()].filter(id=>{let found=false;view.root.traverse(o=>{if(occurrenceId(o)===id)found=true;});return!found;}).length} ID operacji bez obiektu 3D. Kolor pokazuje udział, nie odbiór montażu.`;
 }
 download(){if(!this.report)return;const value=structuredClone(this.report);delete value.summary;const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download='RockPro_przebieg_'+value.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 async importFile(){try{const file=this.file.files[0],c=this.context();if(!file)return;if(!c.id||c.dirty)throw Error('Najpierw zapisz bieżący draft.');if(file.size>8*1024*1024)throw Error('Limit raportu: 8 MB');const report=JSON.parse(await file.text());await this.api('process',{action:'import',draft_id:c.id,revision:c.revision,report});await this.refresh();}catch(e){this.message.textContent=e.message;}finally{this.file.value='';}}
}
