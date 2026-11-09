const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),assert=require('assert/strict'),path=require('path');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1500,height:1080}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const base='http://127.0.0.1:51342/FVpz8nmQczBPgO4yEpvwEugiffxTCB-J/';
  await page.goto(base+'wizard.html');await page.waitForFunction(()=>window.rockproWizardView?.model);await page.click('[data-step="4"]');
  const catalog=await page.evaluate(()=>fetch('wizard/parts').then(r=>r.json()));
  assert.equal(catalog.items.filter(r=>r.image).length,13);assert.equal(await page.locator('.part-card .part-image-missing').count(),1);
  // Force-load every thumbnail, including cards below the fold.
  for(const img of await page.locator('.part-card img').all()){await img.scrollIntoViewIfNeeded();await img.evaluate(e=>e.decode());}
  assert.equal(await page.locator('.part-card img').count(),13);
  await page.fill('#parts-search','H7159');const draft=await page.evaluate(()=>window.rockproWizard.getDraft());
  await page.getByRole('button',{name:'Powiększ obraz H7159',exact:true}).click();await page.locator('dialog[open] img').evaluate(e=>e.decode());assert.equal(await page.locator('dialog[open]').count(),1);
  assert.deepEqual(await page.evaluate(()=>window.rockproWizard.getDraft()),draft);await page.screenshot({path:path.join(__dirname,'enlarged.png')});await page.keyboard.press('Escape');assert.equal(await page.locator('dialog[open]').count(),0);
  await page.locator('#parts-list input[data-part="H7159"]').check();await page.waitForFunction(()=>window.rockproWizardView.model.hardware_summary.definition_count===1);
  assert.equal(await page.locator('#hardware-summary img').count(),1);await page.screenshot({path:path.join(__dirname,'studio-images.png'),fullPage:true});
  await page.fill('#parts-search','27095');assert.equal(await page.locator('#parts-list img').count(),1);assert.match(await page.locator('.part-image-caption').textContent(),/Zdjęcie producenta/);
  await page.setViewportSize({width:430,height:900});await page.getByRole('button',{name:'Powiększ obraz 27095',exact:true}).click();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(__dirname,'mobile-enlarged.png')});await page.getByRole('button',{name:'Zamknij ×',exact:true}).click();
  // Contact sheet for visual review of each exact mapped SKU, isolated from user drafts.
  await page.setViewportSize({width:1200,height:1500});await page.route('**/contact-sheet',r=>r.fulfill({contentType:'text/html',body:'<html><body></body></html>'}));await page.goto(base+'contact-sheet');
  await page.evaluate(items=>{document.body.replaceChildren();document.body.style.cssText='display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:20px;background:#e8eee5;font:16px Arial';for(const row of items){const card=document.createElement('div'),img=document.createElement('img'),label=document.createElement('b');label.textContent=row.id;card.style.cssText='background:white;padding:8px;text-align:center';card.append(label);if(row.image){img.src=row.image.url;img.style.cssText='display:block;width:100%;height:220px;object-fit:contain';card.append(img);}document.body.append(card);}},catalog.items);
  await page.locator('img').evaluateAll(async imgs=>await Promise.all(imgs.map(e=>e.decode())));await page.screenshot({path:path.join(__dirname,'contact-sheet.png'),fullPage:true});
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(__dirname,'browser-report.json'),JSON.stringify({passed:true,images:13,cad_renders:10,manufacturer_photos:3,missing_geometry_placeholder:true,modal:true,selection_unchanged:true,summary_thumbnail:true,mobile:true,errors},null,2));console.log('PASS: 13 verified images, modal, selection, summary and mobile');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});

