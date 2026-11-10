const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const base='http://127.0.0.1:51342/FVpz8nmQczBPgO4yEpvwEugiffxTCB-J/';
  await page.goto(base+'company-parts.html?draft=70a10d97998143749cdfe9ae793e3bdc');
  await page.waitForFunction(()=>document.querySelector('#company-rows').children.length===265);
  const catalogue=await page.evaluate(()=>fetch('company/catalog').then(r=>r.json()));assert.equal(catalogue.items.length,265);
  assert.equal(catalogue.items.filter(r=>r.image).length,231);assert.equal(catalogue.items.filter(r=>r.cutout_note).length,15);
  await page.waitForTimeout(500);await page.screenshot({path:path.join(__dirname,'catalog-light.png')});
  const firstImage=page.locator('#company-rows img').first();await firstImage.scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>document.querySelector('#company-rows img').naturalWidth>0);
  await page.locator('#company-search').fill('PN - H1052S');assert.equal(await page.locator('#company-rows tr').count(),2);
  await page.locator('#company-search').fill('');await page.locator('#company-cutouts').check();assert.equal(await page.locator('#company-rows tr').count(),15);
  await page.screenshot({path:path.join(__dirname,'cutout-notes.png')});
  await page.locator('#company-cutouts').uncheck();await page.locator('#company-models').check();
  const meshCandidates=await page.locator('#company-rows tr').count();assert(meshCandidates>0&&meshCandidates<265);
  await page.locator('#company-models').uncheck();await page.locator('#theme-toggle').click();await page.screenshot({path:path.join(__dirname,'catalog-dark.png')});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(__dirname,'catalog-mobile.png')});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2);if(overflow)console.log(errors,await page.evaluate(()=>[...document.querySelectorAll('body>*')].map(x=>({tag:x.tagName,cls:x.className,w:x.getBoundingClientRect().width,left:x.getBoundingClientRect().left,right:x.getBoundingClientRect().right,scroll:x.scrollWidth}))));assert.equal(overflow,false);
  await page.setViewportSize({width:1600,height:1000});
  await page.locator('a[data-app-page=wizard]').click();await page.waitForFunction(()=>window.rockproWizardView?.model.project_summary.total_count===76);
  const ref=await page.evaluate(async()=>{const parts=await fetch('wizard/parts').then(r=>r.json());return parts.items.find(r=>r.id==='EG-0113').company_references;});assert(ref.length>0);
  assert.deepStrictEqual(errors,[]);
  fs.writeFileSync(path.join(__dirname,'browser-results.json'),JSON.stringify({passed:true,records:265,images:231,cutout_notes:15,meshCandidates,roundtrip_case_parts:76,errors},null,2));
  console.log(JSON.stringify({passed:true,records:265,meshCandidates}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
