import {PartPreferences} from './part-preferences.js';
// Step 4 selects versioned definitions. Placement and quantities belong to step 5.
function element(tag,text,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;}
const cutLabels={required:'Wycięcie w sklejce: wymagane',none:'Wycięcie w sklejce: niewymagane',unknown:'Wycięcie w sklejce: do ustalenia'};

export class PartsPicker {
 constructor(host,catalog,onChange){
  this.host=host;this.catalog=catalog;this.onChange=onChange;this.selected=[];
  this.dialog=element('dialog',null,'part-image-dialog');
  const close=element('button','Zamknij ×','part-image-close');close.type='button';close.onclick=()=>this.dialog.close();
  this.dialogTitle=element('h2');this.dialogTitle.id='part-image-title';this.dialog.setAttribute('aria-labelledby',this.dialogTitle.id);
  this.dialogImage=element('img');this.dialogCaption=element('p',null,'hint');this.dialog.append(close,this.dialogTitle,this.dialogImage,this.dialogCaption);
  this.dialog.addEventListener('click',e=>{if(e.target===this.dialog){const r=this.dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)this.dialog.close();}});
  document.body.append(this.dialog);
  host.append(element('p',`Baza części: ${catalog.items.length} pozycji, w tym ${catalog.company_record_count??0} rekordów z Excela. Pozycje katalogowe bez sprawdzonego modelu są widoczne, lecz nie można ich jeszcze rozmieszczać w 3D.`,'hint'));
  const fullCatalog=element('a','Otwórz pełny katalog firmowy ↗');fullCatalog.href='company-parts.html'+location.search;fullCatalog.id='company-catalog-link';host.append(fullCatalog);
  const searchLabel=element('label','Szukaj części');this.search=element('input');this.search.type='search';this.search.id='parts-search';this.search.placeholder='SKU, nazwa, producent lub alias CAD';searchLabel.append(this.search);
  const categoryLabel=element('label','Kategoria');this.category=element('select');this.category.id='parts-category';
  this.category.append(new Option('Wszystkie kategorie',''));for(const [id,label]of Object.entries(catalog.categories))this.category.append(new Option(label,id));categoryLabel.append(this.category);
  const sourceLabel=element('label','Pochodzenie części');this.source=element('select');this.source.id='parts-source';this.source.append(new Option('Wszystkie źródła',''),new Option('Modele 3D producenta — STEP','supplier'),new Option('Biblioteka modeli T1','base'),new Option('Katalog z Excela — wszystkie pozycje','company'),new Option('Pozostałe projekty — wszystkie','source'));for(const key of [...new Set(catalog.items.flatMap(r=>r.observed_projects??(r.source_project?[r.source_project]:[])))].sort())this.source.append(new Option('Zaobserwowane w projekcie '+key,key));sourceLabel.append(this.source);
  const onlyLabel=element('label',null,'parts-only');this.only=element('input');this.only.type='checkbox';this.only.id='parts-only-selected';onlyLabel.append(this.only,document.createTextNode('Pokaż tylko wybrane'));
  this.count=element('p',null,'hint');this.count.id='parts-count';this.list=element('div');this.list.id='parts-list';
  const favoriteLabel=element('label',null,'parts-only preference-filter');this.favoritesOnly=element('input');this.favoritesOnly.type='checkbox';this.favoritesOnly.id='parts-only-favorites';favoriteLabel.append(this.favoritesOnly,document.createTextNode('Tylko ulubione'));
  const sortLabel=element('label','Kolejność');this.sort=element('select');this.sort.id='parts-sort';this.sort.append(new Option('Polecane: ulubione i często wybierane','recommended'),new Option('Najczęściej wybierane','frequent'),new Option('Nazwa A–Z','name'));sortLabel.append(this.sort);
  this.preferences=new PartPreferences(()=>this.render(),message=>{this.count.textContent=message;});
  host.append(searchLabel,categoryLabel,sourceLabel,sortLabel,onlyLabel,favoriteLabel,this.count,this.list);
  for(const control of [this.search,this.category,this.source,this.sort,this.only,this.favoritesOnly])control.addEventListener('input',()=>this.render());
  this.render();this.preferences.refresh();
 }
 setSelection(refs){this.selected=structuredClone(refs??[]);this.render();}
 toggle(row,checked){
  this.selected=this.selected.filter(r=>r.part_id!==row.id);
  if(checked)this.selected.push({part_id:row.id,revision:row.revision});
  this.onChange(structuredClone(this.selected));this.render();
 }
 image(row,small=false){
  if(!row.image){const empty=element('div',row.id==='2643'?'Brak geometrii w źródle':'Obraz do uzupełnienia','part-image-missing');return empty;}
  const button=element('button',null,'part-image-button'+(small?' compact':''));button.type='button';button.setAttribute('aria-label','Powiększ obraz '+row.id);
  const img=element('img');img.src=row.image.url;img.alt=row.name+' — '+row.image.label;img.loading='lazy';img.width=720;img.height=480;
  img.onerror=()=>{button.replaceWith(element('div','Nie udało się wczytać obrazu','part-image-missing'));};
  button.append(img);if(!small)button.append(element('span',row.image.label+' · Powiększ ↗','part-image-caption'));
  button.onclick=()=>{this.dialogTitle.textContent=(row.sku??'SKU nieustalone')+' · '+row.name;this.dialogImage.src=row.image.url;this.dialogImage.alt=img.alt;this.dialogCaption.textContent=row.image.label+'. '+row.image.source.description;this.dialog.showModal();};
  return button;
 }
 render(){
  const selected=new Set(this.selected.map(r=>r.part_id)),query=this.search.value.trim().toLocaleLowerCase('pl');
  const rows=this.preferences.sort(this.catalog.items.filter(r=>r.show_as_complete_part!==false&&( !this.category.value||r.family_id===this.category.value)
   &&(!this.source.value||(this.source.value==='supplier'?r.geometry_status==='supplier_step_display':this.source.value==='company'?r.catalog_only||r.pricing_company_id:this.source.value==='base'?!r.source_project&&!r.catalog_only&&r.geometry_status!=='supplier_step_display':this.source.value==='source'?!!r.source_project:(r.observed_projects??[r.source_project]).includes(this.source.value)))
   &&(!this.only.checked||selected.has(r.id))
   &&(!this.favoritesOnly.checked||this.preferences.stat(r.id).favorite)
   &&[r.id,r.sku,r.catalog_code_raw,r.source_project,r.name,r.manufacturer,this.catalog.categories[r.family_id],...r.aliases].filter(Boolean).join(' ').toLocaleLowerCase('pl').includes(query)),this.sort.value);
  this.count.textContent=`Widoczne: ${rows.length} / ${this.catalog.items.length} · wybrane rodzaje: ${selected.size}`;
  this.list.replaceChildren();
  if(!rows.length){this.list.append(element('p','Brak części pasujących do filtra.','hint'));return;}
  for(const row of rows){
   const card=element('article',null,'part-card'+(selected.has(row.id)?' selected':''));card.dataset.part=row.id;
   card.append(this.preferences.button(row.id,row.sku??row.catalog_code_raw??row.name),this.image(row));
   const usage=this.preferences.stat(row.id).project_count;if(usage)card.append(element('p','Wybrano w '+usage+(usage===1?' projekcie':' projektach'),'part-usage'));
   const label=element('label',null,'part-choice'),check=element('input');check.type='checkbox';check.checked=selected.has(row.id);check.disabled=!row.selectable;check.dataset.part=row.id;check.setAttribute('aria-label','Wybierz '+(row.sku??row.name));
   check.onchange=()=>this.toggle(row,check.checked);
   const title=element('div');title.append(element('b',row.sku??row.catalog_code_raw??'SKU niepotwierdzone'),element('span',row.name));label.append(check,title);card.append(label);
   card.append(element('p',`${this.catalog.categories[row.family_id]} · ${row.manufacturer??'Producent niepotwierdzony'}`,'hint'));
   const badges=element('div',null,'part-badges');badges.append(element('span',cutLabels[row.cutout_status],'part-badge'));
   badges.append(element('span',row.mounting_status==='prototype_specific'?'Dane prototypowe — do sprawdzenia w nowym układzie':'Montaż: dane niepotwierdzone','part-badge'));
   card.append(badges);
   if(row.duplicate_code)card.append(element('p','Kod występuje w kilku rekordach Excela — warianty zachowane osobno.','part-blocked'));
   if(row.source_project)card.append(element('p','Wariant źródłowy · '+row.source_project+' · kod z CAD, SKU niezatwierdzony'+(row.component_only?' · zespół / komponent, nie komplet':''),'part-blocked'));
   if(!row.selectable)card.append(element('p',row.selection_blocker,'part-blocked'));
   const details=element('details'),summary=element('summary','Szczegóły i źródło');details.append(summary,element('p',row.description),element('p',row.note));
   details.append(element('p',`Rewizja definicji: ${row.revision}. Źródło: ${row.source_document}; rozpoznanie: ${row.source_checked_on}.`,'hint'));
   if(row.observed_projects)details.append(element('p','Kod zaobserwowano w: '+row.observed_projects.join(', ')+'. Obraz przedstawia wybrany wariant '+row.source_project+'; inne wystąpienia nie zostały uznane za identyczne.','hint'));
   if(row.source_body_count!==undefined&&row.source_body_count!==null)details.append(element('p','Wybrane poddrzewo źródła: '+row.source_body_count+' brył CAD. To nie liczba kompletnych produktów. Podpis renderu wskazuje, czy pokazano całość, podczęść czy fragment profilu.','hint'));
   for(const ref of row.company_references??[])details.append(element('p','Katalog firmowy: '+ref.code+' · stan zapisany w Excelu: '+(ref.cached_stock_raw??'brak danych')+' · komórka '+ref.source_cell+(ref.cutout_note?' · wycięcie: '+ref.cutout_note:''),'hint'));
   details.append(element('p','Wybór koncepcyjny. Brak zgody na automatyczny montaż lub produkcję. Jednostka zakupowa i stan magazynowy nie są potwierdzone.','hint'));
   if(row.source_url){const a=element('a','Źródło katalogowe ↗');a.href=row.source_url;a.target='_blank';a.rel='noreferrer noopener';details.append(a);}
   if(row.image?.source.page_url){const a=element('a','Źródło zdjęcia ↗');a.href=row.image.source.page_url;a.target='_blank';a.rel='noreferrer noopener';details.append(a);}
   card.append(details);this.list.append(card);
  }
 }
 renderSummary(host,summary){
  host.replaceChildren(element('h2','Wybrane części'),element('p',`Pozycje katalogowe: ${summary.definition_count}. To rodzaje części, nie liczba zamontowanych sztuk.`,'hint'));
  if(!summary.items.length){host.append(element('p','W kroku 4 wybierz części z biblioteki.','hint'));return;}
  const list=element('div',null,'selected-parts');
  for(const row of summary.items){const chip=element('div',null,'selected-part'),definition=this.catalog.items.find(r=>r.id===row.id);if(definition?.image&&definition.show_as_complete_part!==false)chip.append(this.image(definition,true));chip.append(element('span',(row.sku??row.catalog_code_raw??'SKU nieustalone')+' · '+row.name));const remove=element('button','Usuń');remove.type='button';remove.setAttribute('aria-label','Usuń '+row.id);remove.onclick=()=>this.toggle(row,false);chip.append(remove);list.append(chip);}
  host.append(list,element('p',summary.note,'hint'));
  for(const warning of summary.warnings)host.append(element('p',warning,'notice'));
 }
}
