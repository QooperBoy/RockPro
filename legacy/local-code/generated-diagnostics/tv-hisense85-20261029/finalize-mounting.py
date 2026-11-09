import csv,json,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
s=Path.cwd();root=s.parents[2];e=s/'artifacts/tv-hisense85-20261029';p=root/'projekty/Telewizor_Hisense85_parametryczny_20261029'
q=json.loads((e/'mounting-present-request.json').read_text(encoding='utf-8'));b=json.loads((e/'mounting-04/result.json').read_text(encoding='utf-8'));v=json.loads((e/'mounting-present-02/result.json').read_text(encoding='utf-8'))
assert b['passed'] and v['passed'] and len(v['parameters'])==34
sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest()
assert sha(q['source'])==q['sha256']
model=Path(q['output']);digest=sha(model);snapshot=p/'04_Snapshoty/RockPro_Hisense85_r002_montaz_sprawdzone_IC2027.ics'
if not snapshot.exists():shutil.copy2(model,snapshot)
assert sha(snapshot)==digest
review=p/'06_Odbior/R002_montaz';review.mkdir(exist_ok=True)
for f in ['final.png','przod.png']:shutil.copy2(e/'mounting-present-02'/f,review/f)
shutil.copy2(e/'mounting-04/result.json',review/'TESTY_NATYWNE.json');shutil.copy2(e/'mounting-present-02/result.json',review/'PARAMETRY_I_NAZWY.json')
shutil.copy2(e/'mounting-plan.json',p/'00_Karta_zlecenia/PLAN_MONTAZU_R002.json')
for f in ['PARAMETRY.csv','MAPOWANIE_CZESCI.csv']:
 old=p/'00_Karta_zlecenia'/f;archive=old.with_name(old.stem+'_R001.csv')
 if old.exists() and not archive.exists():shutil.copy2(old,archive)
