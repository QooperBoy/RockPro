# RockPro — przekazanie po nocnej kolejce, 25.10.2026

Wykonano dostępne przyrosty kodu i interfejsu na tym stanowisku. **Wszystkie
zadania Linear nie są ukończone.** Pozostałe odbiory wymagają działającego CAD,
potwierdzonych danych konstrukcyjnych/technologicznych albo udziału RockPro.
Nie oznaczono tych braków jako PASS i nie wysłano zamówień ani wiadomości.

Stan źródeł: gałąź `codex/roc42-catalog-continuation`, implementacja do
`cfe9d67`. Historia od początkowego `4bd25ec` zawiera osobne lokalne commity
sprawdzonych przyrostów. Push odłożony zgodnie z poleceniem użytkownika.
Nowa DLL została skompilowana, **nie została zarejestrowana ani załadowana**.
Zachowane wdrożenie obok repozytorium, oryginały CAD i baza klienta są chronione.
Automatyzację `rockpro-nocna-realizacja-kolejki` wstrzymano (`PAUSED`), zgodnie
z poleceniem użytkownika, po opisaniu pozostałych blokerów. Nie będzie ponawiać
tych samych prób co pół godziny; projekt pozostaje otwarty do wznowienia.

## Co wykonano

| Zadania | Zmiana dostępna w źródle | Dowód i granica |
|---|---|---|
| ROC-18 | Wersjonowany import/eksport Excel, jednostki, CAS i idempotencja | `b8b5590`; [kontrakt](EXCEL_CONFIGURATION_INPUT.md). Done zapisane w Linear wcześniej. |
| ROC-21 | Pakiet plików przypięty do jednej rewizji; odmowa obcego ICS i brakujących kontroli | `f39dd3e`, `a742ed4`; [pakiety](REVISION_RELEASE_BUNDLE.md). Rzeczywisty pakiet nadal draft. |
| ROC-23 | Katalog urządzeń z jednostkami, źródłami, wariantami, brakami i konfliktami | `39c8479`; Done zapisane w Linear wcześniej. Nie wysyłano zapytań do dostawców. |
| ROC-24 | Jawne filtry/ranking rodzin i evaluator oznaczonego benchmarku | `ccdf9b8`; [rekomendacje](FAMILY_RECOMMENDATIONS.md). Trafność na rzeczywistej historii niezmierzona. |
| ROC-25 | Do trzech propozycji układu, wybór w WinForms, chronione wymiary katalogowe, powiązanie źródła z rewizją układu | `f6ceabb`, `025ddaf`, `a49fde7`; [układy](DEVICE_LAYOUT_VARIANTS.md). Natywne wnętrze/pianki nieodebrane. |
| ROC-26 | Osobna ograniczona bramka AI, limity czasu/wywołań, hash schematów polityki, tylko odczyt/propozycje | `1d15358`, `8e9885c`; [polityka](AGENT_RUN_POLICY.md). Brak zewnętrznego pilotażu, rzeczywistych kosztów/tokenów i zgód AI. |
| ROC-20/22 | Zachowanie własnych kopii po błędzie zapisu; naprawione powroty async na wątek WinForms w oknach odzyskiwania, decyzji i głównym panelu | `6347907`, `9232d31`, `09e1d43`, `37171d6`. Błędy odtworzono przed naprawą; brak ponawiania CAD po niepewnym wyniku. |
| ROC-27 | Audyt lokalnych możliwości PLAN i zapis braków technologii | `6fef934`; [audyt](MATERIAL_INTEGRATION_AUDIT.md). Lokalnego PLAN nie znaleziono. |
| ROC-28/29/30 | Macierz braków historycznych; niezmienny import BOM, agregacja, referencyjny rozkrój i niezależny checker | `988fa6d`; [BOM](CUTTING_BOM_IMPORT.md), [rozkrój](CUTTING_PLAN_CONTRACT.md). Testy technologii syntetycznej, brak zatwierdzenia maszyny. |
| ROC-31 | Magazyn, partie/resztki, rezerwacje, wydania, zwroty i dostawy; podgląd i osiem jawnych akcji operatora | `79627c1`, `bb8dbf5`–`e1f65e1`; [kontrakt](INVENTORY_CONTRACT.md). Jedna SQLite, trwałe żądania, CAS, odzyskanie tego samego ID po utracie odpowiedzi. Nie wpisano fikcyjnego zapasu klienta. |
| ROC-32 | Propozycje zakupów: bilans terminowy, paczki/MOQ, pełny wydatek, brakujące oferty, limity i eksport szkicu | `08a528e`, `c2a6abb`, `e271977`; [zakupy](PURCHASE_PROPOSALS.md). Potwierdzone 75/100 z przykładu zadania, brak automatycznego zamawiania. |
| ROC-33 | Niezmienne plany i historia wykonania, aktualność plików, wersje/porównanie w WinForms oraz eksport dowodów | `557b221`, `cfe9d67`; [wersje](MATERIAL_PLAN_REVISIONS.md). 4 wykonane / 3 kandydatów / 1 pozostała, zachowane 123 PLN na danych testowych; koszt zmiany nieznany bez wyceny. |
| ROC-37 | Procedura utrzymania i rzeczywiste odtworzenie izolowanego snapshotu | `0f757d7`; [utrzymanie](OPERATIONS_AND_OWNERSHIP.md). Odtworzono 268 plików, historię i spójną SQLite; imienna odpowiedzialność/koszty nieuzgodnione. |
| ROC-40 | Trwałe decyzje/odsadzenia H7159, okno konstruktora, odczyt SDK i kontrola świeżości przed zapisem decyzji | `6a21194`, `dc00210`; [ręczne zmiany](NATIVE_MANUAL_CHANGES.md). Starszy natywny offset 12 mm PASS; nowszy pomiar z okna NOT RUN. Pełny guard innych rodzin nadal otwarty. |

