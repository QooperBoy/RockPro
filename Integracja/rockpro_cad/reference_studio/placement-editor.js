const faceLabels={left:'Lewa',right:'Prawa',front:'Przód',rear:'Tył',top:'Góra',bottom:'Dół'};
import {opposite,propose} from './placement_math.mjs';
function el(tag,text,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;}
function select(label,values,value,id){const l=el('label',label),e=el('select');e.id=id;for(const [v,t]of values)e.append(new Option(t,v));e.value=value;l.append(e);return [l,e];}
function number(label,value,min,max,step,id){const l=el('label',label),e=el('input');e.type='number';Object.assign(e,{value,min,max,step,id});l.append(e);return[l,e];}

export class PlacementEditor {
 constructor(host,catalog,getDraft,onChange,onSelect,onArm,onMessage){this.host=host;this.catalog=catalog;this.getDraft=getDraft;this.onChange=onChange;this.onSelect=onSelect;this.onArm=onArm;this.onMessage=onMessage;this.selected=null;this.part=null;this.defaults=null;}
 selectedRow(){return this.catalog.items.find(r=>r.id===this.part);}
 template(part){if(part.family_id==='hinges'&&this.model?.placement.joint_lines.length)return {part_id:part.id,revision:part.revision,pattern:'joint_line',joint_id:this.model.placement.joint_lines[0].id,hinge_count:2,edge_inset_mm:80};const handle=part.family_id==='handles';return {part_id:part.id,revision:part.revision,section_id:'body',face:handle?'left':'front',u:.5,v:.5,rotation_deg:0,pattern:handle?'symmetric':'single',count_per_wall:handle?2:1,opposite_wall:handle,spread:.5,...(handle?{handles_per_wall:2}:{})};}
 setModel(model){this.model=model;const selected=this.getDraft().hardware.map(r=>r.part_id);if(!selected.includes(this.part)){this.part=selected[0]??null;this.defaults=null;}if(!this.getDraft().placements?.some(g=>g.id===this.selected))this.selected=null;this.render();}
 selectGroup(id){const g=this.getDraft().placements?.find(g=>g.id===id);if(!g)return;this.selected=id;this.part=g.part_id;this.onSelect(id);this.render();}
 choosePart(id,render=true){this.part=id;this.selected=null;this.defaults=this.template(this.selectedRow());const candidates=this.model.placement.faces.filter(f=>f.section_id==='body');if(this.defaults.pattern!=='joint_line'&&!candidates.some(f=>f.face===this.defaults.face))this.defaults.face=candidates[0]?.face??'front';this.onArm(id);this.onSelect(null);if(render)this.render();}
 change(patch){if(patch.pattern==='symmetric')patch={...patch,u:.5};const d=this.getDraft(),g=d.placements?.find(g=>g.id===this.selected);if(g){Object.assign(g,patch);this.onChange();}else{this.defaults={...(this.defaults??this.template(this.selectedRow())),...patch};this.render();}}
 candidate(hit){const d=this.getDraft(),existing=d.placements?.find(g=>g.id===hit.group_id),part=this.catalog.items.find(r=>r.id===(existing?.part_id??hit.part_id));if(!part||!d.hardware.some(r=>r.part_id===part.id))return null;const base=existing??{...(this.defaults?.part_id===part.id?this.defaults:this.template(part)),id:'preview'};return propose(base,hit,this.model,!!existing);}
 drop(hit){
  if(!this.model)return;
  const d=this.getDraft(),existing=d.placements?.find(g=>g.id===hit.group_id),part=this.catalog.items.find(r=>r.id===(existing?.part_id??hit.part_id));
  if(!part||!d.hardware.some(r=>r.part_id===part.id)){this.onMessage('Najpierw wybierz część w kroku 4.');return;}
  const g=this.candidate(hit);if(!g){this.onMessage('Wskaż istniejącą ściankę/parę albo stronę zawiasów przy właściwej linii styku.');return;}
  if(!existing&&d.placements?.length>=32){this.onMessage('Maksymalnie 32 grupy okuć.');return;}
  if(existing)Object.assign(existing,g);else{g.id=crypto.randomUUID();(d.placements??=[]).push(g);}
  this.selected=g.id;this.part=part.id;this.onSelect(g.id);this.onChange();this.onMessage('Zapisano pozycję w koncepcji. Przeciągnij okucie ponownie, aby zmienić jego grupę.');
 }
 render(){
  const d=this.getDraft(),chosen=this.catalog.items.filter(r=>d.hardware.some(ref=>ref.part_id===r.id));this.host.replaceChildren();
  if(!chosen.length){this.host.append(el('p','Wybierz najpierw części w kroku 4.','notice'));return;}
  const palette=el('div',null,'placement-palette');palette.id='placement-palette';
  for(const row of chosen){const b=el('button',null,'placement-part'+(row.id===this.part?' active':''));b.type='button';b.draggable=true;b.dataset.part=row.id;b.setAttribute('aria-label','Rozmieść '+row.id);if(row.image){const img=el('img');img.src=row.image.url;img.alt='';img.draggable=false;b.append(img);}b.append(el('span',row.sku??'Koło referencyjne'));b.ondragstart=e=>{this.choosePart(row.id,false);e.dataTransfer.setData('application/x-rockpro-part',row.id);e.dataTransfer.setData('text/plain',row.id);e.dataTransfer.effectAllowed='copy';};b.onclick=()=>this.choosePart(row.id);palette.append(b);}
  this.host.append(palette);const stop=el('button','Zakończ wstawianie / obracaj widok');stop.id='placement-stop';stop.onclick=()=>this.onArm(null);this.host.append(stop);
  let g=d.placements?.find(g=>g.id===this.selected);const row=this.selectedRow();if(!row)return;const value=g??this.defaults??this.template(row),handle=row.family_id==='handles';
  const form=el('div',null,'placement-form');form.append(el('h2',g?'Edycja grupy · '+row.id:'Nowa grupa · '+row.id));
  if(row.family_id==='hinges'){
   if(value.pattern!=='joint_line'&&this.model.placement.joint_lines.length){const bind=el('button','Rozmieść równo na linii zawiasów');bind.onclick=()=>{const replacement={...this.template(row),...(g?{id:g.id}:{})};if(g){d.placements=d.placements.map(p=>p.id===g.id?replacement:p);this.onChange();}else{this.defaults=replacement;this.render();}};form.append(bind);}
   if(value.pattern==='joint_line'){this.renderJoint(form,value,g);this.host.append(form);this.renderGroups(d);return;}
  }
  const target=value.section_id+'/'+value.face,targets=this.model.placement.faces.map(f=>[f.key,f.label]);if(!targets.some(([key])=>key===target))targets.unshift([target,'Brak dawnej ścianki — wybierz nową']);
  const [tl,ti]=select('Sekcja i ścianka',targets,target,'placement-target');ti.onchange=()=>{const f=this.model.placement.faces.find(f=>f.key===ti.value);this.change({section_id:f.section_id,face:f.face});};form.append(tl);
  let ci,cl;
  if(handle)[cl,ci]=select('Uchwyty na każdą ściankę',Array.from({length:16},(_,i)=>[i+1,String(i+1)]),value.handles_per_wall,'handles-per-wall');
  else [cl,ci]=number('Liczba na każdą ściankę',value.count_per_wall,1,16,1,'placement-count');
  ci.onchange=()=>{const n=Number(ci.value);if(!Number.isInteger(n)||n<1||n>16)return;this.change({count_per_wall:n,...(handle?{handles_per_wall:n}:{}),pattern:value.pattern==='symmetric'?'symmetric':n===1?'single':'row'});};form.append(cl);
  for(const [label,key,checked,id]of[['Symetrycznie względem środka ścianki','symmetry',value.pattern==='symmetric','placement-symmetry'],['Także na przeciwległej ściance tej sekcji','opposite_wall',value.opposite_wall,'placement-opposite']]){const l=el('label',null,'placement-check'),c=el('input');c.type='checkbox';c.id=id;c.checked=checked;c.onchange=()=>this.change(key==='symmetry'?{pattern:c.checked?'symmetric':value.count_per_wall===1?'single':'row'}:{opposite_wall:c.checked});l.append(c,document.createTextNode(label));form.append(l);}
  const position=el('div',null,'dimensions two');
  for(const [label,key,val,id]of[['Poziom środka grupy [%]','u',value.pattern==='symmetric'?50:value.u*100,'placement-u'],[value.face==='top'||value.face==='bottom'?'Pozycja w głąb ścianki [%]':'Wysokość na ściance [%]','v',value.v*100,'placement-v'],['Rozstaw skrajnych [% szerokości]','spread',value.spread*100,'placement-spread']]){const [l,e]=number(label,Number(val.toFixed(2)),0,100,.1,id);e.disabled=(key==='u'&&value.pattern==='symmetric')||(key==='spread'&&value.count_per_wall===1);e.onchange=()=>{const n=Number(e.value);if(e.value!==''&&Number.isFinite(n)&&n>=0&&n<=100)this.change({[key]:n/100});};position.append(l);}
  const [rl,ri]=select('Obrót w płaszczyźnie ścianki',[[0,'0°'],[90,'90°'],[180,'180°'],[270,'270°']],value.rotation_deg,'placement-rotation');ri.onchange=()=>this.change({rotation_deg:Number(ri.value)});position.append(rl);form.append(position);
  const add=el('button',g?'Dodaj kolejną taką grupę':'Dodaj na wybranej ściance','primary');add.id='placement-add';add.onclick=()=>{const old=this.selected;this.selected=null;this.defaults=structuredClone(value);this.drop({part_id:row.id,section_id:value.section_id,face:value.face,u:value.pattern==='symmetric'&&value.count_per_wall>1?.5-value.spread/2:value.u,v:value.v});if(!this.selected)this.selected=old;};form.append(add);
  form.append(el('p',`${value.count_per_wall*(value.opposite_wall?2:1)} szt. w grupie · ${value.count_per_wall} na ściankę${value.opposite_wall?' × 2 przeciwległe ścianki':''}. To liczba w koncepcji, nie ilość zakupowa.`,'hint'));this.host.append(form);
  this.renderGroups(d);
 }
 renderJoint(form,value,g){
  const targets=this.model.placement.joint_lines.map(j=>[j.id,j.label]);if(!targets.some(([id])=>id===value.joint_id))targets.unshift([value.joint_id,'Brak dawnej linii — wybierz otwieraną pokrywę']);
  const [jl,ji]=select('Linia styku dla zawiasów',targets,value.joint_id,'hinge-joint');ji.onchange=()=>this.change({joint_id:ji.value});form.append(jl);
  for(const [label,key,id,min,max]of[['Liczba zawiasów na linii','hinge_count','hinge-count',1,16],['Odsunięcie skrajnych osi od końców [mm]','edge_inset_mm','hinge-inset',0,5000]]){const [l,e]=number(label,value[key],min,max,key==='hinge_count'?1:.1,id);e.onchange=()=>{const n=Number(e.value);if(e.value!==''&&Number.isFinite(n)&&n>=min&&n<=max&&(key!=='hinge_count'||Number.isInteger(n)))this.change({[key]:n});};form.append(l);}
  form.append(el('p','Równy rozstaw pomiędzy skrajnymi osiami. Jeden zawias trafia na środek. Linia i orientacja wynikają z rodzaju pokrywy i strony zawiasów w kroku 2.','hint'));
  const add=el('button',g?'Dodaj kolejny rząd':'Dodaj rząd zawiasów','primary');add.id='hinge-add';add.onclick=()=>{const d=this.getDraft();if((d.placements?.length??0)>=32)return;const copy={...structuredClone(value),id:crypto.randomUUID()};(d.placements??=[]).push(copy);this.selected=copy.id;this.onChange();};form.append(add);
 }
 renderGroups(d){
  const list=el('div',null,'placement-groups');list.id='placement-groups';list.append(el('h2','Grupy rozmieszczenia'));
  for(const group of d.placements??[]){const line=el('div',null,'placement-group'+(group.id===this.selected?' active':''));const b=el('button',group.part_id+' · '+(group.pattern==='joint_line'?'Linia zawiasów · '+group.hinge_count:faceLabels[group.face]+(group.opposite_wall?' + '+faceLabels[opposite[group.face]]:'')+' · '+group.count_per_wall*(group.opposite_wall?2:1))+' szt.');b.type='button';b.dataset.group=group.id;b.onclick=()=>this.selectGroup(group.id);const remove=el('button','Usuń');remove.setAttribute('aria-label','Usuń grupę '+group.id);remove.onclick=()=>{d.placements=d.placements.filter(g=>g.id!==group.id);if(this.selected===group.id)this.selected=null;this.onSelect(this.selected);this.onChange();};line.append(b,remove);list.append(line);}this.host.append(list);
  const warnings=el('div');warnings.id='placement-warnings';warnings.setAttribute('role','status');
  const unique=new Set();for(const w of this.model.placement.warnings){if(unique.has(w.message))continue;unique.add(w.message);warnings.append(el('p',w.message,'notice'));}
  if(!unique.size&&this.model.placement.items.length)warnings.append(el('p','Znane obrysy 2D mieszczą się na ściankach. Pozostałe obrysy, ruch zawiasów i wycięcia wymagają dalszej kontroli.','hint'));
  this.host.append(warnings);
 }
}
