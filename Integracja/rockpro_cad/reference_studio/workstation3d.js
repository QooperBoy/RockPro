import * as THREE from './vendor/three.module.min.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {configureOrbit} from './scene-controls.js';
import {placement} from './preview_math.mjs';

export class WorkstationView {
 constructor(host,status,onChange){this.host=host;this.status=status;this.onChange=onChange;this.meshes=[];this.loaded=false;this.coverVisible=false;}
 async load(){
  if(this.pending)return this.pending;
  this.pending=this.initialize();return this.pending;
 }
 async initialize(){
  this.status.textContent='Wczytywanie rzeczywistych siatek workstation…';
  const response=await fetch('workstation/model.json');if(!response.ok)throw Error('Brak eksportu 3D workstation');
  this.model=await response.json();const m=this.model;
  if(m.kind!=='workstation_native_preview'||m.shelves.length!==4)throw Error('Nieobsługiwane mapowanie workstation');
  const binary=await fetch('workstation/geometry.bin').then(r=>{if(!r.ok)throw Error('Brak geometrii');return r.arrayBuffer();});
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',binary)),v=>v.toString(16).padStart(2,'0')).join('');
  if(hash!==m.geometry_sha256)throw Error('Niezgodna suma geometrii');
  this.scene=new THREE.Scene();this.scene.background=new THREE.Color(0xe9eeea);
  this.camera=new THREE.PerspectiveCamera(38,1,.01,100);this.camera.up.set(0,0,1);
  this.renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
  this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));this.renderer.outputColorSpace=THREE.SRGBColorSpace;
  this.host.append(this.renderer.domElement);this.controls=new OrbitControls(this.camera,this.renderer.domElement);configureOrbit(this.controls);
  this.scene.add(new THREE.HemisphereLight(0xffffff,0x7b8c80,2.8));
  const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(-2,-3,4);this.scene.add(light);
  this.scene.add(new THREE.AmbientLight(0xffffff,.3));
  const materialCache=new Map();
  const material=color=>{if(!materialCache.has(color))materialCache.set(color,new THREE.MeshStandardMaterial({color,roughness:.65,metalness:.18,side:THREE.DoubleSide}));return materialCache.get(color);};
  let triangles=0;
  for(const row of m.elements){
   const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(binary,row.offset,row.floats),3));
   geometry.setAttribute('normal',new THREE.BufferAttribute(new Float32Array(binary,row.offset+row.floats*4,row.floats),3));
   let offset=0;const materials=[];
   for(const group of row.materials){geometry.addGroup(offset,group.count,materials.length);materials.push(material(group.color));offset+=group.count;}
   const mesh=new THREE.Mesh(geometry,materials);mesh.matrixAutoUpdate=false;
   const original=new THREE.Matrix4().fromArray(row.matrix);mesh.matrix.copy(original);
   mesh.userData={row,original};this.scene.add(mesh);this.meshes.push(mesh);triangles+=row.floats/9;
  }
  this.dimensions=[0,1,2].map(k=>1000*(m.baseline_bounds[k+3]-m.baseline_bounds[k]));this.travels=[0,0,0,0];
  const grid=new THREE.GridHelper(4,40,0x9aac9e,0xd0dad1);grid.rotation.x=Math.PI/2;grid.position.z=m.baseline_bounds[2]-.16;this.scene.add(grid);
  this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(this.host);
  this.loaded=true;this.apply();this.fit();this.resize();
  this.renderer.setAnimationLoop(()=>{if(this.host.hidden||this.host.closest('[hidden]'))return;this.controls.update();this.renderer.render(this.scene,this.camera);});
  this.status.textContent=`${m.elements.length} części · ${Math.round(triangles/1000)} tys. trójkątów · podgląd koncepcji z modelu CAD`;
  window.rockproWorkstation=this;return this;
 }
 resize(){const w=this.host.clientWidth,h=this.host.clientHeight;if(!w||!h)return;this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();}
 apply(){
  if(!this.loaded)return;
  const baseline=this.model.baseline_bounds,target=this.dimensions.map(x=>x/1000);
  for(const mesh of this.meshes){const {row,original}=mesh.userData;
   const bounds=this.model.group_bounds[row.deform_group];const p=placement(bounds,baseline,target,row.resize_axes);
   const shift=new THREE.Matrix4().makeTranslation(...p.destination);
   const resize=new THREE.Matrix4().makeScale(...p.scale);const back=new THREE.Matrix4().makeTranslation(...p.center.map(x=>-x));
   const transform=shift.multiply(resize).multiply(back);
   if(row.shelf_id){const i=this.model.shelves.findIndex(s=>s.id===row.shelf_id);const travel=this.travels[i]/1000;transform.premultiply(new THREE.Matrix4().makeTranslation(...this.model.shelf_axis.map(x=>x*travel)));}
   mesh.matrix.copy(transform.multiply(original));mesh.matrixWorldNeedsUpdate=true;mesh.visible=this.coverVisible||!row.cover;
  }
  this.scene.updateMatrixWorld(true);this.onChange?.();
 }
 setDimensions(values){if(values.length!==3||values.some((v,k)=>{const b=1000*(this.model.baseline_bounds[k+3]-this.model.baseline_bounds[k]);return !Number.isFinite(v)||v<b*.8||v>b*1.4;}))throw Error('Wymiary podglądu muszą mieścić się w zakresie 80–140% wzorca');this.dimensions=values;this.apply();}
 setTravel(index,value){this.travels[index]=value;this.apply();}
 fit(){
  if(!this.loaded)return;const b=this.model.baseline_bounds;const size=Math.max(...this.dimensions)/1000;
  const center=new THREE.Vector3(...[0,1,2].map(k=>b[k]+this.dimensions[k]/2000));
  this.controls.target.copy(center);this.camera.position.copy(center).add(new THREE.Vector3(1.4,-2.2,1.3).multiplyScalar(size));this.controls.update();
 }
 state(){return {source_sha256:this.model.source_sha256,external_mm:[...this.dimensions],shelf_travel_mm:[...this.travels],covers_visible:this.coverVisible};}
 restore(state){if(!state||state.source_sha256!==this.model.source_sha256)return;this.dimensions=[...state.external_mm];this.travels=[...state.shelf_travel_mm];this.coverVisible=state.covers_visible;this.apply();}
}
