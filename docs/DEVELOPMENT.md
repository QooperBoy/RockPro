# RockPro CAD — kontrakt developerski

## Kontrakt i inwentarz części — ROC-15 / ROC-42

Pakiet `Integracja/rockpro_cad/core_case` zawiera walidatory danych, generator
`plan_case` i osobnego wykonawcę natywnego prototypu CAD. [CASE_CONTRACT.md](CASE_CONTRACT.md)
opisuje wersje, jednostki, pochodzenie wymiarów, tożsamość części, kotwy i grupy
symetrii. [PARTS_MANIFEST.md](PARTS_MANIFEST.md) opisuje źródłowy inwentarz oraz
powtarzalny odczyt z zachowaną mapą UUID. Oba moduły są sprawdzane w kroku
`core-contracts` zwykłego `scripts/Verify.ps1`.

`inventory_draft` z odczytu CAD jest propozycją pełnego rozliczenia węzłów.
Nie jest wykonywalnym szablonem: brak potwierdzonych ról, ram montażowych,
parowania lub symetrii blokuje dalsze użycie. Kontrakt zgłasza
`MANIFEST_NOT_READY`, gdy taki szkic jest podstawiany do żądania planera.
Zgody i dane syntetyczne z ROC-43 nie zatwierdzają rzeczywistego modelu Epson.
Przy odczycie JSON zawsze podawaj `encoding='utf-8'`; domyślne kodowanie Windows
może uszkodzić polskie nazwy i spowodować prawidłową odmowę zgodności hashy.

Rzeczywiste manifesty klienta i mapowania źródła przechowuj wyłącznie lokalnie,
w ignorowanym `artifacts/`. Zakończenie kontraktu nie oznacza ukończenia montażu,
promocji źródłowego manifestu do szablonu ani natywnej walidacji ICS.

Architektura i zakres docelowy (nie wszystkie moduły są gotowe produkcyjnie):
[CORE_CASE_DESIGN.md](CORE_CASE_DESIGN.md) — pełna rodzina skrzyń, kotwy okuć,
zachowanie ręcznej pracy i TDD. Pierwszy przyrost: ROC-43; plan nadrzędny: ROC-6.

ROC-43: [specyfikacja testów i instrukcja uruchomienia](ROC43_TDD.md).
Zwykły harness uruchamia `core-design` w trybie `all`: zamrożone wymagania
generatora oraz testy obliczeń układu i niezależnego weryfikatora oczekiwań.
Historyczna nazwa `--mode red` oznacza teraz ten sam zestaw TDD po implementacji;
wynik musi być PASS, a każdy regres zwraca kod niezerowy.
Nie zastępuj błędów skip/expectedFailure ani nie przedstawiaj testów offline
jako dowodu działania CAD. Osobno sprawdzaj zapis, ponowne otwarcie i pomiar ICS.

Nowy przepływ `mcp/core_service.py` korzysta z tej samej bazy co UI. Wersjonuje
żądanie, przypina plan do wersji karty i układu oraz SHA źródła. Dziennik operacji
uniemożliwia ponowny montaż po niejednoznacznym błędzie; odzyskiwanie weryfikuje
zapisany raport przed rejestracją snapshotu. Prototyp generuje bryły zastępcze,
nie zatwierdzone okucia katalogowe. Nie promuje manifestu Epson ani gotowości
produkcyjnej. Szczegóły: [CORE_RUNTIME.md](CORE_RUNTIME.md).

## Źródło i środowisko

Źródłem kodu jest checkout `rockpro-cad`. Sąsiedni `../Integracja/rockpro_cad` to lokalne wdrożenie autora, z własnym venv, bazą, manifestem i rewizjami. Zmiany wdrożeniowe należy najpierw zachować w Git; baz i konfiguracji nie kopiujemy między checkoutami. Nowa kompilacja nie przeładowuje DLL w otwartym IronCAD.

