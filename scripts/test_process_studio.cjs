// Isolated Studio E2E. All generated operation counts are explicitly simulation.
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('playwright');
(async()=>{
 const base=(process.argv[2]??'http://127.0.0.1:53077/RockProProcessEvidence20261031Test/').replace(/\/$/,'')+'/',out=path.resolve('artifacts/process-runs-e2e');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(base+'wizard.html');await page.waitForFunction(()=>window.rockproWizard&&window.rockproPlacementView);
  const result=await page.evaluate(async()=>{
   const w=window.rockproWizard,d=w.getDraft();d.name='TEST — obserwacja SDK / AI';d.hardware=[{part_id:'H7159',revision:1}];
   d.placements=[{id:'carry',part_id:'H7159',revision:1,section_id:'body',face:'left',u:.5,v:.5,rotation_deg:0,pattern:'symmetric',count_per_wall:2,handles_per_wall:2,opposite_wall:true,spread:.5}];
   await w.load({draft:d});const saved=await w.save(true);if(!saved)throw Error('Save failed');
   const token=location.pathname.split('/')[1],post=async value=>{const r=await fetch('process',{method:'POST',headers:{'Content-Type':'application/json','X-RockPro-Session':token},body:JSON.stringify(value)});const data=await r.json();if(!r.ok)throw Error(data.error);return data;};
   const run=await post({action:'create',draft_id:saved.id,revision:saved.revision,label:'Przykład 270 standard + 30 AI',mode:'simulation'});
   const occurrences=window.rockproWizardView.model.placement.items;
   const events=[{event_id:'reason',kind:'intervention',operation_id:'unknown-handle',stage:'handles',status:'resolved',origin:'ai',executor:'agent',reason:'SYMULACJA: nowy wariant uchwytu bez mapy otworu; agent przygotował propozycję do sprawdzenia.',part_id:'H7159',label:'Nowy wariant uchwytu — przykład'}];
   for(let i=0;i<300;i++)events.push({event_id:'op-'+i,kind:'operation',operation_id:'op-'+i,stage:i<270?'structure':'handles',status:'success',origin:i<270?'standard':'ai',executor:'sdk',label:'Przykładowa operacja '+i,duration_ms:2,part_id:'H7159',occurrence_id:occurrences[i<270?1:0].id,...(i>=270?{intervention_id:'unknown-handle'}:{})});
   const final=await post({action:'append',run_id:run.id,events,state:'completed'});
   await window.rockproProcessPanel.refresh();return{run_id:run.id,draft_id:saved.id,summary:final.summary,occurrence:occurrences[0].id};
  });
  assert.equal(result.summary.completed,300);assert.equal(result.summary.by_origin.ai,30);assert.equal(result.summary.by_origin.standard,270);assert.equal(result.summary.by_executor.sdk,300);
  await page.locator('#process-panel').evaluate(n=>n.open=true);await page.locator('#process-panel .process-card').first().waitFor();
  await page.locator('.process-layer input').check();
  const colors=await page.evaluate(()=>({tinted:window.rockproProcessPanel.originals.length,colors:window.rockproProcessPanel.originals.map(([mesh])=>mesh.material.color.getHex())}));assert(colors.tinted>0);assert(colors.colors.includes(0xb58aff));
  await page.locator('#process-panel .process-tools select').nth(1).selectOption('ai');
  assert.equal(await page.locator('#process-panel tbody tr').count(),30);
  const downloaded=page.waitForEvent('download');await page.locator('#process-panel button',{hasText:'Pobierz log JSON'}).click();const download=await downloaded;await download.saveAs(path.join(out,'export.json'));
  const report=JSON.parse(fs.readFileSync(path.join(out,'export.json'),'utf8'));assert.equal(report.events.length,301);assert.equal(report.mode,'simulation');
  await page.locator('#process-panel input[type=file]').setInputFiles(path.join(out,'export.json'));await page.waitForTimeout(500);
  assert.equal(await page.locator('#process-panel select').first().locator('option').count(),1);
  await page.locator('#process-panel').screenshot({path:path.join(out,'panel.png')});
  await page.locator('#theme-toggle').click();await page.waitForTimeout(200);
  await page.locator('#process-panel').screenshot({path:path.join(out,'panel-dark.png')});
  assert.equal(await page.evaluate(()=>getComputedStyle(document.querySelector('.process-rows th')).color), 'rgb(229, 238, 232)');
  await page.reload();await page.waitForFunction(()=>window.rockproProcessPanel?.report?.summary.completed===300);
  await page.evaluate(async()=>{const w=window.rockproWizard;const d=w.getDraft();d.internal_mm[0]+=10;await w.load({...w.getStorage(),draft:d});await w.save();});
  await page.waitForTimeout(500);assert.equal(await page.evaluate(()=>window.rockproProcessPanel.current()),false);
  await page.locator('#process-panel').evaluate(n=>n.open=true);await page.locator('.process-layer input').check();assert.equal(await page.evaluate(()=>window.rockproProcessPanel.originals.length),0);
  await page.setViewportSize({width:430,height:900});await page.waitForTimeout(300);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),true);
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({passed:true,summary:{completed:300,standard:270,ai:30,sdk:300},colors:true,export_import:true,persistence:true,stale_layer_disabled:true,mobile:true,errors},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
