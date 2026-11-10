# Start dla Kuby i jego agenta AI

Stan przekazania: **3 listopada 2026**; kod funkcji do 31.10, kontrola paczek 03.11.
Aktualizacja publikacji 10.11.2026: repozytorium
[QooperBoy/RockPro](https://github.com/QooperBoy/RockPro), gałąź **main**.
To prototyp developerski, bez odbioru produkcyjnego. [Starszy opis](KUBA_HANDOVER_20261021.md)
pozostaje historią; nie używaj jego komend ani statusów jako aktualnego planu.

## Właściwy kod i pierwsza sesja

```powershell
git clone https://github.com/QooperBoy/RockPro.git
cd RockPro
git status --short
git log -5 --oneline
```

`main` zawiera aktualny kod Studio, nowych rodzin CAD, montażu i rejestru SDK/AI.
10.11 połączono obie historie bez force push; 19 commitów starego main miało
odpowiedniki patchy w nowszym kodzie. Gałąź `codex/roc42-catalog-continuation`
zachowuje wcześniejszy tor roboczy, a `qoopercodding/RockPro` jest starszą kopią.
`codex/t2-parametryzacja` to osobny tor T2/T1 z drugiego czatu. Nie nakładaj go
na bieżącą gałąź i nie scalaj automatycznie: najpierw porównaj kontrakty i testy.
Gałęzie snapshotów są historią. Push nie aktualizuje Vercela ani zainstalowanej DLL.

Czytaj kolejno: ten dokument, [AGENTS](../AGENTS.md), [DEVELOPMENT](DEVELOPMENT.md),
[proces produktu](CUSTOM_CASE_WORKFLOW.md), [domyślne zasady](CASE_DEFAULTS.md),
[kontrakty](CASE_CONTRACT.md), [manifest części](PARTS_MANIFEST.md),
[wycięcia i styki](ROC41_CUTOUTS_AND_JOINTS.md),
[niezawodność i rejestr](RELIABILITY_AND_OBSERVER.md).
Nie uruchamiaj skryptów CAD podczas samego poznawania projektu.

Uzupełnienie kodu 09.11.2026: [narzędzia workspace](../tools/workspace/README.md)
oraz [archiwum źródeł lokalnych](../legacy/local-code/README.md). To zachowane
skrypty pomocnicze i historyczne warianty, nie pliki do nakładania na backend.
Modele projektu są ignorowane przez Git, także demonstracyjny
`Integracja/skeleton/demo/RockPro_Epson_szkielet_MVP.ics`. Jego lokalna kopia
została zachowana, ale nowy klon musi otrzymać ją osobnym kanałem, jeżeli chce
wykonać dawny scenariusz szkieletu. Nie zastępuj brakującego modelu atrapą.

## Mapa programów

Ścieżki bez katalogu w tabeli odnoszą się do `Integracja/rockpro_cad/`.

| Obszar | Pliki i rola |
|---|---|
| Studio lokalne | `reference_studio.py`: HTTP i usługi zapisu; `reference_studio/`: HTML, CSS, JS i Three.js |
| Draft i koncepcja | `configurator.py`: typy, sekcje, gabaryty, rewizje; `family_concepts.py`: galeria |
| Części | `studio_parts.py`, `source_parts.py`, `supplier_parts.py`, `company_catalog.py`, `part_registry.py`; `assets/supplier-parts/` to siatki, nie zatwierdzone montaże |
| Układ i kontrola | `studio_placement.py`, `studio_closures.py`, `studio_structure.py`, `studio_review.py` |
| Stan lokalny | `mcp/project_store.py` i usługi `mcp/`: SQLite, historia i konflikty rewizji. Nie dodawaj drugiego źródła prawdy we frontendzie |
| SDK / AI | `process_runs.py`, `process_capture.py`, `process_observer.py`, `reference_studio/process-panel.js`; CLI `scripts/studio_process_run.py` |
| Dodatek | `addin/`: C# / WinForms / .NET Framework i mostek do Pythona; instalacja osobna od strony |
| CAD | `core_case/`: kontrakty i wykonanie; `scripts/prepare_*.py` oraz `scripts/native/*.cs`: adaptery przypięte do źródeł |
| Dane prywatne | Ignorowane `artifacts/`, lokalne projekty ICS, SQLite, snapshoty, mapowania i wyniki; klon nie jest obrazem komputera autora |

Zachowane wdrożenie `RockPro/Integracja` obok checkoutu u autora jest oddzielne.
Nie zastępuj go nowym demo i nie używaj jako bieżących źródeł.

## Uruchomienie Studio bez IronCADa

Python 3.11+ (zalecany 3.12 x64), przeglądarka z WebGL i prywatne pakiety danych.
Nie potrzeba klucza OpenAI ani hosta CAD. Sam klon nie zawiera pełnej galerii.
Odbierz osobnym kanałem:

- `RockPro_CZESCI_20261103.zip`: CAD producentów, dodatkowe części, zdjęcia,
  katalog i siatki. 265 rekordów nie oznacza 265 gotowych modeli STEP.
- `RockPro_MODELE_20261103.zip`: wejściowe i opracowane ICS, mapowania, dowody
  oraz finalne podglądy siedmiu wzorców galerii.
- Opcjonalnie `RockPro_KOD_AI_KATALOG_20261103.zip`: snapshot kodu i historii
  zadań sprzed tego pushu. Nie nadpisuj nim nowszego klona.

Sumy archiwów: [HANDOVER_PACKAGES.json](HANDOVER_PACKAGES.json). Sprawdź np.
`Get-FileHash -Algorithm SHA256 C:\Paczki\RockPro_CZESCI_20261103.zip`.
W archiwach są też manifesty SHA każdego pliku i indeks HTML modeli.

Wypakuj paczki i nałóż zawartość ich **DO_WGRANIA_DO_KODU** na katalog klona:
powstaną głównie ignorowane `artifacts/` i zasoby siatek. Najpierw porównaj
istniejące pliki; nie nadpisuj lokalnych zmian ani baz. Nie commituj nakładek.
Paczki nie zawierają haseł, SDK, instalatorów, Excela, zleceń ani starej bazy.
Brak zasobów zgłaszaj jako brak danych; nie zastępuj ich atrapą.

Z katalogu klona:

```powershell
py -3.12 -m venv Integracja\.venv
cd Integracja
.\.venv\Scripts\python.exe -m rockpro_cad.reference_studio --bundle ..\artifacts\model-library-20261026 --previews ..\artifacts\family-3d-20261027\index.json --database .\studio-kuba.sqlite
```

Serwer Studio używa biblioteki standardowej; zależności natywnego backendu to
osobna konfiguracja. Otwórz wypisany URL i dopisz `wizard.html`. Zapisz draft,
pobierz JSON i ponownie otwórz zapis. Ctrl+C zatrzymuje serwer. Baza jest nowa,
bez projektów autora. Dawne porty i tokeny sesji nie są trwałymi adresami.

Alternatywnie skrypt `zloz_przekazanie.py` z archiwów składa trzy paczki do
nowego folderu. To odtworzenie snapshotu z 03.11, nie aktualizacja klona ani
instalator CAD. Test przekazania korzystał z istniejącego Pythona autora;
nie oznacza instalacji wszystkich zależności na pustym systemie.
Ten sam skrypt jest w repo jako [assemble_handover.py](../scripts/assemble_handover.py).
Parametry `--code`, `--parts` i `--models` wskazują wypakowane paczki, `--dest`
nowy, nieistniejący folder; `--help` pokazuje składnię. Nie uruchamia instalacji,
nie dotyka CAD i odmawia zastąpienia istniejącego katalogu docelowego.

## Co faktycznie działa i jakie są granice

- Studio ma osiem kroków: konstrukcja, wieka, wymiary sekcji, katalog,
  uchwyty/ścianki, zatrzaski/zawiasy, konstrukcja/podstawa i kontrola projektu.
  Typy kreatora: Skrzynia, Szafa i Skrzynia 3-elementowa. Galeria wzorców ma
  osobną klasyfikację; liczba typów nie jest liczbą plików ICS.
- Działa koncepcyjne rozmieszczanie, siatki, rewizje draftów, JSON, BOM roboczy,
  częściowe ceny i panel niespójności. Katalog w archiwum przekazania ma usunięte
  ceny i stany, więc sam nie zapewnia wyceny.
- Lokalnie zapis jest w SQLite; Vercel zapisuje w przeglądarce, bez zdalnego
  sterowania IronCADem i bez połączenia z bazą autora.
- Zapisane prototypy sześciu rodzin: T1/projektor, TV, Wing Compact, kufer,
  rack 9U i serwis szufladowy. Wciągarki i oświetlenie mają wejściowe wzorce,
  bez gotowych parametrycznych ICS. Archiwum obejmuje osiem grup i 36 unikalnych
  wejściowych ICS, nie osiem zatwierdzonych generatorów.
- Przy pakowaniu SHA modeli Wing, kufer, rack i serwis pasowały do zapisanych
  wyników. Aktualny TV R005 różni się od testowanej rewizji — wymaga ponownego
  testu. T1 jest historycznym prototypem. Nie ma odbioru produkcyjnego.
- Rejestr przypina wykonanie do rewizji/SHA draftu. `origin` i `executor` są
  osobne. AI zlecające SDK nie tworzy dwóch operacji. Starsze pliki bez zdarzeń
  pozostają `unknown`, a demo pozostaje `simulation`.
- **Uniwersalny przycisk dowolny draft -> kompletny, zweryfikowany ICS nadal
  wymaga dokończenia.** Adapter konkretnego wzorca nie mapuje nowych SKU sam.
  Siatka nie potwierdza wycięcia, montażu, ruchu, nośności ani CNC.

## Parametry i bezpieczna praca CAD

Docelowa wersja: **IronCAD 2023** — klient pracuje na 2023 (potwierdzone
ponownie 04.11.2026; jeden komputer firmy, konstruktorzy łączą się przez RDP).
Dotychczasowe rodziny parametryczne zapisano w 2027 (`*_IC2027.ics`) i nie
otwierają się w 2023; wymagają odtworzenia w 2023. Build dodatku 2023 tego nie
zmienia. Patrz [macierz zgodności](IRONCAD_2023_COMPATIBILITY.md).
10.11.2026 natywny test 2023 (część diagnostyczna, wiązanie parametru, zapis i
ponowne otwarcie) wraz z rejestrem i panelem Phoenix: PASS —
[OBSERVABILITY_HOWTO](OBSERVABILITY_HOWTO.md).

**Nie dodawaj parametrów liczby okuć, pól `*_Liczba`, szyków ani automatycznego
powielania/usuwania uchwytów, zawiasów i zamków w CAD.** Użytkownik wycofał to
31.10; R003–R005 są historią. Wybór zestawu części w Studio i liczenie BOM nie
upoważnia do przywrócenia kontrolera liczności w natywnym modelu.
Parametryzuj gabaryty, sekcje, położenia, rozstawy, orientacje i obróbki
istniejących wystąpień. Przy braku miejsca zgłaszaj konflikt.

Parametry muszą mieć polską nazwę/komentarz, jednostkę, znaczenie i zakres.
Drzewo: „Rodzaj + SKU — sekcja — ściana — pozycja”, stabilne ID osobno.
Ustal osie ścian projektu; nie zgaduj ich z kamery. Nie skaluj SKU.
Okucie, wycięcie i przerwa profilu mają wspólną kotwę. Koła i płyta nośna
mają wspólny montaż; górne gniazda są sparowane z kołami.
Sklejka `#408080`; płytkie wieko zwykle 10–15% korpusu, minimum z pionowego
miejsca montażu zawiasu i luzów. Nie stosuj trzech szerokości okucia.
Wysoka zdejmowana czapka TV/miksera zachowuje topologię swojego wzorca.

Przed jobem: zweryfikuj źródło/SHA, zrób nową kopię, wybierz host i ścieżki.
Jeden wykonawca CAD naraz. `prepare_*` czytają konkretne inwentarze i często
wyznaczają `projekty/` względem katalogów autora. Absolutne ścieżki dowodów są
pochodzeniem, nie przenośną konfiguracją. Nie podmieniaj ich masowo, bo zerwiesz
powiązania SHA. Klon w nowym miejscu wymaga dostosowania joba przed wykonaniem.
Testuj niezależnie gabaryty, montaż, wycięcia, zapis i ponowne otwarcie.

Instalacja dodatku: Windows x64, własny IronCAD/ICAPI SDK i .NET Framework.
Zapisz dokumenty i zamknij host przed instalacją:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -Python python -IronCADYear 2023 -InstallAddin
```

Setup instaluje zależności z `requirements.txt`, buduje i rejestruje DLL.
Nie uruchamiaj go tylko do testów. Host uruchom normalnie jako ten sam użytkownik.
Szczegóły: [HANDOVER](../HANDOVER.md), [AUTOSTART](../AUTOSTART.md).

## Weryfikacja i dalsze zadania

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1 -IronCADYear 2023
# Po przygotowaniu SDK, dla zmiany dodatku:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1 -IronCADYear 2023 -WithAddinBuild -WithUiChecks
```

Dla samych dokumentów: `scripts/repo_audit.py`, odnośniki i zgodność komend.
Wyniki do `artifacts/`, jawnie PASS / FAIL / NOT RUN. Offline nie potwierdza CAD.
03.11 osobno odtworzono Studio z paczek: 265 rekordów, siedem podglądów
z kontrolą powiązań, 135 wpisów z siatką, pobranie jednej siatki i zapis draftu
PASS. Nie powtarzano testów CAD ani instalacji na pustym komputerze.

Przed pushem instrukcji 03.11.2026 pełny `Verify.ps1 -IronCADYear 2027`
zakończył się PASS: repository, backend, parts, core-design, core-contracts,
qa i harness. Raport lokalny: `artifacts/verification/20261103T220010892252Z/`.
Natywny CAD i build dodatku: NOT RUN w tym przebiegu. Pierwsza próba w sandboxie
nie przeszła z powodu odmowy dostępu Windows do tymczasowych plików testów;
wynik PASS dotyczy powtórzenia poza tym ograniczeniem, bez zmiany kodu testów.

Kolejność: środowisko i testy -> jedna rodzina -> potwierdzenie montażu/obróbek
-> przypięcie rewizji Studio do adaptera -> test CAD na kopii -> rejestr/review
-> odbiór konstruktora. Potem kolejne rodziny i ERP. Excel jest lokalny,
zwykle edytowany przez jedną osobę; import nie upoważnia do nadpisania pliku.
Nie zaczynaj od przepisywania całej aplikacji ani przywrócenia liczności okuć.

[Linear RockPro CAD](https://linear.app/rock-pro/project/rockpro-cad-d99cc3102643/overview)
w workspace **Rock_Pro** wymaga osobnego zaproszenia. GitHub go nie nadaje.
Punkty wejścia: [ROC-45](https://linear.app/rock-pro/issue/ROC-45),
[ROC-41](https://linear.app/rock-pro/issue/ROC-41), [ROC-42](https://linear.app/rock-pro/issue/ROC-42).
[TODO](TODO_20261028.md) i 61 rekordów z paczki (28.10 plus lokalne raporty do
31.10) są historyczne. Odczytaj bieżące wymagania/dependencje w Linear; po pracy
powiąż commit i wyniki, bez pozornego odbioru konstruktora.

## Prompt pierwszej sesji agenta Kuby

> Przeczytaj docs/KUBA_HANDOVER.md, AGENTS.md, docs/DEVELOPMENT.md oraz lokalne
> skille scope-check i verification. Sprawdź gałąź i stan Git. Oddziel kod,
> prywatne zasoby, zainstalowaną DLL i historyczne dowody CAD. Sprawdź paczki
> po SHA, uruchom Studio z nową bazą i właściwe kontrole. Wypisz rzeczywiste
> wyniki i braki. Nie zmieniaj oryginałów CAD, nie uruchamiaj Setup bez potrzeby
> i nie przywracaj parametrów liczby okuć. Zaproponuj jeden mały przyrost
> z mierzalnym kryterium odbioru.
