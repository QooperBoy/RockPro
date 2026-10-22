# CatalogAsset v1 — zmierzony kandydat H7159

Moduł `Integracja/rockpro_cad/core_case/catalog_assets.py` przekształca jawnie
przekazane, zapisane raporty JSON w wersjonowaną definicję jednego assetu H7159.
Nie odczytuje plików, nie importuje adapterów natywnych, COM ani IronCAD i nie
uruchamia kodu z danych. Nie zmienia zamrożonego POC ani jego raportów. Bieżący
zakres to import danych, walidacja, podgląd dwóch wystąpień oraz niezależny sidecar
do istniejącego szkicu inwentarza.

## Publiczne API

| Funkcja | Kontrakt |
|---|---|
| `import_candidate(bundle, trusted_bindings)` | Sześć jawnych raportów jako bajty UTF-8 lub tekst JSON. Oczekiwane hashe, GUID, poddrzewo i rewizję przekazuje wywołujący niezależnie. Wynik to odłączona definicja kandydata. |
| `validate_asset(asset)` | Zwraca głęboką kopię poprawnego kontraktu; odrzuca uszkodzoną treść, nieznane pola, eskalację zgody i sprzeczne świadectwa. |
| `plan_candidate_pair(asset, request)` | Czysty podgląd jednej pary sztywnych uchwytów. Przy odmowie zwraca `status="blocked"`, diagnostykę i `changes=[]`, bez częściowego wykazu wystąpień. |
| `build_manifest_sidecar(manifest, asset, selected_occurrence_ids)` | Zwraca osobny dokument powiązania dokładnie jednego udowodnionego korzenia źródłowego. Nie zmienia manifestu ani jego statusu. |

Import, walidacja i sidecar zgłaszają `CatalogAssetError`, podtyp `ValueError`,
z polami `code` i `message`. Dane wejściowe pozostają niezmienione.

## Wejściowe raporty i niezależne przypięcie

`bundle` ma dokładnie klucze `inventory`, `source_chain`, `catalog_receipt`,
`face_evidence`, `poc_receipt` i `prepared_plans`. Obsługiwany jest jeden kształt
raportów pochodzący z ekstrakcji H7159 i POC 03/04. Nie jest to uniwersalna migracja
historycznych dokumentów. Import sprawdza hashe dokładnych bajtów przed dekodowaniem,
odrzuca powtórzone klucze JSON, NaN/inf, zbyt głębokie lub nadmierne dane oraz
nieznane pola przy modelowanych granicach kontraktu. Nazwy i ścieżki z raportów
pozostają danymi; importer nigdy ich nie otwiera.

`trusted_bindings` ma dokładnie następujące pola:

```text
schema_version=1
definition_id, definition_revision
source_inventory_sha256
original_source_sha256, original_source_guid
source_subtree, source_node_id
captured_source_sha256, captured_source_guid
asset_sha256, asset_guid
report_sha256={inventory,source_chain,catalog_receipt,face_evidence,poc_receipt,prepared_plans}
```

Rewizja jest dodatnią liczbą całkowitą, bez konwersji z bool, float lub tekstu.
Hashe to SHA256 małymi znakami hex; poddrzewo jest jawną listą indeksów wystąpień.
Importer nie wybiera poddrzewa po nazwie H7159 i nie wyprowadza z raportu własnego
zaufania. Wywołujący musi dobrać i sprawdzić przypięcia. Sam hash nie uwierzytelnia
autora raportu i nie jest podpisem zatwierdzenia konstruktora.

Oryginał na dysku, przechwycona scena oraz wyeksportowany asset mają oddzielne
SHA/GUID. Raport eksportu musi odnosić się do przechwyconego źródła, a raport POC
i świadectwa płaszczyzn — do tego samego wyeksportowanego assetu. Połączenia są
sprawdzane przez jawne dane pochodzenia, nie przez podobieństwo nazw lub ścieżek.

## Definicja i geometria

Definicja zawiera `definition_id`, `definition_revision`, `content_sha256`,
`sku="H7159"`, `family="handles"`, `units="mm"`, `frame="catalog.local"`,
`geometry_policy="rigid"`, `stage="measured_candidate"`, `source_binding`,
`geometry_signature`, `geometry_signature_sha256`, `root_poses`,
`mounting_candidate`, `mounting_rule` i jawny zakres dowodu. Pola
`mounting_approved` i `production_approved` zawsze mają wartość `false`.
Nie ma ścieżki wejściowej nadającej zgodę produkcyjną.

`content_sha256` jest hashem kanonicznego JSON całej definicji bez tego pola.
Zmiana treści lub rewizji daje inny hash. Czysty walidator potwierdza zgodność
struktury i hasha; przyszły wspólny magazyn SQLite musi dodatkowo zapewnić,
że raz zapisane `(definition_id, definition_revision)` nie zostanie zastąpione
inną treścią. Ten przyrost nie implementuje magazynu ani osobnej bazy C#.

Sygnatura rozdziela kontenery zespołów od dokładnie 13 części fizycznych.
Każdy komponent ma stabilne ID wynikające z jawnej definicji i ścieżki względnej,
rodzaj i położenie wewnętrzne. Części mają również lokalne obrysy, objętość,
dokładność pomiaru i liczniki topologii. Weryfikowane są kompletność hierarchii,
unikalność ścieżek, dodatnia objętość, poprawne obrysy oraz niezmienność macierzy
wewnętrznych pomiędzy raportami. Oryginalne, nieprzekształcane odbicia wewnątrz
assetu są zachowywane; nowa orientacja całego uchwytu jest właściwym obrotem,
bez odbicia i skalowania. Poza sygnaturą zapisane są osobne położenia korzenia
przechwyconego źródła i wyeksportowanego assetu.