Panel obserwacji i wspólny rejestr etapów powstały wcześniej:
[RELIABILITY_AND_OBSERVER.md](RELIABILITY_AND_OBSERVER.md).
Rejestr synchronizuje górne gniazda z kołami w etapie 6. Podgląd jest narzędziem
analizy procesu; nie zastępuje pomiaru CAD. Czasy zagnieżdżone nie sumują się
do czasu procesu. Nie ma jeszcze zatwierdzonego baseline pracy konstruktora
ani porównania kosztu z rzeczywistym zewnętrznym agentem.

## Testy i bezpieczny punkt powrotu

Ostatni kompletny przebieg:
`artifacts/verification/20261025T133758293539Z/results.json`:
repository, backend, parts, core-design, core-contracts, QA, harness,
kompilacja DLL, kompilacja C# QA i formularze **PASS**; native IronCAD **NOT RUN**.
Polecenie: `scripts/Verify.ps1 -WithAddinBuild -WithUiChecks`.
Nowe ekrany magazynu/zakupów/planów sprawdzono osobno z backendem testowym
PL/EN przy 100/150 i obejrzano zrzuty; serwisy Python używają izolowanych baz.
Makieta formularza nie jest dowodem działania w hoście.

Dowody ekranów: `artifacts/inventory-ui-20261025/`,
`artifacts/inventory-command-ui-20261025/`, `artifacts/purchase-ui-20261025/`,
`artifacts/material-plan-ui-20261025/`. Szczegółowe przyrosty i poprzednie
przebiegi: [OVERNIGHT_PROGRESS.md](OVERNIGHT_PROGRESS.md).

Snapshot sprzed nocy w nadrzędnym workspace:
`workspace/snapshoty/przed-nocna-kolejka-20261024-232012`.
Zawiera bundle Git, ZIP źródeł/projektów i spójny backup SQLite.
Próba odtworzenia PASS:
`artifacts/overnight-20261024/restore-exercise/restore_verification.json`.
Nie nadpisywano snapshotu. Bieżące zmiany kodu zachowuje lokalny Git;
do wznowienia użyć aktualnej gałęzi, nie przywracać starego snapshotu na nią.
Osobny końcowy bundle samej śledzonej historii kodu i kwit jego kontroli:
`artifacts/overnight-20261024/available-queue-handoff-20261025/`.
Nie jest nowym backupem projektów CAD ani bazy klienta.

## Co blokuje dalsze zamykanie zadań

