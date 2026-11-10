const fs=require('fs');const path=require('path');
const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const folder=__dirname;const index=JSON.parse(fs.readFileSync(path.join(folder,'index.json'),'utf8'));
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1600,height:1000}});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:51342/FVpz8nmQczBPgO4yEpvwEugiffxTCB-J/wizard.html');
 await page.waitForFunction(()=>window.rockproWizard&&window.rockproPlacementView);
 const checks=[];
 for(const row of index){
  const draft=JSON.parse(fs.readFileSync(path.join(folder,row.slug,'draft.json'),'utf8'));
  await page.evaluate(async ({row,draft})=>{await window.rockproWizard.load({id:row.id,revision:row.revision,draft});window.rockproWizard.navigate(6);},{row,draft});
  await page.waitForFunction(()=>window.rockproPlacementView.markers.length>0);
  await page.waitForTimeout(700);
  const state=await page.evaluate(()=>({name:window.rockproWizard.getDraft().name,sections:window.rockproWizardView.groups.size,markers:window.rockproPlacementView.markers.length,canvas:window.rockproWizardView.renderer.domElement.width}));
  if(state.sections!==draft.covers.length+1||!state.canvas)throw Error('Missing 3D scene '+row.slug);
  await page.screenshot({path:path.join(folder,row.slug,'studio-zamknieta.png'),fullPage:true});
  await page.evaluate(()=>window.rockproWizardView.all(100));await page.waitForTimeout(200);
  await page.screenshot({path:path.join(folder,row.slug,'studio-otwarta.png'),fullPage:true});
  checks.push({...row,...state,passed:true});
 }
 if(errors.length)throw Error(JSON.stringify(errors));
 fs.writeFileSync(path.join(folder,'browser-results.json'),JSON.stringify({passed:true,checks,errors},null,2));
 await browser.close();console.log(JSON.stringify({passed:true,examples:checks.length}));
})().catch(e=>{console.error(e);process.exit(1)});
