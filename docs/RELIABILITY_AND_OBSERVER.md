# Reliability fixes and process observer — 24 October 2026

Implements the four findings in the Astra audit, followed by a read-only Python
observer. Baseline: aefb7b6; the pre-audit local ZIP and Git bundle are preserved.

## F1 — UI timeout is not cancellation

`RpcProcessSession` owns the Python process and all redirected streams. On a
response timeout the UI detaches; a background continuation continues draining
the reply/error streams and keeps the parent alive until its work returns.
Only then is stdin closed and the process reaped. Neither the 180-second response
timeout nor the old five-second exit wait calls Kill. Python therefore retains
the CAD mutex while its synchronous SDK child is executing.

This is not a universal supervisor for OS crashes, host shutdown or forced
process termination, and does not implement cancellation. Never interpret a UI
timeout as safe permission to repeat an operation. Existing operation journal
and native writer lock remain authoritative. The process test uses actual child
processes and an exclusive file lock, with no COM calls.

## F2 — a busy writer has not started

`CadBusyError` is raised only when acquisition refuses entry into the lock.
The case service records a terminal failed attempt with `CAD_BUSY_NOT_STARTED`
and `execution_started=false`. Reusing its operation ID returns the same result;
a new ID is an explicit new attempt. Exceptions after entering the executor
remain `outcome_unknown`; recovery still requires evidence. Abandoned-lock
diagnostics are not weakened into a normal busy response.

## F3 — one public layout field contract

`layout.LAYOUT_PROPERTIES` is used by the MCP schema and backend field allowlist.
It includes optional hinge height, constructor override (boolean) and the legacy
hardware width. Optional fields are not injected into DEFAULT: loading an old
saved layout must not silently opt it into a different geometry policy.
Tests cover published tools/list, roundtrip, false override and non-boolean input.

## F4 — explicitly owned documents and verified recovery

The skeleton worker tracks only documents whose full paths matched its own
new revision. On failure it preserves modified owned scenes to unique recovery
files, verifies saved identity and clean Modified state, then closes them.
The original error is retained, and cleanup failure is separately reported.
Successful worker output is explicitly handed to the user for review.

The C# bridge registers its newly created and reopened documents in
OwnedDocumentScope. It closes them on success and error; modified work is saved
to a new recovery file first. Failed recovery leaves the affected document open,
continues other cleanup and records a failed cleanup result. Environment.Exit
occurs only after the cleanup block and result write.

A native fault probe revealed that SaveAsCopy can display a save error without
raising an exception. Recovery on an operation-owned scene therefore uses Update
and SaveAs to a unique new path, checks file existence, document name and Modified
state. This never saves the original model. A repeat probe reopened the recovery
ICS and confirmed the one part created before the injected duplicate-ID error.
The initial failed recovery evidence is retained; it is not counted as PASS.

## Observer

