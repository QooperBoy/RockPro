import json,pathlib,hashlib,re,sys,os
root=pathlib.Path(__file__).resolve().parents[2];folder=root/'artifacts/family-3d-20261027'
bundle=pathlib.Path(r'C:\Users\zuzan\.codex\worktrees\6acf\Ironcad\workspace\rockpro-cad\artifacts\model-library-20261026')
sys.path.insert(0,str(root/'scripts'));from prepare_workstation_preview import convert
specs={
'M01':dict(blocks=['root/115/174','root/116/198'],cover=['root/115'],rigid=['root/247','root/263'],refs=[],motion=[('hood','Osłona górna — rozsuń poglądowo',['root/115'],[0,0,1],700),('clamps','Dociski — poglądowe odsunięcie Y',['root/116/3594','root/116/10729','root/116/10745','root/116/10761'],[0,1,0],150)]),
'M02':dict(blocks=['root/3249/1456/1457','root/3249/1646/1647'],cover=['root/3249/1456'],rigid=['root/3249/3118'],refs=[],extra=[1911,3161,3169],motion=[('hood','Czapka — unieś',['root/3249/1456'],[0,0,1],600),('device','Mikser — unieś poglądowo',['root/3249/3118'],[0,0,1],350)]),
'M03':dict(blocks=['root/1008/1009','root/1210/1211'],cover=['root/1008'],rigid=[],refs=['root/4085'],motion=[('lid','Pokrywa — rozsuń poglądowo',['root/1008'],[0,0,1],500),('interior','Wnętrze — unieś poglądowo',['root/1210/3852'],[0,0,1],300)]),
'M05':dict(blocks=['root/205/206','root/3/4'],cover=['root/3'],rigid=['root/'+str(i) for i in [3836,4612,4689,4766,4843]],refs=[],motion=[('lid','Pokrywa — rozsuń poglądowo',['root/3'],[0,0,1],500)]+[('insert-'+str(i+1),'Wkład '+str(i+1)+' — unieś poglądowo',['root/'+str(n)],[0,0,1],300) for i,n in enumerate([3836,4612,4689,4766,4843])]),
'M06':dict(blocks=['root/3/3412','root/3537/208/3388'],cover=['root/3'],rigid=['root/3537/2102','root/3537/2934'],refs=['root/3537/1333'],motion=[('lid','Pokrywa — rozsuń poglądowo',['root/3'],[0,0,1],600),('device-1','Oprawa 1 — unieś poglądowo',['root/3537/2102'],[0,0,1],350),('device-2','Oprawa 2 — unieś poglądowo',['root/3537/2934'],[0,0,1],350)]),
'M07':dict(blocks=['root/115/174','root/116/198'],cover=['root/115'],rigid=['root/247','root/263'],refs=[],motion=[('hood','Osłona górna — rozsuń poglądowo',['root/115'],[0,0,1],700),('clamps','Dociski — poglądowe odsunięcie Y',['root/116/3594','root/116/10729','root/116/10745','root/116/10761'],[0,1,0],150)])}
index={};summary={}
for key in os.environ.get('ROCKPRO_PREVIEW_KEYS','M02,M03,M05,M06,M01,M07,M04').split(','):
 p=bundle/'native-02'/(key+'-inventory.json');data=json.loads(p.read_text(encoding='utf-8'));nodes={r['path']:r for r in data['rows']};dest=folder/key;dest.mkdir(exist_ok=True)
 if key=='M04':
  ann=json.loads((root/'artifacts/workstation-3d-20261027/mapping.json').read_text(encoding='utf-8'));ann['motions']=[dict(s,axis=ann['shelf_axis'],min=0,max=500,unit='mm') for s in ann['shelves']];ann['model_key']=key
  export=root/'artifacts/workstation-3d-20261027/export-02'
 else:
  spec=specs[key];parts={};external=[]
  for path,n in nodes.items():
   if n['type']!='Z_ELEMENT_PART':continue
   ancestors=[nodes['/'.join(path.split('/')[:i])] for i in range(2,len(path.split('/'))) if '/'.join(path.split('/')[:i]) in nodes]
   board=any(path.startswith(b+'/') for b in spec['blocks']) and n['name'] in ['WG','BP','BL','WD','PL','FB']
   policy='panel' if board or n['id'] in spec.get('extra',[]) else 'rigid';group=path
   if board:external.append(path)
   if policy=='rigid' and (any(a['name'].startswith('EG-') or a['name']=='Profiles' for a in ancestors) or n['name'].startswith('EG-')):policy='profile'
   if policy=='rigid':
    fixed=next((x for x in spec['rigid'] if path==x or path.startswith(x+'/')),None)
    candidates=[a for a in ancestors if re.match(r'^(H\d|L\d|B\d|C\d|\d{4,}|Penn)',a['name'])]
    group=fixed or (candidates[0]['path'] if candidates else path)
   parts[path]={'policy':policy,'rigid_group':group}
  ann=dict(source_sha256=data['source_sha256'],inventory_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),model_key=key,parts=parts,external_panel_paths=external,cover_paths=spec['cover'],reference_paths=spec['refs'],shelves=[],default_covers_visible=True,motions=[dict(id=i,label=l,paths=paths,axis=axis,min=0,max=mx,unit='mm') for i,l,paths,axis,mx in spec['motion']])
  export=dest/('export-01' if key=='M02' else 'kernel-safe-04')
  if key!='M02' and not (export/'export-receipt.json').exists():raise RuntimeError('Complete kernel dataset not ready: '+key)
 mapping=dest/'mapping.json';mapping.write_text(json.dumps(ann,ensure_ascii=False,indent=2),encoding='utf-8')
 dataset=dest/'model-01'
 if dataset.exists() and not (dataset/'model.json').exists():dataset=dest/'model-02'
 if (dataset/'model.json').exists():
  model=json.loads((dataset/'model.json').read_text(encoding='utf-8'))
  assert model['source_sha256']==data['source_sha256'] and model['geometry_sha256']==hashlib.sha256((dataset/'geometry.bin').read_bytes()).hexdigest()
  result={'mesh_count':len(model['elements']),'reused_verified_dataset':True}
 else:result=convert(export/'native-export.zip',export/('export-receipt.json' if (export/'export-receipt.json').exists() else 'result.json'),p,mapping,dataset)
 index[key]=dataset.relative_to(folder).as_posix();summary[key]=result;print(key,json.dumps(result,ensure_ascii=True),flush=True)
(folder/'index.json').write_text(json.dumps(dict(schema='rockpro.preview-index/1',models=index),indent=2),encoding='utf-8')
(folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
