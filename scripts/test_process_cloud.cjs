// Generated cloud bundle: report validation is stateless, persistence is browser-local.
const fs=require('fs'),path=require('path'),assert=require('assert'),{execFileSync}=require('child_process');
const {chromium}=require('playwright');
(async()=>{
 const root=path.resolve('.'),out=path.resolve('artifacts/process-cloud-e2e');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-swiftshader']});
 try{
  const context=await browser.newContext(),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:53081/wizard.html');await page.waitForFunction(()=>window.rockproWizard);
  const saved=await page.evaluate(()=>window.rockproWizard.save(true));assert(saved);
  fs.writeFileSync(path.join(out,'saved.json'),JSON.stringify(saved));
  const code="import sys,json,hashlib;from pathlib import Path;sys.path.insert(0,'Integracja');from rockpro_cad import configurator,process_runs;d=json.loads(Path('artifacts/process-cloud-e2e/saved.json').read_text(encoding='utf-8'));r=json.loads(Path('artifacts/process-runs-e2e/export.json').read_text(encoding='utf-8'));r['binding']=dict(draft_id=d['id'],draft_revision=d['revision'],draft_sha256=hashlib.sha256(process_runs.canonical(configurator.preview(d['draft'])['draft']).encode()).hexdigest());Path('artifacts/process-cloud-e2e/report.json').write_text(json.dumps(r,ensure_ascii=False),encoding='utf-8')";
  execFileSync(path.join(root,'Integracja/.venv/Scripts/python.exe'),['-c',code],{cwd:root});
  await page.locator('#process-panel').evaluate(n=>n.open=true);
  await page.locator('#process-panel input[type=file]').setInputFiles(path.join(out,'report.json'));
  await page.waitForFunction(()=>window.rockproProcessPanel?.report?.summary.completed===300);
  await page.reload();await page.waitForFunction(()=>window.rockproProcessPanel?.report?.summary.completed===300);
  await page.locator('#process-panel').evaluate(n=>n.open=true);assert(await page.locator('#process-panel').innerText().then(t=>t.includes('SYMULACJA')));
  assert.equal(await page.locator('#process-panel button',{hasText:'Przygotuj pomiar'}).isVisible(),false);
  const wrong=JSON.parse(fs.readFileSync(path.join(out,'report.json'),'utf8'));wrong.binding.draft_revision++;
  const response=await page.evaluate(async report=>{const s=window.rockproWizard.getStorage();const r=await fetch('process',{method:'POST',body:JSON.stringify({action:'import',draft_id:s.id,revision:s.revision,report})});return {status:r.status,text:await r.text()};},wrong);assert.equal(response.status,400);
  const other=await browser.newContext(),otherPage=await other.newPage();await otherPage.goto('http://127.0.0.1:53081/wizard.html');await otherPage.waitForFunction(()=>window.rockproWizard);
  assert.equal(await otherPage.evaluate(()=>Object.keys(JSON.parse(localStorage.getItem('rockpro.cloud-demo.storage.v1')??'{}').processRuns??{}).length),0);
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({passed:true,import:true,reload:true,wrong_revision_rejected:true,browser_isolation:true,errors},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
