// End-to-end check of stored supplier meshes and actual placement rendering.
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('playwright');
(async()=>{
 const base=(process.argv[2]??'http://127.0.0.1:51346').replace(/\/$/,'')+'/',out=path.resolve(process.argv[3]??'artifacts/supplier-studio-check');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:process.env.ROCKPRO_CHROME??'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'wizard.html');await page.waitForFunction(()=>window.rockproWizard&&window.rockproPlacementView);
  const assets=await page.evaluate(async()=>{
   const cat=await fetch('wizard/parts').then(r=>r.json()),rows=cat.items.filter(r=>r.geometry_status==='supplier_step_display');
   const unique=[...new Map(rows.map(r=>[r.image.mesh_sha256,r])).values()],{decodeMesh}=await import('./mesh-codec.js');let triangles=0;
   for(const row of unique){
    const res=await fetch(row.image.mesh_url);if(!res.ok)throw Error('Missing '+row.id);const raw=await res.arrayBuffer();
    const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),v=>v.toString(16).padStart(2,'0')).join('');if(sha!==row.image.mesh_sha256)throw Error('SHA mismatch');
    const mesh=await decodeMesh(raw,row.image.mesh_compression);
    if(mesh.units!=='m'||mesh.frame!=='mount.local_uvn'||!mesh.display_only)throw Error('Bad frame');
    for(const e of mesh.elements){if(!e.positions.length||e.positions.length%9||e.positions.length!==e.normals.length||!e.positions.every(Number.isFinite)||e.materials.reduce((s,m)=>s+m.count,0)!==e.positions.length/3)throw Error('Bad triangles');triangles+=e.positions.length/9;}
   }
   const byFamily=family=>rows.find(r=>r.family_id===family&&r.concept_envelope_mm.every(v=>v<300));
   return {models:unique.length,definitions:rows.length,triangles,handle:byFamily('handles'),vent:byFamily('vents'),hinge:byFamily('hinges')};
  });
  assert.equal(assets.models,74);assert(assets.definitions>=74);
  await page.evaluate(async({handle,vent,hinge})=>{
   const d=window.rockproWizard.getDraft();d.name='Próba modeli producenta — uchwyty, wentylacja, zawiasy';d.internal_mm=[1000,800,600];d.covers[0].id="top";d.covers[0].depth_mm=90;d.hardware=[handle,vent,hinge].map(r=>({part_id:r.id,revision:r.revision}));d.construction={enabled:false,wheels:false,stacking:false};
   d.placements=[{id:'vendor-handle',part_id:handle.id,revision:1,section_id:'body',face:'right',u:.5,v:.5,rotation_deg:0,pattern:'single',count_per_wall:1,handles_per_wall:1,opposite_wall:true,spread:0},
    {id:'vendor-vent',part_id:vent.id,revision:1,section_id:'body',face:'front',u:.5,v:.45,rotation_deg:0,pattern:'single',count_per_wall:1,opposite_wall:false,spread:0},
    {id:'vendor-hinge',part_id:hinge.id,revision:1,pattern:'closure_line',seam_id:'seam-top-rear',count:2,edge_inset_mm:200,clearance_mm:5,avoid_handles:true}];
   await window.rockproWizard.load({draft:d});window.rockproWizard.navigate(5);
  },assets);
  await page.waitForFunction(()=>window.rockproPlacementView.markers.length>=5&&window.rockproPlacementView.markers.every(m=>m.userData.geometryMode==='source_mesh'),{},{timeout:60000});
  // Exercise the real step-5 palette/form: add an occurrence, then resize back.
  await page.locator('#placement-add').click();
  await page.waitForFunction(()=>window.rockproWizard.getDraft().placements.length===4);
  await page.evaluate(async()=>{const d=window.rockproWizard.getDraft();d.internal_mm=[1100,850,650];await window.rockproWizard.load({draft:d});});
  await page.waitForFunction(()=>window.rockproWizardView.model.internal_mm?.[0]===1100||window.rockproWizard.getDraft().internal_mm[0]===1100);
  await page.evaluate(()=>window.rockproWizard.save());
  await page.waitForFunction(()=>window.rockproWizard.getStorage().id);
  const before=await page.evaluate(()=>window.rockproWizard.getDraft()),id=await page.evaluate(()=>window.rockproWizard.getStorage().id);
  await page.goto(base+'wizard.html?draft='+id);await page.waitForFunction(()=>window.rockproWizard?.getStorage().id&&window.rockproPlacementView?.markers.length>=5);
  assert.deepStrictEqual(await page.evaluate(()=>window.rockproWizard.getDraft()),before);
  await page.evaluate(()=>{window.rockproWizard.navigate(5);window.rockproWizardView.fit();});
  await page.locator('canvas').first().screenshot({path:path.join(out,'supplier-placement.png')});
  await page.screenshot({path:path.join(out,'studio-suppliers.png'),fullPage:true});
  assert.deepStrictEqual(errors,[]);
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({passed:true,models:assets.models,definitions:assets.definitions,triangles:assets.triangles,draft_id:id,errors},null,2));
  console.log('PASS: '+assets.models+' supplier meshes; placement, extra occurrence, resize, save/reload');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});


