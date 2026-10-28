import {estimateCosts} from './cost_math.mjs';
const node=(tag,value)=>{const n=document.createElement(tag);if(value!==undefined)n.textContent=value;return n;};
const money=value=>value===null?'—':new Intl.NumberFormat('pl-PL',{minimumFractionDigits:2,maximumFractionDigits:2}).format(value);
let latest,catalog,error;
const host=node('section');host.id='cost-summary';host.className='cost-summary';
host.append(node('h2','Podsumowanie cenowe części'));
const label=node('label'),assume=node('input');assume.type='checkbox';assume.checked=true;assume.id='cost-assume-piece';
label.append(assume,document.createTextNode(' Szacuj cenę okuć za sztukę'));host.append(label);
const body=node('div');body.id='cost-results';host.append(body);document.getElementById('step-7')?.append(host);
function render(){
 if(error){body.replaceChildren(node('p','Nie udało się odczytać cen: '+error));return;}
 if(!latest||!catalog){body.replaceChildren(node('p','Przygotowanie zestawienia…'));return;}
 const estimate=estimateCosts(latest.project_summary,catalog,assume.checked);body.replaceChildren();
 body.append(node('p','Orientacyjna, częściowa wycena. Arkusz nie określa waluty, netto/brutto ani wszystkich jednostek cen. Założenie ceny za sztukę dotyczy tylko okuć. Profile, płyty i pianki wymagają potwierdzenia jednostek oraz przypisania materiału.'));
 const wrap=node('div');wrap.className='cost-table-wrap';const table=node('table'),head=node('tr');
 for(const title of ['Część','Ilość','Cena / jedn.','Wartość','Uwagi'])head.append(node('th',title));table.append(head);
 for(const row of estimate.rows){const tr=node('tr');tr.append(node('td',row.name+' · '+row.part_id),node('td',row.quantity+' '+row.unit),node('td',money(row.price)),node('td',money(row.amount)),node('td',row.reason||(row.assumedUnit?'Przyjęto cenę za sztukę':'Cena i jednostka z katalogu')));table.append(tr);}
 wrap.append(table);body.append(wrap);
 for(const total of estimate.totals){const sum=node('p','Suma wycenionych pozycji: '+money(total.amount)+' · '+total.currency);sum.className='cost-subtotal';sum.dataset.amount=String(total.amount);body.append(sum);}
 if(!estimate.totals.length)body.append(node('p','Brak pozycji z potwierdzoną ceną i przyjętą jednostką.'));
 const missing=node('p','Pozycje bez wyceny: '+estimate.unpriced+' z '+estimate.rows.length+'. Kwota nie jest kosztem całej skrzyni.');missing.id='cost-coverage';body.append(missing);
}
assume.onchange=render;
document.addEventListener('rockpro:preview',event=>{latest=event.detail;render();});
document.addEventListener('rockpro:preview-pending',()=>{latest=null;render();});
fetch('company/catalog').then(r=>{if(!r.ok)throw Error('katalog niedostępny');return r.json();}).then(data=>{catalog=data;render();}).catch(e=>{error=e.message;render();});
