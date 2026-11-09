const fs=require('fs'),path=require('path');
const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1600,height:1000}});
 const saved=JSON.parse(fs.readFileSync(path.join(__dirname,'saved.json'),'utf8'));
 await page.goto('http://127.0.0.1:51342/FVpz8nmQczBPgO4yEpvwEugiffxTCB-J/wizard.html?draft='+saved.id);
 await page.waitForFunction(()=>window.rockproStructureView?.items.length===58);await page.waitForTimeout(500);
 await page.locator('#viewport').screenshot({path:path.join(__dirname,'model-przod.png')});
 await page.evaluate(()=>{const v=window.rockproWizardView,c=v.controls.target;v.camera.position.set(c.x+1.3,c.y+2.1,c.z+1.3);v.controls.update();});await page.waitForTimeout(300);
 await page.locator('#viewport').screenshot({path:path.join(__dirname,'model-tyl.png')});
 await page.evaluate(()=>{const v=window.rockproWizardView,c=v.controls.target;v.camera.position.set(c.x+1.2,c.y-1.8,c.z-1.5);v.controls.update();});await page.waitForTimeout(300);
 await page.locator('#viewport').screenshot({path:path.join(__dirname,'model-podwozie.png')});
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
