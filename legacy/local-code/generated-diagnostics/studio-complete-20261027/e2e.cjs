const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const folder=__dirname,url='http://127.0.0.1:51342/FVpz8nmQczBPgO4yEpvwEugiffxTCB-J/';
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto(url+'wizard.html');await page.waitForFunction(()=>window.rockproWizard);
 const draft=JSON.parse(fs.readFileSync(path.join(folder,'base-draft.json'),'utf8'));
 await page.evaluate(async d=>{for(const g of d.draft.placements){if(g.pattern==='closure_line')g.edge_inset_mm=150;else if(g.part_id==='H7159')g.spread=.5;}await window.rockproWizard.load(d);window.rockproWizard.navigate(7);},fs.existsSync(path.join(folder,'saved.json'))?await page.evaluate(async id=>fetch('wizard/drafts/'+id).then(r=>r.json()),JSON.parse(fs.readFileSync(path.join(folder,'saved.json'),'utf8')).id):{draft});
 await page.locator('#construction-apply').click();
 await page.waitForFunction(()=>window.rockproStructureView?.items.length>40,{},{timeout:30000});
 await page.waitForTimeout(1000);
 const state=await page.evaluate(()=>({draft:window.rockproWizard.getDraft(),model:window.rockproWizardView.model,
   structure:window.rockproStructureView.items.map(g=>({id:g.userData.occurrence.id,mode:g.userData.geometryMode,children:g.children.length})),
   markers:window.rockproPlacementView.markers.map(g=>({id:g.userData.occurrence.id,mode:g.userData.geometryMode,sourceMeshes:g.children.filter(c=>c.isMesh&&c.userData.sharedResources).length})),status:document.querySelector('#status').textContent}));
 if(state.structure.length!==state.model.construction.items.length)throw Error('Incomplete construction');
 if(state.structure.some(i=>!i.children)||state.markers.some(i=>i.mode!=='source_mesh'||i.sourceMeshes<1))throw Error('Missing actual models');
 if(state.model.placement.unresolved_groups.length)throw Error('Unresolved placement');
 const prior=await page.evaluate(()=>window.rockproWizard.getStorage().revision);const saveResponse=page.waitForResponse(r=>r.url().endsWith('/wizard/save'));await page.locator('#save-top').click();const sr=await saveResponse;if(!sr.ok())throw Error(await sr.text());await page.waitForFunction(prior=>window.rockproWizard.getStorage().revision>prior,prior);
 const saved=await page.evaluate(()=>({id:window.rockproWizard.getStorage().id,revision:window.rockproWizard.getStorage().revision,draft:window.rockproWizard.getDraft()}));
 fs.writeFileSync(path.join(folder,'saved.json'),JSON.stringify(saved,null,2));
 await page.locator('details.storage>summary').click();const download=page.waitForEvent('download');await page.locator('#export').click();await (await download).saveAs(path.join(folder,'RockPro_T1_kompletna.json'));
 await page.screenshot({path:path.join(folder,'studio-kompletna-zamknieta.png'),fullPage:true});
 const motionBefore=await page.evaluate(()=>window.rockproStructureView.items.filter(g=>['corner/100','wheel-00'].includes(g.userData.occurrence.id)).map(g=>({id:g.userData.occurrence.id,pos:g.matrixWorld.elements.slice(12,15)})));
 await page.evaluate(()=>window.rockproWizardView.all(100));await page.waitForTimeout(250);
 const motionAfter=await page.evaluate(()=>{window.rockproWizardView.root.updateMatrixWorld(true);return window.rockproStructureView.items.filter(g=>['corner/100','wheel-00'].includes(g.userData.occurrence.id)).map(g=>({id:g.userData.occurrence.id,pos:g.matrixWorld.elements.slice(12,15)}));});
 for(const before of motionBefore){const after=motionAfter.find(x=>x.id===before.id);if(before.id==='wheel-00')assert.deepStrictEqual(after.pos,before.pos);else if(Math.hypot(...after.pos.map((x,i)=>x-before.pos[i]))<.1)throw Error('Lid accessories did not follow opening');}

 await page.screenshot({path:path.join(folder,'studio-kompletna-otwarta.png'),fullPage:true});
 // Actual input edit, then verify regenerated construction instead of a screenshot-only test.
 await page.evaluate(()=>window.rockproWizard.navigate(3));await page.locator('#dim-x').fill('700');
 await page.waitForFunction(()=>window.rockproWizardView.model.draft.internal_mm[0]===700&&window.rockproStructureView.items.length>40);
 await page.waitForTimeout(300);
 const resized=await page.evaluate(()=>({width:window.rockproWizardView.model.sections[0].size_mm[0],items:window.rockproWizardView.model.construction.items}));
 if(!resized.items.some(i=>i.family_id==='stacking_sockets'&&i.seat_world_mm[0]>500))throw Error('Sockets did not follow resize');
 // Discard only this test's unsaved resize by loading the known saved revision.
 await page.evaluate(async saved=>{await window.rockproWizard.load(saved);window.rockproWizard.navigate(7);},saved);
 await page.waitForFunction(()=>window.rockproStructureView.items.length>40);
 const context=await browser.newContext({viewport:{width:1600,height:1000}}),second=await context.newPage();
 await second.goto(url+'wizard.html?draft='+saved.id);await second.waitForFunction(()=>window.rockproWizard);
 
 await second.waitForFunction(()=>window.rockproStructureView?.items.length>40);
 const reopened=await second.evaluate(()=>window.rockproWizard.getDraft());assert.deepStrictEqual(reopened,saved.draft);
 if(errors.length)throw Error(JSON.stringify(errors));
 fs.writeFileSync(path.join(folder,'e2e-results.json'),JSON.stringify({passed:true,saved,state,resized,reopened,errors},null,2));
 await browser.close();console.log(JSON.stringify({passed:true,id:saved.id,structure:state.structure.length,placements:state.model.placement.instance_count,panels:state.model.panels.length}));
})().catch(e=>{console.error(e);process.exit(1)});
