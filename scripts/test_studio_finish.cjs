// Reproduce the final-step dead end, portable download and browser-storage failures.
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const base=(process.argv[2]??'http://127.0.0.1:51345').replace(/\/$/,'')+'/',out=path.resolve(process.argv[3]??'artifacts/save-finish-local');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const context=await browser.newContext({viewport:{width:1500,height:1000}}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'wizard.html');await page.waitForFunction(()=>window.rockproWizard);
  const examples=await page.evaluate(()=>fetch('examples.json').then(r=>r.json()));
  const fixture=path.resolve('artifacts/save-finish-20261028/user-project-before.json');
  const draft=fs.existsSync(fixture)?JSON.parse(fs.readFileSync(fixture,'utf8')):examples.items[0].draft;
  await page.evaluate(async draft=>{await window.rockproWizard.load({draft});window.rockproWizard.navigate(7);},draft);
  assert(await page.locator('#next').isEnabled());assert.equal(await page.locator('#next').textContent(),'Sprawdź projekt →');assert(await page.locator('#download-final').isVisible());
  if(draft.type!=='case')assert(!(await page.locator('#construction-apply').isEnabled()));
  await page.locator('#next').click();await page.waitForSelector('#review-overview');assert(await page.locator('#step-8').isVisible());await page.locator('#next').click();await page.waitForFunction(()=>window.rockproWizard.getStorage().revision===1);
  const first=await page.evaluate(()=>window.rockproWizard.getStorage());assert(new URL(page.url()).searchParams.get('draft')===first.id);
  assert((await page.locator('#action-feedback').textContent()).includes('Zapisano projekt'));assert(await page.locator('details.storage').evaluate(el=>el.open));
  await page.reload();await page.waitForFunction(()=>window.rockproWizard);assert.equal(await page.evaluate(()=>window.rockproWizard.getStorage().id),first.id);assert.deepStrictEqual(await page.evaluate(()=>window.rockproWizard.getDraft()),draft);
  await page.screenshot({path:path.join(out,'finish-saved.png')});
  // Export must be synchronous and work while preview/save networking is offline.
  await page.route('**/wizard/preview',route=>route.abort());const download=page.waitForEvent('download');await page.locator('#download-top').click();await(await download).saveAs(path.join(out,'download.json'));assert.deepStrictEqual(JSON.parse(fs.readFileSync(path.join(out,'download.json'),'utf8')),draft);await page.unroute('**/wizard/preview');
  // Failed persistence is visible and leaves the current saved revision unchanged.
  await page.evaluate(()=>{window.finishOriginalSet=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='rockpro.cloud-demo.storage.v1')throw new DOMException('Full','QuotaExceededError');return window.finishOriginalSet.call(this,k,v);};});
  await page.locator('#save-top').click();await page.waitForFunction(()=>document.querySelector('#action-feedback').textContent.includes('Nie zapisano projektu'));
  assert.equal(await page.evaluate(()=>window.rockproWizard.getStorage().revision),1);assert(await page.locator('#next').isEnabled());
  await page.evaluate(()=>{Storage.prototype.setItem=window.finishOriginalSet;});
  // Save-as-new updates the URL and reloads the copy, preserving the original.
  if(!(await page.locator('#save-copy').isVisible()))await page.locator('details.storage>summary').click();await page.locator('#save-copy').click();await page.waitForFunction(id=>window.rockproWizard.getStorage().id!==id,first.id);
  const second=await page.evaluate(()=>window.rockproWizard.getStorage());assert.notEqual(first.id,second.id);assert.equal(new URL(page.url()).searchParams.get('draft'),second.id);
  await page.reload();await page.waitForFunction(()=>window.rockproWizard);assert.equal(await page.evaluate(()=>window.rockproWizard.getStorage().id),second.id);
  assert.equal((await page.evaluate(()=>fetch('wizard/drafts').then(r=>r.json()))).length,2);
  // Missing browser-local permalink must not disable the entire editor or import.
  const missing=await context.newPage();missing.on('pageerror',e=>errors.push(e.message));await missing.goto(base+'wizard.html?draft='+'f'.repeat(32));await missing.waitForFunction(()=>window.rockproWizard);
  assert((await missing.locator('#action-feedback').textContent()).includes('Nie znaleziono projektu'));assert(await missing.locator('#download-top').isEnabled());
  await missing.locator('#file').setInputFiles(path.join(out,'download.json'));await missing.waitForFunction(draft=>JSON.stringify(window.rockproWizard.getDraft())===JSON.stringify(draft)&&!new URL(location.href).searchParams.has('draft'),draft);
  assert.equal(new URL(missing.url()).searchParams.get('draft'),null);assert.deepStrictEqual(await missing.evaluate(()=>window.rockproWizard.getDraft()),draft);
  await missing.locator('#save-top').click();await missing.waitForFunction(()=>window.rockproWizard.getStorage().revision===1);await missing.close();
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));await page.screenshot({path:path.join(out,'finish-mobile.png')});
  assert.deepStrictEqual(errors,[]);fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({status:'PASS',base,type:draft.type,saved:true,downloadWithoutNetwork:true,quotaFailureVisible:true,copyUrlStable:true,missingLinkImport:true,errors},null,2));console.log(JSON.stringify({status:'PASS',type:draft.type,downloadWithoutNetwork:true,quotaFailureVisible:true,copyUrlStable:true,missingLinkImport:true}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
