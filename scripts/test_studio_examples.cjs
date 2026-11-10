const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const base=(process.argv[2]??'http://127.0.0.1:51345').replace(/\/$/,'')+'/',out=path.resolve(process.argv[3]??'artifacts/examples-local');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'index.html');await page.waitForSelector('[data-open-example]');
  assert.equal(await page.locator('[data-open-example]').count(),3);
  await page.waitForFunction(()=>[...document.querySelectorAll('.ready-example>img')].every(i=>i.complete&&i.naturalWidth>0));
  await page.screenshot({path:path.join(out,'library.png')});
  await page.evaluate(()=>localStorage.setItem('rockpro.configurator.recovery.v3','preserved-unsaved-draft'));
  const examples=await page.evaluate(()=>fetch('examples.json').then(r=>r.json())),results=[],ids=[];
  for(const example of examples.items){
   await page.locator('[data-open-example="'+example.id+'"]').click();await page.waitForURL('**/wizard.html?draft=*');
   await page.waitForFunction(name=>window.rockproWizard?.getDraft().name===name,example.name);
   await page.waitForFunction(n=>window.rockproWizardView?.model.project_summary.total_count===n&&window.rockproPlacementView.markers.every(g=>g.userData.geometryMode==='source_mesh'),example.total_count);
   assert(await page.locator('#step-7').isVisible());assert.equal(await page.evaluate(()=>localStorage.getItem('rockpro.configurator.recovery.v3')),'preserved-unsaved-draft');
   const id=await page.evaluate(()=>window.rockproWizard.getStorage().id);ids.push(id);
   const model=await page.evaluate(()=>window.rockproWizardView.model);assert.equal(model.placement.unresolved_groups.length,0);assert.equal(model.project_summary.unplaced_selection.length,0);assert(model.placement.warnings.every(w=>w.code==='closure_reference'));
   await page.evaluate(()=>window.rockproWizardView.all(100));assert.equal(await page.evaluate(()=>window.rockproWizardView.values.top),100);
   await page.screenshot({path:path.join(out,example.id+'-open.png')});
   await page.reload();await page.waitForFunction(name=>window.rockproWizard?.getDraft().name===name,example.name);assert.equal(await page.evaluate(()=>window.rockproWizard.getStorage().id),id);
   results.push({id:example.id,parts:example.total_count,copy:id});await page.goto(base+'index.html');await page.waitForSelector('[data-open-example]');
  }
  assert.equal(new Set(ids).size,3);const saved=await page.evaluate(()=>fetch('wizard/drafts').then(r=>r.json()));assert.equal(saved.length,3);
  await page.locator('#theme-toggle').click();await page.setViewportSize({width:390,height:844});await page.waitForTimeout(250);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));await page.screenshot({path:path.join(out,'library-mobile-dark.png')});
  assert.deepStrictEqual(errors,[]);fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({status:'PASS',base,results,unsavedDraftPreserved:true,errors},null,2));console.log(JSON.stringify({status:'PASS',examples:results.map(x=>({id:x.id,parts:x.parts}))}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
