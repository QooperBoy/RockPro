import json,csv,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
source=Path.cwd();root=source.parents[2];e=source/'artifacts/tv-hisense85-20261029';project=root/'projekty/Telewizor_Hisense85_parametryczny_20261029'
p=json.loads((e/'plan.json').read_text(encoding='utf-8'));build=json.loads((e/'build-07/result.json').read_text(encoding='utf-8'));cuts=json.loads((e/'validate-cuts-04/result.json').read_text(encoding='utf-8'))
assert build['passed'] and cuts['passed']
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
original=root/'biblioteka_projektow/04_Telewizory/oryginaly/Telewizory/TR Group - HISENSE 85U8Q.ics'
assert sha(original)==p['sha256']==sha(p['source'])
model=Path(p['output']);digest=sha(model)
snapshot=project/'04_Snapshoty/RockPro_Hisense85_r001_sprawdzone_IC2027.ics'
if not snapshot.exists():shutil.copy2(model,snapshot)
assert sha(snapshot)==digest
review=project/'06_Odbior'
for image in ['final.png','wyciecia-przod.png']:shutil.copy2(e/'validate-cuts-04'/image,review/image)
for name,path in [('TESTY_PARAMETRYZACJI.json',e/'build-07/result.json'),('TESTY_WYCIEC.json',e/'validate-cuts-04/result.json')]:shutil.copy2(path,review/name)
rows=[]
for row in p['mapping']:
 row=dict(row);row['native_id']=build['part_id_map'].get(str(row['id']),row['id']);rows.append(row)
