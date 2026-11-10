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
folder=root/'presentation';folder.mkdir(exist_ok=False)
with cad_writer_lock():
 d=IronCADPrototypeDriver(r['output_path'])
 d.adapter.document.QueryInterface(d.api.IZSceneDoc).SaveAsCopy(str(folder/'H7159_POC_presentation.ics'),d.api.Z_LINKS_COPY_ALL,False)
 doc=d.base.OpenFile(str(folder/'H7159_POC_presentation.ics'),False)
 scene=doc.QueryInterface(d.api.IZSceneDoc)
 pose=NativePoseAdapter(d.adapter.legacy,d.base,doc,d.api,Path(doc.Name))
 appearance=[]
 for i in range(pose.child_count(pose.root())):
  node=pose.child_at(pose.root(),i).QueryInterface(d.api.IZElement)
  if pose.identity(node)['kind']=='assembly':node.QueryInterface(d.api.IZAssembly).Update()
  else:
   p=node.QueryInterface(d.api.IZPart)
   if str(node.Name).startswith('RP:'):
    f=p.SurfaceFinish
    if str(node.Name)=='RP:product/1':f.Color=0xD09024
    else:f.Color=0x9CBADD;f.Transparency=.72
    appearance.append({'id':int(node.Id),'name':str(node.Name),'color':int(f.Color),'transparency':float(f.Transparency)})
   p.Update()
 scene.UpdateGraphics(0);scene.Redraw()
 ids={h['id']:h['node_id'] for h in r['after_reopen']['handles']}
 observation=_measure(pose,r['plan'],ids,r['source_body_signature'])
 scene.SaveAs(str(folder/'H7159_POC_presentation.ics'),d.api.Z_LINKS_COPY_ALL,True)
 d.assert_source_unchanged()
 write_receipt_once(folder/'presentation_receipt.json',{'passed':True,'closed_proof_source':r['output_path'],'closed_proof_unchanged':True,'presentation_path':str(doc.Name),'presentation_sha256':file_sha256(doc.Name),'geometry_observation':observation,'appearance':appearance,'visibility_changes':[]})
 print('PRESENTATION PASS',flush=True)
