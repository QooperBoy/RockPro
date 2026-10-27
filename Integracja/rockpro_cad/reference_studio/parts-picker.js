// Step 4 selects versioned definitions. Placement and quantities belong to step 5.
function element(tag,text,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;}
const cutLabels={required:'Wycięcie w sklejce: wymagane',none:'Wycięcie w sklejce: niewymagane',unknown:'Wycięcie w sklejce: do ustalenia'};

export class PartsPicker {
 constructor(host,catalog,onChange){
  this.host=host;this.catalog=catalog;this.onChange=onChange;this.selected=[];
  host.append(element('p',`Baza robocza: ${catalog.items.length} pozycji z dotychczasowych źródeł i prototypów. Pełny katalog firmy zostanie dołączony później.`,'hint'));
  const searchLabel=element('label','Szukaj części');this.search=element('input');this.search.type='search';this.search.id='parts-search';this.search.placeholder='SKU, nazwa, producent lub alias CAD';searchLabel.append(this.search);
  const categoryLabel=element('label','Kategoria');this.category=element('select');this.category.id='parts-category';
  this.category.append(new Option('Wszystkie kategorie',''));for(const [id,label]of Object.entries(catalog.categories))this.category.append(new Option(label,id));categoryLabel.append(this.category);
  const onlyLabel=element('label',null,'parts-only');this.only=element('input');this.only.type='checkbox';this.only.id='parts-only-selected';onlyLabel.append(this.only,document.createTextNode('Pokaż tylko wybrane'));
  this.count=element('p',null,'hint');this.count.id='parts-count';this.list=element('div');this.list.id='parts-list';
  host.append(searchLabel,categoryLabel,onlyLabel,this.count,this.list);
  for(const control of [this.search,this.category,this.only])control.addEventListener('input',()=>this.render());
  this.render();
 }
 setSelection(refs){this.selected=structuredClone(refs??[]);this.render();}
 toggle(row,checked){
  this.selected=this.selected.filter(r=>r.part_id!==row.id);
  if(checked)this.selected.push({part_id:row.id,revision:row.revision});
  this.onChange(structuredClone(this.selected));this.render();
 }
 render(){
  const selected=new Set(this.selected.map(r=>r.part_id)),query=this.search.value.trim().toLocaleLowerCase('pl');
  const rows=this.catalog.items.filter(r=>(!this.category.value||r.family_id===this.category.value)
   &&(!this.only.checked||selected.has(r.id))
   &&[r.id,r.sku,r.name,r.manufacturer,this.catalog.categories[r.family_id],...r.aliases].filter(Boolean).join(' ').toLocaleLowerCase('pl').includes(query));
  this.count.textContent=`Widoczne: ${rows.length} / ${this.catalog.items.length} · wybrane rodzaje: ${selected.size}`;
  this.list.replaceChildren();
  if(!rows.length){this.list.append(element('p','Brak części pasujących do filtra.','hint'));return;}
  for(const row of rows){
   const card=element('article',null,'part-card'+(selected.has(row.id)?' selected':''));card.dataset.part=row.id;
   const label=element('label',null,'part-choice'),check=element('input');check.type='checkbox';check.checked=selected.has(row.id);check.disabled=!row.selectable;check.dataset.part=row.id;check.setAttribute('aria-label','Wybierz '+(row.sku??row.name));
   check.onchange=()=>this.toggle(row,check.checked);
   const title=element('div');title.append(element('b',row.sku??'SKU niepotwierdzone'),element('span',row.name));label.append(check,title);card.append(label);
   card.append(element('p',`${this.catalog.categories[row.family_id]} · ${row.manufacturer??'Producent niepotwierdzony'}`,'hint'));
   const badges=element('div',null,'part-badges');badges.append(element('span',cutLabels[row.cutout_status],'part-badge'));
   badges.append(element('span',row.mounting_status==='prototype_specific'?'Dane prototypowe — do sprawdzenia w nowym układzie':'Montaż: dane niepotwierdzone','part-badge'));
   card.append(badges);
   if(!row.selectable)card.append(element('p',row.selection_blocker,'part-blocked'));
   const details=element('details'),summary=element('summary','Szczegóły i źródło');details.append(summary,element('p',row.description),element('p',row.note));
   details.append(element('p',`Rewizja definicji: ${row.revision}. Źródło: ${row.source_document}; rozpoznanie: ${row.source_checked_on}.`,'hint'));
   details.append(element('p','Wybór koncepcyjny. Brak zgody na automatyczny montaż lub produkcję. Jednostka zakupowa i stan magazynowy nie są potwierdzone.','hint'));
   if(row.source_url){const a=element('a','Źródło katalogowe ↗');a.href=row.source_url;a.target='_blank';a.rel='noreferrer noopener';details.append(a);}
   card.append(details);this.list.append(card);
  }
 }
 renderSummary(host,summary){
  host.replaceChildren(element('h2','Wybrane części'),element('p',`Pozycje katalogowe: ${summary.definition_count}. To rodzaje części, nie liczba zamontowanych sztuk.`,'hint'));
  if(!summary.items.length){host.append(element('p','W kroku 4 wybierz części z biblioteki.','hint'));return;}
  const list=element('div',null,'selected-parts');
  for(const row of summary.items){const chip=element('div',null,'selected-part');chip.append(element('span',(row.sku??'SKU nieustalone')+' · '+row.name));const remove=element('button','Usuń');remove.type='button';remove.setAttribute('aria-label','Usuń '+row.id);remove.onclick=()=>this.toggle(row,false);chip.append(remove);list.append(chip);}
  host.append(list,element('p',summary.note,'hint'));
  for(const warning of summary.warnings)host.append(element('p',warning,'notice'));
 }
}
