import * as THREE from './vendor/three.module.min.js';

// One renderer shared with the plywood view; optional meshes are reference geometry.
export class PlacementView {
 constructor(view,onDrop,onSelect,onMessage){
  this.view=view;this.onDrop=onDrop;this.onSelect=onSelect;this.onMessage=onMessage;this.enabled=false;this.activePart=null;this.meshCache=new Map();this.textures=new Map();this.markers=[];this.serial=0;
  this.raycaster=new THREE.Raycaster();const canvas=view.renderer.domElement;
  canvas.addEventListener('dragover',e=>{if(!this.enabled)return;e.preventDefault();if(e.dataTransfer)e.dataTransfer.dropEffect='copy';this.hover(e.clientX,e.clientY);});
  canvas.addEventListener('dragleave',()=>this.clearHover());
  canvas.addEventListener('drop',e=>{if(!this.enabled)return;e.preventDefault();this.clearHover();const hit=this.wallAt(e.clientX,e.clientY),part=e.dataTransfer.getData('application/x-rockpro-part');if(hit&&part)this.onDrop({part_id:part,...hit});else this.onMessage('Upuść część na zewnętrznej powierzchni istniejącej ścianki.');});
  // Capture phase stops OrbitControls only when an attachment is actually dragged.
  canvas.addEventListener('pointerdown',e=>{
   if(!this.enabled||e.button!==0)return;const item=this.markerAt(e.clientX,e.clientY);
   if(item){e.stopImmediatePropagation();e.preventDefault();canvas.setPointerCapture(e.pointerId);view.controls.enabled=false;this.drag={id:item.group_id,item,start:[e.clientX,e.clientY],pointer:e.pointerId};this.onSelect(item.group_id);}
   else if(this.activePart){e.stopImmediatePropagation();this.pendingClick=[e.clientX,e.clientY];}
  },true);
  canvas.addEventListener('pointermove',e=>{if(!this.enabled)return;if(this.drag){e.stopImmediatePropagation();this.hover(e.clientX,e.clientY);}else if(this.activePart)this.hover(e.clientX,e.clientY);},true);
  canvas.addEventListener('pointerup',e=>{
   if(this.drag){e.stopImmediatePropagation();const drag=this.drag;this.drag=null;view.controls.enabled=true;if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);this.clearHover();if(Math.hypot(e.clientX-drag.start[0],e.clientY-drag.start[1])>4){const hit=this.wallAt(e.clientX,e.clientY);if(hit)this.onDrop({group_id:drag.id,occurrence:drag.item,...hit});else this.onMessage('Brak ścianki pod kursorem — pozycja pozostała bez zmian.');}}
   else if(this.pendingClick){const start=this.pendingClick;this.pendingClick=null;if(Math.hypot(e.clientX-start[0],e.clientY-start[1])<5){const hit=this.wallAt(e.clientX,e.clientY);if(hit)this.onDrop({part_id:this.activePart,...hit});}}
  },true);
  canvas.addEventListener('pointercancel',()=>this.cancelDrag());
  canvas.addEventListener('contextmenu',()=>{this.activePart=null;this.clearHover();});
 }
 cancelDrag(){this.drag=null;this.pendingClick=null;this.view.controls.enabled=true;this.clearHover();}
 setEnabled(value){this.enabled=value;if(!value){this.cancelDrag();this.activePart=null;}this.view.renderer.domElement.classList.toggle('placement-active',value);}
 setPart(id){this.activePart=id;this.view.renderer.domElement.style.cursor=id?'crosshair':'';}
 pointRay(x,y){const r=this.view.renderer.domElement.getBoundingClientRect();this.view.root.updateMatrixWorld(true);this.raycaster.setFromCamera(new THREE.Vector2((x-r.left)/r.width*2-1,-(y-r.top)/r.height*2+1),this.view.camera);}
 markerAt(x,y){this.pointRay(x,y);const panels=[];this.view.root.traverse(o=>{if(o.userData.mountFace)panels.push(o);});const wall=this.raycaster.intersectObjects(panels,false)[0];for(const hit of this.raycaster.intersectObjects(this.markers,true)){if(wall&&hit.distance>wall.distance+.025)continue;let obj=hit.object;while(obj&&!obj.userData.occurrence)obj=obj.parent;if(obj?.userData.occurrence)return obj.userData.occurrence;}return null;}
 wallAt(x,y){
  this.pointRay(x,y);const panels=[];this.view.root.traverse(o=>{if(o.userData.mountFace)panels.push(o);});
  for(const hit of this.raycaster.intersectObjects(panels,false)){
   const face=hit.object.userData.mountFace,section=this.view.groups.get(face.section_id),normal=new THREE.Vector3(...face.normal).transformDirection(section.matrixWorld),hitNormal=hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
   if(normal.dot(hitNormal)<.8)continue; // Never silently place on an interior face or plywood edge.
   const closed=section.worldToLocal(hit.point.clone()).add(new THREE.Vector3(...section.userData.pivot));
   const delta=closed.multiplyScalar(1000).sub(new THREE.Vector3(...face.origin_mm));
   const u=delta.dot(new THREE.Vector3(...face.u_axis))/face.size_mm[0],v=delta.dot(new THREE.Vector3(...face.v_axis))/face.size_mm[1];
   if(u>=0&&u<=1&&v>=0&&v<=1)return {section_id:face.section_id,face:face.face,u,v,frame:face};
  }return null;
 }
 clearHover(){if(this.hoverMesh){this.hoverMesh.material.emissive.setHex(0);this.hoverMesh=null;}}
 hover(x,y){this.clearHover();const hit=this.wallAt(x,y);if(!hit)return;this.view.root.traverse(o=>{if(o.userData.mountFace?.key===hit.frame.key){o.material.emissive.setHex(0x183829);this.hoverMesh=o;}});}
 async mesh(row){
  if(!row.image?.mesh_url)return null;
  if(!this.meshCache.has(row.id))this.meshCache.set(row.id,(async()=>{
   const res=await fetch(row.image.mesh_url);if(!res.ok)throw Error('Brak siatki '+row.id);const raw=await res.arrayBuffer();
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),v=>v.toString(16).padStart(2,'0')).join('');if(hash!==row.image.mesh_sha256)throw Error('Niezgodna siatka '+row.id);
   const model=JSON.parse(new TextDecoder().decode(raw));if(model.schema!=='rockpro.part-mesh/1'||model.units!=='m'||model.frame!=='mount.local_uvn')throw Error('Nieobsługiwana siatka '+row.id);return model;
  })());
  return this.meshCache.get(row.id);
 }
 texture(row){if(!row.image)return null;if(!this.textures.has(row.id)){const t=new THREE.TextureLoader().load(row.image.url);t.colorSpace=THREE.SRGBColorSpace;this.textures.set(row.id,t);}return this.textures.get(row.id);}
 clear(){this.clearHover();for(const marker of this.markers){marker.parent?.remove(marker);marker.traverse(o=>{o.geometry?.dispose();if(Array.isArray(o.material))o.material.forEach(m=>m.dispose());else o.material?.dispose();});}this.markers=[];}
 async update(model,catalog,selected){
  const serial=++this.serial;this.clear();this.catalog=catalog;
  this.view.root.traverse(o=>{if(o.userData.panelIndex!==undefined)o.userData.mountFace=model.placement.faces.find(f=>f.panel_index===o.userData.panelIndex);});
  const rows=new Map(catalog.items.map(r=>[r.id,r]));
  const sources=new Map();await Promise.all([...new Set(model.placement.items.map(i=>i.part_id))].map(async id=>{try{sources.set(id,await this.mesh(rows.get(id)));}catch(e){sources.set(id,null);this.onMessage(e.message+' — pokazano znacznik zastępczy.');}}));
  if(serial!==this.serial)return;
  for(const item of model.placement.items){
   const row=rows.get(item.part_id),group=new THREE.Group(),section=this.view.groups.get(item.section_id);if(!section)continue;
   group.userData.occurrence=item;group.position.fromArray(item.position_mm.map((v,k)=>v/1000-section.userData.pivot[k]));
   const basis=new THREE.Matrix4().makeBasis(new THREE.Vector3(...item.u_axis),new THREE.Vector3(...item.v_axis),new THREE.Vector3(...item.normal));group.quaternion.setFromRotationMatrix(basis);group.rotateZ(THREE.MathUtils.degToRad(item.rotation_deg));
   const native=sources.get(item.part_id);
   if(native){
    for(const e of native.elements){const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(e.positions,3));geometry.setAttribute('normal',new THREE.Float32BufferAttribute(e.normals,3));let offset=0;const mats=e.materials.map((g,i)=>{geometry.addGroup(offset,g.count,i);offset+=g.count;return new THREE.MeshStandardMaterial({color:g.color===16777215?0xbec9cf:g.color,roughness:.5,metalness:.45,side:THREE.DoubleSide});});group.add(new THREE.Mesh(geometry,mats));}
   }else{
    // A plainly labelled concept marker, never a substitute CAD solid or cutout.
    const size=[...item.footprint_mm];if(item.rotation_deg%180)size.reverse();
    const marker=new THREE.Mesh(new THREE.BoxGeometry(size[0]/1000,size[1]/1000,.004),new THREE.MeshStandardMaterial({color:0xe4ded1,roughness:.75}));marker.position.z=.004;group.add(marker);
    const texture=this.texture(row);if(texture){const plane=new THREE.Mesh(new THREE.PlaneGeometry(size[0]/1000*.92,size[1]/1000*.92),new THREE.MeshBasicMaterial({map:texture}));plane.position.z=.0061;group.add(plane);}
   }
   const flagged=model.placement.warnings.some(w=>w.group_id===item.group_id||w.other_group_id===item.group_id),size=[...item.footprint_mm];group.userData.flagged=flagged;if(item.rotation_deg%180)size.reverse();
   const outline=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(size[0]/1000+.004,size[1]/1000+.004,.003)),new THREE.LineBasicMaterial({color:item.group_id===selected?0xf06b1f:flagged?0xc48a24:0x447359}));outline.position.z=.008;group.add(outline);
   section.add(group);this.markers.push(group);
  }this.view.apply();
 }
 select(id){for(const marker of this.markers){const line=marker.children.find(c=>c.isLineSegments);if(line)line.material.color.setHex(marker.userData.occurrence.group_id===id?0xf06b1f:marker.userData.flagged?0xc48a24:0x447359);}}
}