Windows x64, IronCAD 2027 / 29.0 i lokalny ICAPI SDK. C# używa kompilatora .NET Framework z Build.ps1 oraz WinForms, System.Drawing, System.Web.Extensions i interop dostawcy. Nie stosujemy automatycznie zaleceń C# 14/ASP.NET. Python u autora: 3.14.3; backend bez CAD używa stdlib, operacje natywne comtypes i przypiętego python-ironcad z requirements.txt. Inne wersje hosta wymagają osobnej próby.

## Granice modułów

| Obszar | Pliki | Kontrakt |
| --- | --- | --- |
| Rejestracja | addin/RockProAddin.cs, Install-User.ps1 | Stały GUID/ProgID, per-user HKCU; osobny test autostartu |
| Interfejs | addin/RockProPanel.cs, LayoutForm.cs | UI → MCP stdio; aktualizacje na wątku formularza |
| Protokół | mcp/server.py, worker.py | Jawne narzędzia i argumenty; stdout JSON; brak arbitrary exec |
| Dane | mcp/project_store.py, layout.py | Jedna SQLite, karta i układ projektu; statusy ręczne |
| Obliczenia | mcp/layout.py | mm; obrysy, przegrody, komora; minimum objętości 18 wariantów |
| CAD | worker.py, Integracja/ironcad_adapter.py | Znany szkielet, sześć RP_*, zmiany wyłącznie na kopii |
| Walidacja | Integracja/review_skeleton*.py | Pomiary geometrii po zmianie i ponownym otwarciu |

Ścieżki addin/ i mcp/ powyżej są względem Integracja/rockpro_cad. Bieżące narzędzia MCP odczytuj przez tools/list, nie z liczby wpisanej w starym raporcie. Aktualny zakres i ograniczenia modelu są w LAYOUT.md. Kontrakt sceny zawiera RP_Length, RP_Depth, RP_BaseHeight, RP_LidHeight, RP_Thickness, RP_DisplayGap. Wartości narzędzi są w mm, wartości natywnego API przeliczamy na metry, gdy API tego wymaga.

## Instrukcje, prompty i skille

