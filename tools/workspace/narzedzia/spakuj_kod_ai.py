"""Prepare a code/AI/catalog handover without CAD models, customer records or runtimes."""
from pathlib import Path
import os,sys,json,shutil,hashlib,subprocess,re,zipfile
from html import escape
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Transfer_RockPro_20261024/RockPro/rockpro-cad'
DEST=ROOT/'outputs/RockPro_KOD_AI_KATALOG_20261103'
SKIP={'.git','.venv','venv','node_modules','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.vs','.vercel','site-packages','awesome-copilot'}
CODE={'.py','.cs','.ps1','.psm1','.js','.mjs','.cjs','.ts','.tsx','.jsx','.html','.css','.md','.rst','.txt','.toml','.yaml','.yml','.ini','.cfg','.xml','.csproj','.sln','.resx','.props','.targets','.bat','.cmd','.sh','.lock','.gitignore','.gitattributes','.editorconfig'}
CODE_NAMES={'.gitignore','.gitattributes','.editorconfig','LICENSE','LICENSE.txt','Dockerfile'}
HIST={'.py','.cs','.ps1','.js','.mjs','.cjs','.ts','.css'}
OMITTED=[]

def allowed(p,base):
 rel=p.relative_to(base);parts=rel.parts;name=p.name.casefold()
 if any(part in SKIP or part.lower().startswith(('bin-','obj-')) for part in parts[:-1]):return False
 if any(part in {'bin','obj','data','runs','logs','acceptance_tmp','images','models','meshes'} or part.startswith('acceptance_tmp_') for part in parts[:-1]):return False
 if name in {'mcp-config.local.json','credentials.json','auth.json','secrets.json'} or name.startswith('.env') and name not in {'.env.example','.env.template'}:return False
 if 'artifacts' in parts:
  if any(x in parts for x in ('public','vendor','Integracja')):return False
  return p.suffix.lower() in HIST
 if p.suffix.lower()=='.json':
  return any(x in parts for x in ('docs','tests','fixtures','templates','examples')) or name in {'package.json','package-lock.json','tsconfig.json','provenance.json'} or name.endswith(('.template.json','.schema.json'))
 return p.suffix.lower() in CODE or p.name in CODE_NAMES or (p.suffix.lower()=='.svg' and name in {'favicon.svg','logo.svg'})

def copy_code(base,target):
 count=0
 if not base.exists():return 0
 for cur,dirs,files in os.walk(base,followlinks=False):
  dirs[:]=[d for d in dirs if d not in SKIP and not (Path(cur)/d/'pyvenv.cfg').exists() and not (Path(cur)/d).is_symlink()]
  for name in files:
   p=Path(cur)/name
   if not p.is_file() or p.is_symlink() or not allowed(p,base):continue
   q=target/p.relative_to(base);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);count+=1
 return count

