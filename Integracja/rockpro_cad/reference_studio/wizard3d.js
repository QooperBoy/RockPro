import * as THREE from './vendor/three.module.min.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {ViewportUI} from './viewport-ui.js';
import {configureOrbit,stopOrbitMotion} from './scene-controls.js';

export class ConceptView {
 constructor(host){
  this.host=host;this.scene=new THREE.Scene();this.scene.background=new THREE.Color(0xe9eee5);
  this.camera=new THREE.PerspectiveCamera(38,1,.005,200);this.camera.up.set(0,0,1);
  this.renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));
  this.renderer.toneMapping=THREE.ACESFilmicToneMapping;host.append(this.renderer.domElement);
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);configureOrbit(this.controls);
  this.scene.add(new THREE.HemisphereLight(0xffffff,0x657460,2));const light=new THREE.DirectionalLight(0xffffff,2.5);light.position.set(2,-3,5);this.scene.add(light);
  this.grid=new THREE.GridHelper(20,100,0x95a88d,0xcad5c2);this.grid.rotation.x=Math.PI/2;this.scene.add(this.grid);
  this.root=new THREE.Group();this.scene.add(this.root);this.groups=new Map();this.values={};this.faceTextures=new Map();
  this.chrome=new ViewportUI(this);
  new ResizeObserver(()=>this.resize()).observe(host);this.resize();
  this.renderer.setAnimationLoop(()=>{this.beforeRender?.();this.controls.update();this.chrome.update();this.renderer.render(this.scene,this.camera);});
 }
 resize(){const w=this.host.clientWidth,h=this.host.clientHeight;if(!w||!h)return;const oldAspect=this.camera.aspect;this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();if(this.model&&Math.abs(oldAspect-this.camera.aspect)>.02)this.chrome.frame(null,false);}
 setModel(model){
  const previous=this.values,hadModel=!!this.model;this.root.traverse(o=>{if(o.userData.sharedResources)return;o.geometry?.dispose();if(Array.isArray(o.material))o.material.forEach(m=>m.dispose());else o.material?.dispose();});this.root.clear();this.groups.clear();this.model=model;
  const body=model.sections[0].size_mm.map(v=>v/1000);this.values={};
  for(const s of model.sections){
   const group=new THREE.Group();let pivot=[0,0,0],axis=2,direction=1;
   if(s.id!=='body'){
    const lo=s.position_mm.map(v=>v/1000),size=s.size_mm.map(v=>v/1000),high=s.hinge_edge==='high';
    if(s.face==='top'){pivot=[lo[0],lo[1]+(high?size[1]:0),lo[2]];axis=0;direction=high?-1:1;}
    else if(s.face==='front'||s.face==='rear'){pivot=[lo[0]+(high?size[0]:0),lo[1]+(s.face==='front'?size[1]:0),lo[2]];axis=2;direction=(high?1:-1)*(s.face==='front'?1:-1);}
    else{pivot=[lo[0]+(s.face==='left'?size[0]:0),lo[1]+(high?size[1]:0),lo[2]];axis=2;direction=(high?-1:1)*(s.face==='left'?1:-1);}
    this.values[s.id]=previous[s.id]??0;
   }
   group.position.fromArray(pivot);group.userData={section:s,pivot,axis,direction};this.root.add(group);this.groups.set(s.id,group);
  }
  for(const [panelIndex,p] of model.panels.entries()){
   const group=this.groups.get(p.section),pivot=group.userData.pivot;
   const geometry=new THREE.BoxGeometry(...p.size_mm.map(v=>v/1000));
   const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:p.section==='body'?0x408080:0x5a9891,roughness:.85,metalness:0}));
   mesh.userData.panelIndex=panelIndex;
   mesh.position.fromArray(p.center_mm.map((v,k)=>v/1000-pivot[k]));group.add(mesh);
   const edges=new THREE.LineSegments(new THREE.EdgesGeometry(geometry),new THREE.LineBasicMaterial({color:0x294e47,transparent:true,opacity:.55}));edges.position.copy(mesh.position);group.add(edges);
  }
  this.addFaceLabels(model);
 // Topology edits reset opening state: old motion cannot bypass new dependencies.
  this.values=Object.fromEntries(model.sections.slice(1).map(s=>[s.id,0]));this.apply();if(hadModel)this.chrome.frame(null,false);else this.fit();
  this.grid.position.set(body[0]/2,body[1]/2,-.002);this.grid.scale.setScalar(Math.max(...body)/4);
 }
 faceTexture(face){
  if(!this.faceTextures.has(face)){
   const names={front:'PRZÓD',rear:'TYŁ',left:'LEWA',right:'PRAWA',top:'GÓRA',bottom:'DÓŁ'};
   const canvas=document.createElement('canvas');canvas.width=512;canvas.height=128;
   const ctx=canvas.getContext('2d');ctx.fillStyle='rgba(23,55,49,.88)';ctx.fillRect(4,4,504,120);
   ctx.strokeStyle='#a9d5c9';ctx.lineWidth=3;ctx.strokeRect(5,5,502,118);
   ctx.fillStyle='#ffffff';ctx.font='700 65px "Segoe UI", Arial';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(names[face],256,65);
   const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;this.faceTextures.set(face,texture);
  }return this.faceTextures.get(face);
 }
 addFaceLabels(model){
  for(const face of model.placement.faces){
   const section=model.sections.find(s=>s.id===face.section_id);
   // Six exterior directions; thin lid rims must not duplicate the body label.
   if(section.id!=='body'&&section.face!==face.face)continue;
   const group=this.groups.get(section.id),width=Math.min(face.size_mm[0]*.3,face.size_mm[1]*.8,160)/1000;
   const label=new THREE.Mesh(new THREE.PlaneGeometry(width,width/4),new THREE.MeshBasicMaterial({map:this.faceTexture(face.face),transparent:true,depthWrite:false,toneMapped:false}));
   label.userData.faceLabel=face.face;label.raycast=()=>{};
   const v=['top','bottom'].includes(face.face) ? .5 : .25;
   label.position.fromArray(face.origin_mm.map((x,k)=>(x+.5*face.size_mm[0]*face.u_axis[k]+v*face.size_mm[1]*face.v_axis[k]+2*face.normal[k])/1000-group.userData.pivot[k]));
   label.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(new THREE.Vector3(...face.u_axis),new THREE.Vector3(...face.v_axis),new THREE.Vector3(...face.normal)));
   group.add(label);
  }
 }
 apply(){
  const normals={top:[0,0,1],front:[0,-1,0],rear:[0,1,0],left:[-1,0,0],right:[1,0,0]};
  for(const [id,group] of this.groups){const {section:s,pivot,axis,direction}=group.userData;group.position.fromArray(pivot);group.rotation.set(0,0,0);if(id==='body')continue;
   const fraction=this.values[id]/100;
   if(s.kind==='removable')group.position.add(new THREE.Vector3(...normals[s.face]).multiplyScalar((Math.max(...s.size_mm)/1000*.7+.15)*fraction));
   if(s.kind==='hinged')group.rotation[['x','y','z'][axis]]=direction*THREE.MathUtils.degToRad(100)*fraction;
  }
  this.root.updateMatrixWorld(true);
 }
 setMotion(id,value){
  const sections=this.model.sections.slice(1);if(!this.groups.has(id)||!Number.isFinite(value)||value<0||value>100)throw Error('Nieprawidłowe otwarcie sekcji');
  const current=this.values[id],section=sections.find(s=>s.id===id);
  if(value>0&&section.requires.some(key=>this.values[key]<99.9))throw Error('Najpierw otwórz: '+section.requires.map(key=>sections.find(s=>s.id===key).label).join(', '));
  if(value<current&&sections.some(s=>s.requires.includes(id)&&this.values[s.id]>0))throw Error('Najpierw zamknij zależne pokrywy.');
  if(this.model.draft.cooperation==='together')for(const s of sections)this.values[s.id]=value;else this.values[id]=value;
  this.apply();
 }
 all(value){for(const key of Object.keys(this.values))this.values[key]=value;this.apply();this.chrome.frame(null,false);}
 fit(){if(!this.model)return;this.resize();stopOrbitMotion(this.controls);const box=new THREE.Box3().setFromObject(this.root),sphere=box.getBoundingSphere(new THREE.Sphere());const v=THREE.MathUtils.degToRad(this.camera.fov),h=2*Math.atan(Math.tan(v/2)*this.camera.aspect),distance=sphere.radius/Math.sin(Math.min(v,h)/2)*1.06;this.controls.target.copy(sphere.center);this.camera.position.copy(sphere.center).add(new THREE.Vector3(1.4,-2.2,1.5).normalize().multiplyScalar(distance));this.controls.update();}
}
