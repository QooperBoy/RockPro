import pathlib,json,sys,os,hashlib,zipfile
root=pathlib.Path(__file__).resolve().parents[2];folder=root/'artifacts/family-3d-20261027'
bundle=pathlib.Path(r'C:\Users\zuzan\.codex\worktrees\6acf\Ironcad\workspace\rockpro-cad\artifacts\model-library-20261026')
os.environ['ROCKPRO_IRONCAD_YEAR']='2027';sys.path.insert(0,str(root/'scripts'));from run_t1_machining_job import run
manifest=json.loads((bundle/'pristine/manifest.json').read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
for key in ['M06','M03','M05','M01','M07']:
 inv=json.loads((bundle/'native-02'/(key+'-inventory.json')).read_text(encoding='utf-8'));parts=[];nodes={}
 for row in inv['rows']:
  if row['path']=='root':continue
  part=row['type']=='Z_ELEMENT_PART';node=dict(n=row['name'],id=row['id'],t='p' if part else 'a',i=str(len(parts)) if part else '0',c=[])
  if part:parts.append(dict(node_id=row['id'],mesh_id=len(parts),name=row['name']))
  nodes[row['path']]=node
 for row in inv['rows']:
  if row['path']=='root':continue
  parent=row['path'].rsplit('/',1)[0]
  if parent in nodes:nodes[parent]['c'].append(nodes[row['path']])
 tree={'t':[nodes[row['path']] for row in inv['rows'] if row['path']!='root' and row['path'].rsplit('/',1)[0]=='root']}
 model=next(m for m in manifest['models'] if m['key']==key);output=folder/key/'kernel-fast-03'
 run(output,root/'scripts/native/ExportKernelMeshes.cs',dict(expected_pid=11432,source=model['source'],source_sha256=model['sha256'],parts=parts))
 result=json.loads((output/'result.json').read_text(encoding='utf-8'))
 assert len(result['files'])==len(parts) and result['passed'] and result['context_preserved'] and result['source_unchanged']
 export=output/'native-export.zip'
 with zipfile.ZipFile(export,'x',zipfile.ZIP_DEFLATED) as archive:
  archive.writestr('tree.json',json.dumps(tree,ensure_ascii=False))
  for item in result['files']:
   path=output/'meshes'/item['file'];assert sha(path)==item['sha256'];archive.write(path,item['file'])
 receipt=dict(passed=True,source_unchanged=True,context_preserved=True,source_sha256=model['sha256'],export_sha256=sha(export),kernel_report_sha256=sha(output/'result.json'),method='ICAPI.GetSpecifiedPolyMeshes',native_part_count=len(parts),saved=False)
 (output/'export-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 print('KERNEL COMPLETE',key,len(parts),flush=True)

import runpy
runpy.run_path(str(folder/"prepare_library.py"),run_name="__main__")
print("ALL SEVEN DATASETS PREPARED; index.json ready for final UI checks",flush=True)
