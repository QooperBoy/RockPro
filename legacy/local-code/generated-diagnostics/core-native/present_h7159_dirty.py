import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import IronCADPrototypeDriver,write_receipt_once
from rockpro_cad.core_case.hardware_poc_native import _measure
from rockpro_cad.core_case.native_reader import NativePoseAdapter
from rockpro_cad.cad_lock import cad_writer_lock
from rockpro_cad.parts.native import file_sha256
root=Path('artifacts/h7159-poc-native-20261022-02').resolve()
r=json.loads((root/'C-return/hardware_poc_receipt.json').read_text(encoding='utf-8'))
folder=root/'presentation-dirty';folder.mkdir(exist_ok=False);output=folder/'H7159_POC_display.ics'
with cad_writer_lock():
 d=IronCADPrototypeDriver(r['output_path'])
 d.adapter.document.QueryInterface(d.api.IZSceneDoc).SaveAsCopy(str(output),d.api.Z_LINKS_COPY_ALL,False)
 doc=d.base.OpenFile(str(output),False);scene=doc.QueryInterface(d.api.IZSceneDoc)
 a=NativePoseAdapter(d.adapter.legacy,d.base,doc,d.api,output)
 def walk(node):
  node=node.QueryInterface(d.api.IZElement);kind=a.identity(node)['kind']
  if kind in ('scene','assembly'):
   for i in range(a.child_count(node)):walk(a.child_at(node,i))
   if kind=='assembly':node.QueryInterface(d.api.IZAssembly).Update()
  elif kind=='part':node.QueryInterface(d.api.IZPart).Update()
  node.SetDirtyFlag(d.api.Z_DIRTY_GRAPHICS)
 walk(a.root());scene.Update();scene.UpdateGraphics(0);scene.Redraw()
 scene.SaveAs(str(output),d.api.Z_LINKS_COPY_ALL,True);doc.Close();doc=d.base.OpenFile(str(output),False)
 scene=doc.QueryInterface(d.api.IZSceneDoc);a=NativePoseAdapter(d.adapter.legacy,d.base,doc,d.api,output)
 scene.UpdateGraphics(0);scene.Redraw()
 ids={h['id']:h['node_id'] for h in r['after_reopen']['handles']}
 observation=_measure(a,r['plan'],ids,r['source_body_signature'])
 d.assert_source_unchanged()
 write_receipt_once(folder/'presentation_receipt.json',{'passed_geometry':True,'source_unchanged':True,'output':str(output),'output_sha256':file_sha256(output),'after_reopen':observation,'sequence':['copy','recursive part.Update/assembly.Update','SetDirtyFlag(Z_DIRTY_GRAPHICS) each element','scene.Update','UpdateGraphics(0)','Redraw','save','close','reopen','UpdateGraphics(0)','Redraw']})
 print('DIRTY GRAPHICS MEASUREMENT PASS',flush=True)
