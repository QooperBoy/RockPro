// Studio-to-CAD handoff. A blocked plan never starts a reduced or substitute build.
const token=location.pathname.split('/').filter(Boolean)[0];
let plan=null,preparedDraft=null,preparedStorage=null,pollTimer=null,requestVersion=0,busy=false,operationId=null;
const card=document.createElement('section');card.className='notice';card.id='cad-handoff';
const title=document.createElement('h2');title.textContent='Generowanie w IronCAD 2027';
const explanation=document.createElement('p');explanation.className='hint';explanation.textContent='Sprawdź zapisaną rewizję: parametry, wszystkie wybrane części oraz wymagane wycięcia i połączenia. Braki trzeba uzupełnić przed generowaniem.';
const prepare=document.createElement('button');prepare.id='cad-prepare';prepare.textContent='Sprawdź plan CAD';
const build=document.createElement('button');build.id='cad-build';build.className='primary';build.textContent='Wygeneruj całą skrzynię';build.disabled=true;
const message=document.createElement('p');message.id='cad-plan-status';message.setAttribute('role','status');message.setAttribute('aria-live','polite');message.textContent='Najpierw zapisz aktualny draft.';
const jobMessage=document.createElement('p');jobMessage.id='cad-job-status';jobMessage.setAttribute('role','status');jobMessage.style.overflowWrap='anywhere';
const report=document.createElement('details'),summary=document.createElement('summary'),list=document.createElement('ul');
list.style.maxHeight='18rem';list.style.overflow='auto';list.style.lineHeight='1.5';list.style.fontSize='12px';
summary.textContent='Zakres i brakujące dane';report.append(summary,list);
const exportButton=document.createElement('button');exportButton.id='cad-export-plan';exportButton.textContent='Pobierz plan i listę braków';exportButton.disabled=true;
card.append(title,explanation,prepare,build,message,jobMessage,report,exportButton);
document.querySelector('.editor').insertBefore(card,document.querySelector('.storage'));

async function api(endpoint,data){
 const response=await fetch(endpoint,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-RockPro-Session':token},body:JSON.stringify(data)});
 const value=await response.json();if(!response.ok)throw Error(value.error||'Nie udało się połączyć z wykonawcą CAD');return value;
}
function current(){const wizard=window.rockproWizard;if(!wizard)throw Error('Poczekaj na uruchomienie kreatora.');return {draft:wizard.getDraft(),storage:wizard.getStorage(),...wizard.getCadState()};}
function invalidate(){requestVersion++;plan=null;preparedDraft=preparedStorage=null;operationId=null;build.disabled=exportButton.disabled=true;message.textContent='Plan nieaktualny. Zapisz zmiany i sprawdź nową rewizję.';list.replaceChildren();}
document.addEventListener('rockpro:cad-invalidated',invalidate);
function render(){
 list.replaceChildren();const add=text=>{const li=document.createElement('li');li.textContent=text;list.append(li);};
 add('Rewizja '+plan.draft_revision+' · '+plan.panels.length+' płyt skrzyni · '+plan.occurrences.length+' elementów montażu · '+plan.selected_parts.length+' wybranych definicji.');
 if(plan.native_spec)add('CAD: '+plan.native_spec.panels.length+' płyt i podpór, '+plan.native_spec.parts.length+' wystąpień części, '+plan.native_spec.cuts.length+' obróbek. Zestaw T1 z przypiętych modeli źródłowych.');
 for(const row of plan.selected_parts)add(row.part_id+': '+row.instance_ids.length+' wystąpień w podglądzie; baza montażu: '+(row.native_binding_status==='source_pinned'?'powiązana ze źródłem':'do powiązania')+'.');
 for(const blocker of plan.blockers)add(blocker.message);
 message.textContent=plan.executable?'Plan gotowy do wykonania w IronCAD 2027.':'Generowanie zablokowane: '+plan.blockers.length+' braków. Plan obejmuje wszystkie wybory; szczegóły poniżej.';
 build.disabled=!plan.executable;exportButton.disabled=false;report.open=plan.blockers.length>0;
}
prepare.onclick=async()=>{
 if(busy)return;busy=true;prepare.disabled=true;const version=++requestVersion;build.disabled=true;
 try{
  const state=current();if(state.dirty||state.selectionPending||!state.storage.id)throw Error('Najpierw zastosuj typ i zapisz aktualny draft.');
  const result=await api('wizard/native-plan',{draft_id:state.storage.id,expected_revision:state.storage.revision});
  if(version!==requestVersion)return;
  const after=current();if(after.dirty||JSON.stringify(after.draft)!==JSON.stringify(state.draft)||JSON.stringify(after.storage)!==JSON.stringify(state.storage))throw Error('Draft zmienił się podczas sprawdzania. Przygotuj nowy plan.');
  plan=result;preparedDraft=JSON.stringify(state.draft);preparedStorage=JSON.stringify(state.storage);operationId=crypto.randomUUID().replaceAll('-','');render();
 }catch(e){if(version===requestVersion){plan=null;build.disabled=exportButton.disabled=true;message.textContent=e.message;}}
 finally{busy=false;prepare.disabled=false;}
};
async function poll(id){
 try{const job=await api('wizard/native-jobs/'+id);showJob(job);if(['queued','running'].includes(job.status))pollTimer=setTimeout(()=>poll(id),1500);}
 catch(e){jobMessage.textContent=e.message+' Sprawdź wynik operacji przed ponowieniem.';}
}
function showJob(job){const labels={queued:'Oczekuje w kolejce',running:'Generowanie w IronCAD',succeeded:'Generowanie zakończone',rejected:'Plan odrzucony przed rozpoczęciem budowy',failed_reconciled:'Budowa nieudana — kopia odzyskiwania zachowana, sprzątnięcie potwierdzone',outcome_unknown:'Wynik wymaga sprawdzenia przed ponowieniem',reconciliation_required:'Operacja przerwana — wymagane uzgodnienie wyniku'};jobMessage.textContent=(labels[job.status]??job.status)+' · operacja '+job.operation_id;if(job.status==='succeeded'&&job.receipt?.output_path)jobMessage.textContent+=' · '+job.receipt.occurrence_count+' elementów · '+job.receipt.machining_count+' obróbek · plik: '+job.receipt.output_path;}
build.onclick=async()=>{
 if(busy||!plan?.executable)return;
 try{
  const state=current();if(state.dirty||state.selectionPending||JSON.stringify(state.draft)!==preparedDraft||JSON.stringify(state.storage)!==preparedStorage){invalidate();return;}
  busy=true;build.disabled=prepare.disabled=true;
  const job=await api('wizard/native-build',{plan_id:plan.plan_id,plan_sha256:plan.plan_sha256,operation_id:operationId});
  showJob(job);if(['queued','running'].includes(job.status))pollTimer=setTimeout(()=>poll(job.operation_id),1500);
 }catch(e){message.textContent=e.message;}
 finally{busy=false;prepare.disabled=false;}
};
exportButton.onclick=()=>{if(!plan)return;const url=URL.createObjectURL(new Blob([JSON.stringify(plan,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='RockPro_plan_CAD_rew_'+plan.draft_revision+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
window.addEventListener('pagehide',()=>clearTimeout(pollTimer));
