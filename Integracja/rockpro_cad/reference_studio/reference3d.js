import * as THREE from './vendor/three.module.min.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {placement} from './preview_math.mjs';

// One WebGL context for the gallery. Replace and dispose geometry on selection.
export class ReferenceView {
 constructor(host,status,onChange){this.host=host;this.status=status;this.onChange=onChange;this.meshes=[];this.materials=[];this.loaded=false;this.serial=0;}
 async load(url,key){
  if(this.loaded&&this.url===url)return this;
  const serial=++this.serial;this.abort?.abort();this.abort=new AbortController();const signal=this.abort.signal;
  this.loaded=false;this.status.textContent='Wczytywanie rzeczywistych siatek '+key+'…';
  try{
   const response=await fetch(url+'/model.json',{signal});if(!response.ok)throw Error('Brak eksportu 3D '+key);
   const model=await response.json();
   if(!['reference_native_preview','workstation_native_preview'].includes(model.kind)||(model.model_key??'M04')!==key)throw Error('Niezgodne mapowanie modelu');
   model.motions??=model.shelves.map(s=>({...s,axis:model.shelf_axis,min:0,max:500,unit:'mm'}));
   for(const row of model.elements)row.motion_ids??=row.shelf_id?[row.shelf_id]:[];
   const binary=await fetch(url+'/geometry.bin',{signal}).then(r=>{if(!r.ok)throw Error('Brak geometrii');return r.arrayBuffer();});
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',binary)),v=>v.toString(16).padStart(2,'0')).join('');
   if(hash!==model.geometry_sha256)throw Error('Niezgodna suma geometrii');
   if(serial!==this.serial)return null;
   this.initializeRenderer();this.clearGeometry();this.model=model;this.key=key;this.url=url;
   const materials=new Map();const material=color=>{if(!materials.has(color))materials.set(color,new THREE.MeshStandardMaterial({color,roughness:.65,metalness:.18,side:THREE.DoubleSide}));return materials.get(color);};
   let triangles=0;
   for(const row of model.elements){
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(binary,row.offset,row.floats),3));
    geometry.setAttribute('normal',new THREE.BufferAttribute(new Float32Array(binary,row.offset+row.floats*4,row.floats),3));
    let offset=0;const mats=[];for(const group of row.materials){geometry.addGroup(offset,group.count,mats.length);mats.push(material(group.color));offset+=group.count;}
    const mesh=new THREE.Mesh(geometry,mats);mesh.matrixAutoUpdate=false;
    const original=new THREE.Matrix4().fromArray(row.matrix);mesh.matrix.copy(original);mesh.userData={row,original};
    this.scene.add(mesh);this.meshes.push(mesh);triangles+=row.floats/9;
   }
   this.materials=[...materials.values()];this.dimensions=this.baselineDimensions();this.coverVisible=model.default_covers_visible??false;this.referencesVisible=false;
   this.motionValues=Object.fromEntries(model.motions.map(m=>[m.id,0]));
   this.grid.position.set((model.baseline_bounds[0]+model.baseline_bounds[3])/2,(model.baseline_bounds[1]+model.baseline_bounds[4])/2,model.baseline_bounds[2]-.16);
   this.grid.scale.setScalar(Math.max(...this.dimensions)/1000);
   this.loaded=true;this.apply();this.fit();this.resize();
   this.status.textContent=`${key} · ${model.elements.length} części · ${Math.round(triangles/1000)} tys. trójkątów · podgląd koncepcji`;
   window.rockproReferenceView=this;if(key==='M04')window.rockproWorkstation=this;return this;
  }catch(error){if(error.name==='AbortError'||serial!==this.serial)return null;this.clearGeometry();this.status.textContent='Błąd modelu '+key+': '+error.message;throw error;}
 }
 initializeRenderer(){
  if(this.renderer)return;
  this.scene=new THREE.Scene();this.scene.background=new THREE.Color(0xe9eeea);
  this.camera=new THREE.PerspectiveCamera(38,1,.01,100);this.camera.up.set(0,0,1);
  this.renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));this.renderer.outputColorSpace=THREE.SRGBColorSpace;
  this.host.append(this.renderer.domElement);this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;
  this.scene.add(new THREE.HemisphereLight(0xffffff,0x7b8c80,2.8));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(-2,-3,4);this.scene.add(light);this.scene.add(new THREE.AmbientLight(0xffffff,.3));
  this.grid=new THREE.GridHelper(4,40,0x9aac9e,0xd0dad1);this.grid.rotation.x=Math.PI/2;this.scene.add(this.grid);
  this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(this.host);
  this.renderer.setAnimationLoop(()=>{if(!this.loaded||this.host.hidden||this.host.closest('[hidden]'))return;this.controls.update();this.renderer.render(this.scene,this.camera);});
 }
 clearGeometry(){for(const mesh of this.meshes){this.scene?.remove(mesh);mesh.geometry.dispose();}for(const material of this.materials)material.dispose();this.meshes=[];this.materials=[];}
 cancel(){++this.serial;this.abort?.abort();}
 resize(){const w=this.host.clientWidth,h=this.host.clientHeight;if(!w||!h||!this.renderer)return;this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();}
 baselineDimensions(){return [0,1,2].map(k=>1000*(this.model.baseline_bounds[k+3]-this.model.baseline_bounds[k]));}
 apply(){
  if(!this.loaded)return;
  const baseline=this.model.baseline_bounds,target=this.dimensions.map(x=>x/1000);const motions=new Map(this.model.motions.map(m=>[m.id,m]));
  for(const mesh of this.meshes){const {row,original}=mesh.userData;
   const p=placement(this.model.group_bounds[row.deform_group],baseline,target,row.resize_axes);
   const transform=new THREE.Matrix4().makeTranslation(...p.destination).multiply(new THREE.Matrix4().makeScale(...p.scale)).multiply(new THREE.Matrix4().makeTranslation(...p.center.map(x=>-x)));
   for(const id of row.motion_ids){const motion=motions.get(id),travel=this.motionValues[id]/1000;transform.premultiply(new THREE.Matrix4().makeTranslation(...motion.axis.map(x=>x*travel)));}
   mesh.matrix.copy(transform.multiply(original));mesh.matrixWorldNeedsUpdate=true;
   const moving=row.motion_ids.some(id=>this.motionValues[id]!==0);
   mesh.visible=(!row.cover||this.coverVisible||moving)&&(!row.reference_only||this.referencesVisible);
  }
  this.scene.updateMatrixWorld(true);this.onChange?.(this.state(),this.key);
 }
 setDimensions(values){const base=this.baselineDimensions();if(values.length!==3||values.some((v,k)=>!Number.isFinite(v)||v<base[k]*.8||v>base[k]*1.4))throw Error('Gabaryt podglądu: zakres 80–140% wzorca');this.dimensions=values;this.apply();}
 setMotion(id,value){const m=this.model.motions.find(m=>m.id===id);if(!m||!Number.isFinite(value)||value<m.min||value>m.max)throw Error('Ruch poza zakresem podglądu');this.motionValues[id]=value;this.apply();}
 reset(){this.dimensions=this.baselineDimensions();this.motionValues=Object.fromEntries(this.model.motions.map(m=>[m.id,0]));this.coverVisible=this.model.default_covers_visible??false;this.referencesVisible=false;this.apply();}
 fit(){if(!this.loaded)return;const b=this.model.baseline_bounds,size=Math.max(...this.dimensions)/1000;const center=new THREE.Vector3(...[0,1,2].map(k=>b[k]+this.dimensions[k]/2000));this.controls.target.copy(center);this.camera.position.copy(center).add(new THREE.Vector3(1.4,-2.2,1.3).multiplyScalar(size));this.controls.update();}
 state(){return {source_sha256:this.model.source_sha256,external_mm:[...this.dimensions],motion_values:{...this.motionValues},covers_visible:this.coverVisible};}
 restore(state){if(!state||state.source_sha256!==this.model.source_sha256)return;this.dimensions=[...state.external_mm];this.coverVisible=state.covers_visible;this.motionValues=state.motion_values?{...state.motion_values}:Object.fromEntries(this.model.motions.map((m,i)=>[m.id,state.shelf_travel_mm?.[i]??0]));this.apply();}
}
