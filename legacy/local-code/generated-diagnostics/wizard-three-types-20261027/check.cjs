const {chromium}=require('C:/Users/zuzan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const url='http://127.0.0.1:51343/wizard_test_session_20261027/wizard.html';
const lid=(id,face,kind)=>({id,label:id,face,kind,depth_mm:45,hinge_edge:'high',requires:[],height_override:false});
const legacy={schema:'rockpro.configurator/1',name:'Archiwalna skrzynia',type:'case',subtype:'two_covers',internal_mm:[600,500,350],thickness_mm:9.8,joint_gap_mm:2,cooperation:'independent',covers:[lid('top','top','hinged'),lid('front','front','removable')]};
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:1500,height:1100},acceptDownloads:true});
 await context.addInitScript(value=>{if(!localStorage.getItem('rockpro.configurator.recovery.v1'))localStorage.setItem('rockpro.configurator.recovery.v1',JSON.stringify({draft:value,storage:{id:'a'.repeat(32),revision:1},dirty:true}));},legacy);
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 await page.goto(url);await page.waitForFunction(()=>window.rockproWizardView?.model);await page.locator('#legacy-notice').waitFor({state:'visible'});
 assert.deepEqual(await page.locator('#type option').allTextContents(),['Skrzynia','Szafa','Skrzynia 3-elementowa']);
 assert.equal(await page.locator('#subtype,#cover-count,#apply-count').count(),0);
 const oldRaw=await page.evaluate(()=>localStorage.getItem('rockpro.configurator.recovery.v1'));
 await page.click('#legacy-convert');await page.waitForFunction(()=>window.rockproWizardView.model.draft.type==='three_piece');
 assert.equal(await page.evaluate(()=>window.rockproWizard.getStorage().id),null);
 assert.equal(await page.evaluate(()=>localStorage.getItem('rockpro.configurator.recovery.v1')),oldRaw);
 async function flush(){return page.evaluate(()=>{
  const v=window.rockproWizardView,top=v.model.sections.find(s=>s.face==='top'),front=v.model.sections.find(s=>s.face==='front'),body=v.model.sections[0];
  const upper=id=>Math.max(...v.groups.get(id).children.filter(o=>o.isMesh).map(o=>{o.geometry.computeBoundingBox();return o.getWorldPosition(v.camera.position.clone()).z+o.geometry.boundingBox.max.z;}));
  return {front:upper(front.id),top:upper(top.id),body:body.size_mm[2],frontHeight:front.size_mm[2],bottom:front.position_mm[2],kind:v.model.sections.slice(1).map(s=>s.kind)};
 });}
 let bounds=await flush();assert.ok(Math.abs(bounds.front-bounds.top)<1e-6);assert.equal(bounds.bottom,0);assert.deepEqual(bounds.kind,['removable','removable']);
 await page.click('[data-step="3"]');
 for(const [id,value]of[['dim-z','500'],['thickness','12'],['gap','4']])await page.fill('#'+id,value);
 await page.locator('#section-editors input[type=number]').nth(0).fill('125');await page.locator('#section-editors input[type=number]').nth(1).fill('80');
 await page.waitForFunction(()=>{const d=window.rockproWizardView.model.draft;return d.internal_mm[2]===500&&d.thickness_mm===12&&d.joint_gap_mm===4&&d.covers[0].depth_mm===125;});
 bounds=await flush();assert.ok(Math.abs(bounds.front-bounds.top)<1e-6);assert.equal(bounds.body,524);assert.equal(bounds.frontHeight,653);
 await page.click('#close-all');await page.screenshot({path:path.join(__dirname,'three-piece-flush.png'),fullPage:true});await page.locator('#viewport').screenshot({path:path.join(__dirname,'flush-3d.png')});
 await page.click('#save');await page.waitForFunction(()=>window.rockproWizard.getStorage().revision===1);
 const dlPromise=page.waitForEvent('download');await page.click('#export');const dl=await dlPromise;const jsonFile=path.join(__dirname,'roundtrip-v2.json');await dl.saveAs(jsonFile);
 const exported=JSON.parse(fs.readFileSync(jsonFile));assert.equal(exported.schema,'rockpro.configurator/2');assert.equal('subtype'in exported,false);
 await page.reload();await page.waitForFunction(()=>window.rockproWizardView?.model?.draft.type==='three_piece');assert.ok(Math.abs((await flush()).front-(await flush()).top)<1e-6);
 await page.setInputFiles('#file',jsonFile);await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Wczytano JSON'));assert.deepEqual(await page.evaluate(()=>window.rockproWizard.getDraft()),exported);
 await page.click('[data-step="1"]');await page.selectOption('#type','case');await page.click('#next');await page.waitForFunction(()=>window.rockproWizardView.model.draft.type==='case');
 assert.equal(await page.evaluate(()=>window.rockproWizardView.model.sections.length),2);assert.equal(await page.evaluate(()=>window.rockproWizardView.model.sections[1].kind),'hinged');
 await page.click('[data-step="1"]');await page.selectOption('#type','cabinet');await page.click('#apply-type');await page.waitForFunction(()=>window.rockproWizardView.model.draft.type==='cabinet');await page.click('[data-step="2"]');
 await page.getByLabel('Sposób otwierania').selectOption('removable');await page.waitForFunction(()=>window.rockproWizardView.model.sections[1].kind==='removable');
 assert.equal(await page.evaluate(()=>window.rockproWizardView.model.sections.length),2);
 const unsupported=structuredClone(legacy);unsupported.covers[0].face='front';const bad=path.join(__dirname,'archived-double-front.json');fs.writeFileSync(bad,JSON.stringify(unsupported));
 await page.setInputFiles('#file',bad);await page.locator('#legacy-notice').waitFor({state:'visible'});await page.click('#legacy-convert');await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('nie pasuje do trzech'));
 assert.equal(await page.evaluate(()=>window.rockproWizard.getDraft().type),'cabinet');
 await page.setViewportSize({width:430,height:900});await page.click('#fit');assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),430);assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(__dirname,'browser-report.json'),JSON.stringify({passed:true,exact_three_types:true,no_subtype:true,case_hinged:true,cabinet_removable:true,three_piece_both_removable:true,flush_rendered_meshes:bounds,preserved_body:true,legacy_preserved:true,legacy_conversion_explicit:true,double_front_refused:true,sqlite_roundtrip:true,json_v2_roundtrip:true,mobile:true,errors},null,2));
 await browser.close();console.log('PASS: three types, flush rendered geometry after resize, archive preservation and draft roundtrip');
})().catch(e=>{console.error(e);process.exit(1);});

