// E2E of the isolated demo bundle: backend geometry, meshes, local persistence,
// revision conflicts, JSON portability, browser isolation and public photo URLs.
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const base=(process.argv[2]??'http://127.0.0.1:51345').replace(/\/$/,'')+'/',out=path.resolve(process.argv[3]??'artifacts/vercel-e2e-local');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const context=await browser.newContext({viewport:{width:1600,height:1000}}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'wizard.html');await page.waitForFunction(()=>window.rockproWizard);
  const parts=await page.evaluate(()=>fetch('wizard/parts').then(r=>r.json()));assert.equal(parts.items.length,279);assert.equal(parts.items.filter(r=>r.catalog_only).length,265);assert(!JSON.stringify(parts).includes('cached_stock_raw'));assert(!JSON.stringify(parts).includes('C:\\Users'));
  await page.evaluate(()=>window.rockproWizard.navigate(4));await page.locator('#parts-source').selectOption('company');assert.equal(await page.locator('#parts-list article').count(),265);await page.locator('#parts-search').fill('H1052S');assert.equal(await page.locator('#parts-list article').count(),2);assert.equal(await page.locator('#parts-list input:disabled').count(),2);await page.locator('#parts-search').fill('');await page.locator('#parts-source').selectOption('');
  const draft=JSON.parse(fs.readFileSync(path.resolve('artifacts/studio-complete-20261027/RockPro_T1_kompletna.json'),'utf8'));draft.name='Demo T1 · kompletna';
  await page.evaluate(async draft=>{await window.rockproWizard.load({draft});window.rockproWizard.navigate(7);},draft);
  await page.waitForFunction(()=>window.rockproStructureView?.items.length===58&&window.rockproPlacementView.markers.every(g=>g.userData.geometryMode==='source_mesh'),{},{timeout:60000});
  const geometry=await page.evaluate(()=>({structure:window.rockproStructureView.items.length,manual:window.rockproWizardView.model.placement.items.length,visualGroups:window.rockproPlacementView.markers.length,summary:window.rockproWizardView.model.project_summary,status:document.querySelector('#status').textContent}));assert.equal(geometry.manual,8);
  await page.waitForFunction(()=>document.querySelector('.cost-subtotal'));assert((await page.locator('#cost-coverage').textContent()).includes('Pozycje bez wyceny'));await page.locator('#cost-assume-piece').uncheck();assert.equal(await page.locator('.cost-subtotal').count(),0);await page.locator('#cost-assume-piece').check();assert(await page.locator('.cost-subtotal').count()>0);
  await page.locator('#save-top').click();await page.waitForFunction(()=>window.rockproWizard.getStorage().revision===1);
  const id=await page.evaluate(()=>window.rockproWizard.getStorage().id);await page.locator('#save-top').click();await page.waitForFunction(()=>window.rockproWizard.getStorage().revision===2);
  const pref=await page.evaluate(()=>fetch('parts/preferences').then(r=>r.json()));assert.equal(pref.items.H7159.project_count,1);
  const stale=await page.evaluate(async({draft,id})=>(await fetch('wizard/save',{method:'POST',body:JSON.stringify({draft,id,expected_revision:1})})).status,{draft,id});assert.equal(stale,409);
  await page.evaluate(()=>window.rockproWizard.navigate(4));await page.locator('[data-favorite-id="H7159"]').click();await page.waitForFunction(()=>document.querySelector('[data-favorite-id="H7159"]').getAttribute('aria-pressed')==='true');
  await page.goto(base+'wizard.html?draft='+id);await page.waitForFunction(id=>window.rockproWizard?.getStorage().id===id,id);
  assert.equal(await page.evaluate(()=>window.rockproWizard.getStorage().revision),2);
  assert.equal((await page.evaluate(()=>fetch('parts/preferences').then(r=>r.json()))).items.H7159.favorite,true);
  await page.evaluate(()=>window.rockproWizard.navigate(3));await page.locator('#dim-x').fill('700');await page.locator('#dim-x').dispatchEvent('change');
  await page.waitForFunction(()=>window.rockproWizardView.model.draft.internal_mm[0]===700);await page.locator('#save-top').click();await page.waitForFunction(()=>window.rockproWizard.getStorage().revision===3);
  await page.locator('details.storage>summary').click();const download=page.waitForEvent('download');await page.locator('#export').click();await(await download).saveAs(path.join(out,'demo-export.json'));assert.equal(JSON.parse(fs.readFileSync(path.join(out,'demo-export.json'),'utf8')).internal_mm[0],700);
  await page.evaluate(()=>window.rockproWizard.navigate(7));await page.screenshot({path:path.join(out,'wizard.png')});
  await page.locator('#cost-summary').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'cost-summary.png')});
  await page.goto(base+'company-parts.html');await page.waitForFunction(()=>document.querySelectorAll('#company-rows tr').length===265);
  const company=await page.evaluate(()=>fetch('company/catalog').then(r=>r.json()));assert.equal(new Set(company.items.map(r=>r.id)).size,265);assert.equal(company.items.filter(r=>r.image).length,232);assert.equal(company.items.filter(r=>r.duplicate_code).length,4);assert.equal(company.items.filter(r=>r.price_raw===null).length,8);assert(!JSON.stringify(company).includes('cached_stock_raw'));assert(!JSON.stringify(company).includes('stock_cell'));
  await page.locator('#company-search').fill('H1052S');assert.equal(await page.locator('#company-rows tr').count(),2);await page.locator('#company-search').fill('');await page.screenshot({path:path.join(out,'full-company-catalog.png')});
  await page.goto(base+'photos.html');const photoCount=await page.evaluate(()=>fetch('manufacturer-photos.json').then(r=>r.json()).then(r=>r.items.length));assert(photoCount>=92);await page.waitForFunction(count=>document.querySelectorAll('#photo-list article').length===count,photoCount);await page.waitForFunction(()=>[...document.querySelectorAll('#photo-list img')].slice(0,3).every(i=>i.naturalWidth>0));
  await page.locator('#photo-search').fill('17251');assert(await page.locator('#photo-list article').count()>0);await page.screenshot({path:path.join(out,'manufacturer-photos.png')});
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(250);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
  const isolated=await browser.newContext(),other=await isolated.newPage();await other.goto(base+'wizard.html');await other.waitForFunction(()=>window.rockproWizard);assert.equal((await other.evaluate(()=>fetch('wizard/drafts').then(r=>r.json()))).length,0);await isolated.close();
  const types=await page.evaluate(async()=>{
   const result=[];for(const type of ['case','cabinet','three_piece']){
    const c=(face,kind)=>({id:crypto.randomUUID(),label:face,face,kind,depth_mm:45,hinge_edge:'high',requires:[],height_override:false});
    const d={schema:'rockpro.configurator/3',name:'Test '+type,type,internal_mm:[600,500,350],thickness_mm:9.8,cooperation:'independent',covers:type==='case'?[c('top','hinged')]:type==='cabinet'?[c('front','hinged')]:[c('top','removable'),c('front','removable')],hardware:[],placements:[]};
    const response=await fetch('wizard/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)}),model=await response.json();if(!response.ok)throw Error(model.error);result.push({type,sections:model.sections.length});
   }return result;
  });assert.deepStrictEqual(types.map(x=>x.sections),[2,2,3]);assert.deepStrictEqual(errors,[]);
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({status:'PASS',base,geometry,types,photos:photoCount,companyRecords:265,companyImages:232,companyMissingPrices:8,costEstimate:true,localDraftRevisions:3,browserIsolation:true,errors},null,2));console.log(JSON.stringify({status:'PASS',base,structure:geometry.structure,manual:geometry.manual,photos:photoCount,companyRecords:265,costEstimate:true}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
