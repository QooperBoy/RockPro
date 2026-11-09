import os,sys,json,pathlib,ctypes
os.environ['ROCKPRO_IRONCAD_YEAR']='2027';sys.path.insert(0,'Integracja')
import comtypes.client
from rockpro_cad.icapi_runtime import ICAPI as A
base=comtypes.client.GetActiveObject('IronCAD.Application',dynamic=True).ZIronCADApp.QueryInterface(A.IZBaseApp)
rows=[]
for raw in base.GetAllOpenDocs():
 d=ctypes.cast(int(raw),ctypes.POINTER(A.IZDoc)) if isinstance(raw,int) else raw.QueryInterface(A.IZDoc)
 rows.append(dict(path=d.Name,guid=d.FileGUID,modified=bool(d.Modified)))
result=dict(api_version=base.ApiVersion,active=base.ActiveDoc.Name,documents=rows)
pathlib.Path('artifacts/other-project-parts-20261027/open-documents.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
