const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 const base='http://127.0.0.1:51342/FVpz8nmQczBPgO4yEpvwEugiffxTCB-J/';let page,original,companyId;const errors=[];
 const set=async(id,favorite)=>page.evaluate(async({id,favorite})=>{const r=await fetch('parts/preferences',{method:'POST',headers:{'Content-Type':'application/json','X-RockPro-Session':location.pathname.split('/')[1]},body:JSON.stringify({part_id:id,favorite})});if(!r.ok)throw Error(await r.text());},{id,favorite});
 try{
  page=await browser.newPage({viewport:{width:1600,height:1000}});page.on('pageerror',e=>errors.push(e.stack??e.message));
  await page.goto(base+'wizard.html?draft=70a10d97998143749cdfe9ae793e3bdc');await page.waitForFunction(()=>window.rockproWizard);
  original=await page.evaluate(()=>fetch('parts/preferences').then(r=>r.json()));fs.writeFileSync(path.join(__dirname,'preferences-before.json'),JSON.stringify(original,null,2));const before=await page.evaluate(()=>({draft:window.rockproWizard.getDraft(),storage:window.rockproWizard.getStorage()}));
  await page.evaluate(()=>window.rockproWizard.navigate(4));
  const star=page.locator('[data-favorite-id="H7159"]');await star.waitFor();
  if(await star.getAttribute('aria-pressed')==='true'){await star.click();await page.waitForFunction(()=>document.querySelector('[data-favorite-id="H7159"]').getAttribute('aria-pressed')==='false');}
  await star.click();await page.waitForFunction(()=>document.querySelector('[data-favorite-id="H7159"]').getAttribute('aria-pressed')==='true');
  await page.locator('#parts-only-favorites').check();assert(await page.locator('.part-card[data-part="H7159"]').count());
  assert.equal(await page.locator('.part-card>.favorite-button[aria-pressed=false]').count(),0);
  await page.screenshot({path:path.join(__dirname,'wizard-favorites.png')});
  await page.locator('#parts-only-favorites').uncheck();await page.locator('#parts-sort').selectOption('frequent');
  const counts=await page.evaluate(()=>fetch('parts/preferences').then(r=>r.json()));const visible=await page.locator('.part-card').evaluateAll(rows=>rows.map(r=>r.dataset.part));
  assert.equal(counts.items[visible[0]]?.project_count??0,Math.max(...visible.map(id=>counts.items[id]?.project_count??0)));
  const after=await page.evaluate(()=>({draft:window.rockproWizard.getDraft(),storage:window.rockproWizard.getStorage()}));assert.deepStrictEqual(after,before);
  await page.locator('a[data-app-page=library]').click();await page.locator('a[data-app-page=wizard]').click();await page.waitForFunction(()=>window.rockproWizard);assert.equal(await page.locator('#parts-sort').inputValue(),'frequent');assert.equal(await page.locator('#parts-only-favorites').isChecked(),false);
  const other=await browser.newContext({viewport:{width:1600,height:1000}}),second=await other.newPage();
  await second.goto(base+'wizard.html?draft=70a10d97998143749cdfe9ae793e3bdc');await second.waitForFunction(()=>window.rockproWizard);await second.evaluate(()=>window.rockproWizard.navigate(4));
  await second.waitForFunction(()=>document.querySelector('[data-favorite-id="H7159"]')?.getAttribute('aria-pressed')==='true');await other.close();
  await page.goto(base+'company-parts.html');await page.waitForFunction(()=>document.querySelectorAll('#company-rows tr').length===265);
  const catalog=await page.evaluate(()=>fetch('company/catalog').then(r=>r.json()));const duplicate=catalog.items.filter(r=>r.code==='PN - H1052S');companyId=duplicate[0].id;
  await set(companyId,false);await page.reload();await page.waitForFunction(()=>document.querySelectorAll('#company-rows tr').length===265);
  const companyStar=page.locator('[data-favorite-id="'+companyId+'"]');await companyStar.click();
  await page.waitForFunction(id=>document.querySelector('[data-favorite-id="'+id+'"]').getAttribute('aria-pressed')==='true',companyId);
  await page.locator('#company-favorites').check();assert(await page.locator('tr[data-part="'+companyId+'"]').count());
  if(!original.items[duplicate[1].id]?.favorite)assert.equal(await page.locator('tr[data-part="'+duplicate[1].id+'"]').count(),0);
  await page.locator('#theme-toggle').click();await page.screenshot({path:path.join(__dirname,'company-favorites-dark.png')});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(__dirname,'favorites-mobile.png')});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
  const final=await page.evaluate(()=>fetch('parts/preferences').then(r=>r.json()));
  for(const [id,stat]of Object.entries(original.items))assert.equal(final.items[id]?.project_count??0,stat.project_count);
  assert.deepStrictEqual(errors,[]);fs.writeFileSync(path.join(__dirname,'browser-results.json'),JSON.stringify({passed:true,persistence_new_browser_context:true,usage_unchanged_by_reads:true,draft_unchanged:true,frequency_sort:true,duplicate_variants_separate:true,errors},null,2));
  console.log(JSON.stringify({passed:true}));
 }finally{
  if(original&&page){try{await set('H7159',original.items.H7159?.favorite??false);if(companyId)await set(companyId,original.items[companyId]?.favorite??false);}catch(e){console.error('Preference cleanup failed',e);process.exitCode=1;}}
  await browser.close();
 }
})().catch(e=>{console.error(e);process.exit(1)});