def writejson(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 if DEST.exists():raise RuntimeError('Output already exists; preserve it and choose a new package name.')
 DEST.mkdir(parents=True)
 counts={}
 counts['current_code']=copy_code(SOURCE,DEST/'01_KOD_GLOWNY')
 counts['preserved_deployment']=copy_code(ROOT/'Transfer_RockPro_20261024/RockPro/Integracja',DEST/'05_WARIANTY_KODU/poprzednie_wdrozenie')
 external=Path(r'C:\Users\zuzan\.codex\worktrees\6acf\Ironcad')
 counts['other_chat_code']=copy_code(external,DEST/'05_WARIANTY_KODU/inny_czat')
 copy_code(ROOT/'narzedzia',DEST/'02_INSTRUKCJE_AI_I_DOKUMENTY/narzedzia')
 docs=DEST/'02_INSTRUKCJE_AI_I_DOKUMENTY';docs.mkdir(exist_ok=True)
 for name in ['AGENTS.md','START_HERE.md','MAPA_FOLDEROW_I_PROJEKTOW.md','MAPA_FOLDEROW_I_PROJEKTOW.html']:
  p=ROOT/name
  if p.exists():shutil.copy2(p,docs/name)
 for p in (ROOT/'raporty').rglob('*'):
  if p.is_file() and p.suffix.lower() in {'.md','.txt'}:
   q=docs/'raporty'/p.relative_to(ROOT/'raporty');q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 for cur in (ROOT/'projekty').glob('*/CURRENT.json'):
  j=json.loads(cur.read_text(encoding='utf-8-sig'))
  writejson(docs/'stan_prototypow'/(cur.parent.name+'.json'),{k:j[k] for k in ('status','production_approved','host_year','controls','source_commit','contract') if k in j})
 # The original workbook, prices, stocks, orders and images are not copied.
 company=json.loads((SOURCE/'artifacts/erp-company-parts/catalog.json').read_text(encoding='utf-8-sig'))
 fields={'id','code','name','category','manufacturer','source_url','mass_raw','unit','cutout_note','duplicate_code','geometry_approved','production_approved'}
 items=[{k:v for k,v in row.items() if k in fields} for row in company['items']]
 catalog=dict(schema='rockpro.company-catalog-metadata/1',records=len(items),scope='Kody, opisy, jednostki i uwagi montażowe. Bez cen, stanów i geometrii.',items=items)
 writejson(DEST/'03_BAZA_CZESCI/KATALOG_265_POZYCJI.json',catalog)
 suppliers=json.loads((SOURCE/'assets/supplier-parts/index.json').read_text(encoding='utf-8-sig'))
 writejson(DEST/'03_BAZA_CZESCI/DEFINICJE_DOSTAWCOW_BEZ_GEOMETRII.json',dict(schema=suppliers['schema'],items=suppliers['items'],geometry_included=False))
 shutil.copy2(SOURCE/'docs/catalog/hardware-reference.json',DEST/'03_BAZA_CZESCI/hardware-reference.json')
 # Keep metadata at the source module's expected location for future configuration.
 writejson(DEST/'01_KOD_GLOWNY/assets/supplier-parts/index.json',suppliers)
 clean_company=dict(schema='rockpro.company-catalog/1',source={'sha256':company['source']['sha256'],'filename':'Katalog części — bez danych magazynowych'},items=[dict(r,image=None) for r in items],summary={'records':len(items),'images':0})
 writejson(DEST/'01_KOD_GLOWNY/artifacts/erp-company-parts/catalog.json',clean_company)
 # Functional browser-storage Studio kit from the existing clean release; no meshes/photos/customer data.
 release=SOURCE/'artifacts/process-layer-cloud-20261031'
 studio=DEST/'04_RP_STUDIO_PRZENOSNE'
 for p in release.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(release)
  if '__pycache__' in rel.parts:continue
  if rel.parts[0]=='public':
   if p.suffix.lower() not in {'.html','.js','.mjs','.css','.json','.svg'}:continue
   if any(x in rel.parts for x in ('parts','supplier-parts','company-images','manufacturer-images','examples')):continue
   if p.suffix.lower()=='.json' and p.name not in {'catalog-parts.json','company-catalog.json','options.json','examples.json'}:continue
  elif rel.parts[0]=='assets':
   if rel.as_posix()!='assets/supplier-parts/index.json':continue
  elif p.suffix.lower() not in {'.py','.json'}:continue
  q=studio/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 # Use the latest software, not the release's earlier UI revision.
 for name in ['process-panel.js','process-panel.css']:
  shutil.copy2(SOURCE/'Integracja/rockpro_cad/reference_studio'/name,studio/'public'/name)
 # Remove image/mesh pointers from both public catalogues; keep all definitions and units.
 for name in ['catalog-parts.json','company-catalog.json']:
  p=studio/'public'/name;j=json.loads(p.read_text(encoding='utf-8-sig'))
  for row in j['items']:
   row['image']=None
   for k in list(row):
    if any(x in k.casefold() for x in ('price','stock','usage','cached')):row.pop(k)
   if row.get('geometry_status'):row['geometry_status']='geometry_excluded_from_software_kit'
  if name=='company-catalog.json':
   j['summary']['images']=0
   for row in j['items']:row['geometry_candidates']=[]
  writejson(p,j)
 e=studio/'public/examples.json';j=json.loads(e.read_text(encoding='utf-8'))
 for row in j['items']:row.pop('image',None)
 writejson(e,j)
 shutil.copy2(SOURCE/'scripts/serve_vercel_studio.py',studio/'URUCHOM_SERWER.py')
 (studio/'START_RP_STUDIO.ps1').write_text('''$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$python=Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw 'Wymagany Python 3.10 lub nowszy. Nie dołączono instalatora ani środowiska Python.' }
Write-Host 'Otwórz http://127.0.0.1:53110/wizard.html — Ctrl+C kończy serwer.'
& $python.Source (Join-Path $PSScriptRoot 'URUCHOM_SERWER.py') $PSScriptRoot --port 53110
''',encoding='utf-8-sig')
 # Historical task inventory and explicit local progress, without claiming current remote state.
 sync=json.loads((SOURCE/'artifacts/company-cad-20261028/linear-sync-20261028.json').read_text(encoding='utf-8-sig'))
 tasks={}
 for record in sync['existing']+sync['created']:
  m=re.search(r'ROC-\d+',record.get('text','')+' '+record.get('url',''))
  if not m:continue
  key=m.group();lines=record.get('text','').splitlines();state=next((s for s in lines if s in {'Done','Todo','Backlog','In Progress','Canceled','Duplicate'}),'Nie zachowano statusu w eksporcie')
  tasks[key]=dict(id=key,title=record.get('title') or next((s for s in lines if s.startswith('[')),record.get('text','')),status_in_export=state,url=record.get('url'),raw_text=record.get('text'))
 notes={'ROC-51':'Lokalnie przygotowano pytania dla Tomka 31.10. Oczekujemy odpowiedzi, nie potwierdzono mapowań.',
 'ROC-53':'Opracowano prototypy kilku rodzin. Nie oznacza wspólnego generatora wszystkich odmian.',
 'ROC-54':'Pełny przycisk Studio → IronCAD dla kompletnego T1 nadal do wdrożenia i odbioru.',
 'ROC-55':'Odczyt katalogu wykonany; zapis zleceń i ruchy magazynowe w firmowym Excelu nie są domknięte.',
 'ROC-56':'Rejestr, panel, kolory 3D i testy gotowe lokalnie. Pozostaje instrumentacja wszystkich wykonawców i rzeczywisty odbiór CAD; brak pełnych danych kosztów/tokenów.',
 'ROC-57':'2023 częściowo sprawdzony. Nowe prace 2027 nie oznaczają zgodności wszystkich modeli z 2023.',
 'ROC-61':'Modele producenta wdrożono wcześniej. Warstwa obserwacji z 31.10 nie została opublikowana na Vercelu.'}
 for key,note in notes.items():
  if key in tasks:tasks[key]['local_progress_2026_10_31']=note
 taskrows=sorted(tasks.values(),key=lambda r:int(r['id'].split('-')[1]))
 writejson(DEST/'06_ZADANIA/ZADANIA_ROCKPRO.json',dict(source_export_date='2026-10-28',local_update_date='2026-10-31',live_linear_verified=False,items=taskrows))
 title='RockPro — zadania wykonane i otwarte (ostatni zapis lokalny)'
 html=['<!doctype html><html lang="pl"><meta charset="utf-8"><title>'+title+'</title><style>body{font:15px/1.5 system-ui;max-width:1200px;margin:30px auto;padding:20px}td,th{padding:12px;border:1px solid #ccc;text-align:left;vertical-align:top}table{border-collapse:collapse;width:100%}</style><h1>'+title+'</h1><p>Status Linear pochodzi z eksportu 28.10.2026. Lokalny postęp uwzględnia prace do 31.10.2026. Nie jest to aktualny odczyt workspace Linear.</p><table><tr><th>ID</th><th>Zadanie</th><th>Status w eksporcie</th><th>Nowsza notatka lokalna</th></tr>']
 for r in taskrows:html.append('<tr>'+''.join('<td>'+escape(str(v or ''))+'</td>' for v in [r['id'],r['title'],r['status_in_export'],r.get('local_progress_2026_10_31','')])+'</tr>')
 html.append('</table></html>');(DEST/'06_ZADANIA/ZADANIA.html').write_text('\n'.join(html),encoding='utf-8')
 for name in ['TODO_20261028.md','CUSTOM_CASE_WORKFLOW.md','RELIABILITY_AND_OBSERVER.md','STUDIO_VERCEL.md']:
  shutil.copy2(SOURCE/'docs'/name,DEST/'06_ZADANIA'/name)
 # Metadata about source history, not a raw Git bundle containing geometry.
 gitlog=subprocess.check_output(['git','-C',str(SOURCE),'log','--all','--date=iso-strict','--format=%h %ad %s'],text=True,encoding='utf-8',errors='replace')
 (DEST/'02_INSTRUKCJE_AI_I_DOKUMENTY/HISTORIA_COMMITOW.txt').write_text(gitlog,encoding='utf-8')
 (DEST/'CZYTAJ_NAJPIERW.txt').write_text('''ROCKPRO — KOD, INSTRUKCJE AI I KATALOG CZĘŚCI
Stan paczki: 03.11.2026. Kod główny: commit 66fa99f, ostatnie prace 31.10.2026.

01_KOD_GLOWNY — aktualny kod Studio, dodatku, wykonawców i testów.
02_INSTRUKCJE_AI_I_DOKUMENTY — instrukcje, raporty, mapa folderów i historia commitów.
03_BAZA_CZESCI — 265 rekordów katalogu i definicje wariantów dostawców; bez cen,
stanów magazynowych, zdjęć i geometrii. Nie wszystkie części mają potwierdzony montaż.
04_RP_STUDIO_PRZENOSNE — przeglądarkowa wersja Studio bez danych użytkownika i siatek
okuć. Uruchom START_RP_STUDIO.ps1 lub: python URUCHOM_SERWER.py . --port 53110
Otwórz http://127.0.0.1:53110/wizard.html. Potrzebny własny Python >=3.10 i
przeglądarka z WebGL. Drafty tej wersji zapisują się w tej przeglądarce.
Płyty są rysowane parametrycznie, okucia bez siatki mają znaczniki poglądowe.
05_WARIANTY_KODU — zachowany starszy kod i wariant z drugiego czatu. Nie nakładać
ich na kod główny; są odniesieniem dla AI i migracji.
06_ZADANIA — zapisane zadania oraz lokalny stan wykonania i braki.

DLA AI: zacznij od 01_KOD_GLOWNY/AGENTS.md i docs/DEVELOPMENT.md. Zasada z 31.10:
nie parametryzować liczby uchwytów/zawiasów/zamków w CAD. Starsze opisy są historyczne.
Wspólny generator dowolnej skrzyni Studio → IronCAD nie jest jeszcze domknięty.
Parametryzacja kilku konkretnych modeli została przetestowana w IronCAD 2027;
to nie oznacza kompatybilności ich plików z 2023 ani zatwierdzenia produkcyjnego.
Przebieg SDK/AI ma implementację, ale przykład 270+30 jest jawną symulacją.

NIE DOŁĄCZONO: projektów i danych klientów, plików ICS/STEP/STL/GLB/DXF,
siatek 3D, snapshotów, SQLite, zleceń, Excela, maili, haseł/tokenów, .git i
pełnej historii binarnej, instalatorów IronCAD/SDK/Python ani środowisk zależności.
Kod dodatku buduje się narzędziami z zainstalowanego lokalnie IronCAD/SDK.
Szczegółowe mapy i źródła modeli wymienione w historycznych dokumentach mogą
wymagać pełnej prywatnej paczki projektu, której ta lekka wersja nie zawiera.
Archiwum powstało lokalnie; niczego nie opublikowano ani nie pobierano.
''',encoding='utf-8')
 print(json.dumps({'folder':str(DEST),'source_files':counts,'tasks':len(taskrows),'catalog_records':len(items)},ensure_ascii=False))

if __name__=='__main__':
 sys.stdout.reconfigure(encoding='utf-8');main()
