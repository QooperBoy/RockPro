# H7159 — świeża baza montażowa i para, 24.10.2026

Przyrost ROC-42/ROC-17 po [przechwyceniu zapisanej rewizji](SOURCE_REVISION_CAPTURE.md).
Zakres obejmuje dwie zmierzone płaszczyzny kołnierza oraz trzy natywne sceny
z samą parą uchwytów. Nie zastępuje pełnego montażu skrzyni, odbioru konstruktora
ani istniejącego kontraktu sześciu raportów [CatalogAsset](CATALOG_ASSETS.md).

## Implementacja

`core_case/mount_capture.py` i `scripts/capture_h7159_mount.py`:

- wymagają dokładnego bindingu źródła, poprawnego raportu eksportu i niezależnie
  podanego SHA256 assetu; odrzucają zmodyfikowane lub nieudowodnione źródło;
- otwierają wyłącznie własne, identyczne bajtowo kopie przez ukryte `OpenFile2`;
  odmawiają przejęcia już otwartego dokumentu;
- odczytują płaszczyzny 194/353 części kołnierza [0]: surowe wierzchołki,
  normalne bazowe i osobne flagi odwrócenia; nie wnioskują bazy z bbox;
- wyprowadzają kandydata bazy przez istniejący `candidate_datum` i reguły pary
  `plan_hardware_poc`/`validate_pair`;
- sprawdzają płaszczyznę styku Y=0, stronę zewnętrzną Y=1,2 mm, obrys
  161 × 107 mm, zwrot uchwytu i symetrię względem X=0;
- zapisują A (900 × 600 × 330), B (1100 × 720 × 410) i powrót C=A,
  każdorazowo otwierają zapis i mierzą ponownie. Każda scena ma dwa zespoły,
  łącznie 26 rzeczywistych części. Płyt ani urządzenia nie generują;
- zachowują rozmiary i transformacje wewnętrznych części; szczegółowa sygnatura
  eksportu jest porównywana raz przy przejęciu assetu;
- zamykają własne dokumenty, zachowując niespodziewane zmiany w nowej kopii.
  PASS powstaje dopiero po sprzątaniu i kontroli aktywnego dokumentu oraz SHA256.

Domyślne uruchomienie CLI sprawdza wejścia bez COM i bez zapisu. `--native`
uruchamia opisany pomiar. Katalog wyniku musi być nowy i znajdować się w
`artifacts/`; żadne wcześniejsze świadectwo ani snapshot nie są nadpisywane.
GUID assetu jest odczytywany z kopii chronionej dokładnym SHA256.

## Dowody lokalne

Źródło: eksport `artifacts/saved-source-native-20261024-02/h7159-export-20261024-01/`,
binding `artifacts/h7159-saved-binding-20261024-01/binding.json`.
Asset SHA256: `08d54a0a7b3d5558e34643c101342677599b725536cd66c7d9d108c23ea5bd65`.

Końcowy przebieg: `artifacts/h7159-fresh-mount-20261024-03/`.
Zawiera `face_evidence.json`, `datum.json`, trzy pliki `A_pair.ics`/`B_pair.ics`/
`C_pair.ics` oraz `mount_pair_receipt.json`.

PASS natywny: trzy sceny po 26 części, zgodne pomiary przed zapisem i po otwarciu,
powrót A/C, niezmieniony asset i aktywny dokument, wszystkie własne dokumenty
zamknięte. SHA256 użytkowej skrzyni 2000 × 3000 × 4000 pozostał bez zmian.
PASS offline: cztery nowe testy guardów i wyprowadzenia bazy; cały harness
repository/backend/parts/core-design/core-contracts/qa/harness.
Wyniki: `artifacts/verification/20261024T133415323983Z/results.json`.
Polecenie: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Verify.ps1 -Python .\Integracja\.venv\Scripts\python.exe`.

Wcześniejszy przebieg 01 zatrzymał się na brakującym jawnym QueryInterface
korzenia IUnknown; dokument zamknięto, bez świadectwa PASS. Przebieg 02 przeszedł;
03 sprawdza także zaostrzoną tolerancję obrotów i GUID źródła. Żadne historyczne
raporty nie zostały przepisane na nowy asset.

## Granice i następny krok

To kandydat bazy, nie zatwierdzony montaż. Próbka pary nie ma fizycznej ściany:
styk sprawdzany jest względem jawnego datum ściany z planu. Weryfikacja grafiki
pozostaje NOT RUN; dokumenty operacji są zamykane, a otwarta skrzynia użytkownika
pozostaje bez zmian. Resize oznacza osobną regenerację scen z kotew,
nie trwałe wiązania natywne. Brak wycięć i oceny kolizji/nośności.

Następny krok: świeży pełny POC z płytami i urządzeniem oraz uzgodnienie jego
raportów z `catalog_assets` i sidecarem zapisanej rewizji. Nie podstawiać
tego dowodu pary pod starszy raport 37 części i nie osłabiać jego walidatora.
ROC-42 i ROC-17 pozostają In Progress; zgody montażowa i produkcyjna są false.
