import sys,json,hashlib,shutil,math
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.icapi_runtime import ICAPI as api,assert_host
import comtypes.client
out=ROOT/'artifacts/ironcad2023-pu1sp1-validation/t2-roundtrip-03';out.mkdir(exist_ok=False)
source=ROOT/"artifacts/t2-analysis-20261026/source/DiGiCo Quantum 1'12.ics"
expected='e7dccb157f58ffec249c4634896b71b831b6228354afd688f37ba83f50cb75cb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source)==expected
working=out/'working.ics';shutil.copyfile(source,working)
final=out/'RockPro_T2_reference_IC2023.ics'
report={'passed':False,'source_sha256':expected};owned=None
base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(api.IZBaseApp)
assert_host(base)
def state():
 d=base.ActiveDoc
 return [d.Name,d.FileGUID,bool(d.Modified)] if d else None
def snapshot(doc):
 rows=[]
 def walk(element):
  e=element.QueryInterface(api.IZElement)
  r={'id':e.Id,'name':e.Name,'type':e.Type,'children':e.GetChildrenCount()}
  if e.Type==api.Z_ELEMENT_PART:
   part=e.QueryInterface(api.IZPart)
   r['bounds']=list(part.GetBody(True).GetBoundingBox())
   assert len(r['bounds'])==6 and all(math.isfinite(v) for v in r['bounds'])
   r['features']=e.QueryInterface(api.IZPartFeatureMgr).GetFeaturesCount()
  if e.Type in [api.Z_ELEMENT_PART,api.Z_ELEMENT_ASSEMBLY]:
   m=e.QueryInterface(api.IZSceneElement).GetTransformToGlobal()
   r['world']=[m.GetValue(i,j) for i in range(4) for j in range(4)]
   assert all(math.isfinite(v) for v in r['world'])
  rows.append(r)
  if e.GetChildrenCount():
   a=e.GetChildrenZArray()
   for i in range(e.GetChildrenCount()):
    child=a.Get(i).QueryInterface(api.IZElement)
    if child.Type in [api.Z_ELEMENT_PART,api.Z_ELEMENT_ASSEMBLY]:walk(child)
 walk(doc.QueryInterface(api.IZSceneDoc).GetTopElement())
 return rows
with cad_writer_lock():
 report['api_version']=base.ApiVersion;report['context_before']=state()
 try:
  already,candidate=base.OpenFile2(str(working),False,False)
  if already:raise ValueError('Already open; ownership refused')
  owned=candidate
  before=snapshot(owned)
  assert len(before)==449 and sum(r['type']==api.Z_ELEMENT_PART for r in before)==335
  owned.QueryInterface(api.IZSceneDoc).SaveAs(str(final),api.Z_LINKS_COPY_ALL,False)
  assert not owned.Modified
  owned.Close();owned=None
  already,candidate=base.OpenFile2(str(final),False,False)
  if already:raise ValueError('Reopen ownership refused')
  owned=candidate;after=snapshot(owned)
  assert len(before)==len(after)
  errors=[]
  for b,a in zip(before,after):
   for key in ['id','name','type','children','features']:
    if b.get(key)!=a.get(key):errors.append([b['id'],key])
   for key in ['bounds','world']:
    if len(b.get(key,[]))!=len(a.get(key,[])) or any(not math.isclose(v,w,rel_tol=1e-8,abs_tol=1e-8) for v,w in zip(b.get(key,[]),a.get(key,[]))):errors.append([b['id'],key])
  report.update(rows=len(after),parts=335,comparison_errors=errors,saved_path=str(final),saved_sha256=sha(final))
  assert not errors
  report['passed']=True
 except Exception as e:
  import traceback
  report['error']=traceback.format_exc()
 finally:
  if owned is not None:
   try:
    if owned.Modified:owned.QueryInterface(api.IZSceneDoc).SaveAsCopy(str(out/'recovery.ics'),api.Z_LINKS_COPY_ALL,False)
    owned.Close()
   except Exception as e:report['cleanup_error']=repr(e);report['passed']=False
  report['source_unchanged']=sha(source)==expected;report['context_after']=state()
  if not report['source_unchanged'] or report['context_before']!=report['context_after']:report['passed']=False
  (out/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report));sys.exit(0 if report['passed'] else 1)


