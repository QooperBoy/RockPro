import sys,json,ctypes,datetime
from pathlib import Path
sys.path.insert(0,str(Path('Integracja').resolve()))
from rockpro_cad.parts.native import NativePartsAdapter,file_sha256
from rockpro_cad.core_case.native import write_receipt_once
from rockpro_cad.cad_lock import cad_writer_lock
repo=Path('.').resolve();folder=repo/'artifacts'/('prototype-cleanup-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));folder.mkdir(exist_ok=False)
candidates=[Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\Integracja\rockpro_cad\qa\core-native-158e2ef\case_prototype.ics'),repo/'artifacts/h7159-poc-native-20261022-04/delivery/POC_H7159_wnetrze_900x600x330.ics',Path(r'C:\Ai\Podnośniki\Materialy_dla_firm\RockPro\AI_CAD\T_1_1\Showcase_Epson_parametry.ics')]
a=None
for p in candidates:
 try:a=NativePartsAdapter.attach(p);break
 except RuntimeError:pass
if a is None:raise RuntimeError('no existing explicit context; refusing any open/activation')
user=ctypes.WinDLL('user32');user.GetForegroundWindow.restype=ctypes.c_void_p
def state():
 d=a.base.ActiveDoc
 return {'foreground_hwnd':int(user.GetForegroundWindow() or 0),'active_doc':{'path':str(d.Name),'guid':str(d.FileGUID),'modified':bool(d.Modified)}}
with cad_writer_lock():
 before=state();rows=[]
 for item in a.base.GetAllOpenDocs():
  d=item.QueryInterface(a.api.IZDoc);name=str(d.Name);path=Path(name)
  reason=None;owned=False
  if 'showcase' in path.name.lower() or 'epson' in path.name.lower():reason='preserve named original/user source'
  elif path.is_absolute() and path.is_relative_to(repo/'artifacts'):
   rel=path.relative_to(repo/'artifacts');first=rel.parts[0].lower()
   if first.startswith(('h7159-poc-','corner410429-','runtime-ui-')):owned=True;reason='generated prototype/hidden copy under exact owned task directory'
   elif first=='core-native' and len(rel.parts)>2 and rel.parts[1].startswith(('native-','real-H7159-','core-service-native')) and path.name.lower() in ('case_prototype.ics','source_snapshot.ics','source_catalog_asset.ics','h7159_native.ics'):owned=True;reason='recorded generated native prototype/asset path'
   else:reason='outside narrowly owned prototype directories; preserve'
  elif path.is_absolute() and path.parent==candidates[0].parent and path.name in ('case_prototype.ics','H7159_native.ics'):owned=True;reason='our light QA context/asset copies'
  else:reason='unknown or unsaved document; preserve'
  rows.append({'path':name,'guid':str(d.FileGUID),'modified':bool(d.Modified),'read_only':bool(d.IsReadOnly()),'type':int(d.Type),'owned_prototype':owned,'reason':reason,'sha256_disk':file_sha256(path) if path.is_file() else None})
 after=state();assert before==after
 result={'read_only_inventory':True,'context_path':str(a.source),'before':before,'after':after,'get_open_docs_count':int(a.base.GetOpenDocsCount()),'all_open_doc_count':len(rows),'documents':rows,
  'excluded_original':str(candidates[-1]),'cleanup_policy':'Only exact inventoried owned paths; modified own prototypes capture memory to unique backup and new saved work file, then close clean. No original/user unknown documents. Foreground HWND must remain unchanged; CAD active document may change intentionally on close.'}
 write_receipt_once(folder/'inventory_before.json',result)
 print(json.dumps({'folder':str(folder),'count':len(rows),'owned_count':sum(r['owned_prototype'] for r in rows),'documents':rows},ensure_ascii=True),flush=True)