Obrysy, objętość, liczniki topologii i macierze nie są pełnym kryptograficznym
odciskiem BRep. Zachowanie tych miar nie dowodzi identyczności każdej powierzchni.
Nazwy części i prywatne ścieżki raportów nie są kopiowane do definicji.

## Kandydat płaszczyzny montażowej i para

Płaszczyzny 194 i 353 mają surowe wierzchołki, normalne bazowe i oddzielne flagi
odwrócenia. Z nich wyprowadzane są początek, zwrot na zewnątrz i świadectwa obrysu.
Przypięta konwencja H7159 wymaga styku Y=0, strony zewnętrznej Y=1,2 mm,
wycentrowanego kołnierza 161×107 mm i kierunku góry katalogu −Z.

`mounting_candidate.component_path=[0]` i odpowiadające `component_id` wskazują
konkretną część kołnierza. `component_binding="pinned_h7159_extractor_convention"`
oznacza konwencję znanego ekstraktora POC 03/04, a nie metadane odczytane z JSON.
W tej wersji część [0] musi mieć lokalną macierz jednostkową względem korzenia assetu;
każdy wierzchołek świadectwa musi mieścić się w jej lokalnym obrysie. Inne
przypisanie części lub układu wymaga osobnej wersji, bez automatycznej heurystyki.

Żądanie podglądu ma dokładnie `schema_version=1`, `units="mm"`,
`frame="case.closed"`, `size=[W,D,H]`, `thickness`, `lid_height`,
`edge_inset_mm` i `count=2`. Dla odsadzenia e punkty montażu wynoszą:

```text
lewy  = [−(W/2 − e − 80,5), −D/2, (H − lid_height)/2]
prawy = [ +(W/2 − e − 80,5), −D/2, (H − lid_height)/2]
obrót katalogu do skrzyni = diag(1, −1, −1)
```

Sprawdzane są miejsce na parę, minimalna przerwa 25 mm, odsadzenie od dołu i szwu
oraz skończone wartości. Wystąpienia mają stabilne ID przy resize i powrocie.
Podgląd zawiera wyłącznie dwa uchwyty; nie dodaje urządzenia ani dziesięciu płyt,
nie tworzy ICS i nie przedstawia planu jako natywnego pomiaru.

## Sidecar i ograniczenie historycznej relacji

Sidecar wymaga dokładnie tego samego hasha pliku i treści inwentarza, oryginalnego
źródła, GUID, poddrzewa i ID korzenia. Wybranie innej części lub jednego z pozostałych
zespołów nazwanych H7159 jest odrzucane. Ręczne i nierozliczone elementy manifestu
pozostają niezmienione. `inventory_draft`, `runtime_template_compatible=false`
i brak zgody produkcyjnej nie są promowane przez sidecar.

Gdy oryginał lub przechwycone źródło miało `modified=true`, albo nie udowodniono
zgodności sceny z dyskiem, definicja zachowuje
`inventory_relation_status="unproven_live_memory"`. Import zmierzonych danych
assetu i podgląd pary pozostają możliwe, ale powiązanie z pełnym inwentarzem kończy
się `INVENTORY_RELATION_UNPROVEN`. Brakujący dowód to nowy odczyt inwentarza i eksport
wykonane z jednej przypiętej, zapisanej rewizji źródła. Podobne nazwy, GUID lub
zgodny hash starszego pliku dyskowego nie zastępują tego dowodu.

## CLI i powtarzalność

`scripts/import_catalog_asset.py` przyjmuje wyłącznie jawne ścieżki argumentów:

```powershell
python scripts/import_catalog_asset.py --inventory <inventory.json> --source-chain <source_chain.json> --catalog-receipt <native_receipt.json> --face-evidence <faces.json> --poc-receipt <hardware_poc_receipt.json> --prepared-plans <prepared_plans.json> --trusted-bindings <trusted.json> --output-dir <nowy_katalog>
```

Opcjonalne `--manifest <manifest.json> --selected-occurrence-id <ID>` zleca próbę
sidecaru. Raport jawnie rozdziela powodzenie importu/podglądu od zablokowanego
sidecaru. CLI waliduje wejścia przed utworzeniem katalogu, odmawia użycia
istniejącego katalogu i zapisuje pliki wyłącznie w trybie nowego pliku. Nie otwiera
ścieżek ICS ani innych wskazówek znajdujących się w raportach.

Wyniki to `asset.json`, `preview-A.json`, `preview-B.json`, `preview-C.json`,
`import_report.json` i opcjonalny `sidecar.json` albo `sidecar_blocked.json`.
A ma obrys 900×600×330, B — 1100×720×410, C wraca do A. Porównywane są całe dane
podglądu A/C. Raporty i definicje rzeczywistego klienta należy przechowywać lokalnie
w ignorowanym `artifacts/`, bez kopiowania prywatnych danych do fixture Git.

Testy `test_catalog_assets.py` i niezależny `test_catalog_assets_oracle.py`
korzystają ze sztucznych raportów, jawnych równań i prób sprzeczności wspólnych
danych. Sprawdzają również czysty import modułu przy zablokowanych modułach CAD/COM,
brak odczytów plików przez API oraz wyłączność zapisu CLI. Stan RED→GREEN zapisuje
się lokalnie; pełny harness i odbiór natywny pozostają oddzielnymi dowodami.
