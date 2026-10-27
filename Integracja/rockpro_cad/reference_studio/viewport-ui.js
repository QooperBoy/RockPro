import * as THREE from './vendor/three.module.min.js';
import {ViewportGizmo} from './vendor/three-viewport-gizmo.js';
import {stopOrbitMotion} from './scene-controls.js';

const paths={
 fit:'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M8 8h8v8H8z',
 home:'m3 10 9-7 9 7M5 9v12h14V9M9 21v-8h6v8',
 open:'M4 11h16v10H4zM4 11l3-8 14 4-1 4M8 15h8',
 close:'M4 8h16v13H4zM3 8l3-5h12l3 5M9 14h6',
 grid:'M3 3h18v18H3zM3 9h18M3 15h18M9 3v18M15 3v18',
 label:'M3 5h18v14H3zM7 9h10M7 13h7',
 help:'M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 4M12 18h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 expand:'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5',
 select:'m5 3 14 10-7 1-3 7z',save:'M4 3h13l4 4v14H3V3zM7 3v6h10V3M7 21v-7h10v7',
 chevron:'m9 5 7 7-7 7',box:'m3 7 9-4 9 4v10l-9 4-9-4zM3 7l9 4 9-4M12 11v10',
 hand:'M8 12V5a2 2 0 0 1 4 0v6-7a2 2 0 0 1 4 0v7-4a2 2 0 0 1 4 0v9l-3 5H9l-5-7a2 2 0 0 1 3-3l1 1',
 check:'m5 12 4 4L19 6'
};
export function icon(name){const e=document.createElementNS('http://www.w3.org/2000/svg','svg');e.setAttribute('viewBox','0 0 24 24');e.setAttribute('fill','none');e.setAttribute('stroke','currentColor');e.setAttribute('stroke-width','1.7');e.setAttribute('stroke-linecap','round');e.setAttribute('stroke-linejoin','round');e.setAttribute('aria-hidden','true');const p=document.createElementNS(e.namespaceURI,'path');p.setAttribute('d',paths[name]??paths.box);e.append(p);return e;}
const node=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text)e.textContent=text;return e;};
const directions={front:{name:'Przód',short:'Pr',axis:[0,-1,0],color:'y'},rear:{name:'Tył',short:'Ty',axis:[0,1,0],color:'y'},left:{name:'Lewa',short:'L',axis:[-1,0,0],color:'x'},right:{name:'Prawa',short:'P',axis:[1,0,0],color:'x'},top:{name:'Góra',short:'G',axis:[0,0,1],color:'z'},bottom:{name:'Dół',short:'D',axis:[0,0,-1],color:'z'}};