- AGENTS.md: krótkie reguły repozytorium i routing skilli.
- .github/copilot-instructions.md: wejście dla Copilota; .github/instructions/*.instructions.md: reguły z applyTo dla właściwych plików.
- .github/prompts/*.prompt.md: jawnie uruchamiane zadania. W obsługującym je edytorze wybierz prompt; w innym kliencie załącz plik lub wklej jego treść.
- .agents/skills/rockpro-scope-check: ocena zakresu i konkretny prompt powrotu do jakości.
- .agents/skills/rockpro-verification: dobór dowodów i komend.
- .agents/skills/bug-reproduction-brief: pobrany upstream, tylko do zleconego briefu diagnostycznego. Pełna naprawa nie kończy się na briefie.

Skille są repozytoryjne: otwieraj Codex w katalogu checkoutu. Przy pracy z katalogu nadrzędnego odczytuj je bezpośrednio według AGENTS.md workspace. Instalacja nie dodaje działającego w tle agenta do IronCAD i nie gwarantuje, że model zawsze rozpozna problem; wykonawcze sprawdzenia zapewnia harness.

## Sprawdzanie

Po zwykłym Setup.ps1:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1 -WithAddinBuild -WithUiChecks
```

Jeśli checkout nie ma venv, podaj istniejący Python bez uruchamiania instalatora:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1 -Python '..\Integracja\.venv\Scripts\python.exe' -WithAddinBuild -WithUiChecks
```

Harness nie rejestruje dodatku, nie uruchamia CAD i nie zmienia modeli. Uruchamia unittest MCP/SQLite/układu i QA, audyt struktury, a opcjonalnie kompilację DLL i C# LayoutUiChecks. Ostatnia opcja tworzy chwilowy formularz testowy poza IronCAD. Raporty trafiają do ignorowanego artifacts/verification/. Nie utrzymujemy sztywnej liczby testów jako kryterium; liczy się powodzenie odkrytego zestawu.

Test natywny wykonuje jeden aktor: zapisane dane użytkownika → znany plik źródłowy → odczyt → zmiana na kopii → pomiar → zapis i ponowne otwarcie → kontrola niezmienności oryginału, historii i SQLite. Nie wykonuj live_test.py --change jako zwykłego testu: zmienia kopię i otwiera dokumenty hosta. UI, autostart oraz geometrię raportuj oddzielnie od testów bez CAD.

## Utrzymanie i wydanie

Nie mieszaj dużego refaktoru i nowych możliwości bez rozdzielenia rezultatów i dowodów. Nie przeformatowuj całego MVP przy drobnym fixie. Przy powtarzającym się problemie najpierw odtwórz objaw i napraw przyczynę, potem wróć do funkcji. Konkretna forma checkpointu jest w skillu scope-check.

Instrukcje procesu nie zastępują jawnego zlecenia użytkownika. Nie wymagamy dodatkowej zgody na odwracalne, autoryzowane zmiany. Przy publikacji, zmianie środowiska lub danych stosuj rzeczywiste uprawnienia zadania. Kopie binarne wdrażaj dopiero po testach, z zachowaniem poprzedniej wersji i zamkniętym hostem. Samo opublikowanie kodu na Git nie dowodzi instalacji u Kuby.

Zmiany instrukcji aktualizuj razem z kontraktem, który zmieniają. Źródła zewnętrzne i decyzje adopcji: docs/AI_SOURCES.md. Stan audytu i pozostałe braki: docs/REPOSITORY_AUDIT.md.

Kontrakt wersjonowania układu, konfliktów i powiązania CAD: [LAYOUT_VERSIONING.md](LAYOUT_VERSIONING.md). UI i AI muszą przekazywać odczytane expected_revision; nie ponawiać konfliktu z automatycznie odświeżonym tokenem.

Karta projektu i każdy etap mają niezależne rewizje. Kontrakt aktualizacji,
historii i odbioru: [PROJECT_CONCURRENCY.md](PROJECT_CONCURRENCY.md).

## Czytnik części — etap przed montażem okuć

Pakiet `Integracja/rockpro_cad/parts` jest osobnym narzędziem tylko do odczytu,
nie nowym panelem dodatku ani uruchomionym w tle agentem. Rozdziela czysty traversal
z wstrzykiwanym adapterem, adapter natywnego ICAPI i lokalny dziennik JSONL.
Testy `parts/test_*.py` są częścią `scripts/Verify.ps1` w kroku `parts`.

Obowiązuje hierarchia zespołów i wystąpień części, nie drzewo wszystkich operacji
wewnątrz brył. Liczba węzłów/zespołów/części nie jest zakupowym BOM: połówki zamka
mogą być osobnymi wystąpieniami, a puste zespoły nie oznaczają fizycznych elementów.
Czytnik nie rozpoznaje automatycznie kodów i nie zatwierdza reguł mocowania.

Obrys ma jawny układ `part_local`: min/max API w metrach przeliczamy na mm.
Nie jest to obrys globalny po obrocie ani gwarancja wymiaru katalogowego.
Brak obrysu, niepoprawne współrzędne i brak właściwości są oznaczane w wyniku;
nie zamieniamy ich na fikcyjne zera. Materiał modelu pozostaje `material_cad_raw`.

Odczyt ma ograniczenia głębokości, liczby węzłów/prób i czasu. Limit czasu jest
kooperacyjny między wywołaniami API; pojedynczy zablokowany COM nie ma bezpiecznego
przerwania. Nie uruchamiaj równolegle modyfikacji CAD podczas zbierania inwentarza.
Natywny adapter tylko dołącza do otwartego pliku przez ROT, porównuje pełną ścieżkę,
odczytuje stan dokumentu i hash pliku przed/po. Nie uruchamia IronCAD, nie otwiera,
nie aktywuje, nie zamyka i nie zapisuje dokumentów. Hash dysku nie dowodzi zgodności
ze stanem pamięci; zapisane w raporcie flagi dokumentu są osobnym dowodem.

Surowy wynik może zawierać nazwy i dane klienta: zapisujemy go wyłącznie lokalnie,
poza śledzonymi plikami repo. Osobny logger przepuszcza tylko ograniczone metadane,
liczniki i hashe; nie zapisuje pełnych ścieżek, geometrii ani treści wyjątków.
Limit logu daje jawny znacznik ucięcia. Błąd zapisu logu nie może dawać sukcesu.
Pole modelu pozostaje null, gdy dana operacja jest deterministycznym odczytem API.

Plan routingu modeli, rozwoju dowodów i regresji:
[PARTS_CATALOG_PLAN.md](PARTS_CATALOG_PLAN.md). Nie wszystkie pola planowanego
pełnego audytu (np. rewizje SQLite i relacje zdarzeń projektu) są częścią tego loggera.

### Uruchomienie czytnika

Użyj Pythona z przygotowanego venv (patrz rozdział Sprawdzanie), z katalogu
`Integracja` tego checkoutu. Plik musi już być otwarty w IronCAD i wskazany pełną
ścieżką. Katalog raportu musi istnieć, a plik wynikowy nie może istnieć wcześniej.

```text
python -m rockpro_cad.parts --source "C:\projekty\przyklad.ics" --max-seconds 180 --output "..\artifacts\nowy-inwentarz.json"
```

Domyślne limity: głębokość 12, 10000 węzłów/prób przejścia do dzieci, 30 sekund
samego traversal. Poza tym czasem pozostają m.in. attach, hashowanie i zapis raportu.
Kody wyjścia: `0` kompletny odczyt w zadanym zakresie, `2` wynik częściowy,
`1` błąd wykonania lub integralności. `0` nie oznacza gotowego projektu produkcyjnego.
Inwentarz zapisany przez `--output` ma `operation_log_status=pending_finalization`:
finalnym potwierdzeniem jest JSON na stdout i odpowiadający mu końcowy wpis JSONL
z hashem inwentarza. Te dwa pliki nie stanowią transakcji atomowej. Nie traktuj samego
inwentarza jako dowodu ukończenia audytu. Stdout można zachować jako osobny lokalny
plik odbioru; zawiera dane klienta tak samo jak inwentarz.

Sandbox może nie widzieć rejestru COM procesu na pulpicie. Komunikat o braku otwartego
źródła nie dowodzi wtedy, że użytkownik zamknął model. Nie dodawaj fallbacku otwierania
lub uruchamiania aplikacji: sprawdź uprawnienia i kontekst uruchomienia testu.

### Odbiór pierwszej wersji 21.10.2026

- PASS: cały harness repozytorium, backendu, części, QA i harnessu; 29 testów części.
- PASS: natywny odczyt już otwartego modelu, pełna ścieżka/GUID i hash przed/po.
  403 węzły hierarchii: 113 zespołów (11 pustych) i 289 wystąpień części; 254 obrysy
  przeszły walidację liczbową. Nie jest to zatwierdzenie geometrii montażu.
- Oczekiwany wynik natywny: `partial`, exit 2. 35 obrysów jest niepoprawnych, a flaga
  Modified była true przed i po odczycie. Hash źródła był identyczny; dokumentu nie zapisano.
- PASS: niezależny przegląd Astra kodu, lokalnych raportów i JSONL; implementacja Sol.
- NOT RUN: nowe UI, nowy endpoint MCP, montaż okuć i jego geometria — nie należą do tej wersji.

Dowody lokalne: `artifacts/verification/20261021T160039766635Z/`,
`artifacts/parts-reader-native/20261021T160057Z/` i wskazany w raporcie dziennik
`artifacts/agent-runs/`. Te dane nie są publikowane w Git.