Run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Observe.ps1`.
The launcher chooses the newest native trace, or opens an empty observer when no
trace is available. Optional `-Trace` and `-Database` select explicit inputs.

- Separate Python/Tk window, Polish controls, green plywood preview, no CAD API.
- Timeline with actual event times, measured phase durations, replay slider,
  progressive simplified bounds and live file refresh.
- Existing OperationLogger writes bounded metadata. Native bridge progress adds
  part creation, regeneration, measurement, save and reopen events. The number of
  native parts is bounded by the executor's 1000-occurrence limit.
- Geometry is in a separate local process_preview.json, bound to the logger by
  SHA256, with stable IDs and bounded finite coordinates. It is planned proxy
  geometry, not a rendering or validation of the real Epson CAD model.
- The observer reads the shared SQLite journal using mode=ro/query_only and closes
  connections after each read. It does not call store.db(), migrate, initialize
  tables, execute operations or create a second project database.
- Historical prototype reports show their recorded checks, with timing and
  provenance explicitly unavailable. Corrupt/partial/truncated logs are flagged.
- Script execution is distinct from decision authorship. Unknown intervention
  history, model, tokens and cost stay unknown; no fabricated automation percentage.

Instrumentation currently covers the synthetic native executor, not every
historical standalone Epson script. The `case.create` span contains SDK build,
native creation, save/reopen and bridge cleanup; native child spans are included
in it and must not be added again. Python save_reopen is only an output check,
not the duration of the SDK save itself. Existing coarse report durations cannot
be used to reconstruct missing per-stage history.

## Evidence and deployment boundary

- Baseline full harness/build/UI PASS: artifacts/verification/20261024T192556108266Z.
- Four-fix intermediate harness/build/UI PASS: artifacts/verification/20261024T192900456517Z.
- Final full harness/build/UI PASS: artifacts/verification/20261024T193839048254Z.
- Targeted tests: process timeout with live child; busy/idempotency/unknown recovery;
  MCP lid roundtrip; worker failures including silent recovery failure; C# cleanup
  helper; observer readonly SQLite, trace bounds and incomplete log behavior.
- Native success: artifacts/reliability-observer-native-20261024/native-probe-01/;
  67 proxy occurrences, independent measurements before/after reopening, source
  unchanged, owned documents closed. This is a new test model, not a rebuilt Epson.
- Native injected failure: cleanup-fault-02/verification.json, preserved single
  part reopened successfully; source unchanged, owned documents closed.
- Actual observer window opened and replay inspected with the native trace.

Building does not reload the DLL in an open IronCAD host. Current session still
uses its previously loaded panel. F1 requires loading the rebuilt add-in on a
safe next restart; backend, bridge and observer run from the modified sources.
Existing modified user tabs were not closed or overwritten for deployment.


## Warstwy i czytelne etapy — 2026-10-24

Usunięto odrzucony rysunek AABB z obserwatora. Dziennik grupuje zdarzenia
w numerowane etapy z kolorami, rozwijanymi szczegółami, bieżącym etapem
oraz stanami oczekuje / w toku / OK / BŁĄD. Suwak zachowuje oryginalną
kolejność zdarzeń; grupy są klasyfikacją, nie zmianą harmonogramu wykonania.
Czasy pozostają na zdarzeniach: sumowanie SDK i etapów liczyłoby pracę dwukrotnie.

Przycisk modelu otwiera lokalny Three.js r180 (MIT, vendor/PROVENANCE.json).
Eksport siatek pochodzi z IZSceneDoc.ExportICWebViewerFile; konwerter
scripts/prepare_layer_viewer.py zachowuje macierze i kolory. Nie zmienia ICS.
Serwer udostępnia wyłącznie allowlistę plików na loopback, pod losowym tokenem.
Nie wysyła modelu do zewnętrznej usługi. SHA256 bufora jest sprawdzany przez
serwer i przeglądarkę. Wymagany WebGL.

Uruchomienie: scripts/View3D.ps1 -Dataset <folder-z-model.json> albo
scripts/Observe.ps1 -Trace <plik.jsonl> -Model <folder-z-model.json>.
Warstwy: sklejka, profile, narożniki/wzmocnienia, zamki/zawiasy, uchwyty, koła.
Dostępne obrót, zoom, widok z obu stron, ukrywanie warstw, kolory etapów
oraz poglądowe składanie. Animacja NIE odtwarza czasu historycznej operacji.

Dowód lokalny: artifacts/epson-layer-viewer-20261024/model-02 — rzeczywisty
prototyp Epson 650 × 500 × 381 mm, 240 siatek / 582780 trójkątów.
Cztery puste węzły zawiasów nie mają siatki w eksporcie; zapisane w
missing_export_meshes i ujawnione w UI. Model źródłowy pozostał niezmieniony.
Trace native-probe-01 dotyczy osobnego syntetycznego testu 67 elementów,
nie historii tworzenia tego Epsona. Brak powiązania nie jest ukrywany.

PASS: pełny harness artifacts/verification/20261024T200943262042Z;
sprawdzenie widoku rzeczywistych siatek, tylnej strony, ukrytej sklejki,
kolorów warstw oraz rozwijania etapów w aplikacjach. Nie zmieniano DLL ani CAD.


## Nocna kontynuacja ROC-20 — sprzątanie katalogowego wykonawcy

Znaleziono drugi, starszy helper catalog_native.close_owned_documents, który
korzystał jeszcze z SaveAsCopy bez potwierdzenia pliku. Wymieniono go na Update
+ SaveAs własnego dokumentu do unikalnej kopii odzyskiwania. Przed zamknięciem
sprawdzane są istnienie pliku, zgodna nazwa dokumentu i Modified=false.
Nieudane zachowanie pozostawia zmieniony dokument i jego wpis własności w hoście.
Pozostałe własne dokumenty nadal są sprzątane.

PASS: trzy testy, w tym silent save failure bez pliku, który nie może zamknąć
zmienionego dokumentu. PASS natywny na kopii lekkiego szkieletu: zmiana długości
935 mm, celowy błąd ciała operacji, zachowanie kopii i ponowne otwarcie tej samej
wartości. Oryginał i aktywny kontekst bez zmian. Dowód:
artifacts/overnight-20261024/catalog-cleanup-native/verification.json.
PASS pełny harness: artifacts/verification/20261024T215741060210Z/results.json.


## 31.10.2026 — rejestr wykonania zapisany w Studio (część ROC-56)

Wdrożono `process_runs.py` i panel „Przebieg wykonania · SDK / AI” pod podglądem.
Każdy przebieg jest osobnym, trwałym zapisem w tej samej SQLite co drafty,
związanym z ID, rewizją i SHA treści draftu. Nie zmienia kontraktu draftu,
nie zapisuje danych obserwacji w geometrii i nie parametryzuje liczby okuć.
Odczyt/import/eksport logu JSON, lista historycznych przebiegów, filtr po
pochodzeniu, wyszukiwanie części/etapu, powody interwencji i czasy operacji.

### Co oznaczają liczniki

- Operacja to nazwany krok roboczy, np. wstawienie elementu, regeneracja,
  pomiar lub zapis. Nie oznacza pojedynczego wywołania COM ani liczby trójkątów.
- `operation_id` ma kolejne próby. Start i wynik tej samej próby liczą się raz;
  ponowienie pokazujemy osobno. Zakończone operacje to ostatnie udane wyniki.
- `origin` wyznacza rozłączne grupy standard / AI / konstruktor / nieustalone.
  `executor` jest drugą osią. 270 standard + 30 AI może nadal oznaczać 300 SDK.
- Interwencja AI ma osobne ID, SKU, etap i krótki powód, np. brak mapy otworu.
  Operacje AI wskazują jej ID. Jedna interwencja może dotyczyć 30 operacji;
  nie oznacza to 30 osobnych decyzji lub wywołań modelu.
- Nadrzędny czas etapu (`span`) nie wchodzi do licznika operacji ani sumy ich
  czasów. Suma prób może różnić się od czasu zegarowego całego przebiegu.
- Nieustalone pochodzenie pozostaje w mianowniku; pusty przebieg ma brak
  procentu, nie 100% automatyzacji. Raportowanie jest deklaracją wykonawcy,
  nie automatycznym dowodem autorstwa decyzji ani odbiorem CAD.

### Uruchomienie pomiaru i integracja wykonawcy

Zapisz draft. W panelu kliknij „Przygotuj pomiar” i skopiuj run_id.
Przycisk zakłada rejestr; nie uruchamia IronCADa. Alternatywnie:

```powershell
Integracja/.venv/Scripts/python.exe scripts/studio_process_run.py start ID_DRAFTU 1 "T1 — wykonanie CAD"
Integracja/.venv/Scripts/python.exe scripts/studio_process_run.py append RUN_ID zdarzenia.json
Integracja/.venv/Scripts/python.exe scripts/studio_process_run.py finish RUN_ID completed
Integracja/.venv/Scripts/python.exe scripts/studio_process_run.py export RUN_ID nowy_log.json
```

Żądanie wspólnego `scripts/run_t1_machining_job.py` może zawierać:

```json
{"studio_trace":{"run_id":"ID_PRZEBIEGU","origin":"standard","stage":"handles","part_id":"H7159"}}
```

Nowy element bez mapy: najpierw append zdarzenia `kind=intervention`,
`operation_id=ID_INTERWENCJI`, `origin=ai`, `executor=agent`, `status=requested`,
`reason` i `part_id`. Każde zdarzenie ma unikalny `event_id`, `stage` i
opcjonalne `occurrence_id`. Wynik interwencji (resolved/failed) jest kolejnym
zdarzeniem tego samego operation_id. W żądaniu wykonawcy ustaw origin=ai
oraz intervention_id=ID_INTERWENCJI. Dopiero wtedy wolno przypisać operacje AI.

`process_capture.py` mierzy wywołanie wykonawcy jako span i importuje szczegółowy
`native_progress.jsonl` z jawnych zdarzeń native.create/regenerate/measure/save/reopen.
Zachowuje SHA dowodu i ID wystąpień. Nie tworzy operacji z BOM ani z liczby części.
Starszy helper bez śladu szczegółowego dostaje tylko pomiar całego etapu i jawny
komunikat o braku szczegółów. Aby objąć inny wykonawca, trzeba przekazać to samo
run_id i emitować ten protokół; nie wszystkie historyczne skrypty są zinstrumentowane.
Agent poza tym przepływem nie jest wykrywany automatycznie. Nie wdrożono tu
samodzielnego generowania/akceptacji map dla nieznanych części ani pomiaru tokenów/kosztu LLM.

### Warstwa 3D, zapis i wersja online

Zielony = standard, fioletowy = udział AI, bursztynowy = konstruktor,
szary = nieustalone. Kolory używają dokładnego ID wystąpienia, nigdy podobieństwa
SKU/nazwy. Brakujące ID są pokazane jako niedopasowane. Gdy przy części jest
zarówno standard, jak i AI, kolor AI pokazuje jej udział; liczby pozostają per
operacja. Zmiana draftu lub rewizji wyłącza historyczne kolory, zachowując log.
Materiały podglądu są klonowane i przywracane; CAD i wspólne zasoby nie zmieniają się.

W przygotowanej paczce Vercel można importować i eksportować log JSON; walidator
jest bezstanowy, a zapis pozostaje w tej przeglądarce. To nie współdzielona baza
logów online i nie dostęp przeglądarki do IronCADa. Nie wykonano publikacji tej
zmiany na Vercelu. Lokalny zapis Studio jest w SQLite.

### Weryfikacja i granice

- 12 testów procesu PASS: 300/270/30 bez podwójnego liczenia, ponowienia,
  nieustalone źródło, interwencje, granice rewizji/importu, atomowość partii,
  częściowy ślad po błędzie, brak wymyślonych operacji, HTTP/session/origin.
- Pełny harness offline `artifacts/verification/20261031T161004138899Z`: 7 grup PASS;
  po dodaniu dodatkowych blokad i testu HTTP ponownie 12 testów procesu PASS.
- `artifacts/process-runs-e2e/result.json`: panel, filtry, kolory modeli,
  eksport/import, zapis/odczyt, wyłączenie starej warstwy i układ mobilny PASS.
- `artifacts/process-cloud-e2e/result.json`: import/reload, odrzucenie innej
  rewizji, izolacja przeglądarek na lokalnej paczce Vercel PASS.
- Natywny CAD w tej zmianie: NOT RUN. Test adaptera używa kontrolowanego śladu;
  nie przedstawia tych wyników jako nowego narysowania skrzyni w IronCADzie.
- Przykład 270+30 jest mode=simulation na nowym draftcie, z jawną etykietą.


Dla płyt warstwa używa `panel/<key ramy montażu>`, dla okuć `placement.items[].id`,
dla konstrukcji `construction.items[].id`. Gdy native_progress ma inne ID,
wykonawca przekazuje jawną `occurrence_map` w studio_trace. Brak takiej mapy
nie uruchamia zgadywania po SKU. Niezarejestrowane obiekty są szare przy włączonej
warstwie. Wyłączenie warstwy przywraca zwykły wygląd sklejki i okuć.

Końcowa regresja: `artifacts/verification/20261031T162023509924Z` — wszystkie 7 grup PASS. Końcowe 12 prób procesu: `artifacts/process-runs-tests-final.log` — PASS.
