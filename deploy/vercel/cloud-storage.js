// Public demo: drafts/favorites remain in this browser. No shared ERP database.
(() => {
 const nativeFetch=window.fetch.bind(window), key='rockpro.cloud-demo.storage.v1';
 const read=()=>{const raw=localStorage.getItem(key);return raw?JSON.parse(raw):{drafts:{},favorites:{}};};
 const reply=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
 const write=async action=>navigator.locks?navigator.locks.request(key,action):action();
 const preferences=db=>{
  const items={};for(const [id,favorite]of Object.entries(db.favorites))items[id]={favorite,project_count:0,last_used:null};
  for(const draft of Object.values(db.drafts))for(const id of draft.used_parts){items[id]??={favorite:false,project_count:0,last_used:null};items[id].project_count++;if(!items[id].last_used||draft.updated_at>items[id].last_used)items[id].last_used=draft.updated_at;}
  return {items,usage_basis:'distinct_saved_projects_across_revisions',scope:'this_browser_demo'};
 };
 window.fetch=async(input,init)=>{
  const url=new URL(typeof input==='string'?input:input.url,location.href),route=url.pathname.replace(/^\//,''),method=(init?.method??'GET').toUpperCase();
  if(url.origin!==location.origin||!['wizard/drafts','wizard/save','parts/preferences'].includes(route)&&!/^wizard\/drafts\/[a-f0-9]{32}$/.test(route))return nativeFetch(input,init);
  try{
   if(method==='GET'){
    const db=read();
    if(route==='parts/preferences')return reply(preferences(db));
    if(route==='wizard/drafts')return reply(Object.values(db.drafts).sort((a,b)=>b.updated_at.localeCompare(a.updated_at)).map(({id,name,revision,updated_at})=>({id,name,revision,updated_at})));
    const saved=db.drafts[route.split('/').pop()];return saved?reply(saved):reply({error:'Ten draft nie jest zapisany w tej przeglądarce. Poproś autora o plik JSON i użyj importu.'},404);
   }
   const data=JSON.parse(init?.body??'null');
   if(route==='parts/preferences'&&method==='POST')return write(()=>{if(!data||typeof data.part_id!=='string'||typeof data.favorite!=='boolean')throw Error('Nieprawidłowa ulubiona część.');const db=read();db.favorites[data.part_id]=data.favorite;localStorage.setItem(key,JSON.stringify(db));return reply(preferences(db));});
   if(route==='wizard/save'&&method==='POST'){
    const check=await nativeFetch('wizard/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data.draft)}),model=await check.json();
    if(!check.ok)return reply(model,400);
    return write(()=>{
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
