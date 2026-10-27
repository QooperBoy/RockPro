import * as THREE from './vendor/three.module.min.js';

// Complete opaque reference parts; only extruded profiles change axial length.
export class StructureView {
 constructor(view){this.view=view;this.cache=new Map();this.items=[];this.serial=0;}
 async resource(row){
  const meta=row?.image;if(!meta?.mesh_url)throw Error('Brak geometrii 3D: '+row?.id);
  const key=row.id+'@'+meta.mesh_sha256;
  if(!this.cache.has(key))this.cache.set(key,(async()=>{
   const response=await fetch(meta.mesh_url);if(!response.ok)throw Error('Nie można wczytać części '+row.id);
   const raw=await response.arrayBuffer(),sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),v=>v.toString(16).padStart(2,'0')).join('');
   if(sha!==meta.mesh_sha256)throw Error('Niezgodna suma geometrii '+row.id);
   const model=JSON.parse(new TextDecoder().decode(raw));
   if(model.schema!=='rockpro.part-mesh/1'||model.units!=='m'||!['source.local','mount.local_uvn'].includes(model.frame))throw Error('Nieobsługiwany model '+row.id);
   return model.elements.map(e=>{
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(e.positions,3));geometry.setAttribute('normal',new THREE.Float32BufferAttribute(e.normals,3));
    const colors=new Float32Array(e.positions.length);let at=0;
    for(const m of e.materials){const c=new THREE.Color(m.color===16777215?0xbec9cf:m.color);for(let i=0;i<m.count;i++){colors[at++]=c.r;colors[at++]=c.g;colors[at++]=c.b;}}
    geometry.setAttribute('color',new THREE.BufferAttribute(colors,3));
    return {geometry,material:new THREE.MeshStandardMaterial({vertexColors:true,metalness:.55,roughness:.4,side:THREE.DoubleSide})};
   });
  })());
  return this.cache.get(key);
 }
 clear(){for(const group of this.items){group.parent?.remove(group);group.traverse(o=>{if(o.userData.sharedResources)return;o.geometry?.dispose();o.material?.dispose();});}this.items=[];}
 async update(model,catalog){
  const first=this.items.length===0,serial=++this.serial;this.clear();const specs=model.construction?.items??[],rows=new Map(catalog.items.map(r=>[r.id,r]));
  const assets=new Map();await Promise.all([...new Set(specs.map(s=>s.part_id).filter(Boolean))].map(async id=>assets.set(id,await this.resource(rows.get(id)))));
  if(serial!==this.serial)return;
  for(const spec of specs){
   const parent=this.view.groups.get(spec.section_id);if(!parent)throw Error('Brak sekcji konstrukcji');
   const group=new THREE.Group();group.userData.occurrence=spec;group.userData.geometryMode=spec.part_id?'source_mesh':'designed_plywood';
   if(spec.part_id){for(const r of assets.get(spec.part_id)){const mesh=new THREE.Mesh(r.geometry,r.material);mesh.userData.sharedResources=true;group.add(mesh);}}
   else {const mesh=new THREE.Mesh(new THREE.BoxGeometry(...spec.size_mm.map(v=>v/1000)),new THREE.MeshStandardMaterial({color:0x408080,roughness:.85}));mesh.position.fromArray(spec.size_mm.map(v=>v/2000));group.add(mesh);}
   const r=spec.rotation;group.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(...r.map(v=>new THREE.Vector3(...v))));
   if(spec.length_mm)group.scale.z=spec.length_mm/spec.seed_length_mm;
   group.position.fromArray(spec.position_mm.map((v,k)=>v/1000-parent.userData.pivot[k]));parent.add(group);this.items.push(group);
  }
  this.view.root.updateMatrixWorld(true);this.view.grid.position.z=specs.length?new THREE.Box3().setFromObject(this.view.root).min.z-.002:-.002;
  if(first&&specs.length)this.view.fit();
 }
}
