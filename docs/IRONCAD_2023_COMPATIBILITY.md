# IronCAD 2023 — zgodność RockPro i przekazywanie modeli

26.10.2026: użytkownik potwierdził, że Tomasz i firma pracują na IronCAD 2023.
Dotychczasowy host developerski i natywne testy RockPro dotyczą 2027.
Zgodność z 2023 jest wymaganiem odbiorcy, ale nie została jeszcze wdrożona
ani potwierdzona testem. Nie wysyłać ICS zapisanych w 2027 jako plików dla 2023.

## Format modeli

Producent jednoznacznie podaje, że zapis 2027 nie otwiera się w starszych
wersjach. Nie ma zapisu natywnego modelu 3D do wcześniejszej wersji ICS.
Eksport STEP, Parasolid lub ACIS pozwala przekazać bryły, ale traci historię
modelowania. Nie zachowa naszego parametrycznego szkieletu, wyrażeń i relacji
obróbek jako natywnego szablonu. Dobór wersji formatu i rzeczywisty import
trzeba sprawdzić w 2023; powtórny import w 2027 nie jest takim testem.

Źródła sprawdzone 26.10.2026:

- [Informacje producenta o 2027](https://www.ironcad.com/support/readme/2027/Readme.htm).
- [Baza wsparcia IronCAD Japan: brak zapisu wstecz i utrata historii przy eksporcie](https://techbase.ironcad.jp/portal/en/kb/articles/opening-data-created-in-a-newer-version-of-ironcad).

## API i Python

IronCAD 2023 ma ICAPI i obsługuje dodatki. Producent wskazuje środowisko
Visual Studio 2019 / toolset v142. Python/MCP, obliczenia, SQLite i obserwator
działają poza hostem CAD; ich architektura nie wymaga roku 2027. Warstwa
wykonująca operacje CAD musi natomiast być przygotowana i przetestowana
z SDK oraz bibliotekami 2023. Nie ma jeszcze dowodu, że wszystkie użyte przez
RockPro metody/interfejsy i zachowania są identyczne.

- [API w dokumentacji 2023](https://www.ironcad.com/support/2023/IRONCAD_Help/Content/Understanding_the_Basics/Using_the_API.htm).
- [Środowisko developerskie 2023](https://www.ironcad.com/support/readme/2023/Readme.htm).
- [Oficjalny python-ironcad](https://github.com/IronCAD/python-ironcad): domyślnie wybiera najnowszą zainstalowaną wersję; README wymienia również ograniczenia niektórych VARIANT.

## Konkretne przeszkody w obecnym kodzie

1. `addin/Build.ps1` kompiluje z interop z katalogu 2027.
2. `addin/Install-User.ps1` deklaruje minimum `29..` i zapisuje ustawienia
   dla `IRONCAD 29.0`; `Repair-IcApi.py` wyszukuje wyłącznie 29.0.
3. `scripts/run_t1_machining_job.py` używa SDK 2027 i lokalnego mostu
   zweryfikowanego tylko z tym hostem. Potrzebny build/test dla 2023.
4. Przypięty python-ironcad (commit `85644fad891e428e32617e1063687e44dad15274`)
   w `core.py` i instalatorze iteruje `range(35, 25, -1)`.
   Pętla wyklucza 25, czyli IronCAD 2023. Nie wykryje samodzielnej instalacji
   2023. To konkretny problem wykrywania; zmiana dolnej granicy nie dowodzi
   jeszcze zgodności całego API.
5. Generowanie metadanych COM i `GetActiveObject("IronCAD.Application")`
   wymagają kontroli docelowej wersji/procesu przy instalacjach równoległych.
   Osobny venv sam nie izoluje rejestracji COM systemu.
6. Modele, eksportowane zasoby i szablony zapisane przez 2027 nie staną się
   natywnie zgodne z 2023 po samej zmianie kodu. Trzeba użyć zachowanych
   oryginałów otwieralnych w 2023 i odtworzyć przyrosty w tej wersji.

[Kod przypiętej biblioteki](https://github.com/IronCAD/python-ironcad/blob/85644fad891e428e32617e1063687e44dad15274/python_ironcad/core.py).
[Mapowanie roku 2023 na wersję 25.0 w bazie wsparcia](https://techbase.ironcad.jp/portal/en/kb/articles/ironcad-displays-in-english-after-installation).

## Zalecana kolejność

1. Ustalić dokładny build 2023 u Tomasza (PU/SP) i przygotować legalnie
   aktywowane stanowisko 2023 z SDK. Lokalnie znaleziono tylko katalog 2027;
   natywnego testu 2023 nie wykonano.
2. Oddzielić wybór SDK, hosta, rejestracji i bibliotek od kodu funkcji.
   Zbudować dodatek dla 2023 i jawnie wybierać właściwy proces.
   Nie obniżać samej deklaracji zgodności do 25 jako pozornej naprawy.
3. Test na kopii: start dodatku, Python/MCP, odczyt, zmiana parametrów,
   profile, kopiowanie pełnych szkiców wycięć, pomiar, zapis/otwarcie i SQLite.
4. Odtworzyć T1 na oryginalnych zasobach zgodnych z 2023 i sprawdzić plik
   na docelowym stanowisku. Następnie kontynuować parametryzację T2.
5. Przyjąć 2023 jako proponowaną bazę natywnych wydań dla tego odbiorcy;
   zgodność tego samego kodu z 2027 utrzymywać jako oddzielnie sprawdzany cel.
   Dla szybkiego obejrzenia istniejących wyników użyć neutralnego eksportu,
   jasno oznaczonego jako geometria bez parametrów.

Stan: dokumentacja i przegląd kodu PASS; eksport/import w 2023, kompilacja
z SDK 2023, autostart 2023 i natywne operacje RockPro 2023 NOT RUN.
Ta analiza nie zmieniała instalacji, rejestru, modeli ani aktywnego hosta.