with (p/'00_Karta_zlecenia/PARAMETRY.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,delimiter=';');w.writerow(['Nazwa parametru','Wartość [mm]','Równanie','Komentarz'])
 for r in v['parameters']:w.writerow([r['name'],r['value_mm'],r['expression'],r['notes']])
by={r['id']:r for r in q['inventory']};names={r['id']:r['name'] for r in q['names']};aliases=b['aliases']
with (p/'00_Karta_zlecenia/DRZEWO_SCENY_R002.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,delimiter=';');w.writerow(['Źródłowe ID','Natywne ID R002','Etykieta polska','Typ','Źródłowy rodzic ID'])
 for i,n in names.items():w.writerow([i,aliases.get(str(i),i),n,by[i]['type'],by[i]['parent']])
base=json.loads((e/'plan.json').read_text(encoding='utf-8'))
rows=[]
for r in base['mapping']:
 r=dict(r);r['native_id']=aliases.get(str(r['id']),r['id']);r['etykieta_PL']=names[r['id']];rows.append(r)
with (p/'00_Karta_zlecenia/MAPOWANIE_CZESCI.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';');w.writeheader();w.writerows(rows)
checks='\n'.join('| '+c['name']+' | PASS | '+str(c['parts'])+' | '+str(c['cuts'])+' |' for c in b['checks'])
paramrows='\n'.join('| '+r['name']+' | '+f"{r['value_mm']:.6f}".rstrip('0').rstrip('.')+' | '+r['notes']+' |' for r in v['parameters'])
report=f'''# R002 — regulacja okuć i opisane części, IronCAD 2027

Bieżący model: `{model}`.

Dodano 28 działających regulacji montażu; łącznie 34 parametry sceny. Zmiana wartości przesuwa geometrię i jej wycięcia w IronCAD. Nie wymaga agenta. Wybierz dokument R002 oraz poziom sceny w tabeli parametrów; tabela pozostawionej R001 nadal ma swoje sześć pól.

## Szybka próba

1. `RP_ZamkiPrzod_Rozstaw`: zmień 761,9 na 690 mm. Wszystkie trzy zamki przodu zmienią równy rozstaw; tył pozostanie niezależny.
2. `RP_ZamkiTyl_Przesuniecie`: np. -18 mm przesunie cały tylny rząd w stałej osi X.
3. `RP_UchwytyPrzod_Rozstaw`: np. 1400 mm zmieni rozstaw pary przednich uchwytów.
4. `RP_UchwytKorpusPrzodLewy_Wysokosc`: np. 220 mm zmieni wysokość tylko lewego przedniego uchwytu.
5. `RP_UchwytCzapkaPrawa_Pozycja`: np. 210 mm zmieni pozycję bocznego uchwytu od przedniej krawędzi.

Domyślne równania wiążą pojedyncze uchwyty z rozstawami par i wymiarami skrzyni. Wpisana liczba zastępuje to powiązanie i umożliwia asymetrię. Wysokość uchwytu korpusu liczymy od spodu sklejki dna (bez kół), a czapki od jej dolnej krawędzi sklejki. Strony są stałe w projekcie i nie zależą od kamery.

## Zakres

- 6 parametrów dla rzędów zamków: rozstaw, przesunięcie w poziomie i w pionie, osobno przód/tył.
- 6 parametrów dla par uchwytów korpusu: rozstaw, przesunięcie i wspólna wysokość, osobno przód/tył.
- 16 parametrów pojedynczych uchwytów: pozycja i wysokość każdego z ośmiu H7159.
- 20 jednostek okuć: 8 uchwytów oraz 12 połówkowych zespołów sześciu zamków.
- 56 sprzężonych obróbek: 12 otworów zamków, 8 otworów uchwytów i 36 wycięć w profilach złącza.
- 439 opisów w drzewie: sekcja, ściana, pozycja, funkcja i dostępny kod. Nieustalone role podczęści oraz SKU oznaczono wprost.

Przekroje profili i okucia katalogowe nie są skalowane. Cztery profile złącza odtworzono na kopii, aby usunąć konkurencyjne stare relacje. Mapa ID zachowuje przejście ze źródła do R002. Oryginały i R001 zachowano.

## Parametry

| Nazwa | Wartość początkowa [mm] | Komentarz |
|---|---:|---|
{paramrows}

## Testy w IronCAD 2027

| Próba | Wynik | Części | Obróbki |
|---|---|---:|---:|
{checks}

Kontrolowano rzeczywiste macierze świata, granice i wymiary części oraz położenie, orientację i długości krzywych obróbek. Kontrola obejmuje także połączoną zmianę gabarytów i rozmieszczenia. Po próbach przywrócono wartości początkowe.

PASS: odtworzenie i ponowna edycja po zapisie/otwarciu. PASS: zmiana opisów drzewa bez zmiany parametrów i geometrii. PASS: repository/backend/parts/core-design/core-contracts/QA/harness, dowód `artifacts/verification/20261029T111201177445Z`.

Dziennik lokalny: `{e}` — udany wykonawca `mounting-04`, końcowa prezentacja `mounting-present-02`. Wcześniejsze nieudane kopie/proby pozostają diagnostyką. Pierwsze próby wykryły zastępczy sześcienny SizeBox nowej operacji przed wygenerowaniem bryły oraz zmianę kolejności operacji profilu; naprawiono kolejność generowania i mapowanie po ID.

Źródłowy snapshot R001: `{q['sha256']}` — bez zmian.
Końcowa R002 i jej snapshot: `{digest}`.

## Granice tego przyrostu

Liczba okuć pozostaje zgodna ze wzorcem: trzy zamki na przodzie, trzy z tyłu, osiem uchwytów łącznie. Liczba, inny SKU i swobodny obrót wymagają osobnego przyrostu generatora. Zalecane odległości w komentarzach nie są automatyczną blokadą tabeli IronCAD. To nie pełny test kolizji bryłowych, nośności, CNC ani odbiór produkcyjny. Pełne przypisanie zakupowych SKU pozostaje do potwierdzenia. `production_approved=false`.

## Pliki

- `00_Karta_zlecenia/PARAMETRY.csv`: wszystkie 34 pola, rzeczywiste wartości, równania i komentarze.
- `00_Karta_zlecenia/DRZEWO_SCENY_R002.csv`: 439 etykiet z ID źródłowymi i natywnymi.
- `00_Karta_zlecenia/MAPOWANIE_CZESCI.csv`: aktualna mapa 383 części fizycznych.
- `04_Snapshoty/RockPro_Hisense85_r002_montaz_sprawdzone_IC2027.ics`: zachowana kopia bieżącej wersji.
- `06_Odbior/R002_montaz`: raport, testy i podglądy.
'''
(review/'RAPORT_R002.md').write_text(report,encoding='utf-8')
(p/'CZYTAJ_MNIE.md').write_text('''# Hisense 85 — bieżąca wersja R002, IronCAD 2027

[Model R002 — montaż](03_CAD/Do_sprawdzenia/'''+model.name+''').

**34 parametry sceny, w tym 28 regulacji montażu.** [Instrukcja i testy](06_Odbior/R002_montaz/RAPORT_R002.md).

[Lista parametrów](00_Karta_zlecenia/PARAMETRY.csv) · [Drzewo części](00_Karta_zlecenia/DRZEWO_SCENY_R002.csv) · [Mapa części](00_Karta_zlecenia/MAPOWANIE_CZESCI.csv).

[Historia R001](06_Odbior/RAPORT_PARAMETRYZACJI.md). Oryginał w 01_Kopia_zrodla, potwierdzone kopie obu rewizji w 04_Snapshoty. Kolejne zmiany zapisuj jako R003. Prototyp wymaga odbioru konstruktora.
''',encoding='utf-8')
manifest=dict(revision='r002',created_utc=datetime.now(timezone.utc).isoformat(),output=str(model),output_sha256=digest,snapshot=str(snapshot),source=q['source'],source_sha256=q['sha256'],scene_parameters=34,new_mounting_parameters=28,physical_parts=383,mounting_units=20,coupled_operations=56,tree_labels=439,native_tests_passed=True,production_approved=False)
(p/'STATUS_PROJEKTU.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');(p/'04_Snapshoty/SNAPSHOT_R002.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False))
