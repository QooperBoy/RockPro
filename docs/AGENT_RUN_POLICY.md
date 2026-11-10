# ROC-26 — ograniczona bramka propozycji AI

Nowe wejście MCP agent_server.py udostępnia tylko statyczną allowlistę odczytu,
obliczeń i propozycji. Nie oferuje set_stage, zapisów projektu/układu/katalogu,
importu Excel, wykonania CAD ani odzyskiwania. Bezpośrednia próba ich wywołania
również jest odrzucana. Nie ma arbitralnego shell/exec ani zatwierdzania produkcji.

server.py pozostaje wspólnym lokalnym backendem operatora używanym przez DLL.
configure.py wskazuje agent_server.py w konfiguracji MCP dla AI przy przyszłym
konfigurowaniu. Nie uruchamiano configure.py w istniejącym wdrożeniu: jego
pozostałe czynności ustawiają demo, którego nie wolno podstawić za prywatny projekt.
Istniejące mcp-config.local.json przepięto wyłącznie z server.py na
agent_server.py po sprawdzeniu oczekiwanej ścieżki; oryginał zachowano w prywatnym
artifacts/overnight-20261024/mcp-config-before-proposal-gate.json. Nie zmieniono
konfiguracji projektu ani demo. Aktywne klienty muszą odświeżyć proces/listę narzędzi. Jest to rozdział zakresów interfejsu, nie uwierzytelnianie OS.

## Polityka przebiegu

Wersjonowana Policy v1: max_tool_calls=30, max_seconds=120, max_retries=2,
prompt_version=proposal-only-v2. Sesja ma UUID i hash polityki. Argumenty są
sprawdzane względem schematów znanych narzędzi, z ograniczeniem rozmiaru i głębokości.
Nieznane narzędzie, błędne jednostki lub instrukcja ukryta w referencji dokumentu
nie zwiększają uprawnień. Błędna próba zużywa budżet wywołań.

Limit czasu jest kooperacyjny: wywołanie kończy się znanym wynikiem; kolejne
są odrzucane. Nie zabija się workera ani IronCAD w trakcie pracy. Plik
<run_id>.stop w katalogu logów blokuje następne wywołanie. Powtórzenia tego
samego błędnego narzędzia/argumentów są ograniczone; nie ma samoczynnych ponowień.

## Obserwowalność i granice

Metadane w artifacts/agent-runs: run_id, polityka, narzędzie, hash argumentów,
status wykonania narzędzia, zmierzony duration_ms, liczba wywołań i kod błędu.
Nie zapisuje się treści źródeł, argumentów, wyników, haseł ani treści e-maili.
model, reasoning_effort, tokens i cost pozostają null z usage_status=unavailable.
Nie są zamieniane na zero. Status passed oznacza zakończenie narzędzia, nie
odbiór geometrii ani zgody. W odpowiedzi narzędzia pozostają właściwe blokady.

Nie uruchomiono jeszcze rzeczywistego zewnętrznego modelu w produkcyjnym pilotażu.
Koszt modelu, fałszywe zatwierdzenia pełnego agenta oraz jakość end-to-end H0–H6
pozostają NOT RUN. Ta bramka nie oznacza zamknięcia całego ROC-26. Nie ma potrzeby
fine-tuningu ani automatycznego zmieniania reguł na podstawie logów.

PASS: siedem testów — odmowa zapisów/zgód, tekst prompt injection jako dane,
limity wywołań, stop, czas bez zabijania pracy, błędne argumenty/ponowienia,
zmierzony czas przy nieznanym koszcie oraz rzeczywisty handshake stdio i odmowa
execute_case_plan. Model testu jest deterministycznym klientem, nie ukrytym LLM.

Pełny harness: PASS, artifacts/verification/20261024T215341335976Z/results.json.


## 25.10 — źródłowe propozycje współdzielone z UI

Statyczna allowlista zawiera teraz także list_device_records,
preview_catalog_layouts i preview_bound_device_layout. Agent odczytuje jednostki,
status i konkretną wersję katalogu, oblicza do trzech wariantów oraz sprawdza
zmieniony wariant tym samym kodem co formularz konstruktora. Wersja wyświetlona
w katalogu jest przypinana przez expected_device_revision; zmiana danych daje
odmowę, a nie podmianę wymiarów w tle.

Zapisy source-bound layoutu, odłączenie źródła, pomiar SDK, decyzje uchwytów,
zmiany wymiarów CAD, akceptacje i odzyskiwanie pozostają niedostępne AI.
Lista nie jest budowana z podobieństwa nazw ani rozszerzana automatycznie
przez dodanie narzędzia do operatorowego server.py.

Hash polityki obejmuje teraz hash rzeczywiście udostępnionych schematów.
Log zawiera toolset_sha256 i policy_sha256. Pozwala to odróżnić przebiegi
z innymi uprawnieniami mimo identycznych limitów liczbowych. Nie zapisuje
argumentów ani treści katalogu. Brak kosztu modelu nadal oznacza null.

PASS: osiem testów bramki, w tym prawdziwy dispatcher z izolowaną SQLite,
wybór → propozycje → sprawdzenie, odmowa starego źródła i identyczny SHA pliku
bazy przed/po propozycjach. Rzeczywisty stdio potwierdza widoczność nowych
odczytów i odmowę wykonania CAD. Pełny harness PASS:
artifacts/verification/20261025T084149875582Z/results.json.
Nie uruchomiono zewnętrznego modelu ani pilotażu klienta; test nie oznacza
ukończenia H0–H6 ani całego ROC-26. Aktywne klienty MCP wymagają odświeżenia
procesu/listy narzędzi; ich połączeń nie przeładowano automatycznie.
