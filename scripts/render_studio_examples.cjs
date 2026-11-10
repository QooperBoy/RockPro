// Render actual Studio geometry, never AI mockups or source-customer screenshots.
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const base=(process.argv[2]??'http://127.0.0.1:51345').replace(/\/$/,'')+'/',release=path.resolve(process.argv[3]??'artifacts/vercel-studio-20261028-07');
 const images=path.resolve('artifacts/studio-example-images');fs.mkdirSync(images,{recursive:true});fs.mkdirSync(path.join(release,'public/examples'),{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1100}});await page.goto(base+'wizard.html');await page.waitForFunction(()=>window.rockproWizard);
  const examples=await page.evaluate(()=>fetch('examples.json').then(r=>r.json()));
  for(const example of examples.items){
   await page.evaluate(async draft=>{await window.rockproWizard.load({draft});window.rockproWizard.navigate(7);window.rockproWizardView.fit();},example.draft);
   await page.waitForFunction(count=>window.rockproWizardView.model.project_summary.total_count===count&&window.rockproPlacementView.markers.every(g=>g.userData.geometryMode==='source_mesh')&&window.rockproStructureView.items.every(g=>g.children.length),example.total_count);
   assert.equal(await page.evaluate(()=>window.rockproWizardView.model.placement.unresolved_groups.length),0);
   await page.addStyleTag({content:'.viewport-tools,.cube-menu,.cube-home,.standard-view-cube,.viewport-hud,.viewport-selection{visibility:hidden!important}'});
   await page.waitForTimeout(300);const file=path.join(images,example.id+'.png');await page.locator('#viewport').screenshot({path:file});fs.copyFileSync(file,path.join(release,'public',example.image));
  }
  console.log('PASS: rendered three complete examples from actual 3D meshes');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
