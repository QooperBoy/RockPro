import * as THREE from './vendor/three.module.min.js';
import {OrbitControls} from './vendor/OrbitControls.js';

export class ConceptView {
 constructor(host){
  this.host=host;this.scene=new THREE.Scene();this.scene.background=new THREE.Color(0xe9eee5);
  this.camera=new THREE.PerspectiveCamera(38,1,.005,200);this.camera.up.set(0,0,1);
  this.renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));
  this.renderer.toneMapping=THREE.ACESFilmicToneMapping;host.append(this.renderer.domElement);
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;
  this.scene.add(new THREE.HemisphereLight(0xffffff,0x657460,2));const light=new THREE.DirectionalLight(0xffffff,2.5);light.position.set(2,-3,5);this.scene.add(light);
  this.grid=new THREE.GridHelper(20,100,0x95a88d,0xcad5c2);this.grid.rotation.x=Math.PI/2;this.scene.add(this.grid);
  this.root=new THREE.Group();this.scene.add(this.root);this.groups=new Map();this.values={};
  new ResizeObserver(()=>this.resize()).observe(host);this.resize();
  this.renderer.setAnimationLoop(()=>{this.controls.update();this.renderer.render(this.scene,this.camera);});
 }
 resize(){const w=this.host.clientWidth,h=this.host.clientHeight;if(!w||!h)return;this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();}
 setModel(model){
  const previous=this.values;this.root.traverse(o=>{o.geometry?.dispose();if(o.material)o.material.dispose();});this.root.clear();this.groups.clear();this.model=model;
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
  for(const p of model.panels){
   const group=this.groups.get(p.section),pivot=group.userData.pivot;
   const geometry=new THREE.BoxGeometry(...p.size_mm.map(v=>v/1000));
   const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:p.section==='body'?0x408080:0x5a9891,roughness:.85,metalness:0}));
   mesh.position.fromArray(p.center_mm.map((v,k)=>v/1000-pivot[k]));group.add(mesh);
   const edges=new THREE.LineSegments(new THREE.EdgesGeometry(geometry),new THREE.LineBasicMaterial({color:0x294e47,transparent:true,opacity:.55}));edges.position.copy(mesh.position);group.add(edges);
  }
  // Topology edits reset opening state: old motion cannot bypass new dependencies.
  this.values=Object.fromEntries(model.sections.slice(1).map(s=>[s.id,0]));this.apply();this.fit();
  this.grid.position.set(body[0]/2,body[1]/2,-.002);this.grid.scale.setScalar(Math.max(...body)/4);
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
 all(value){for(const key of Object.keys(this.values))this.values[key]=value;this.apply();this.fit();}
 fit(){if(!this.model)return;this.resize();const box=new THREE.Box3().setFromObject(this.root),sphere=box.getBoundingSphere(new THREE.Sphere());const v=THREE.MathUtils.degToRad(this.camera.fov),h=2*Math.atan(Math.tan(v/2)*this.camera.aspect),distance=sphere.radius/Math.sin(Math.min(v,h)/2)*1.06;this.controls.target.copy(sphere.center);this.camera.position.copy(sphere.center).add(new THREE.Vector3(1.4,-2.2,1.5).normalize().multiplyScalar(distance));this.controls.update();}
}
