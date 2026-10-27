import * as THREE from './vendor/three.module.min.js';
import {resolvePreview} from './placement_math.mjs';
import {stopOrbitMotion} from './scene-controls.js';

// One renderer shared with the plywood view; optional meshes are reference geometry.
export class PlacementView {
 constructor(view,onDrop,onSelect,onMessage,candidate){
  this.view=view;this.onDrop=onDrop;this.onSelect=onSelect;this.onMessage=onMessage;this.enabled=false;this.activePart=null;this.meshCache=new Map();this.textures=new Map();this.markers=[];this.serial=0;
  this.candidate=candidate;this.geometryCache=new Map();this.readyMeshes=new Map();this.ghosts=[];this.jointHelpers=[];view.beforeRender=()=>this.flushPreview();
  this.raycaster=new THREE.Raycaster();const canvas=view.renderer.domElement;
  canvas.addEventListener('dragover',e=>{if(!this.enabled)return;e.preventDefault();if(e.dataTransfer)e.dataTransfer.dropEffect='copy';this.pendingPointer=[e.clientX,e.clientY];});
  canvas.addEventListener('dragleave',()=>{this.pendingPointer=null;this.clearHover();this.clearGhosts();});
  canvas.addEventListener('drop',e=>{if(!this.enabled)return;e.preventDefault();this.pendingPointer=null;this.clearHover();this.clearGhosts();const hit=this.wallAt(e.clientX,e.clientY),part=e.dataTransfer.getData('application/x-rockpro-part');if(hit&&part)this.onDrop({part_id:part,...hit});else this.onMessage('Upuść część na zewnętrznej powierzchni istniejącej ścianki.');});
  // Capture phase stops OrbitControls only when an attachment is actually dragged.
  canvas.addEventListener('pointerdown',e=>{
   if(!this.enabled||e.button!==0)return;const item=this.markerAt(e.clientX,e.clientY);
   if(item?.seam_id){e.stopImmediatePropagation();e.preventDefault();this.onSelect(item.group_id);return;}
   if(item){e.stopImmediatePropagation();e.preventDefault();stopOrbitMotion(view.controls);canvas.setPointerCapture(e.pointerId);view.controls.enabled=false;this.drag={id:item.group_id,item,start:[e.clientX,e.clientY],pointer:e.pointerId,originals:this.markers.filter(m=>m.userData.occurrence.group_id===item.group_id).map(m=>({marker:m,parent:m.parent,position:m.position.clone(),quaternion:m.quaternion.clone()}))};this.onSelect(item.group_id);}
   else if(this.activePart){e.stopImmediatePropagation();this.pendingClick=[e.clientX,e.clientY];}
  },true);
  canvas.addEventListener('pointermove',e=>{if(!this.enabled)return;if(this.drag){e.stopImmediatePropagation();this.pendingPointer=[e.clientX,e.clientY];}else if(this.activePart)this.pendingPointer=[e.clientX,e.clientY];},true);
  canvas.addEventListener('pointerup',e=>{
   if(this.drag){e.stopImmediatePropagation();const drag=this.drag,hit=this.wallAt(e.clientX,e.clientY),command=hit?{group_id:drag.id,occurrence:drag.item,...hit}:null,moved=Math.hypot(e.clientX-drag.start[0],e.clientY-drag.start[1])>4;this.pendingPointer=null;if(!moved||!command||!this.candidate(command))this.restoreDrag();this.drag=null;view.controls.enabled=true;if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);this.clearHover();if(moved){if(command)this.onDrop(command);else this.onMessage('Brak ścianki pod kursorem — pozycja pozostała bez zmian.');}}
   else if(this.pendingClick){const start=this.pendingClick;this.pendingClick=null;if(Math.hypot(e.clientX-start[0],e.clientY-start[1])<5){const hit=this.wallAt(e.clientX,e.clientY);if(hit)this.onDrop({part_id:this.activePart,...hit});}}
  },true);
  canvas.addEventListener('pointercancel',()=>this.cancelDrag());
  canvas.addEventListener('lostpointercapture',()=>this.cancelDrag());
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){this.cancelDrag();this.setPart(null);}});
  canvas.addEventListener('contextmenu',()=>{this.activePart=null;this.clearHover();});
 }
 restoreDrag(){for(const saved of this.drag?.originals??[]){saved.parent.add(saved.marker);saved.marker.position.copy(saved.position);saved.marker.quaternion.copy(saved.quaternion);}this.view.root.updateMatrixWorld(true);}
 cancelDrag(){this.restoreDrag();const pointer=this.drag?.pointer;this.drag=null;this.pendingPointer=null;this.pendingClick=null;this.view.controls.enabled=true;this.clearHover();this.clearGhosts();const canvas=this.view.renderer.domElement;if(pointer!==undefined&&canvas.hasPointerCapture(pointer))canvas.releasePointerCapture(pointer);}
 setEnabled(value){this.enabled=value;if(!value){this.cancelDrag();this.setPart(null);}for(const helper of this.jointHelpers)helper.visible=value;this.view.renderer.domElement.classList.toggle('placement-active',value);}
 setPart(id){this.activePart=id;this.clearGhosts();this.view.renderer.domElement.style.cursor=id?'crosshair':'';const row=this.catalog?.items.find(r=>r.id===id);if(row?.image?.mesh_url)this.mesh(row).then(()=>{if(this.activePart===id&&this.lastPointer)this.pendingPointer=this.lastPointer;}).catch(e=>this.onMessage(e.message+' — pokazano znacznik zastępczy.'));}
 pointRay(x,y){const r=this.view.renderer.domElement.getBoundingClientRect();this.view.root.updateMatrixWorld(true);this.raycaster.setFromCamera(new THREE.Vector2((x-r.left)/r.width*2-1,-(y-r.top)/r.height*2+1),this.view.camera);}
 markerAt(x,y){this.pointRay(x,y);const panels=[];this.view.root.traverse(o=>{if(o.userData.mountFace)panels.push(o);});const wall=this.raycaster.intersectObjects(panels,false)[0],hits=[];for(const m of this.markers)m.userData.pickProxy.raycast(this.raycaster,hits);hits.sort((a,b)=>a.distance-b.distance);for(const hit of hits){if(wall&&hit.distance>wall.distance+.025)continue;return hit.object.parent.userData.occurrence;}return null;}
 wallAt(x,y){
  const rect=this.view.renderer.domElement.getBoundingClientRect();if(x<rect.left||x>rect.right||y<rect.top||y>rect.bottom)return null;
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
 clearGhosts(){for(const g of this.ghosts){g.parent?.remove(g);g.traverse(o=>{if(!o.userData.sharedResources){o.geometry?.dispose();o.material?.dispose();}});}this.ghosts=[];}
 pose(marker,item,sectionId,position){const section=this.view.groups.get(sectionId);if(!section)return;section.add(marker);marker.position.fromArray(position.map((x,k)=>x/1000-section.userData.pivot[k]));marker.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(new THREE.Vector3(...item.u_axis),new THREE.Vector3(...item.v_axis),new THREE.Vector3(...item.normal)));marker.rotateZ(THREE.MathUtils.degToRad(item.rotation_deg));}
 flushPreview(){
  if(!this.enabled||!this.pendingPointer)return;const [x,y]=this.pendingPointer;this.lastPointer=[x,y];this.pendingPointer=null;this.hover(x,y);const hit=this.wallAt(x,y);if(!hit){if(this.drag)this.restoreDrag();else this.clearGhosts();return;}
  const command=this.drag?{group_id:this.drag.id,occurrence:this.drag.item,...hit}:{part_id:this.activePart,...hit},candidate=this.candidate?.(command);
  if(!candidate){if(this.drag)this.restoreDrag();else this.clearGhosts();return;}
  const items=resolvePreview(candidate,this.view.model),poses=items.flatMap(item=>(item.visual_halves??[{section_id:item.section_id,position_mm:item.position_mm}]).map(half=>({item,half,key:item.id+'@'+half.section_id})));
  if(this.drag){this.drag.originals.forEach(({marker},i)=>{const pose=poses.find(p=>p.key===marker.userData.visualKey)??poses[i];if(pose)this.pose(marker,pose.item,pose.half.section_id,pose.half.position_mm);});this.drag.preview=candidate;}
  else{
   if(this.ghosts.length!==poses.length||poses.some((p,i)=>this.readyMeshes.has(p.item.part_id)&&!p.item.visual_halves&&this.ghosts[i]?.userData.geometryMode!=='source_mesh')){this.clearGhosts();for(const {item,half}of poses){const size=[...item.footprint_mm];if(item.rotation_deg%180)size.reverse();if(item.visual_halves)size[1]/=2;const ghost=new THREE.Group(),native=this.readyMeshes.get(item.part_id);if(native&&!item.visual_halves){this.addNative(ghost,item.part_id,native,true);ghost.userData.geometryMode='source_mesh';}else{ghost.add(new THREE.Mesh(new THREE.BoxGeometry(size[0]/1000,size[1]/1000,.006),new THREE.MeshBasicMaterial({color:0xe4782d,transparent:true,opacity:.42,depthWrite:false})));}this.ghosts.push(ghost);}}
   poses.forEach((p,i)=>this.pose(this.ghosts[i],p.item,p.half.section_id,p.half.position_mm));
  }this.view.root.updateMatrixWorld(true);
 }
 async mesh(row){
  if(!row?.image?.mesh_url)return null;
  if(!this.meshCache.has(row.id))this.meshCache.set(row.id,(async()=>{
   const res=await fetch(row.image.mesh_url);if(!res.ok)throw Error('Brak siatki '+row.id);const raw=await res.arrayBuffer();
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),v=>v.toString(16).padStart(2,'0')).join('');if(hash!==row.image.mesh_sha256)throw Error('Niezgodna siatka '+row.id);
   const model=JSON.parse(new TextDecoder().decode(raw));if(model.schema!=='rockpro.part-mesh/1'||model.units!=='m'||model.frame!=='mount.local_uvn')throw Error('Nieobsługiwana siatka '+row.id);this.readyMeshes.set(row.id,model);return model;
  })());
  return this.meshCache.get(row.id);
 }
 texture(row){if(!row.image)return null;if(!this.textures.has(row.id)){const t=new THREE.TextureLoader().load(row.image.url);t.colorSpace=THREE.SRGBColorSpace;this.textures.set(row.id,t);}return this.textures.get(row.id);}
 nativeGeometry(id,native){
  if(!this.geometryCache.has(id))this.geometryCache.set(id,native.elements.map(e=>{
   const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(e.positions,3));geometry.setAttribute('normal',new THREE.Float32BufferAttribute(e.normals,3));
   // CAD face groups become vertex colours: one draw call per physical subpart.
   const colours=new Float32Array(e.positions.length);let offset=0;
   for(const g of e.materials){const colour=new THREE.Color(g.color===16777215?0xbec9cf:g.color);for(let i=0;i<g.count;i++){colours[offset++]=colour.r;colours[offset++]=colour.g;colours[offset++]=colour.b;}}
   geometry.setAttribute('color',new THREE.BufferAttribute(colours,3));
   geometry.computeBoundingBox();return {geometry,region:geometry.boundingBox.getCenter(new THREE.Vector3()).y<0?'body':'cover',mats:new THREE.MeshStandardMaterial({vertexColors:true,roughness:.5,metalness:.45,side:THREE.DoubleSide})};
  }));return this.geometryCache.get(id);
 }
 addNative(group,id,native,ghost=false,half=null){
  for(const resource of this.nativeGeometry(id,native)){
   if(half?.mesh_region&&resource.region!==half.mesh_region)continue;
   if(ghost&&!resource.ghostMaterial)resource.ghostMaterial=new THREE.MeshStandardMaterial({vertexColors:true,color:0xf6ba87,transparent:true,opacity:.55,depthWrite:false,roughness:.5,metalness:.3,side:THREE.DoubleSide});
   const mesh=new THREE.Mesh(resource.geometry,ghost?resource.ghostMaterial:resource.mats);mesh.userData.sharedResources=true;mesh.position.y=(half?.mesh_local_offset_y_mm??0)/1000;group.add(mesh);
  }
 }
 clear(){this.cancelDrag();for(const helper of this.jointHelpers){helper.parent?.remove(helper);helper.geometry.dispose();helper.material.dispose();}this.jointHelpers=[];for(const marker of this.markers){marker.parent?.remove(marker);marker.traverse(o=>{if(o.userData.sharedResources)return;o.geometry?.dispose();if(Array.isArray(o.material))o.material.forEach(m=>m.dispose());else o.material?.dispose();});}this.markers=[];}
 async update(model,catalog,selected){
  const serial=++this.serial;this.clear();this.catalog=catalog;
  this.view.root.traverse(o=>{if(o.userData.panelIndex!==undefined)o.userData.mountFace=model.placement.faces.find(f=>f.panel_index===o.userData.panelIndex);});
  const rows=new Map(catalog.items.map(r=>[r.id,r]));
  const sources=new Map();await Promise.all([...new Set(model.placement.items.flatMap(i=>[i.part_id,...(i.visual_halves??[]).map(h=>h.part_id).filter(Boolean)]))].map(async id=>{try{sources.set(id,await this.mesh(rows.get(id)));}catch(e){sources.set(id,null);this.onMessage(e.message+' — pokazano znacznik zastępczy.');}}));
  if(serial!==this.serial)return;
  for(const line of [...model.placement.joint_lines,...(model.placement.closure_lines??[])]){const parent=this.view.groups.get('body'),points=[line.start_mm,line.end_mm].map(p=>new THREE.Vector3(...p.map((x,k)=>x/1000-parent.userData.pivot[k]+line.normal[k]*.0015)));const helper=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineBasicMaterial({color:line.roles?.includes('latches')?0xe28a40:0x3b9dc9}));helper.visible=this.enabled;parent.add(helper);this.jointHelpers.push(helper);}
  for(const item of model.placement.items){
   for(const half of item.visual_halves??[{section_id:item.section_id,position_mm:item.position_mm}]){
   const visualPart=half.part_id??item.part_id,row=rows.get(visualPart),group=new THREE.Group();if(!this.view.groups.has(half.section_id)||row?.show_as_complete_part===false)continue;
   group.userData.occurrence=item;group.userData.visualKey=item.id+'@'+half.section_id;this.pose(group,item,half.section_id,half.position_mm);
   const native=sources.get(visualPart);
   if(native&&(!item.visual_halves||item.seam_id)){
    this.addNative(group,visualPart,native,false,half);group.userData.geometryMode='source_mesh';
   }else{
    // A plainly labelled concept marker, never a substitute CAD solid or cutout.
    const size=[...item.footprint_mm];if(item.rotation_deg%180)size.reverse();if(item.visual_halves)size[1]/=2;
    const marker=new THREE.Mesh(new THREE.BoxGeometry(size[0]/1000,size[1]/1000,.004),new THREE.MeshStandardMaterial({color:0xe4ded1,roughness:.75}));marker.position.z=.004;group.add(marker);
    const texture=this.texture(row);if(texture){const geometry=new THREE.PlaneGeometry(size[0]/1000*.92,size[1]/1000*.92);if(half.uv_range){const uv=geometry.attributes.uv;for(let i=0;i<uv.count;i++)uv.setY(i,half.uv_range[0]+uv.getY(i)*(half.uv_range[1]-half.uv_range[0]));}const plane=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({map:texture}));plane.position.z=.0061;group.add(plane);}
   }
   const flagged=model.placement.warnings.some(w=>w.group_id===item.group_id||w.other_group_id===item.group_id),size=[...item.footprint_mm];group.userData.flagged=flagged;if(item.rotation_deg%180)size.reverse();if(item.visual_halves)size[1]/=2;
   // Pick the real local geometry envelope, including recessed parts. No fixed-size invisible handle.
   const box=new THREE.Box3();for(const child of group.children){if(!child.geometry)continue;child.geometry.computeBoundingBox();box.union(child.geometry.boundingBox.clone().translate(child.position));}
   if(box.isEmpty()){box.min.set(-.02,-.01,0);box.max.set(.02,.01,.004);}
   const bounds=box.getSize(new THREE.Vector3()).max(new THREE.Vector3(.004,.004,.004)),center=box.getCenter(new THREE.Vector3());
   const proxyGeometry=new THREE.BoxGeometry(bounds.x+.004,bounds.y+.004,bounds.z+.004);
   const outline=new THREE.LineSegments(new THREE.EdgesGeometry(proxyGeometry),new THREE.LineBasicMaterial({color:item.group_id===selected?0xf06b1f:flagged?0xc48a24:0x447359}));outline.position.copy(center);outline.visible=item.group_id===selected;group.add(outline);
   const proxy=new THREE.Mesh(proxyGeometry,new THREE.MeshBasicMaterial({side:THREE.DoubleSide}));proxy.visible=false;proxy.position.copy(center);group.add(proxy);group.userData.pickProxy=proxy;this.markers.push(group);
  }}this.view.apply();
 }
 select(id){for(const marker of this.markers){const line=marker.children.find(c=>c.isLineSegments);if(line){line.visible=marker.userData.occurrence.group_id===id;line.material.color.setHex(marker.userData.occurrence.group_id===id?0xf06b1f:marker.userData.flagged?0xc48a24:0x447359);}}}
}
