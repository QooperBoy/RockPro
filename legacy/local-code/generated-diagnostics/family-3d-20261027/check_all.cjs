const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');const path=require('path');const assert=require('assert/strict');
const base='http://127.0.0.1:51342/FVpz8nmQczBPgO4yEpvwEugiffxTCB-J/';
const folder=__dirname;
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1600,height:1050},acceptDownloads:true});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);await page.waitForFunction(()=>window.rockproStudio);
 const catalog=await page.evaluate(async()=>fetch('catalog.json').then(r=>r.json()));const report={models:{},errors};
 const expected={M01:433,M02:162,M03:387,M04:453,M05:434,M06:569,M07:383};
 const families=catalog.families.filter(f=>f.variants.some(v=>catalog.previews[v.id]));
 for(const family of families)for(const variant of family.variants.filter(v=>catalog.previews[v.id])){
  await page.evaluate(id=>window.rockproStudio.selectFamily(id),family.id);
  if(family.variants[0].id!==variant.id)await page.selectOption('#variant',variant.id);
  await page.waitForFunction(key=>window.rockproReferenceView?.loaded&&window.rockproReferenceView.key===key,variant.id,{timeout:120000});
  const metrics=await page.evaluate(()=>{
   const v=window.rockproReferenceView;v.reset();
   const matrices=()=>v.meshes.map(m=>[...m.matrix.elements]);const original=matrices();
   const equal=(a,b)=>a.every((x,i)=>Math.abs(x-b[i])<1e-7);
   const dimensions=v.baselineDimensions();v.setDimensions(dimensions.map(x=>x*1.1));
   const changed=matrices();let rigid=0;
   v.meshes.forEach((m,i)=>{if(m.userData.row.policy==='rigid'){rigid++;for(const j of [0,1,2,4,5,6,8,9,10])if(Math.abs(changed[i][j]-original[i][j])>1e-7)throw Error('Rigid scaling '+m.userData.row.path);}});
   v.reset();const motions=[];
   for(const motion of v.model.motions){
    const travel=Math.min(100,motion.max);v.setMotion(motion.id,travel);const moved=matrices();let affected=0;
    v.meshes.forEach((m,i)=>{
     const member=m.userData.row.motion_ids.includes(motion.id),want=[...original[i]];
     if(member){affected++;motion.axis.forEach((a,k)=>want[12+k]+=a*travel/1000);}
     if(!equal(moved[i],want))throw Error('Unexpected motion '+motion.id+' '+m.userData.row.path);
    });motions.push({id:motion.id,affected});v.reset();
   }
   const reset=matrices().every((m,i)=>equal(m,original[i]));if(!reset)throw Error('Reset mismatch');
   return {meshes:v.meshes.length,source_empty:v.model.source_empty_parts?.length??0,source_sha256:v.model.source_sha256,dimensions,rigid,motions,reset,canvases:document.querySelectorAll('#viewport canvas').length};
  });
  assert.equal(metrics.meshes,expected[variant.id]);assert.equal(metrics.source_sha256,variant.source_sha256);assert.equal(metrics.canvases,1);
  assert.equal(metrics.meshes+metrics.source_empty,variant.part_count);
  assert.equal(await page.locator('#source-warning').isVisible(),metrics.source_empty>0);
  await page.screenshot({path:path.join(folder,variant.id+'-browser.png'),fullPage:true});
  // Exercise the actual JSON download and import, including independent motion state.
  for(const [id,value]of[['x','600'],['y','500'],['z','350']])await page.fill('#'+id,value);
  await page.locator('#slide-0').evaluate(input=>{input.value='100';input.dispatchEvent(new Event('input',{bubbles:true}));});
  const downloadPromise=page.waitForEvent('download');await page.click('#export');const download=await downloadPromise;
  const saved=path.join(folder,variant.id+'-concept.json');await download.saveAs(saved);
  const draft=JSON.parse(fs.readFileSync(saved));assert.equal(draft.variant_id,variant.id);assert.equal(Object.values(draft.preview.motion_values)[0],100);
  await page.click('#reset-view');await page.setInputFiles('#file',saved);
  await page.waitForFunction(()=>document.querySelector('#result').textContent.startsWith('Wczytano szkic'));
  assert.equal(await page.evaluate(()=>Object.values(window.rockproReferenceView.motionValues)[0]),100);
  await page.click('#reset-view');await page.uncheck('#show-covers');
  const motions=await page.evaluate(()=>window.rockproReferenceView.model.motions);
  for(let i=0;i<motions.length;i++)if(!['lid','hood'].includes(motions[i].id))await page.locator('#slide-'+i).evaluate((input,max)=>{input.value=String(Math.min(100,max));input.dispatchEvent(new Event('input',{bubbles:true}));},motions[i].max);
  await page.click('#fit-view');
  await page.screenshot({path:path.join(folder,variant.id+'-open-browser.png'),fullPage:true});
  metrics.json_roundtrip=true;report.models[variant.id]=metrics;console.log(variant.id,JSON.stringify(metrics));
 }
 if(catalog.previews.M01&&catalog.previews.M07){
  await page.evaluate(()=>window.rockproStudio.selectFamily('screens'));
  await page.waitForFunction(()=>window.rockproReferenceView?.loaded&&window.rockproReferenceView.key==='M01');
  await page.locator('#slide-0').evaluate(input=>{input.value='111';input.dispatchEvent(new Event('input',{bubbles:true}));});
  await page.selectOption('#variant','M07');await page.waitForFunction(()=>window.rockproReferenceView?.loaded&&window.rockproReferenceView.key==='M07');
  await page.locator('#slide-0').evaluate(input=>{input.value='77';input.dispatchEvent(new Event('input',{bubbles:true}));});
  await page.selectOption('#variant','M01');await page.waitForFunction(()=>window.rockproReferenceView?.loaded&&window.rockproReferenceView.key==='M01');
  assert.equal(await page.locator('#slide-0').inputValue(),'111');
  await page.selectOption('#variant','M07');await page.waitForFunction(()=>window.rockproReferenceView?.loaded&&window.rockproReferenceView.key==='M07');
  assert.equal(await page.locator('#slide-0').inputValue(),'77');report.separate_screen_variants=true;
 }
 // Rapid selection must leave only the newest requested model, with one renderer.
 await page.evaluate(ids=>{for(const id of ids)window.rockproStudio.selectFamily(id);},families.map(f=>f.id));
 const last=families.at(-1).variants[0].id;
 await page.waitForFunction(key=>window.rockproReferenceView?.loaded&&window.rockproReferenceView.key===key,last,{timeout:120000});
 assert.equal(await page.locator('#viewport canvas').count(),1);report.rapid_selection=true;
 await page.setViewportSize({width:430,height:900});await page.screenshot({path:path.join(folder,'mobile-browser.png'),fullPage:true});
 report.mobile={documentWidth:await page.evaluate(()=>document.documentElement.scrollWidth),viewport:430};
 assert.equal(report.mobile.documentWidth,430);assert.deepEqual(errors,[]);
 report.passed=true;fs.writeFileSync(path.join(folder,Object.keys(report.models).length===7?'browser-report.json':'browser-partial-report.json'),JSON.stringify(report,null,2));await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
