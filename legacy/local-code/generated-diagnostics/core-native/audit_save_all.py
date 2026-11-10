import sys,json,os,traceback
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.parts.native import NativePartsAdapter
from rockpro_cad.core_case.native import write_receipt_once
try:
 source=Path('artifacts/core-native/native-A-20261021-02/case_prototype.ics').resolve()
 a=NativePartsAdapter.attach(source)
 rows=[]
 for item in a.base.GetAllOpenDocs():
  doc=item.QueryInterface(a.api.IZDoc)
  rows.append({'path':str(doc.Name),'file_guid':str(doc.FileGUID),'modified':bool(doc.Modified),'read_only':bool(doc.IsReadOnly()),'type':int(doc.Type)})
 result={'operation':'user-authorized-save-all.preflight','read_only':True,'documents':rows,'count':len(rows)}
 write_receipt_once(Path('artifacts/core-native/save-all-preflight.json'),result)
 print(json.dumps(result,ensure_ascii=True,indent=2),flush=True);os._exit(0)
except BaseException:
 traceback.print_exc();sys.stderr.flush();os._exit(1)
