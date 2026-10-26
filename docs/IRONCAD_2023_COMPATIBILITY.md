# IronCAD 2023 — zgodność RockPro i przekazywanie modeli

26.10.2026: użytkownik potwierdził, że Tomasz i firma pracują na IronCAD 2023.
Dotychczasowy host developerski i natywne testy RockPro dotyczą 2027.
Warstwa uruchomieniowa 2023 jest wdrożona i przetestowana (stan poniżej).
Pełny generator T1 nadal wymaga portowania. Nie wysyłać ICS zapisanych w 2027
jako plików dla 2023.

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

## Przeszkody rozpoznane przed migracją (stan historyczny)

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

## Wdrożenie i dowody — 26.10.2026

Lokalnie działa IronCAD **25.0.0.18479**, SDK 2023 i istniejący trial.
Snapshot przed zmianą: `codex/snapshot-before-ironcad2023-20261026`.
Dowody prywatne: `artifacts/ironcad2023-compatibility/summary.json`;
rejestr przed zmianą w `registration-before/`. Oryginały nie były zapisywane.

- PASS: pełny harness, kompilacja 2023 i testy formularzy:
  `artifacts/verification/20261026T142130743032Z/results.json`.
- PASS: dodatek 2023 z osobnym GUID/ProgID, rejestracja HKCU i autostart po
  restarcie. Log pokazuje host 25.0.0.18479 i hash załadowanej DLL.
- PASS: Python łączy się przez COM z rzeczywistym hostem 25; wybór biblioteki
  jest jawny, bez wyszukiwania najnowszej instalacji ani modyfikacji pakietu pip.
- PASS: nowy model diagnostyczny, parametr sceny, wyciągnięcie 20 → 40 mm,
  pomiar, zapis ICS, ponowne otwarcie i powrót do 20 mm; `native-probe-04/`.
  Geometrię aktualizuje jawnie skrypt na podstawie parametru. Nie jest to dowód
  samoczynnego wiązania wyrażeń po edycji parametru w UI ani kompletna skrzynia.
- PASS: kompilacja wariantu dodatku dla 2027; nie instalowano go ponownie.
- NOT RUN: rzeczywiste kliknięcie przycisku panelu i MCP z panelu w 2023.
  Okno główne jest poza obszarem przechwytywania monitora; nie zastępuj tej
  kontroli samym logiem InitSelf. Stdio MCP sprawdzono testem backendu.

### Uruchamianie

`Build.ps1`, `Install-User.ps1`, `Setup.ps1` i `scripts/Verify.ps1` przyjmują
`-IronCADYear 2023` lub `2027`; domyślnie 2023. Nie uruchamiaj Setup do migracji
istniejącej bazy — konfiguracja demo pozostaje odrębną operacją.
Python używa `ROCKPRO_IRONCAD_YEAR` (domyślnie 2023); dodatek przekazuje swój rok
workerom. Proces Pythona nie może przełączyć już załadowanej biblioteki.
Nieaktualny dodatek 2027 nie przekazuje roku: przed jego dalszym użyciem trzeba
zbudować/rejestrować wariant 2027 albo jawnie ustawić rok procesu.

Instalator odmawia działania przy otwartym IronCAD i sprawdza SHA DLL oraz
manifest docelowej wersji. Metadane ICAPI są rejestrowane dla użytkownika;
`OAPERUSERTLIBREG` działa tylko w procesie instalatora. Dwie instalacje CAD nie
izolują wspólnych wpisów COM: zmianę docelowego hosta wykonuj przy zamkniętych
hostach, z kopią rejestru, a potem ponów test połączenia.

### Faktyczne blokery pełnego T1

Pierwsza kompilacja z `ICAPI/Samples/C#/References/interop.ICApiIronCAD.dll`
nie znalazła metod macierzy, wyrażeń i kolizji (`inspect-original/compile.json`).
Dalsza kontrola wykazała, że **ten przykładowy interop pochodzi z 2018 roku**,
a zainstalowany `bin/ICApiIronCAD.tlb` 2023 udostępnia te funkcje.
Nie utożsamiać błędu przykładowej biblioteki z brakiem funkcji hosta.

`scripts/native/GenerateLocalInterop.cs` używa .NET `TypeLibConverter` i
`LoadTypeLibEx(REGKIND_NONE)`: generuje osobny lokalny interop, bez zmiany
plików producenta i bez rejestracji COM. Runner T1 dla 2023 generuje go w nowym
katalogu operacji, zapisując hashe wejść i wynik konwersji. Ostrzeżenia
importera są zachowane w `interop-generation.json` (dotyczą m.in. metod
surowych wskaźników, których ten przyrost nie wywołuje).

Po dostosowaniu odczytu części do `GetBody(true).GetBoundingBox()` pełny
`T1MachiningPrototype.cs` kompiluje się z tym interopem. To PASS kompilacji,
nie dowód odtworzenia całej skrzyni. Czytnik Python korzysta ze starszego
odczytu bryły tylko gdy interfejs nie ma nowszego getteru; nie maskuje
wyjątków COM. Następna bramka: natywne wykonanie i pomiar na kopiach.

