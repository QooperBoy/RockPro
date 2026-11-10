from pathlib import Path
import json,hashlib,shutil,os,sys,re,zipfile
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'Transfer_RockPro_20261024/RockPro/rockpro-cad';OUT=ROOT/'outputs'
PARTS=OUT/'RockPro_CZESCI_20261103';MODELS=OUT/'RockPro_MODELE_20261103'
LIB=Path(r'C:\Users\zuzan\.codex\worktrees\6acf\Ironcad\workspace\rockpro-cad\artifacts\model-library-20261026')
LEDGER=[]

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024**2),b''):h.update(chunk)
 return h.hexdigest()

def put(p,q,role):
 p=Path(p);q=Path(q)
 if not p.is_file():raise FileNotFoundError(str(p))
 q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():
  if digest(p)!=digest(q):raise ValueError('Collision '+str(q))
 else:shutil.copy2(p,q)
 LEDGER.append(dict(source=str(p),destination=str(q),role=role))

def tree(p,q,role,types=None):
 for f in Path(p).rglob('*'):
  if f.is_file() and '__pycache__' not in f.parts and (types is None or f.suffix.lower() in types):put(f,Path(q)/f.relative_to(p),role)

def jsonout(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 if (PARTS.exists() or MODELS.exists()) and '--resume' not in sys.argv:raise RuntimeError('Do not overwrite a prior delivery')
 PARTS.mkdir(exist_ok=True);MODELS.mkdir(exist_ok=True)
 print('Preparing parts',flush=True)
 tree(ROOT/'biblioteka_czesci',PARTS/'01_CAD_PRODUCENTOW','supplier_native_cad')
 mirror=PARTS/'DO_WGRANIA_DO_KODU'
 for rel in ['assets/supplier-parts','artifacts/studio-part-images','artifacts/studio-project-parts','artifacts/studio-requested-parts','artifacts/manufacturer-images']:
  tree(SRC/rel,mirror/rel,'studio_part_assets')
 cat=SRC/'artifacts/erp-company-parts/catalog.json';data=json.loads(cat.read_text(encoding='utf-8'))
 # Keep part identity, catalog images and technical notes; do not transfer stock/order data.
 allowed={'id','code','name','category','manufacturer','source_url','image','mass_raw','unit','cutout_note','duplicate_code','source','geometry_approved','production_approved'}
 data['items']=[{k:v for k,v in r.items() if k in allowed} for r in data['items']]
 data['summary']={k:v for k,v in data['summary'].items() if not any(t in k.lower() for t in ('stock','price','usage'))}
 jsonout(mirror/'artifacts/erp-company-parts/catalog.json',data)
 tree(cat.parent/'images',mirror/'artifacts/erp-company-parts/images','catalog_images')
 for name in ['hardware-reference.json']:
  put(SRC/'docs/catalog'/name,PARTS/'02_KATALOG'/name,'part_definitions')
 for p in (ROOT/'projekty/RPS_Penn_AdamHall_3f8d90f0/Czesci_CAD').rglob('*'):
  if p.is_file() and p.suffix.lower() in {'.ics','.step','.stp','.json'}:put(p,PARTS/'03_CZESCI_SPECJALNE'/p.relative_to(ROOT/'projekty/RPS_Penn_AdamHall_3f8d90f0/Czesci_CAD'),'special_parts')
 put(SRC/'artifacts/h7159-fresh-mount-20261024-03/asset_input.ics',PARTS/'03_CZESCI_SPECJALNE/H7159/H7159_asset.ics','native_handle_asset')
 for p in (SRC/'artifacts/latch17251-inprocess-native-20261022-09').glob('latch_*.ics'):
  put(p,PARTS/'03_CZESCI_SPECJALNE/17251S'/p.name,'native_latch_asset')
 # Source catalog and availability reports preserve unknown mappings instead of inventing CAD.
 availability=json.loads((ROOT/'biblioteka_czesci/CAD_producenci/manifest.json').read_text(encoding='utf-8'))
 jsonout(PARTS/'02_KATALOG/POKRYCIE_I_BRAKI.json',{'summary':availability['summary'],'items':availability['items'],'scope':'Pobrane modele nie zatwierdzają montażu ani wycięć. Stan skanu 28.10.2026.'})
 # Relative-path manifest for native STEP consumers on another workstation.
 portable=json.loads(json.dumps(availability))
 native_root=ROOT/'biblioteka_czesci'
 for asset in portable['assets']:
  for key in ('file','original_archive'):
   old=Path(asset[key]);asset[key+'_original']=str(old);asset[key]=(Path('01_CAD_PRODUCENTOW')/old.relative_to(native_root)).as_posix()
 for item in portable['items']:
  for key in ('asset_files','reference_files'):
   item[key]=[(Path('01_CAD_PRODUCENTOW')/Path(f).relative_to(native_root)).as_posix() for f in item[key]]
 jsonout(PARTS/'02_KATALOG/MANIFEST_PRZENOSNY.json',portable)
 print('Preparing model families',flush=True)
 groups={'01_T1_Projektor':'T1 / projektor Epson','02_Telewizory':'Telewizory','03_Miksery':'Miksery','04_Kufry':'Kufry',
 '05_Racki':'Racki','06_Serwis_i_Workstation':'Serwis szufladowy / workstation','07_Wciagarki':'Wciągarki','08_Oswietlenie':'Oświetlenie, warianty z wkładami'}
 for group in groups:
  (MODELS/'01_INPUTOWE'/group).mkdir(parents=True,exist_ok=True);(MODELS/'02_SPARAMETRYZOWANE'/group).mkdir(parents=True,exist_ok=True)
 inputs=[];by_sha={}
 def input_file(path,group,sub=''):
  sha=digest(path)
  if sha in by_sha:
   entry=by_sha[sha];entry.setdefault('other_sources',[]).append(str(path));return entry
  q=MODELS/'01_INPUTOWE'/group/sub/path.name;put(path,q,'input_original')
  entry=dict(group=group,file=q.relative_to(MODELS).as_posix(),sha256=sha,source=str(path));inputs.append(entry);by_sha[sha]=entry;return entry
 source_groups={'01_Kufry':'04_Kufry','02_Miksery':'03_Miksery','03_Racki':'05_Racki','04_Telewizory':'02_Telewizory','05_Serwisy_szufladowe':'06_Serwis_i_Workstation'}
 for folder,group in source_groups.items():
  for p in (ROOT/'biblioteka_projektow'/folder).rglob('*.ics'):input_file(p,group,'modele_firmowe')
 for folder in ['T_1','T_1_1']:
  for p in (ROOT/'Transfer_RockPro_20261024/RockPro/AI_CAD'/folder).rglob('*.ics'):input_file(p,'01_T1_Projektor',folder)
 reference=json.loads((LIB/'manifest.json').read_text(encoding='utf-8'))
 refs={'M01':'02_Telewizory','M02':'03_Miksery','M03':'07_Wciagarki','M04':'06_Serwis_i_Workstation','M05':'08_Oswietlenie','M06':'08_Oswietlenie','M07':'02_Telewizory'}
 for row in reference['models']:
  p=Path(row['source'])
  if not p.exists():p=LIB/'pristine'/row['name']
  if not p.exists():
   matches=list(LIB.rglob(row['name']));p=matches[0] if matches else p
  if not p.exists() or digest(p)!=row['sha256']:
   candidates=list((LIB/'pristine').rglob(row['name']))+list((LIB/'sources-from-zip').rglob(row['name']))
   p=next((c for c in candidates if digest(c)==row['sha256']),p)
  assert digest(p)==row['sha256'],p
  input_file(p,refs[row['key']],'wzorce_M01_M07')
 processed=[]
 families=[('02_Telewizory','Telewizor_Hisense85_parametryczny_20261029'),('03_Miksery','Mikser_WingCompact_parametryczny_20261029'),
 ('04_Kufry','Kufer_parametryczny_20261030'),('05_Racki','Rack9U_parametryczny_20261030'),('06_Serwis_i_Workstation','Serwis_szufladowy_parametryczny_20261030')]
 for group,name in families:
  project=ROOT/'projekty'/name;current=json.loads((project/'CURRENT.json').read_text(encoding='utf-8-sig'));p=Path(current['model']);q=MODELS/'02_SPARAMETRYZOWANE'/group/p.name
  put(p,q,'processed_parametric');actual=digest(p);tested=current.get('model_sha256') or current.get('output_sha256')
  entry=dict(group=group,file=q.relative_to(MODELS).as_posix(),sha256=actual,status=current['status'],test_hash_matches=tested==actual if tested else None,production_approved=False,source_project=name)
  processed.append(entry)
  for original in (project/'01_Kopia_zrodla').glob('*.ics'):input_file(original,group,'zrodlo_przerobionego_modelu')
  docs=MODELS/'03_MAPOWANIE_I_DOWODY'/name
  for f in project.rglob('*'):
   if f.is_file() and '04_Snapshoty' not in f.parts and f.suffix.lower() in {'.json','.md','.csv','.txt','.html'}:put(f,docs/f.relative_to(project),'mapping_and_evidence')
  # A stable older mounting-only TV revision is useful alongside the historic wall/count experiment.
  if group=='02_Telewizory':
   old=project/'03_CAD/Do_sprawdzenia/RockPro_Hisense85_parametryczny_r002_montaz_IC2027.ics'
   put(old,MODELS/'02_SPARAMETRYZOWANE'/group/'R002_montaz_bez_dynamicznej_liczby'/old.name,'processed_older_mounting_revision')
 t1=ROOT/'projekty/Epson_EB-L630U/Prototyp_05_pokrywa115_wyciecia/T1_mvp_v_4_3.ics'
 q=MODELS/'02_SPARAMETRYZOWANE/01_T1_Projektor'/t1.name;put(t1,q,'processed_parametric');processed.append(dict(group='01_T1_Projektor',file=q.relative_to(MODELS).as_posix(),sha256=digest(t1),status='Zapisany prototyp T1; historyczne ograniczenia w dokumentacji',production_approved=False))
 for f in (ROOT/'projekty/Epson_EB-L630U').rglob('*'):
  if f.is_file() and f.suffix.lower() in {'.md','.json','.csv','.txt'}:put(f,MODELS/'03_MAPOWANIE_I_DOWODY/Epson_EB-L630U'/f.relative_to(ROOT/'projekty/Epson_EB-L630U'),'mapping_and_evidence')
 for group in ['07_Wciagarki','08_Oswietlenie']:
  (MODELS/'02_SPARAMETRYZOWANE'/group/'BRAK_GOTOWEGO_PARAMETRYCZNEGO_ICS.txt').write_text('Dostępny jest model wejściowy i podgląd Studio. Brak gotowego, zweryfikowanego parametrycznego ICS. Nie oznaczać tej rodziny jako ukończonej.\n',encoding='utf-8')
 # Required small analysis inputs for the existing pinned parametric scripts.
 overlay=MODELS/'DO_WGRANIA_DO_KODU'
 artifact_families=['tv-hisense85-20261029','wing-compact-20261029','kufer-20261030','rack-20261030','szuflady-20261030']
 for folder in artifact_families:
  for p in (SRC/'artifacts'/folder).rglob('*'):
   if p.is_file() and p.suffix.lower() in {'.json','.csv','.md','.cs','.py'}:put(p,overlay/'artifacts'/folder/p.relative_to(SRC/'artifacts'/folder),'parametric_adapter_evidence')
 for folder in ['tv-wall-check-01','tv-wall-guards-04','tv-wall-startup-final','tv-wall-final-display']:
  for p in (SRC/'artifacts'/folder).glob('*.json'):put(p,overlay/'artifacts'/folder/p.name,'parametric_acceptance')
 bridge=SRC/'artifacts/latch17251-inprocess-native-20261022-09/LatchApiProbe.dll'
 assert digest(bridge)=='0b83e25991b23a94ef723ad2fc58ac1e7e08e815913751c779cad891797d79cb'
 put(bridge,overlay/'artifacts/latch17251-inprocess-native-20261022-09/LatchApiProbe.dll','own_rockpro_bridge_not_ironcad_sdk')
 # The reference gallery needs inventories and final preview buffers, not every old export.
 print('Preparing runtime previews',flush=True)
 bundle=overlay/'artifacts/model-library-20261026';put(LIB/'manifest.json',bundle/'manifest.json','studio_reference_manifest')
 for i in range(1,8):
  key=f'M{i:02d}'
  for rel in [f'native-02/{key}-inventory.json',f'working-standard-v1/{key}.json',f'images-full-2027/{key}.png',f'review-2027/{key}.png']:
   p=LIB/rel
   if p.exists():put(p,bundle/rel,'studio_reference_metadata')
 idx=SRC/'artifacts/family-3d-20261027/index.json';index=json.loads(idx.read_text(encoding='utf-8'));put(idx,overlay/'artifacts/family-3d-20261027/index.json','studio_preview_index')
 for rel in index['models'].values():
  for name in ['model.json','geometry.bin']:put(idx.parent/rel/name,overlay/'artifacts/family-3d-20261027'/rel/name,'studio_preview_geometry')
 jsonout(MODELS/'INDEKS_MODELI.json',dict(groups=groups,input_files=inputs,parametric_models=processed,missing_parametric_groups=['07_Wciagarki','08_Oswietlenie'],scope='Osiem grup użytkowych. Oświetlenie zawiera wariant dwóch głów oraz wariant wielu wkładów; nie są zamienne. Zapisane prototypy bez akceptacji produkcyjnej.'))
 lines=['ROCKPRO — MODELE: INPUT I PARAMETRYCZNE\n','01_INPUTOWE — zachowane modele konstruktora, osiem grup; identyczne pliki deduplikowano według SHA256.','02_SPARAMETRYZOWANE — sześć opracowanych rodzin. Dla wciągarek i oświetlenia brak gotowego parametrycznego ICS.','03_MAPOWANIE_I_DOWODY — opisy parametrów, mapy i wyniki testów.','DO_WGRANIA_DO_KODU — nakładka z danymi wymaganymi przez adaptery i galerię Studio.','R005 telewizora jest historycznym eksperymentem: pola liczby pozostają w pliku, lecz funkcję wycofano z dalszego rozwoju. R002 daje wcześniejszy montaż bez tej funkcji.','Wyniki dotyczą konkretnych źródeł i testów 2027. Nie oznaczają otwieralności każdego modelu w 2023 ani akceptacji konstrukcyjnej.','Nie włączono nieudanej migracji R006 ani plików FAILED/working. Nie zapisano/zmieniono żadnego modelu w CAD podczas pakowania.']
 (MODELS/'CZYTAJ_NAJPIERW.txt').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
 (PARTS/'CZYTAJ_NAJPIERW.txt').write_text('''ROCKPRO — WSZYSTKIE DOSTĘPNE ZASOBY CZĘŚCI
01_CAD_PRODUCENTOW: pobrane STEP, oryginalne archiwa i manifesty dostawców.
02_KATALOG: statusy dostępności, braki i przenośny manifest ze względnymi ścieżkami.
03_CZESCI_SPECJALNE: dodatkowe modele z projektów i wydzielone uchwyty/zamki.
DO_WGRANIA_DO_KODU: gotowe siatki, miniatury, zdjęcia i katalog do Studio.
Katalog ma 265 rekordów, ale nie 265 gotowych modeli CAD. Biblioteka producentów
ma 74 unikalne STEP; część SKU i wariantów wymaga potwierdzenia. Dodatkowe modele
źródłowe nie oznaczają zatwierdzenia montażu. Braki są opisane w POKRYCIE_I_BRAKI.json.
Nie dołączono cen, stanów, zleceń, firmowego Excela, kont, instalatorów ani SDK.
Historyczne manifesty zachowują ścieżki autora; do przenoszenia używaj
MANIFEST_PRZENOSNY.json albo nakładki DO_WGRANIA_DO_KODU.
''',encoding='utf-8')
 jsonout(OUT/'PRZEKAZANIE_20261103_pliki.json',LEDGER)
 print(json.dumps(dict(parts_stage=str(PARTS),models_stage=str(MODELS),inputs=len(inputs),parametric_families=len(processed),copied_files=len(LEDGER)),ensure_ascii=False),flush=True)

if __name__=='__main__':sys.stdout.reconfigure(encoding='utf-8');main()
