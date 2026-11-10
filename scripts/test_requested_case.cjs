const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const folder=path.resolve(process.argv[2]),data=JSON.parse(fs.readFileSync(path.join(folder,'project-evidence.json')));
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1050}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(data.studio_url);await page.waitForFunction(n=>window.rockproWizard&&window.rockproStructureView?.items.length===n&&window.rockproPlacementView?.markers.length===14,data.construction.length,{timeout:60000});
  const state=await page.evaluate(()=>({draft:window.rockproWizard.getDraft(),count:window.rockproWizardView.model.project_summary.total_count,
   modes:window.rockproPlacementView.markers.map(m=>m.userData.geometryMode),structure:window.rockproStructureView.items.map(g=>g.userData.occurrence.part_id)}));
  assert.equal(state.count,data.summary.total_count);assert(state.modes.every(m=>m==='source_mesh'));assert.deepStrictEqual(state.draft,JSON.parse(fs.readFileSync(path.join(folder,'RockPro_Penn_AdamHall.json'))));
  await page.evaluate(()=>{window.rockproWizard.navigate(8);window.rockproWizardView.fit();});await page.waitForTimeout(650);
  await page.waitForFunction(()=>document.querySelector('#cost-results')?.textContent.includes('do zakupu 1 op.'));
  assert.equal(await page.locator('.cost-subtotal').getAttribute('data-amount'),'48.78');
  await page.screenshot({path:path.join(folder,'Studio-projekt.png'),fullPage:true});
  await page.locator('canvas').first().screenshot({path:path.join(folder,'Skrzynia-3D.png')});
  await page.evaluate(()=>window.rockproWizardView.all(100));await page.waitForTimeout(400);
  await page.locator('canvas').first().screenshot({path:path.join(folder,'Skrzynia-otwarta.png')});
  await page.reload();await page.waitForFunction(()=>window.rockproWizard?.getStorage().id===new URL(location.href).searchParams.get('draft'));
  assert.deepStrictEqual(errors,[]);fs.writeFileSync(path.join(folder,'browser-check.json'),JSON.stringify({status:'PASS',state,errors},null,2));console.log('PASS: saved project reload, '+state.count+' parts, 14 mesh placements, '+data.construction.length+' structural parts, no JS errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
