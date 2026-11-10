// Transient preview only. Python validates and resolves the committed draft.
export const opposite={left:'right',right:'left',front:'rear',rear:'front',top:'bottom',bottom:'top'};
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
export function pointOnFace(hit){const f=hit.frame;return f.origin_mm.map((x,k)=>x+hit.u*f.size_mm[0]*f.u_axis[k]+hit.v*f.size_mm[1]*f.v_axis[k]);}
export function nearestJoint(hit,model,id){
 const point=pointOnFace(hit);let best=null;
 for(const line of model.placement.joint_lines.filter(j=>!id||j.id===id)){
  const axis=line.end_mm.map((x,k)=>x-line.start_mm[k]),t=clamp(axis.reduce((n,x,k)=>n+x*(point[k]-line.start_mm[k]),0)/line.length_mm**2,0,1);
  const distance=Math.hypot(...axis.map((x,k)=>line.start_mm[k]+t*x-point[k]));
  if(!best||distance<best.distance)best={line,t,distance};
 }return best;
}
export function propose(group,hit,model,existing){
 const g=structuredClone(group);
 if(g.pattern==='joint_line'){
  const near=nearestJoint(hit,model,existing?g.joint_id:null);if(!near||near.distance>150)return null;
  g.joint_id=near.line.id;if(existing&&g.hinge_count>1)g.edge_inset_mm=Math.min(near.t,1-near.t)*near.line.length_mm;
  return g;
 }
 if(!model.placement.faces.some(f=>f.section_id===hit.section_id&&f.face===hit.face)||(g.opposite_wall&&!model.placement.faces.some(f=>f.section_id===hit.section_id&&f.face===opposite[hit.face])))return null;
 const n=g.count_per_wall,idx=hit.occurrence?Number(hit.occurrence.id.split(':').at(-1)):0,offset=n>1?(idx/(n-1)-.5)*g.spread:0;
 Object.assign(g,{section_id:hit.section_id,face:hit.face,u:clamp(hit.u-(existing?offset:0),0,1),v:hit.v});
 if(g.pattern==='symmetric'){
  g.u=.5;
  if(existing&&n>1){const factor=Math.abs(idx/(n-1)-.5);if(factor>1e-5)g.spread=clamp(Math.abs(hit.u-.5)/factor,0,1);}
 }return g;
}
export function resolvePreview(g,model){
 const footprint=model.placement.part_envelopes[g.part_id]??[64,44],result=[];
 if(g.pattern==='joint_line'){
  const line=model.placement.joint_lines.find(j=>j.id===g.joint_id);if(!line||g.hinge_count>1&&g.edge_inset_mm*2>line.length_mm)return result;
  const angle=line.rotation_deg*Math.PI/180,cross=line.u_axis.map((u,k)=>-Math.sin(angle)*u+Math.cos(angle)*line.v_axis[k]);
  for(let i=0;i<g.hinge_count;i++){
   const d=g.hinge_count===1?line.length_mm/2:g.edge_inset_mm+i*(line.length_mm-2*g.edge_inset_mm)/(g.hinge_count-1),pos=line.start_mm.map((x,k)=>x+d/line.length_mm*(line.end_mm[k]-x));
   result.push({id:g.id+':joint:'+i,group_id:g.id,part_id:g.part_id,section_id:'body',position_mm:pos,rotation_deg:line.rotation_deg,u_axis:line.u_axis,v_axis:line.v_axis,normal:line.normal,footprint_mm:line.rotation_deg%180?[...footprint].reverse():footprint,
    visual_halves:[{section_id:'body',position_mm:pos.map((x,k)=>x-footprint[1]/4*cross[k]),uv_range:[0,.5]},{section_id:line.cover_id,position_mm:pos.map((x,k)=>x+footprint[1]/4*cross[k]),uv_range:[.5,1]}]});
  }return result;
 }
 for(const face of [g.face,...(g.opposite_wall?[opposite[g.face]]:[])]){
  const f=model.placement.faces.find(f=>f.section_id===g.section_id&&f.face===face);if(!f)return [];
  for(let i=0;i<g.count_per_wall;i++){
   let u=(g.pattern==='symmetric'?.5:g.u)+(g.count_per_wall===1?0:(i/(g.count_per_wall-1)-.5)*g.spread),v=g.v;
   if(face!==g.face){if(['top','bottom'].includes(face))v=1-v;else u=1-u;}
   result.push({id:g.id+':'+face+':'+i,group_id:g.id,part_id:g.part_id,section_id:g.section_id,position_mm:f.origin_mm.map((x,k)=>x+u*f.size_mm[0]*f.u_axis[k]+v*f.size_mm[1]*f.v_axis[k]),rotation_deg:g.rotation_deg,u_axis:f.u_axis,v_axis:f.v_axis,normal:f.normal,footprint_mm:g.rotation_deg%180?[...footprint].reverse():footprint});
  }
 }return result;
}