Zachowana kopia źródła T1 (SHA zaczynający się `cd15d338`) wyświetla w
buildzie 18479 komunikat o nowszej wersji pliku. Odczyt metadanych OLE wyjaśnił
przyczynę: oryginały **T1 i T2 zapisano w IronCAD 2023 PU1 SP1, build 18734**.
Nie jest to dowód zapisu tych oryginałów w 2027 ani konieczność ponownego
pozyskania plików. Potrzebna jest aktualizacja lokalnego 2023 i ponowna próba.
Kopia z Downloads ma inny SHA (`66c81733`); nie zastępuje zachowanego źródła.
Dowód: `artifacts/ironcad2023-compatibility/file-version-metadata.json`.

Następny przyrost: aktualizacja 2023 do PU1 SP1 + adapter starszego API, dopiero
potem pełna próba T1 (okucia, wycięcia, zmiana gabarytu, zapis i otwarcie).
Analizę kontraktu T2 można kontynuować niezależnie od tych blokerów.

T2: nowa kopia oryginału z T2.zip również została odrzucona przez build 18479.
Metadane potwierdzają ten sam wymagany PU1 SP1. Szczegóły w T2_REFERENCE_ANALYSIS.md.

Oficjalny [instalator 2023 PU1 SP1](https://www.ironcad.com/product-update/2023pu1sp1/)
udostępnia pełną instalację aktualizującą wydanie bazowe. Sam patch wymaga
wcześniejszego PU1 i nie jest właściwą ścieżką dla obecnego wydania bazowego.

### Natywne wyrażenie przez starsze API — dodatkowy dowód

`scripts/probe_2023_legacy_binding.py`
sprawdził rozwiązanie dla jednej brakującej funkcji: legacy `SizeBoxComponent`
udostępnia `Variable(triHeight, 0).Expression`. Po `IZSizeBox.Reset(false)`
przypisano `Parent\Params\RP_ProbeThickness`. Zmiana samego parametru sceny
zmieniła geometrię 20 → 40 mm; po zapisaniu i otwarciu wyrażenie pozostało
zachowane, a dalsze zmiany 40 → 60 → 20 mm działały bez ponownego ustawiania
wymiaru bryły. Pomiar 100 × 50 mm pozostałych osi również przeszedł.

PASS: `artifacts/ironcad2023-compatibility/legacy-expression-roundtrip/result.json`.
Źródło i kontekst aktywnego dokumentu nie zmieniły się; kopie testowe zamknięto.
To rzeczywiste natywne wiązanie, uzupełniające wcześniejszy test sterowania
skryptem. Sprawdzono wyłącznie jedną diagnostyczną bryłę. Mapowanie wystąpień,
wiązania pozycji i operacje wszystkich części T1 nadal wymagają adaptera.
Identyfikatory `Shape.SystemID` legacy i `IZElement.Id` nie są zamienne.
Nie przenoś mapowania jedynej bryły z diagnostyki na dowolną scenę.

Uwaga implementacyjna: `IZSceneDoc.RegenerateParts` w tej próbie 2023 zwróciło
`E_NOTIMPL`; działało `scene.GetTopElement().QueryInterface(IZAssembly).RegenerateParts`.
Nie ukryto błędu — pierwsza próba jest w `legacy-expression-01`, a naprawiona
próba i pełny zapis/otwarcie mają oddzielne dowody.

### Checkpoint aktualizacji PU1 SP1

Pobrano pełny `IC2023PU1SP1.exe` (3058622344 bajty) do lokalnego Downloads/IronCAD.
Authenticode: **Valid, IronCAD, LLC**. Menedżer pobierania zakończył pobieranie,
lecz zgłosił: „Uruchomienie pliku z podwyższonymi uprawnieniami nie powiodło się”.
Aktualizacja **nie została zainstalowana**; ostatni potwierdzony host to 18479.
Zamknięto przez SDK tylko zapisany własny model diagnostyczny, potem pusty host.
Do użytkownika wysłano prośbę o uruchomienie pobranego instalatora jako administrator.
IronCAD po instalacji należy uruchomić zwyczajnie, bez podwyższonych uprawnień.

PASS po zmianach czytnika: pełny harness
`artifacts/verification/20261026T151636458532Z/results.json`.
PASS generowania interopu przez runner: `interop-runner-check/interop-generation.json`.
Kompilacja pełnego generatora T1 z aktualnego TLB 2023 PASS; nie uruchomiono
go jeszcze na skrzyni. Rzeczywiste kliknięcie panelu nadal NOT RUN.

Prompt powrotu: „Wróć do zgodności IronCAD 2023. Użyj $rockpro-scope-check
i $rockpro-verification. Sprawdź aktualizację PU1 SP1 i ApiVersion, otwórz nowe
kopie zachowanych T1/T2, potwierdź odczyt oraz załadowaną DLL, a następnie
odtwórz T1 z zasobów 2023. Zachowaj oryginały i jednego wykonawcę CAD”.