with (project/'00_Karta_zlecenia/MAPOWANIE_CZESCI.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';');w.writeheader();w.writerows(rows)
with (project/'00_Karta_zlecenia/PARAMETRY.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['name','value','notes'],delimiter=';');w.writeheader();w.writerows(p['parameters'])
checks='\n'.join('| '+c['name']+' | PASS | '+str(c['parts_checked'])+' |' for c in build['checks'])
report=f'''# Hisense 85 — prototyp do sprawdzenia, IronCAD 2027

Zapisana wersja: `03_CAD/Do_sprawdzenia/{model.name}`. Oryginał w bibliotece oraz jego kopia porównawcza nie zostały zmienione. W IronCAD pozostawiono kopię porównawczą i nowy model; wcześniejszy otwarty projekt użytkownika zachowano.

## Co działa

- Sześć głównych parametrów sceny z polskimi komentarzami.
- Parametry wymiarów 54 części konstrukcyjnych: 10 płyt sklejki, 24 profile, 20 wkładów/docisków. Płyty odtworzono na nowych bryłach, bez dawnych konfliktowych relacji pozycji.
- Powiązane położenia wszystkich 383 części fizycznych; okucia i ich podczęści zachowują rozmiar katalogowy. Rozpoznano 26 sztywnych zespołów montażowych, w tym podział okuć i logo. Pozostałe części mają własne kotwy lub dziedziczą położenie.
- Poprawione 12 wycięć w przednich i tylnych płytach korpusu/czapki. Wykorzystano właściwe kontury montażowe HWDrill z modeli okuć L905/915, z ich zaokrągleniami i ramą położenia. Poprzedni otwór górnej połówki miał około 98 mm szerokości zamiast 76 mm właściwego konturu.
- Zielona sklejka #408080; polskie nazwy nowych płyt. Zapisany zamknięty widok kompletnej skrzyni.

## Jak sprawdzić parametry

Wybierz scenę w tabeli parametrów i zmieniaj parametry `RP_...` poziomu sceny. Parametry techniczne wewnątrz części i operacji są wynikowe.

| Parametr | Wartość początkowa [mm] | Znaczenie |
|---|---:|---|
'''+ '\n'.join('| '+x['name']+' | '+str(x['value'])+' | '+x['notes']+' |' for x in p['parameters'])+f'''

To zewnętrzne wymiary obrysu sklejki, bez wystających okuć i kół, a nie światło wewnętrzne ani wymiary urządzenia. Początkowa całkowita wysokość sklejki wraz ze szczeliną wynosi około 1160,63 mm. Źródłową szczelinę złącza około 8,6498 mm zachowano. Wysoka zdejmowana czapka jest świadomą cechą tej rodziny.

Przykład większy: 2143 × 412 mm, dół 528,99 mm, czapka 742,99 mm. Przykład mniejszy: 1923 × 352 mm, dół 458,99 mm, czapka 632,99 mm. Uniesienie czapki testowano przy 250 mm. Po próbach przywrócono wartości początkowe. Pomocniczy parametr odsunięcia wkładów zachowano ze źródła; zmiany jego wartości nie są osobnym zatwierdzeniem montażu wkładów.

Pozycje sterowane są wyrażeniami parametrów. Demonstrator nie korzysta z solvera więzów mechanicznych; nie jest to symulacja dynamiki ani zawiasów.

## Testy natywne

Host {build['api_version']}, PID {p['expected_pid']}. Wszystkie kontrole poniżej wykonano w tej sesji, na nowej kopii.

| Próba | Wynik | Części |
|---|---|---:|
{checks}

Dodatkowo PASS: dokładna zgodność 12 konturów z HWDrill, ich macierzy świata, długości krzywych i aktywnej operacji odejmowania; 383 części po zapisie. Końcowy maksymalny błąd położenia: {cuts['max_final_pose_error_mm']:.8f} mm. Maksymalny błąd lokalnej granicy bryły: {cuts['max_final_size_error_mm']:.8f} mm.

PASS: repozytorium, backend, parts, core-design, core-contracts, QA i harness (`artifacts/verification/20261029T102003485791Z`). PASS: 3 testy regresji matematyki ram części/operacji. Wcześniejsze nieudane próby i przyczyny zachowano w lokalnym dzienniku; nie są wydaniami.

Źródło i kopia: SHA256 `{p['sha256']}` — bez zmian.
Model i snapshot: SHA256 `{digest}`.

## Co pozostaje do odbioru

Mapa 383 ID rozlicza części fizyczne, a nie 383 oddzielne SKU zakupowe. Zgodność kodów dostawców z pełnym katalogiem firmy, technologiczne luzy montażowe, wkłady i ich połączenia, pełny przegląd kolizji bryłowych oraz odbiór produkcyjny pozostają do zatwierdzenia przez konstruktora. Nie wykonano prób obciążeniowych, eksportu CNC ani dopuszczenia tej rodziny do ogólnego generatora Studio. `production_approved=false`.

## Pliki i historia

- `00_Karta_zlecenia/MAPOWANIE_CZESCI.csv`: mapa źródłowych i nowych natywnych ID, ról, pochodzenia i zakresu parametryzacji.
- `00_Karta_zlecenia/PARAMETRY.csv`: parametry i objaśnienia.
- `01_Kopia_zrodla`: porównawcza kopia oryginału.
- `03_CAD/Do_sprawdzenia`: bieżący model.
- `04_Snapshoty`: potwierdzona kopia i jej manifest.
- `06_Odbior`: ten raport, testy JSON oraz podglądy.

Szczegółowy dziennik lokalny: `{e}`. Próby build-01–05 ujawniły konflikt starych relacji; build-06 wykrył zamianę osi dwóch obróconych wkładów przy różnych przyrostach wysokości i głębokości. Build-07 przeszedł wszystkie próby. Weryfikacja widoczności używa właściwości IsHidden części/zespołów, ponieważ ogólne flagi stanu nie odzwierciedlały tego ukrycia.
'''
(review/'RAPORT_PARAMETRYZACJI.md').write_text(report,encoding='utf-8')
(project/'CZYTAJ_MNIE.md').write_text('''# Hisense 85 — do sprawdzenia

Gotowy prototyp: [model IronCAD 2027](03_CAD/Do_sprawdzenia/'''+model.name+''').

[Instrukcja parametrów i wyniki testów](06_Odbior/RAPORT_PARAMETRYZACJI.md).

[Mapa części](00_Karta_zlecenia/MAPOWANIE_CZESCI.csv) · [Parametry](00_Karta_zlecenia/PARAMETRY.csv).

Oryginał porównawczy jest w 01_Kopia_zrodla; nie nadpisuj biblioteki. Kolejne zmiany zapisuj jako r002 i kolejne rewizje. Wydanie pozostaje prototypem do odbioru konstruktora.
''',encoding='utf-8')
manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),output=str(model),output_sha256=digest,snapshot=str(snapshot),source=str(original),source_sha256=p['sha256'],native_tests_passed=True,cutouts_verified=12,physical_parts=383,dimensioned_parts=54,production_approved=False)
(project/'04_Snapshoty/SNAPSHOT.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(project/'STATUS_PROJEKTU.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(model=str(model),sha256=digest,report=str(review/'RAPORT_PARAMETRYZACJI.md'))))
