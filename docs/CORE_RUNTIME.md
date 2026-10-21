# Czysty plan i lokalny prototyp skrzyni

`rockpro_cad.core_case.plan_case(request)` interpretuje jawne dane recepty w pamięci,
bez CAD, SQLite, zapisu plików i importów sterowanych danymi. Wersja v1 obsługuje
syntetyczny pakiet `synthetic-roc43-rules-v1`: 37 grup i domyślnie 67 wystąpień.
Nie korzysta z oczekiwań testowych ani identyfikatorów przypadków. Stała lista
operacji, jawne referencje, walidacja nieaktywnych gałęzi, budżety drzewa i obliczeń,
właściwe obroty i pełne odbicia zbioru punktów w każdej zadeklarowanej osi blokują
niepoprawną receptę. Wynik `blocked` zawsze zawiera diagnostykę i `changes=[]`.

Plan zawiera lokalne i zamknięte położenia, ramy, właściwe obroty katalogowe,
wymiary i obrysy części, grupy, parowania, rozliczenie inwentarza, gabaryt AABB
wszystkich części oraz osobne przesunięcie prezentacyjne wieka. Wcześniejszy plan
musi odtworzyć się z danych i decyzji ręcznych. SHA256 całej specyfikacji i recepty
wiąże jego stan; zmiana jednego członka lub podmiana źródła blokuje ponowne użycie.
Zgody `SYNTHETIC-*` są danymi testowymi o jawnym zakresie, bez uwierzytelniania
konstruktora i bez możliwości zatwierdzenia rzeczywistego wzorca Epson.

## Wspólne API UI i MCP

`Integracja/rockpro_cad/mcp/core_service.py` korzysta wyłącznie z bazy
`project_store.DB_PATH`. Dodaje `case_requests`, `case_request_versions`,
`case_plans` i `case_operations`; historia i archiwa pozostają w istniejących
`events` i `snapshots`. Nie zmienia starego wykonawcy sześciu parametrów.

| Operacja | Wynik i warunki |
|---|---|
| `preview_case(request)` | Czysty plan lub blokada; bez I/O. |
| `prepare_case_request(project_id, expected_layout_revision)` | Jawny syntetyczny prototyp ze zapisanego układu; odmawia dla innej liczby urządzeń, braku komory X/Y lub zerowej przegrody. Nie poprawia samowolnie układu. |
| `get_case_request(project_id)` | Zapisane dane, SHA256 i rewizja; brak zapisu ma rewizję 0. |
| `save_case_request(project_id, request, expected_revision, actor, change_source)` | CAS rewizji żądania oraz niezmienna wersja i zdarzenie. Dane nieprzechodzące planera nie są zapisywane. |
| `plan_project_case(project_id, expected_revision, scenario=None)` | Niezmienny plan, hashe specyfikacji/recepty/żądania/planu; przypięta rewizja karty projektu, ścieżka i hash źródła. |
| `execute_case_plan(project_id, plan_id, operation_id, expected_revision)` | Zapis zamiaru, jeden wykonawca na nowej kopii, pomiar i ponowne otwarcie, weryfikacja dowodów i rejestracja archiwum. |
| `get_case_operation(project_id, operation_id)` | Stan dziennika; dla ukończonej operacji sprawdza integralność archiwum i dowodów. |
| `list_case_operations(project_id, limit=50)` | Odczyt do 100 operacji; nieukończone jako pierwsze. Umożliwia odzyskanie identyfikatora po restarcie UI lub procesu. |
| `recover_case_operation(project_id, operation_id)` | Wyłącznie odczyt i weryfikacja istniejących dowodów, bez kolejnego wywołania CAD. |

`expected_revision` w API zapisu/planu/wykonania dotyczy `case_requests`, niezależnie
od rewizji układu i `CaseSpec.revision`. Przygotowany układ zapisuje w źródle wymiarów
referencję `prototype-layout:<projekt>:<rewizja>:<sha>`. Zapis, planowanie i wykonanie
sprawdzają ją ponownie. Konflikt wymaga odczytu i porównania danych; brak automatycznej
zmiany tokenu i ponowienia zapisu.

## Dziennik i odzyskiwanie

Przejścia to `planned → applying → saved → reopened_verified → registered`.
Jawnie nieudana odpowiedź wykonawcy daje `failed`; wyjątek lub utrata odpowiedzi
daje `outcome_unknown`. Nieukończona operacja blokuje nowego wykonawcę tego projektu.
Identyfikator operacji można powtórzyć tylko dla tego samego projektu, planu i
rewizji. Nie uruchamia to ponownie CAD. Wywołanie odzyskiwania bez kompletnego
`native_receipt.json` odmawia i zachowuje niepewny stan.

