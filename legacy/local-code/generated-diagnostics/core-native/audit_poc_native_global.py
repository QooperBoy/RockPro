import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import IronCADPrototypeDriver,write_receipt_once
from rockpro_cad.core_case.native_reader import NativePoseAdapter
root=Path('artifacts/h7159-poc-native-20261022-02').resolve()
source=root/'presentation/H7159_POC_presentation.ics'
d=IronCADPrototypeDriver(source)
a=NativePoseAdapter(d.adapter.legacy,d.base,d.adapter.document,d.api,source)
rows=[]
for i in range(a.child_count(a.root())):
 n=a.child_at(a.root(),i).QueryInterface(d.api.IZElement);kind=a.identity(n)['kind']
 q=n.QueryInterface(d.api.IZPart if kind=='part' else d.api.IZAssembly)
 row={'id':int(n.Id),'name':str(n.Name),'matrix':a.matrix(n,True),'native_global_bbox_mm':[float(v)*1000 for v in q.GetBoundingBox(False)]}
 if kind=='part':row.update(color=int(q.SurfaceFinish.Color),transparency=float(q.SurfaceFinish.Transparency))
 rows.append(row)
d.assert_source_unchanged()
write_receipt_once(root/'presentation/direct_global_bbox.json',{'passed_read_only':True,'rows':rows})
print(json.dumps(rows),flush=True)
