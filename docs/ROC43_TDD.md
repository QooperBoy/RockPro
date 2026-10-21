# ROC-43 — zamrożone przypadki i pierwsze RED

> Aktualizacja po implementacji: poniższy wynik RED opisuje historyczny punkt
> startowy TDD. Generator jest już dostępny; `--mode all` musi przechodzić
> 182 testy i jest obowiązkową częścią `scripts/Verify.ps1`. Dowody i ograniczenia
> nowego prototypu opisuje [CORE_RUNTIME.md](CORE_RUNTIME.md). Testy offline nie
> zastępują ponownego otwarcia i pomiaru natywnego ICS.

To zestaw **offline**, bez uruchamiania IronCAD i bez generatora produkcyjnego.
Implementacja testów: Sol; niezależny przegląd: Astra. Zadanie nadrzędne i zakres:
[CORE_CASE_DESIGN.md](CORE_CASE_DESIGN.md). Nie stanowi odbioru ROC-19 ani ROC-34.

## Historyczny odbiór pierwszego RED — 21.10.2026

- PASS: implementacja testów Sol i niezależny przegląd Astra; blokery przeglądu poprawione.
- PASS: 9 testów GREEN (metody unittest, z dodatkowymi podprzypadkami mutacji).
- RED zgodnie z celem TDD: 173 testy kontraktu; 173 błędy asercji wskazujące brak
  produkcyjnego `plan_case`, zero errors/skips/expectedFailure, exit 1.
- PASS: niezależne porównanie wejściowej recepty z zamrożonymi oczekiwaniami
  dla 15 scenariuszy: A/B/C oraz zmiana X, Y, Z i XYZ każdego przypadku.
- PASS: pełna regresja repozytorium, backendu, części, core-design-green, QA i harnessu.
- NOT RUN: rzeczywisty montaż, manifest Epson, operacje ICS/SQLite i odbiór produkcyjny.

Lokalne dowody (niepublikowane dane uruchomień):
`artifacts/verification/20261021T202759998125Z/`,
`artifacts/roc43/root-red.json`, `artifacts/roc43/green.json`,
`artifacts/roc43-review-green.json`, `artifacts/roc43-review-red.json`.
Raporty testów zawierają SHA256 sprawdzanych źródeł. Sukces ROC-43 oznacza gotowy
zestaw TDD, a nie działający generator. Następny przyrost: kontrakt i manifest
ROC-15/42, następnie kotwy ROC-16 i narożnik w ROC-17.

## Powtarzalne uruchomienie

Z katalogu checkoutu, istniejącym Pythonem przygotowanego wdrożenia:

```powershell
& '..\Integracja\.venv\Scripts\python.exe' scripts/test_core_design.py --mode green --output artifacts/roc43/green.json
& '..\Integracja\.venv\Scripts\python.exe' scripts/test_core_design.py --mode red --output artifacts/roc43/red.json
& '..\Integracja\.venv\Scripts\python.exe' scripts/test_core_design.py --mode all --output artifacts/roc43/all.json
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Verify.ps1 -Python '..\Integracja\.venv\Scripts\python.exe'
```

GREEN obejmuje istniejące `layout.calculate_layout` oraz autotesty wyroczni.
Tryb o historycznej nazwie RED wywołuje wyłącznie `rockpro_cad.core_case.plan_case(request)`.
Brak tej funkcji daje osobny, opisany wymaganiem `AssertionError`; nie ImportError,
skip ani expectedFailure. Kod wyjścia RED/all to 1, dopóki wymagania nie przejdą.
Po implementacji zestaw RED wchodzi do zwykłej bramki jako `--mode all`. Nie używać `python -O`.
Runner wymaga niepustego zestawu bez skip/expectedFailure i zapisuje wynik każdego
testu, błędy podprzypadków, czas UTC oraz SHA256 źródeł i fixture do JSON.
Liczby testów są informacyjne, nie stanowią stałej bramki.

## Dane wejściowe i niezależne oczekiwania

[cases.json](../tests/core_design/cases.json) zawiera dokładne pola dotychczasowego
konfiguratora w `spec.layout`, wersję, rewizję, mm, osie XYZ, źródło syntetyczne
oraz osobne wartości `expected`. Dane nie pochodzą od producentów.

