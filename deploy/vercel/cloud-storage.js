// Public demo: drafts/favorites remain in this browser. No shared ERP database.
(() => {
 const nativeFetch=window.fetch.bind(window), key='rockpro.cloud-demo.storage.v1';
 const read=()=>{const raw=localStorage.getItem(key);return raw?JSON.parse(raw):{drafts:{},favorites:{}};};
 const reply=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
 const write=async action=>navigator.locks?navigator.locks.request(key,action):action();
 const processRequest=async(route,method,init)=>{
  try{
   const db=read(),runs=db.processRuns??{};
   if(method==='GET'&&route.startsWith('process/runs/'))return reply(Object.values(runs).filter(r=>r.binding.draft_id===route.split('/').pop()).sort((a,b)=>b.updated_at.localeCompare(a.updated_at)));
   if(method==='GET'&&route.startsWith('process/run/'))return runs[route.split('/').pop()]?reply(runs[route.split('/').pop()]):reply({error:'Brak przebiegu w tej przeglądarce.'},404);
   if(method!=='POST'||route!=='process')return reply({error:'Nieobsługiwana operacja historii.'},405);
   const data=JSON.parse(init?.body??'null');if(data?.action!=='import')return reply({error:'Wersja online przechowuje importowane logi w przeglądarce. Wykonawca CAD działa lokalnie.'},400);
   return await write(async()=>{
    const db=read(),saved=db.drafts[data.draft_id];if(!saved||saved.revision!==data.revision)return reply({error:'Wczytaj i zapisz bieżący draft przed importem logu.'},409);
    const response=await nativeFetch('api/index?endpoint=process-report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({draft:saved.draft,draft_id:saved.id,revision:saved.revision,report:data.report})});
    const result=await response.json();if(!response.ok)return reply(result,response.status);
    db.processRuns??={};const old=db.processRuns[result.id];
    if(old&&JSON.stringify(old)!==JSON.stringify(result))return reply({error:'ID przebiegu już ma inną treść.'},409);
    if(!old&&Object.keys(db.processRuns).length>=100)throw Error('Limit 100 przebiegów w przeglądarce.');
    db.processRuns[result.id]=result;localStorage.setItem(key,JSON.stringify(db));return reply(result);
   });
  }catch(e){return reply({error:e.name==='QuotaExceededError'?'Brak miejsca w przeglądarce. Zachowaj log JSON na dysku.':e.message},400);}
 };
 const preferences=db=>{
  const items={};for(const [id,favorite]of Object.entries(db.favorites))items[id]={favorite,project_count:0,last_used:null};
  for(const draft of Object.values(db.drafts))for(const id of draft.used_parts??(draft.draft?.hardware??[]).map(r=>r.part_id)){items[id]??={favorite:false,project_count:0,last_used:null};items[id].project_count++;if(!items[id].last_used||draft.updated_at>items[id].last_used)items[id].last_used=draft.updated_at;}
  return {items,usage_basis:'distinct_saved_projects_across_revisions',scope:'this_browser_demo'};
 };
 window.fetch=async(input,init)=>{
  const url=new URL(typeof input==='string'?input:input.url,location.href),route=url.pathname.replace(/^\//,''),method=(init?.method??'GET').toUpperCase();
  if(url.origin===location.origin&&(route==='process'||/^process\/runs?\/[a-f0-9]{32}$/.test(route)))return processRequest(route,method,init);
  if(url.origin!==location.origin||!['wizard/drafts','wizard/save','parts/preferences'].includes(route)&&!/^wizard\/drafts\/[a-f0-9]{32}$/.test(route))return nativeFetch(input,init);
  try{
   if(method==='GET'){
    const db=read();
    if(route==='parts/preferences')return reply(preferences(db));
    if(route==='wizard/drafts')return reply(Object.values(db.drafts).sort((a,b)=>b.updated_at.localeCompare(a.updated_at)).map(({id,name,revision,updated_at})=>({id,name,revision,updated_at})));
    const saved=db.drafts[route.split('/').pop()];return saved?reply(saved):reply({error:'Ten draft nie jest zapisany w tej przeglądarce. Poproś autora o plik JSON i użyj importu.'},404);
   }
   const data=JSON.parse(init?.body??'null');
   if(route==='parts/preferences'&&method==='POST')return await write(()=>{if(!data||typeof data.part_id!=='string'||typeof data.favorite!=='boolean')throw Error('Nieprawidłowa ulubiona część.');const db=read();db.favorites[data.part_id]=data.favorite;localStorage.setItem(key,JSON.stringify(db));return reply(preferences(db));});
   if(route==='wizard/save'&&method==='POST'){
    const check=await nativeFetch('wizard/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data.draft)}),model=await check.json();
    if(!check.ok)return reply(model,400);
    return await write(()=>{
     const db=read(),old=data.id?db.drafts[data.id]:null;
     if((data.id&&!old)||(old?.revision??0)!==data.expected_revision)return reply({error:'Draft zmienił się w innym oknie. Wczytaj go ponownie lub zapisz jako nowy.'},409);
     if(!old&&Object.keys(db.drafts).length>=100)throw Error('Limit 100 draftów w przeglądarce. Wyeksportuj projekty do JSON.');
     const saved={id:data.id??crypto.randomUUID().replaceAll('-',''),name:model.draft.name,revision:(old?.revision??0)+1,updated_at:new Date().toISOString(),draft:model.draft,
      used_parts:[...new Set([...(old?.used_parts??[]),...model.draft.hardware.map(r=>r.part_id)])]};
     db.drafts[saved.id]=saved;localStorage.setItem(key,JSON.stringify(db));return reply(saved);
    });
   }
   return reply({error:'Nieobsługiwana operacja.'},405);
  }catch(e){return reply({error:e.name==='QuotaExceededError'?'Brak miejsca na zapis w przeglądarce. Pobierz projekt jako JSON.':e.message},400);}
 };
})();