| Zadania | Konkretny brak | Co odblokowuje dalszą pracę |
|---|---|---|
| Aktualizacja wszystkich nowych dowodów w Linear | Konektor nadal widzi wyłącznie MOD/Modivo, `hasNextPage=false`; brak narzędzia zalogowanej przeglądarki Rock_Pro | Połączenie z właściwym workspace lub przywrócone narzędzie istniejącej sesji. Nie zmieniano zadań Modivo. |
| ROC-16/17/19/20/22/25/40 i nowe UI | IronCAD PID 20328 nie odpowiada, brak dostępnego COM; pierwsza próba pomiaru zatrzymana przed otwarciem dokumentu | Rozpoznanie/zamknięcie zawieszonego startu bez utraty niezapisanej pracy, jeden działający host, bezpieczne przeładowanie DLL i osobny test na nowych kopiach. Bez drugiej instancji i ponownej rejestracji w ciemno. |
| ROC-42/16/17/19 | Niepotwierdzone role Część2648/importu, SKU/nośność kół i zatwierdzenie pełnej rodziny, w tym H2026 | Rozstrzygnięcia konstruktora i właściwe dane katalogowe. 403 węzły źródła oraz 66 korzeni prototypu to różne zbiory; nie zamieniać ich na jeden rzekomo odebrany manifest. |
| ROC-19/34/40 | Pełne natywne A/B/C, w tym ręczny dodatek z kotwą, i odbiór rzeczywistych rodzin | Działający host + zatwierdzony szablon + konstruktor. Test zastępczych brył i wąski H7159 nie zamykają całości. |
| ROC-21/29/30 | Brak zatwierdzonego technologicznego BOM, rysunków/wycięć/styków i docelowego profilu importu | Dane technologiczne i potwierdzona ścieżka PLAN/produkcji. Obrys okucia nie jest szablonem wycięcia. |
| ROC-27/30 | Brak lokalnego PLAN, wiedzy o licencji/modułach i rzeczywistych parametrach piły/CNC | Próba na stanowisku RockPro: 3 zlecenia + resztka, rzaz/marginesy/grain i decyzja integracyjna. |
| ROC-28/24 | Brak pięciu kompletnych zakończonych wielosztukowych zleceń i oznaczonego benchmarku rodzin | Wskazane zestawy BOM, rozkrojów, kosztów, cen/transportu i etykiet. Pięć kart w SQLite nie spełnia kryterium. |
| ROC-31/32/33/36 | Brak rzeczywistych stanów/ofert, limitów gotówki/zapasu, jakości reuse i pilotażu | Magazyn/zakupy/produkcja przekazują dane i oceniają wyniki. Koszt delta pozostaje `null`; fizyczne zużycie/zamówienia zachowane. |
| ROC-26/35 | Brak nadzorowanego pilotażu AI i uzgodnionych progów/baseline | Wybrane przypadki, koszt/czas korekt i ocena człowieka; nie nadawać AI prawa akceptacji. |
| ROC-34/37/38 | Brak odbioru Tomasza/produkcji, właścicieli/licencji/kosztów i jawnego OK użytkownika | Sesja odbioru; ROC-38 Done dopiero po OK. Autoryzacja nocnej pracy nie zastępuje odbioru. |
| ROC-39 | Zadanie po MVP: brak wskazanej próbki 10–20 projektów/maili i dostępu do stanowiska RockPro | Najpierw odbiór MVP, wskazanie próbki/zakresu źródeł i pilot na kopii. Nie importować całego prywatnego archiwum z domysłu. |
| ROC-41 | Brak zatwierdzonych szablonów wycięć, technologii i dodatnich/ujemnych przykładów konstruktora | Dostarczenie właściwych szablonów i reguł styków przed dokumentacją produkcyjną. |
| ROC-44 | Brak pomiaru rzeczywistych osi obu sworzni i potwierdzonego tworzenia SmartMotion | Pomiar na kopii + próba SDK. Środek obrysu nie jest osią zawiasu. |

Źródłem kolejki są zachowane rzeczywiste opisy Linear z nocy, nie nowe odczyty
Rock_Pro. ROC-15/43 były Done wcześniej; ROC-18/23 zamknięto po dowodach.
ROC-1–4 są onboardingiem Linear, ROC-5–10 epikami. ROC-11–14 przywoływane
w zależnościach nie występują w zachowanej liście; ich bieżącego statusu
nie potwierdzono. Nie odtwarzać tytułów ani kryteriów z domysłów.

## Wznowienie

Najpierw przywrócić dostęp Rock_Pro i działający pojedynczy host, następnie
zaktualizować zadania **dowodami i ograniczeniami**, bez masowego Done.
Przeładować sprawdzoną DLL przy bezpiecznie zamkniętym IronCAD; wykonać test
nowego przepływu na kopii. Potem zależności konstrukcyjne ROC-42/16/17/40/19,
dokumentacja/pilot ROC-21/34 oraz materiały po otrzymaniu danych. Kontynuować
z bieżącego Git i dziennika, nie uruchamiać ukończonych operacji ponownie.

Prompt powrotu: „Wróć do RockPro na `codex/roc42-catalog-continuation`.
Przeczytaj AGENTS.md, DEVELOPMENT.md, OVERNIGHT_HANDOFF_20261025.md i końcówkę
OVERNIGHT_PROGRESS.md. Użyj lokalnych rockpro-scope-check i rockpro-verification.
Sprawdź aktualny dostęp Rock_Pro i pojedynczy host IronCAD bez uruchamiania
kolejnych instancji. Po usunięciu konkretnego blokera dokończ właściwy test na
nowej kopii i zapisz dowody; nie nadpisuj oryginałów, snapshotów ani bazy klienta.
Build, UI testowe, native i odbiór człowieka raportuj oddzielnie”.