| Przypadek | Urządzenie mm | Orientacja / układ | Komora: side, width, depth, height | Wnętrze mm | Sklejka mm | Korpus / wieko mm |
|---|---|---|---|---|---|---|
| A | 300×220×100, 2 szt. | XYZ / X | X, 100, 300, 80 | 808×340×140 | 826×358×158 | 108 / 50 |
| B | 600×350×160, 2 szt. | YXZ / X | Y, 120, 700, 120 | 759×809×200 | 777×827×218 | 148 / 70 |
| C | 500×450×250, 2 szt. | XZY / Z | X, 150, 400, 200 | 739×440×959 | 757×458×977 | 897 / 80 |

Stałe: clearance=20, gap=10, separator=9, thickness=9 mm. `side_width` jest
wymiarem komory w osi wybranej ściany, `side_depth` w drugiej osi. Fixture
zamraża też pozycje i wymiary urządzeń, obu przegród oraz komory, aby regresja
nie ograniczała się do końcowych gabarytów. Origins akcesoriów: A [688,20,20],
B [20,669,20], C [569,20,20]. Wynikają odpowiednio z szerokości pierwotnej
komory 659/640/540 + 9 mm przegrody + 20 mm luzu. Przy przygotowaniu testów
poprawiono omyłki ręcznego rachunku pozycji A/B; oczekiwania gabarytów z planu
CORE pozostały bez zmian.

`resize_targets` zwiększa X, Y, Z osobno i razem o 40 mm. Każdy przypadek ma
zamrożone, dosłowne `resize_expectations`: zmienione ramy, kotwy, wymiary płyt
i długości profili, bez odczytu obliczeń planera. Test scala te dane z bazowym
oczekiwaniem; nie oblicza wyniku przez badaną implementację. Zmniejszenie jest
sprawdzane powrotem do bazowego rozmiaru i porównaniem z niezależną bazą.
Lokalne grupy wnętrza zachowują swoje odniesienie do komory; centralne wkładki
podążają za środkiem korpusu. Zmiana gabarytu nie układa urządzeń ponownie.

Przyszły planer otrzymuje `spec`, syntetyczny `manifest`, `template_recipe`
z [synthetic_template.json](../tests/core_design/synthetic_template.json) oraz
`scenario`. Nie otrzymuje `expected`, `resize_expectations` ani case-specific
wartości oczekiwanych. Recepta jest wejściem syntetycznego szablonu, niezależnym
od rzeczywistego manifestu Epson. Produkcja nie może czytać oczekiwań z testów
ani rozpoznawać A/B/C, aby zwracać gotowe odpowiedzi.

## Inwentarz wymagań

| Etap / wymaganie | Testy w ROC-43 | Oczekiwany stan przed implementacją |
|---|---|---|
| H0 wejście | jednostki/brak źródła/NaN/inf/bool/count/orientacja/grubość/luz/schema/template/revision, zbyt mały korpus i brak miejsca na uchwyty | PASS offline |
| H1 pełny manifest syntetyczny | dokładne physical IDs, oddzielny pusty zespół, nierozstrzygnięte role, brak/duplikat grupy lub części; osobny audyt usunięcia każdej grupy A/B/C | PASS offline |
| H2 płyty i ramy | 10 płyt, stała grubość, ramy ścian i seam, stałe local bounds, własne obroty wystąpień | PASS offline |
| H2 profile | dwa bazowe profile, pionowe krawędzie oraz osobne połowy x/y profili zamykających korpusu i wieka; zmienna długość i stały przekrój | PASS offline |
| H2 okucia | narożniki dół/góra, dwa rodzaje wzmocnień, zwykły uchwyt ścienny i osobny uchwyt narożny, zamki/przednia ściana, zawiasy/tylna, koła/podkłady/gniazda | PASS offline |
| H2 wnętrze | urządzenia, przegrody, akcesoria, pianka, własna część i import; jawne lokalne zakresy oraz syntetyczne zgody | PASS offline |
| H2 symetria | jedna sztuka, para, wzór 3/4; równe odsadzenia, wysokość, środek, X/Y/Z i roundtrip, zamknięte parowanie góra/dół i wheel/socket | PASS offline |
| H2 prezentacja | display_gap=60 nie zmienia fizycznych pozycji, brył, wysokości ani parowania | PASS offline |
| H3 praca ręczna | przesunięcie pojedynczego członka/usunięcie/dodanie bez kotwy i konflikt UI–AI blokują zmiany; zatwierdzona decyzja grupy oraz dodatek C z kotwą przetrwają resize | PASS offline |
| H4 wykonanie ICS/SQLite | jeden writer, idempotencja, timeout, awaria/recovery, fingerprinty i powiązanie snapshot | NOT RUN — dalszy zakres ROC-20/22/40 |
| H5 natywny odbiór | pomiar API, zapis i otwarcie ICS, natywna tabela parametrów, źródło/snapshot/SQLite, ocena konstruktora A/B/C | NOT RUN — ROC-19/34 |
| H6 AI | routing, injection, limity i false PASS | NOT RUN — ROC-26 |

