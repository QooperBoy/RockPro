import {PartPreferences} from './part-preferences.js';
const $=id=>document.getElementById(id);let data,preferences;
const text=(tag,value,cls)=>{const node=document.createElement(tag);node.textContent=value;if(cls)node.className=cls;return node;};
function display(value){if(value===null||value===undefined||value==='')return '—';const n=Number(value);return Number.isFinite(n)?new Intl.NumberFormat('pl-PL',{maximumFractionDigits:4}).format(n):value;}
function render(){
 const query=$('company-search').value.trim().toLocaleLowerCase('pl'),category=$('company-category').value;
 const rows=preferences.sort(data.items.filter(r=>(!category||r.category===category)&&(!$('company-favorites').checked||preferences.stat(r.id).favorite)&&(!$('company-cutouts').checked||r.cutout_note)&&(!$('company-models').checked||r.geometry_candidates.some(m=>m.has_mesh))&&(!query||[r.code,r.name,r.category,r.cutout_note].some(v=>String(v??'').toLocaleLowerCase('pl').includes(query)))),$('company-sort').value,r=>r.code+' '+r.name);
 $('company-result').textContent=rows.length+' z '+data.items.length+' pozycji';$('company-rows').replaceChildren();
 for(const row of rows){
  const tr=document.createElement('tr'),image=document.createElement('td');
  if(row.image){const img=document.createElement('img');img.src=row.image.url;img.alt=row.name;img.loading='lazy';image.append(img);}else image.append(text('span','Brak zdjęcia','muted'));
  const item=document.createElement('td');item.append(text('strong',row.code),text('div',row.name),text('small',row.category,'muted'));
  if(row.duplicate_code)item.append(text('div','Kod występuje w dwóch kolumnach — do rozstrzygnięcia','company-warning'));
  if(row.source_url&&/^https?:\/\//.test(row.source_url)){const a=text('a','Producent ↗');a.href=row.source_url;a.target='_blank';a.rel='noopener noreferrer';item.append(a);}
  const stock=text('td',display(row.cached_stock_raw));stock.title='Stany magazynowe!'+row.source.stock_cell+' · jednostka wymaga potwierdzenia';
  if(row.stock_error||Number(row.cached_stock_raw)<0)stock.className='company-warning';stock.append(text('small',row.source.stock_cell+' · z pliku','muted'));
  const price=text('td',display(row.price_raw));price.title='Cena jednostkowa z wiersza 7. Waluta i jednostka nie są jawnie oznaczone w katalogu.';
  const cut=text('td',row.cutout_note||'—');if(row.cutout_note)cut.append(text('small','Opis źródłowy · do potwierdzenia montażu','muted'));
  const mesh=document.createElement('td'),candidates=row.geometry_candidates.filter(m=>m.has_mesh);
  mesh.append(text('span',candidates.length?'Model kandydujący':'Brak dopasowanego modelu',candidates.length?'':'muted'));
  for(const candidate of candidates)mesh.append(text('small',candidate.id));if(candidates.length)mesh.append(text('small','Wariant do sprawdzenia','muted'));
  const favorite=document.createElement('td');favorite.className='company-favorite';favorite.append(preferences.button(row.id,row.code));
  item.className='company-item';stock.classList.add('company-stock');price.className='company-price';cut.className='company-cutout';
  tr.dataset.part=row.id;tr.append(favorite,image,item,stock,price,cut,mesh);$('company-rows').append(tr);
 }
}
async function init(){
 const response=await fetch('company/catalog');if(!response.ok)throw Error('Nie można odczytać katalogu');data=await response.json();
 $('company-count').textContent=data.items.length+' pozycji';
 if(!data.source){$('company-source').textContent='Nie zaimportowano jeszcze firmowego Excela.';return;}
 $('company-source').textContent=data.source.filename+' · '+data.summary.unique_codes+' różnych kodów · '+data.summary.images+' zdjęć · '+data.summary.cutout_notes+' opisów wycięć.';
 for(const category of Object.keys(data.summary.categories))$('company-category').append(new Option(category,category));
 preferences=new PartPreferences(()=>render(),message=>$('company-result').textContent=message);
 for(const id of ['company-search','company-category','company-sort','company-favorites','company-cutouts','company-models'])$(id).addEventListener(id==='company-search'?'input':'change',render);render();await preferences.refresh();
}
init().catch(e=>$('company-result').textContent=e.message);
