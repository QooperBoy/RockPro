const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('assert/strict'),fs=require('fs'),path=require('path');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1550,height:1100},acceptDownloads:true}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.goto('http://127.0.0.1:51343/wizard_test_placement_20261027/wizard.html');await page.waitForFunction(()=>window.rockproWizard&&window.rockproPlacementView);
  await page.click('[data-step="4"]');for(const id of ['H7159','17251S','27095']){await page.fill('#parts-search',id);await page.locator('#parts-list input[data-part="'+id+'"]').check();}
  await page.waitForFunction(()=>window.rockproWizardView.model.hardware_summary.definition_count===3);await page.click('[data-step="5"]');
  async function facePoint(section,face,u,v){return page.evaluate(async a=>{const T=await import('./vendor/three.module.min.js'),view=window.rockproWizardView,f=view.model.placement.faces.find(f=>f.section_id===a.section&&f.face===a.face),g=view.groups.get(a.section);view.root.updateMatrixWorld(true);const p=new T.Vector3(...f.origin_mm.map((x,k)=>(x+a.u*f.size_mm[0]*f.u_axis[k]+a.v*f.size_mm[1]*f.v_axis[k])/1000-g.userData.pivot[k]));g.localToWorld(p);p.project(view.camera);const r=view.renderer.domElement.getBoundingClientRect();return {x:(p.x+1)*r.width/2,y:(1-p.y)*r.height/2,clientX:r.left+(p.x+1)*r.width/2,clientY:r.top+(1-p.y)*r.height/2};},{section,face,u,v});}
  let p=await facePoint('body','right',.5,.5);
  await page.locator('#placement-palette [data-part="H7159"]').dragTo(page.locator('#viewport canvas'),{targetPosition:{x:p.x,y:p.y}});
  await page.waitForFunction(()=>window.rockproWizardView.model.placement.instance_count===4&&window.rockproPlacementView.markers.length===4);
  assert.equal(await page.evaluate(()=>window.rockproPlacementView.markers[0].children.filter(c=>c.isMesh).length),13);console.log('PASS native drag from palette, four rigid handle meshes');
  const initial=await page.evaluate(()=>window.rockproWizard.getDraft());assert.equal(initial.placements[0].handles_per_wall,2);assert.equal(initial.placements[0].opposite_wall,true);assert.equal(initial.placements[0].spread,.5);assert.equal(initial.placements[0].u,.5);
  // Count changes are per wall, never total or purchase quantities.
  await page.selectOption('#handles-per-wall','1');await page.waitForFunction(()=>window.rockproWizardView.model.placement.instance_count===2);
  assert.ok(await page.evaluate(()=>window.rockproWizardView.model.placement.items.every(i=>i.u===.5)));
  await page.selectOption('#handles-per-wall','2');await page.waitForFunction(()=>window.rockproWizardView.model.placement.instance_count===4&&window.rockproPlacementView.markers.length===4);
  // Drag an existing right-wall handle: changes the group's spread/height, keeps pair alignment.
  const marker=await page.evaluate(async()=>{const T=await import('./vendor/three.module.min.js'),pv=window.rockproPlacementView,m=pv.markers.find(m=>m.userData.occurrence.face==='right'),p=m.getWorldPosition(new T.Vector3()).project(pv.view.camera),r=pv.view.renderer.domElement.getBoundingClientRect();return{x:r.left+(p.x+1)*r.width/2,y:r.top+(1-p.y)*r.height/2};});
  p=await facePoint('body','right',.34,.62);await page.mouse.move(marker.x,marker.y);await page.mouse.down();await page.mouse.move(p.clientX,p.clientY,{steps:16});await page.mouse.up();
  await page.waitForFunction(()=>Math.abs(window.rockproWizard.getDraft().placements[0].v-.62)<.03);assert.equal(await page.evaluate(()=>window.rockproWizardView.model.placement.instance_count),4);console.log('PASS drag existing handle group');
  await page.click('#placement-stop');await page.click('[data-step="3"]');await page.fill('#dim-y','700');
  await page.waitForFunction(()=>window.rockproWizardView.model.draft.internal_mm[1]===700&&window.rockproPlacementView.markers.length===4);
  assert.ok(await page.evaluate(()=>window.rockproWizardView.model.placement.items.every(i=>i.footprint_mm[0]===161)));
  await page.click('[data-step="5"]');await page.getByRole('button',{name:'Rozmieść 17251S',exact:true}).click();await page.selectOption('#placement-target','body/front');await page.click('#placement-add');
  await page.waitForFunction(()=>window.rockproWizardView.model.placement.instance_count===5&&window.rockproPlacementView.markers.length===5);
  assert.equal(await page.evaluate(()=>window.rockproPlacementView.markers.find(m=>m.userData.occurrence.part_id==='17251S').children.filter(c=>c.isMesh).length),35);
  await page.getByRole('button',{name:'Rozmieść 27095',exact:true}).click();await page.selectOption('#placement-target','body/front');await page.click('#placement-add');
  await page.waitForFunction(()=>window.rockproWizardView.model.placement.instance_count===6);await page.waitForFunction(()=>window.rockproWizardView.model.placement.warnings.some(w=>w.code==='overlap'));
  assert.ok((await page.locator('#placement-warnings').textContent()).includes('nachodzą'));await page.fill('#placement-v','99');await page.locator('#placement-rotation').focus();await page.waitForFunction(()=>window.rockproWizardView.model.placement.warnings.some(w=>w.code==='edge_clearance'));
  await page.click('#save');await page.waitForFunction(()=>window.rockproWizard.getStorage().revision===1);const saved=await page.evaluate(()=>window.rockproWizard.getDraft());
  await page.reload();await page.waitForFunction(()=>window.rockproWizard&&window.rockproPlacementView?.markers.length===6);assert.deepEqual(await page.evaluate(()=>window.rockproWizard.getDraft()),saved);
  const downloadEvent=page.waitForEvent('download');await page.click('#export');const download=await downloadEvent;await download.saveAs(path.join(__dirname,'placements.json'));assert.deepEqual(JSON.parse(fs.readFileSync(path.join(__dirname,'placements.json'))),saved);
  await page.setInputFiles('#file',path.join(__dirname,'placements.json'));await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Wczytano JSON'));assert.deepEqual(await page.evaluate(()=>window.rockproWizard.getDraft().placements),saved.placements);
  await page.click('[data-step="5"]');await page.screenshot({path:path.join(__dirname,'step-5.png'),fullPage:true});
  // Independent attachment on lid follows the section animation, preserving its anchor.
  await page.getByRole('button',{name:'Rozmieść H7159',exact:true}).click();await page.uncheck('#placement-opposite');await page.selectOption('#handles-per-wall','1');
  const lid=await page.evaluate(()=>window.rockproWizard.getDraft().covers[0].id);await page.selectOption('#placement-target',lid+'/top');await page.click('#placement-add');await page.waitForFunction(()=>window.rockproWizardView.model.placement.instance_count===7);
  const before=await page.evaluate(()=>{const pv=window.rockproPlacementView,m=pv.markers.find(m=>m.userData.occurrence.section_id!=='body');return m.matrixWorld.elements.slice();});
  await page.click('#open-all');const after=await page.evaluate(()=>{const pv=window.rockproPlacementView,m=pv.markers.find(m=>m.userData.occurrence.section_id!=='body');return m.matrixWorld.elements.slice();});assert.notDeepEqual(before,after);
  await page.setViewportSize({width:430,height:900});await page.screenshot({path:path.join(__dirname,'step-5-mobile.png'),fullPage:true});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(__dirname,'browser-report.json'),JSON.stringify({passed:true,palette_drag:true,existing_group_drag:true,rigid_meshes:true,per_wall_count:true,opposing_symmetry:true,resize:true,overlap_edge_warnings:true,sqlite_and_json:true,lid_motion:true,mobile:true,errors},null,2));console.log('PASS Step 5 drag/drop, symmetry, resize, warnings, persistence, motion, mobile');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});


