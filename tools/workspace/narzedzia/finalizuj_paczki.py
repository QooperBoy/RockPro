from pathlib import Path
import json,hashlib,zipfile,shutil,time,html
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
def main():
 models=OUT/'RockPro_MODELE_20261103'
 idx=json.loads((models/'INDEKS_MODELI.json').read_text(encoding='utf-8'))
 rows=[]
 for group,label in idx['groups'].items():
  rows.append('<h2>'+html.escape(label)+'</h2>')
  for heading,key in [('Wejściowe','input_files'),('Parametryczne','parametric_models')]:
   rows.append('<h3>'+heading+'</h3><ul>')
   entries=[r for r in idx[key] if r['group']==group]
   for r in entries:
    rows.append('<li><a href="'+html.escape(r['file'],quote=True)+'">'+html.escape(Path(r['file']).name)+'</a><br><small>SHA256: '+r['sha256']+'</small></li>')
   if not entries:rows.append('<li>Brak gotowego parametrycznego ICS.</li>')
   rows.append('</ul>')
 (models/'INDEKS_MODELI.html').write_text('<!doctype html><meta charset="utf-8"><title>RockPro — indeks modeli</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px}li{margin:16px 0}small{overflow-wrap:anywhere}</style><h1>RockPro — modele do przeglądu</h1><p>Osiem grup, sześć opracowanych rodzin parametrycznych. Prototypy bez zatwierdzenia produkcyjnego. R002 TV to dodatkowa, starsza rewizja montażowa.</p>'+''.join(rows),encoding='utf-8')
 report=[]
 for name in ['RockPro_CZESCI_20261103','RockPro_MODELE_20261103']:
  stage=OUT/name
  for p in [OUT/'PRZEKAZANIE_DEWELOPEROWI_20261103.txt',ROOT/'narzedzia/zloz_przekazanie.py',OUT/'TEST_PRZEKAZANIA_20261103.json']:
   shutil.copy2(p,stage/p.name)
  files=sorted(p for p in stage.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='MANIFEST_PLIKOW_SHA256.json')
  manifest=[dict(path=p.relative_to(stage).as_posix(),bytes=p.stat().st_size,sha256=digest(p)) for p in files]
  (stage/'MANIFEST_PLIKOW_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
  files.append(stage/'MANIFEST_PLIKOW_SHA256.json')
  dest=OUT/(name+'.zip')
  if dest.exists():raise RuntimeError('Archive already exists: '+str(dest))
  print('ZIP '+name+' files='+str(len(files))+' bytes='+str(sum(p.stat().st_size for p in files)),flush=True)
  with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5,allowZip64=True) as z:
   for i,p in enumerate(files):
    z.write(p,name+'/'+p.relative_to(stage).as_posix())
    if i%100==0:print('  '+str(i)+'/'+str(len(files)),flush=True)
  print('VERIFY '+name,flush=True)
  with zipfile.ZipFile(dest) as z:
   assert z.testzip() is None
   for i,r in enumerate(manifest):
    h=hashlib.sha256()
    with z.open(name+'/'+r['path']) as f:
     for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    assert h.hexdigest()==r['sha256'],r['path']
  sha=digest(dest);dest.with_suffix('.zip.sha256.txt').write_text(sha+'  '+dest.name+'\n',encoding='utf-8')
  report.append(dict(file=str(dest),bytes=dest.stat().st_size,uncompressed_bytes=sum(p.stat().st_size for p in files),files=len(files),sha256=sha,crc=True,all_entry_sha256=True))
  print('DONE '+json.dumps(report[-1]),flush=True)
 (ROOT/'raporty/PACZKI_CZESCI_MODELE_20261103.json').write_text(json.dumps(dict(archives=report,input_models=len(idx['input_files']),parametric_families=len(idx['parametric_models']),groups=len(idx['groups']),native_cad_retest=False),ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