export class ViewportUI{
 constructor(view){
  this.view=view;this.host=view.host;this.labels=true;this.lastQ=new THREE.Quaternion(0,0,0,0);this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  this.toolbar=node('div','viewport-tools');this.toolbar.setAttribute('role','toolbar');this.toolbar.setAttribute('aria-orientation','vertical');this.toolbar.setAttribute('aria-label','Narzędzia widoku 3D');
  const tool=(id,name,label,action,toggle=false)=>{const b=document.getElementById(id)??node('button');b.id=id;b.type='button';b.replaceChildren(icon(name));b.setAttribute('aria-label',label);b.dataset.tooltip=label;b.title=label;b.tabIndex=this.toolbar.children.length? -1:0;if(toggle)b.setAttribute('aria-pressed','true');if(action)b.onclick=action;this.toolbar.append(b);return b;};
  this.home=tool('view-home','home','Widok przestrzenny · 0',()=>this.snap('iso'));
  tool('fit','fit','Dopasuj model · F');
  tool('open-all','open','Otwórz wszystkie wieka');tool('close-all','close','Zamknij wszystkie wieka');
  this.grid=tool('view-grid','grid','Pokaż lub ukryj siatkę',()=>{view.grid.visible=!view.grid.visible;this.grid.setAttribute('aria-pressed',String(view.grid.visible));},true);
  this.tags=tool('view-labels','label','Pokaż lub ukryj nazwy ścianek',()=>{this.labels=!this.labels;view.root.traverse(o=>{if(o.userData.faceLabel)o.visible=this.labels;});this.tags.setAttribute('aria-pressed',String(this.labels));},true);
  this.expand=tool('view-expand','expand','Powiększ obszar roboczy',()=>{const expanded=document.body.classList.toggle('viewport-expanded');this.expand.setAttribute('aria-pressed',String(expanded));view.resize();});this.expand.setAttribute('aria-pressed','false');
  this.help=tool('view-help','help','Sterowanie i skróty · ?',()=>{this.helpPanel.hidden=!this.helpPanel.hidden;this.help.setAttribute('aria-expanded',String(!this.helpPanel.hidden));});this.help.setAttribute('aria-expanded','false');
  this.toolbar.addEventListener('focusin',e=>{for(const b of this.toolbar.children)b.tabIndex=b===e.target?0:-1;e.target.removeAttribute('data-tip-hidden');});
  this.toolbar.addEventListener('pointerover',e=>e.target.closest('button')?.removeAttribute('data-tip-hidden'));
  this.toolbar.addEventListener('keydown',e=>{const buttons=[...this.toolbar.children],i=buttons.indexOf(document.activeElement);let next=null;if(['ArrowDown','ArrowRight'].includes(e.key))next=(i+1)%buttons.length;if(['ArrowUp','ArrowLeft'].includes(e.key))next=(i+buttons.length-1)%buttons.length;if(e.key==='Home')next=0;if(e.key==='End')next=buttons.length-1;if(next!==null){e.preventDefault();buttons[next].focus();}});
  this.host.append(this.toolbar);
  this.helpPanel=node('div','viewport-help');this.helpPanel.hidden=true;this.helpPanel.id='viewport-help';this.help.setAttribute('aria-controls',this.helpPanel.id);
  const title=node('strong',null,'Sterowanie w przestrzeni 3D');this.helpPanel.append(title);
  for(const [keys,meaning]of [['Środkowy przycisk','Obracanie modelu'],['Prawy przycisk','Przesuwanie widoku'],['Rolka','Przybliżanie / oddalanie'],['Lewy przycisk','Wybór i rozmieszczanie części'],['F / 0','Dopasuj / widok przestrzenny'],['1 / 2 / 3','Przód / prawa / góra'],['Esc','Anuluj wstawianie i zamknij pomoc']]){const row=node('div');row.append(node('kbd',null,keys),node('span',null,meaning));this.helpPanel.append(row);}this.host.append(this.helpPanel);
  THREE.Object3D.DEFAULT_UP.set(0,0,1);
  this.gizmo=new ViewportGizmo(view.camera,view.renderer,{type:'cube',radius:.03,container:this.host,size:128,placement:'top-right',offset:{top:15,right:15},animated:!this.reduced,speed:1.5,id:'view-cube',className:'standard-view-cube',
   x:{label:'PRAWA',scale:1,border:{size:1,color:0xcad4ce},color:0xf1f4f2,hover:{color:0xf4cfaa,scale:1}},nx:{label:'LEWA',scale:1,color:0xf1f4f2,hover:{color:0xf4cfaa,scale:1}},
   y:{label:'TYŁ',scale:1,color:0xf1f4f2,hover:{color:0xf4cfaa,scale:1}},ny:{label:'PRZÓD',scale:1,color:0xf1f4f2,hover:{color:0xf4cfaa,scale:1}},
   z:{label:'GÓRA',scale:1,color:0xf1f4f2,hover:{color:0xf4cfaa,scale:1}},nz:{label:'DÓŁ',scale:1,color:0xf1f4f2,hover:{color:0xf4cfaa,scale:1}},
   background:{enabled:false},font:{family:'Segoe UI,Arial',weight:600},corners:{enabled:true,opacity:0,color:0xc8d3cc,hover:{color:0xdb681f,opacity:1}},edges:{enabled:true,opacity:0,hover:{color:0xdb681f,opacity:1}}});
  this.gizmo.attachControls(view.controls);
  this.gizmo.addEventListener('start',()=>{if(this.tween){view.controls.enableDamping=this.tween.damping;this.tween=null;}document.dispatchEvent(new CustomEvent('rockpro:stop-placement'));view.controls.enabled=false;});
  document.getElementById('view-cube').setAttribute('aria-label','Kostka widoków — kliknij ścianę, krawędź lub narożnik');
  this.cubeMenu=node('div','cube-menu');this.compassLabel=node('select','cube-view-select');this.compassLabel.setAttribute('aria-label','Ustaw widok kamery');this.compassLabel.append(new Option('Widok 3D','iso'),...Object.entries(directions).map(([key,d])=>new Option(d.name,key)));this.compassLabel.onchange=()=>this.snap(this.compassLabel.value);this.cubeMenu.append(this.compassLabel);this.host.append(this.cubeMenu);
  this.cubeHome=node('button','cube-home');this.cubeHome.type='button';this.cubeHome.setAttribute('aria-label','Widok przestrzenny');this.cubeHome.title='Widok przestrzenny';this.cubeHome.append(icon('home'));this.cubeHome.onclick=()=>this.snap('iso');this.host.append(this.cubeHome);
  window.addEventListener('scroll',()=>this.gizmo.domUpdate(),{passive:true});
  this.hud=node('div','viewport-hud');this.hud.append(icon('box'),node('span',null,'Podgląd koncepcji'));this.hudText=this.hud.lastChild;this.host.append(this.hud);
  this.selection=node('div','viewport-selection');this.selection.hidden=true;this.selection.setAttribute('role','status');this.selectionText=node('span');this.selection.append(icon('select'),this.selectionText);const finish=node('button',null,'Zakończ · Esc');finish.onclick=()=>document.dispatchEvent(new CustomEvent('rockpro:stop-placement'));this.selection.append(finish);this.host.append(this.selection);
  document.addEventListener('keydown',e=>{if(e.target.closest('input,select,textarea,[contenteditable="true"]')||e.ctrlKey||e.metaKey||e.altKey)return;if(e.key==='Escape'){for(const b of this.toolbar.children)b.dataset.tipHidden='true';this.helpPanel.hidden=true;this.help.setAttribute('aria-expanded','false');if(document.body.classList.contains('viewport-expanded'))this.expand.click();}else if(e.key.toLowerCase()==='f'){e.preventDefault();document.getElementById('fit').click();}else if(['0','1','2','3'].includes(e.key)){e.preventDefault();this.snap({'0':'iso','1':'front','2':'right','3':'top'}[e.key]);}else if(e.key==='?'){e.preventDefault();this.help.click();}});
  this.host.addEventListener('pointerdown',e=>{if(e.target.closest('.viewport-tools,.standard-view-cube,.cube-menu,.cube-home'))document.dispatchEvent(new CustomEvent('rockpro:stop-placement'));});
 }
 frame(direction=null,animated=true){
  const v=this.view;if(!v.model)return;document.dispatchEvent(new CustomEvent('rockpro:stop-placement'));stopOrbitMotion(v.controls);
  const box=new THREE.Box3().setFromObject(v.root),sphere=box.getBoundingSphere(new THREE.Sphere()),center=sphere.center;
  const angle=Math.min(THREE.MathUtils.degToRad(v.camera.fov),2*Math.atan(Math.tan(THREE.MathUtils.degToRad(v.camera.fov/2))*v.camera.aspect));
  const distance=sphere.radius/Math.sin(angle/2)*1.13,axis=direction??v.camera.position.clone().sub(v.controls.target).normalize();
  const end=center.clone().add(axis.clone().normalize().multiplyScalar(distance));
  if(this.tween){v.controls.enableDamping=this.tween.damping;v.controls.enabled=this.tween.enabled;this.tween=null;}
  if(animated&&!this.reduced){this.tween={start:performance.now(),from:v.camera.position.clone(),targetFrom:v.controls.target.clone(),to:end,targetTo:center,damping:v.controls.enableDamping,enabled:v.controls.enabled};v.controls.enableDamping=false;v.controls.enabled=false;}
  else{v.camera.position.copy(end);v.controls.target.copy(center);v.controls.update();}
 }
 snap(key){const axis=key==='iso'?new THREE.Vector3(1.4,-2.2,1.5):new THREE.Vector3(...directions[key].axis);if(key==='top'||key==='bottom')axis.y=-.0001;this.frame(axis);}
 update(){
  const v=this.view;
  if(this.tween){const t=this.tween,p=Math.min(1,(performance.now()-t.start)/260),ease=p*p*(3-2*p);v.camera.position.lerpVectors(t.from,t.to,ease);v.controls.target.lerpVectors(t.targetFrom,t.targetTo,ease);v.controls.update();if(p===1){v.controls.enableDamping=t.damping;v.controls.enabled=t.enabled;this.tween=null;}}
  if(!this.lastQ.equals(v.camera.quaternion)){
   this.lastQ.copy(v.camera.quaternion);const inv=v.camera.quaternion.clone().invert();let nearest=null,best=.985;
   for(const [key,d]of Object.entries(directions)){const p=new THREE.Vector3(...d.axis).applyQuaternion(inv);if(p.z>best){best=p.z;nearest=key;}}
   this.compassLabel.value=nearest??'iso';
  }
 }
 render(){this.gizmo.render();}
 setContext(step,model){const names=['','Konstrukcja','Wieka i współpraca','Wymiary','Biblioteka części','Uchwyty i ścianki','Zatrzaski i zawiasy'];this.hudText.textContent=names[step]+' · '+model.draft.internal_mm.join(' × ')+' mm wewnątrz';vLabels(this.view,this.labels);}
 setSelection(text){this.selection.hidden=!text;this.selectionText.textContent=text??'';}
}
function vLabels(view,value){view.root.traverse(o=>{if(o.userData.faceLabel)o.visible=value;});}