Każda z grup ma stabilne ID, datum, osie, tryb, zakres i członków. Zwykły uchwyt
jest wycentrowany na ścianie. Specjalny **syntetyczny** uchwyt narożny wymaga
oddzielnej jawnej zgody funkcjonalnej; brak zgody jest negatywnym testem.
Nie uznajemy dowolnego punktu pojedynczej części za automatycznie poprawny
środek ściany. Nie przypisujemy tych reguł do niezatwierdzonego H2026.
Układy wnętrza w dotychczasowym konfiguratorze nie są globalnie symetryczne;
mają osobne, jawne zakresy lokalnych komór i syntetyczną zgodę konstruktora.

Testy count=2/3/4 używają odpowiednio kotew [100,W−100],
[100,W/2,W−100], [100,260,W−260,W−100]. Dla syntetycznego uchwytu szerokości
150 mm minimalny odstęp wynosi 10 mm. Fixture ma osobny test tych odstępów;
zbyt duża liczność ma dać odmowę, a nie zbieżne/kolizyjne kotwy.

## Wyrocznia i granice dowodu

[oracle.py](../tests/core_design/oracle.py) sprawdza bezwzględne wymiary,
zatwierdzone lokalne kotwy i ramy, a dopiero potem symetrię. Para przesunięta
symetrycznie do błędnego odsunięcia nie przechodzi. Osobny obrót każdego
wystąpienia musi być ortonormalny o det=+1, mieć właściwą orientację i zachować
bryłę sztywną. Górne narożniki mają odwróconą normalną przez poprawny obrót
180°, bez odbicia i ujemnego skalowania.

Każda syntetyczna część ma `shape`, jawne wycentrowane `local_bounds` i
zatwierdzony punkt montażowy w tej syntetycznej definicji. Ośrodki realnych
okuć nie muszą pokrywać się z tym punktem. Wyrocznia niezależnie transformuje
osiem naroży lokalnych bounds do ramy zamkniętej. Zamrożone skrajne wartości
transportowe tych **syntetycznych brył** to [−15,−30,−60] do [W+30,D+15,H+15],
czyli rozmiar [W+45,D+45,H+75]. Nie są obrysem katalogowym części rzeczywistych.

Autotesty wyroczni celowo usuwają części i grupy, zmieniają kotwy, ramy,
wymiary i obroty każdej grupy; sprawdzają także det=−1, poprawny lecz błędny
obrót, brak zgody, puste grupy, duplikaty i rozparowanie. Funkcja `specimen`
kopiuje oczekiwania wyłącznie jako materiał do tych autotestów lub jako jawny
wejściowy odczyt do testu audytu. Nigdy nie jest odpowiedzią badanej funkcji.
GREEN autotestów dowodzi wykrywania mutacji, a nie istnienia planera.

Serializacja/ponowny odczyt JSON w testach roundtrip dotyczy wyłącznie planu.
Nie jest zapisem ani ponownym otwarciem ICS. Żaden test tego pakietu nie
kontaktuje się z CAD, nie modyfikuje źródła ani wdrożenia. Brak testu kolizji
brył, nośności, technologii, wycięć i styków pozostaje jawnym ograniczeniem;
AABB nie jest dowodem braku kolizji. Rzeczywista kompletność Epson nadal
wymaga ROC-42 oraz decyzji dla nieznanych/importowanych elementów.