Wykonawca otrzymuje istniejący katalog nadrzędny
`Integracja/case_runs/<project_id>` i tworzy nowy podkatalog `<operation_id>`.
Nie przyjmuje dowolnej ścieżki wyjściowej z MCP. Serwis sprawdza granice ścieżek,
hash źródła przed/po, wszystkie etapy natywne, hash pliku wynikowego oraz kopii
źródła, a także niezależnie porównuje pomierzone pozycje i obrysy z planem.
Oddzielne `snapshot.ics` powstaje bez nadpisywania. `service_receipt.json` jest
zapisywany z flush/fsync przed transakcją rejestracji. Awaria rejestracji może być
naprawiona z tych samych plików; zmieniony plik lub dowód blokuje odzyskanie.
SHA256 wykrywa późniejszą zmianę archiwum; nie jest gwarancją WORM.

Rejestracja używa `snapshots.validation="prototype"`,
`production_approved=false` i `source_advanced=false`. Zachowuje przypięte źródło
projektu. Bryły okuć są zastępcze; prototyp nie dowodzi katalogu, wycięć, kolizji,
styku profili, nośności ani odbioru produkcyjnego. Inwentarz Epson z ROC-42 nadal
kończy się `MANIFEST_NOT_READY`, dopóki nie powstanie osobne zatwierdzone mapowanie.

## Sprawdzanie

ROC-43: `scripts/test_core_design.py --mode red` sprawdza pełne 173 wymagania
czystego planera. Nazwa trybu zachowuje historię TDD; wynik jest obecnie GREEN.
`core_case/test_planner.py` dodaje niezależny układ spoza A/B/C, odmowy języka,
kontrolę tożsamości, geometrii i symetrii oraz zachowanie decyzji po resize.
`mcp/test_core_service.py` sprawdza CAS UI/AI, wersje, przypięcie źródła/karty,
idempotencję, granice ścieżek, uszkodzenie hashy, awarie oraz odzyskiwanie bez
ponownego wstawienia części. W tych testach wykonawca zapisuje pliki zastępcze;
ich PASS nie jest natywnym odbiorem IronCAD. Dowód CAD raportuje się oddzielnie.

## Wznowienie odbioru przez CLI

`scripts/run_core_acceptance.py` wywołuje te same funkcje serwisu co UI/MCP,
bez własnego adaptera CAD i bez wykonywania kodu z JSON. Wymaga zapisanego projektu
z przypiętym plikiem roboczym we właściwym `Integracja` oraz bieżących tokenów
z `get_layout` i `get_case_request`. Nie tworzy projektu, nie przełącza bazy ani
nie odświeża automatycznie tokenów po konflikcie. Raport musi być nowym plikiem
w `artifacts/`; istniejący raport blokuje komendę przed zmianą danych.

Z katalogu checkoutu, po podstawieniu odczytanych wartości:

```powershell
& '..\Integracja\.venv\Scripts\python.exe' scripts/run_core_acceptance.py --mode plan --project-id <ID> --expected-layout-revision <L> --expected-case-revision <C> --report artifacts/acceptance/plan.json
```

Ten krok zapisuje żądanie przez CAS i przypina plan. Nie uruchamia IronCAD.
Z raportu odczytaj `result.plan_id` i `result.revision`. Po zwolnieniu hosta otwórz
przypięte źródło w IronCAD; nie zapisuj ani nie zamykaj przez ten runner innych
dokumentów użytkownika. Oddzielna jawna komenda wykonuje plan raz:

```powershell
& '..\Integracja\.venv\Scripts\python.exe' scripts/run_core_acceptance.py --mode execute --project-id <ID> --expected-case-revision <C_NOWE> --plan-id <PLAN_ID> --operation-id pilot-001 --report artifacts/acceptance/execute.json
```

Po timeout lub restarcie najpierw odczytaj dziennik. Brak `--operation-id` w trybie
`status` wypisuje operacje, z nieukończonymi na początku. Odzyskiwanie wyłącznie
sprawdza istniejące pliki; nie wykonuje ponownie wstawiania części:

```powershell
& '..\Integracja\.venv\Scripts\python.exe' scripts/run_core_acceptance.py --mode status --project-id <ID> --report artifacts/acceptance/status.json
& '..\Integracja\.venv\Scripts\python.exe' scripts/run_core_acceptance.py --mode recover --project-id <ID> --operation-id pilot-001 --report artifacts/acceptance/recovery.json
```

Stan `outcome_unknown` bez kompletnego dowodu nadal blokuje nowego wykonawcę.
Nie zmieniaj identyfikatora, aby obejść dziennik. Wynik natywny `registered`
potwierdza wyłącznie prototyp z bryłami zastępczymi i sprawdzone archiwum.
Próba z prawdziwymi okuciami Epson wymaga osobnego zatwierdzenia ich mapowania.
