const node=(tag,text,cls)=>{const el=document.createElement(tag);if(text)el.textContent=text;if(cls)el.className=cls;return el;};
export class ReviewPanel{
 constructor(host,getDraft,onGoto,onReport){this.host=host;this.getDraft=getDraft;this.onGoto=onGoto;this.onReport=onReport;this.serial=0;this.report=null;}
 invalidate(){this.serial++;this.report=null;this.host.replaceChildren(node('p','Projekt zmieniono. Otwórz kontrolę, aby przeliczyć wyniki.'));}
 async check(){
  const version=++this.serial,draft=this.getDraft();this.host.replaceChildren(node('p','Sprawdzanie danych, rozmieszczenia i obrysów…'));
  try{const response=await fetch('wizard/review',{method:'POST',headers:{'Content-Type':'application/json','X-RockPro-Session':location.pathname.split('/').filter(Boolean)[0]},body:JSON.stringify(draft)}),data=await response.json();if(version!==this.serial)return;if(!response.ok)throw Error(data.error||'Nie można wykonać kontroli');this.report=data;this.render();}
  catch(error){if(version===this.serial){this.host.replaceChildren(node('p','Nie wykonano kontroli: '+error.message,'notice error'));this.retry();}}
 }
 retry(){const button=node('button','Sprawdź ponownie');button.type='button';button.id='review-refresh';button.onclick=()=>this.check();this.host.append(button);}
 render(){
  const r=this.report;this.onReport?.(r);this.host.replaceChildren();const summary=node('div',null,'review-overview '+r.status);summary.id='review-overview';
  summary.append(node('h2',r.counts.error?'Wykryto problemy do poprawy':r.counts.warning?'Projekt wymaga uzupełnienia':'Nie wykryto błędów w kontroli koncepcji'));
  summary.append(node('p',r.counts.error+' błędów · '+r.counts.warning+' ostrzeżeń · '+(r.part_count??'—')+' części'));this.host.append(summary);
  const steps=node('div',null,'review-steps');for(const item of r.steps){const b=node('button',item.step+'. '+item.label+' · '+({checked:'sprawdzono',attention:'uzupełnij',blocked:'popraw',pending:'oczekuje'}[item.status]));b.dataset.reviewStep=item.step;b.className=item.status;b.onclick=()=>this.onGoto({step:item.step});steps.append(b);}this.host.append(steps);
  for(const [severity,title]of [['error','Błędy'],['warning','Braki i ostrzeżenia'],['info','Dalsze sprawdzenia']]){
   const rows=r.issues.filter(i=>i.severity===severity);if(!rows.length)continue;
   const section=severity==='info'?node('details'):node('section');section.className='review-issues '+severity;
   section.append(node(severity==='info'?'summary':'h2',title+' ('+rows.length+')'));
   for(const issue of rows){const article=node('article',null,'review-issue');article.dataset.issueCode=issue.code;
    article.append(node('p',issue.message));const actions=node('div',null,'row');const go=node('button','Krok '+issue.step+' · przejdź do poprawy');go.dataset.reviewTarget=issue.group_id??issue.section_id??issue.code;go.onclick=()=>this.onGoto(issue);actions.append(go);
    if(issue.other_group_id){const other=node('button','Pokaż drugą część');other.onclick=()=>this.onGoto({...issue,group_id:issue.other_group_id});actions.append(other);}article.append(actions);section.append(article);
   }this.host.append(section);
  }
  this.host.append(node('p','Sprawdzamy znane obrysy 2D na wspólnych ścianach. Brak zgłoszeń nie zastępuje kontroli konstrukcyjnej w IronCAD.','hint'));this.retry();
 }
}
