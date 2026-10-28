// Both catalogues share SQLite preferences; browsing never increments usage.
export class PartPreferences {
 constructor(onChange,onError){
  this.items={};this.onChange=onChange;this.onError=onError;
  if('BroadcastChannel' in window){this.channel=new BroadcastChannel('rockpro.part-preferences');this.channel.onmessage=()=>this.refresh();}
  this.focus=()=>this.refresh();window.addEventListener('focus',this.focus);document.addEventListener('rockpro:project-saved',this.focus);
 }
 stat(id){return this.items[id]??{favorite:false,project_count:0,last_used:null};}
 async refresh(){
  try{const response=await fetch('parts/preferences');const value=await response.json();if(!response.ok)throw Error(value.error??'Nie można odczytać ulubionych');this.items=value.items;this.onChange?.();}
  catch(e){this.onError?.(e.message);}
 }
 async toggle(id,button){
  button.disabled=true;
  try{
   const token=location.pathname.split('/').filter(Boolean)[0];
   const response=await fetch('parts/preferences',{method:'POST',headers:{'Content-Type':'application/json','X-RockPro-Session':token},body:JSON.stringify({part_id:id,favorite:!this.stat(id).favorite})});
   const value=await response.json();if(!response.ok)throw Error(value.error??'Nie można zapisać ulubionej');
   this.items=value.items;this.onChange?.();this.channel?.postMessage('changed');
  }catch(e){this.onError?.(e.message);}finally{button.disabled=false;}
 }
 button(id,label){
  const favorite=this.stat(id).favorite,b=document.createElement('button');b.type='button';b.className='favorite-button';b.dataset.favoriteId=id;
  b.textContent=favorite?'★':'☆';b.setAttribute('aria-pressed',String(favorite));b.title=(favorite?'Usuń z ulubionych: ':'Dodaj do ulubionych: ')+label;b.setAttribute('aria-label',b.title);
  b.onclick=e=>{e.stopPropagation();this.toggle(id,b);};return b;
 }
 sort(rows,mode='recommended',label=r=>r.name){
  return [...rows].sort((a,b)=>{
   const x=this.stat(a.id),y=this.stat(b.id);
   if(mode==='name')return label(a).localeCompare(label(b),'pl');
   if(mode==='recommended'&&x.favorite!==y.favorite)return Number(y.favorite)-Number(x.favorite);
   return y.project_count-x.project_count||Number(y.favorite)-Number(x.favorite)||label(a).localeCompare(label(b),'pl');
  });
 }
}
