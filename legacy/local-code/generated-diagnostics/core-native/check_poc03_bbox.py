import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.core_case.native import IronCADPrototypeDriver,write_receipt_once
from rockpro_cad.core_case.native_reader import NativePoseAdapter,validate_matrix,transform_bbox
from rockpro_cad.core_case.hardware_poc_native import _direct_global_box
p=Path('artifacts/h7159-poc-native-20261022-03/A-base/working.ics').resolve()
d=IronCADPrototypeDriver(p);a=NativePoseAdapter(d.adapter.legacy,d.base,d.adapter.document,d.api,p)
rows=[]
def walk(node,path):
 node=node.QueryInterface(d.api.IZElement);kind=a.identity(node)['kind']
 if kind=='part':
  m=validate_matrix(a.matrix(node,True));b=a.bbox(node,'part');calc=transform_bbox(b['minimum']+b['maximum'],m);direct=_direct_global_box(node,d.api)
  rows.append({'path':path,'name':str(node.Name),'matrix':m,'local':b,'direct':direct,'transformed':calc,'difference':[x-y for x,y in zip(direct,calc)]})
 elif kind in ('scene','assembly'):
  for i in range(a.child_count(node)):walk(a.child_at(node,i),path+[i])
walk(a.root(),[])
write_receipt_once(Path('artifacts/h7159-poc-native-20261022-03/bbox-diagnostic.json'),{'rows':rows})
for r in rows:
 if max(abs(x) for x in r['difference'])>.003:print(json.dumps(r))
