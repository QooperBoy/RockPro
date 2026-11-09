const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');const assert=require('assert/strict'),fs=require('fs'),path=require('path');
(async()=>{const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});try{
 const page=await browser.newPage({viewport:{width:1500,height:1100},acceptDownloads:true}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 await page.goto('http://127.0.0.1:51343/wizard_source_parts_20261027/wizard.html');await page.waitForFunction(()=>window.rockproWizard&&window.rockproPlacementView);
 const cat=await page.evaluate(()=>fetch('wizard/parts').then(r=>r.json()));assert.equal(cat.items.length,53);assert.equal(cat.source_report.open_documents,9);assert.equal(cat.source_report.candidate_count,39);
 const source=cat.items.filter(r=>r.source_project);assert.equal(source.length,39);assert.ok(source.every(r=>r.image&&r.mounting_status==='unknown'&&!r.production_approved&&r.sku===null));
 await page.click('[data-step="4"]');await page.selectOption('#parts-source','source');assert.equal(await page.locator('.part-card').count(),39);
 await page.locator('.part-card img').evaluateAll(async imgs=>{for(const e of imgs)e.loading='eager';await Promise.all(imgs.map(e=>e.decode()));});
 await page.selectOption('#parts-source','M07');assert.ok(await page.locator('.part-card').count()>0);await page.selectOption('#parts-source','source');
 const h=source.find(r=>r.catalog_code_raw==='H7165/10Z'),wheel=source.find(r=>r.catalog_code_raw==='37034'),hinge=source.find(r=>r.catalog_code_raw==='27083_1');
 for(const row of [h,wheel,hinge]){await page.fill('#parts-search',row.catalog_code_raw);await page.locator('#parts-list input[data-part="'+row.id+'"]').check();}
 await page.waitForFunction(()=>window.rockproWizardView.model.hardware_summary.definition_count===3);await page.screenshot({path:path.join(__dirname,'catalogue.png'),fullPage:true});
 await page.click('[data-step="5"]');await page.locator('#placement-palette [data-part="'+h.id+'"]').click();await page.selectOption('#handles-per-wall','4');await page.click('#placement-add');await page.waitForFunction(()=>window.rockproWizardView.model.placement.instance_count===8);
 await page.locator('#placement-palette [data-part="'+wheel.id+'"]').click();await page.selectOption('#placement-target','body/bottom');await page.click('#placement-add');await page.waitForFunction(()=>window.rockproWizardView.model.placement.instance_count===9);
 await page.locator('#placement-palette [data-part="'+hinge.id+'"]').click();assert.equal(await page.locator('#hinge-add').count(),0);assert.equal(await page.locator('#placement-target').count(),1);
 await page.click('#placement-add');await page.waitForFunction(()=>window.rockproWizardView.model.placement.instance_count===10);
 assert.ok((await page.locator('#placement-warnings').textContent()).includes('Niepotwierdzony'));
 await page.click('#save');await page.waitForFunction(()=>window.rockproWizard.getStorage().revision===1);const draft=await page.evaluate(()=>window.rockproWizard.getDraft());
 await page.reload();await page.waitForFunction(()=>window.rockproWizard&&window.rockproPlacementView?.markers.length===10);assert.deepEqual(await page.evaluate(()=>window.rockproWizard.getDraft()),draft);
 await page.click('[data-step="5"]');await page.screenshot({path:path.join(__dirname,'placement.png'),fullPage:true});
 // Contact sheet for all newly extracted parts, with no modifications to source CAD.
 await page.route('**/contact-sheet',r=>r.fulfill({contentType:'text/html',body:'<html><body></body></html>'}));await page.goto('http://127.0.0.1:51343/wizard_source_parts_20261027/contact-sheet');await page.setViewportSize({width:1200,height:1400});
 await page.evaluate(rows=>{document.body.style.cssText='display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:15px;background:#ecf0e9;font:14px Arial';for(const row of rows){const card=document.createElement('div'),title=document.createElement('b'),img=document.createElement('img');card.style.cssText='background:white;text-align:center;padding:5px';title.textContent=row.catalog_code_raw+' · '+row.source_project;img.src=row.image.url;img.style.cssText='width:100%;height:150px;object-fit:contain';card.append(title,img);document.body.append(card);}},source);
 await page.locator('img').evaluateAll(imgs=>Promise.all(imgs.map(e=>e.decode())));await page.screenshot({path:path.join(__dirname,'contact-sheet.png'),fullPage:true});assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(__dirname,'browser-report.json'),JSON.stringify({passed:true,total:53,source_candidates:39,source_images:39,source_filter:true,observed_project_filter:true,placement_handles_wheel_component:true,partial_hinge_not_auto_joint:true,sqlite_roundtrip:true,errors},null,2));console.log('PASS: 53 catalogue entries, 39 source images, filters, placement and saved draft');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
