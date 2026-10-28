# RockPro CAD / Studio

**Demo dla Tomka:** [rockpro-studio.vercel.app](https://rockpro-studio.vercel.app).
Konfigurator, podgląd 3D i zdjęcia producentów. Drafty oraz ulubione są zapisywane
tylko w przeglądarce; projekt przekaż przez eksport/import JSON. Bez firmowej bazy,
stanów magazynowych oraz bez zdalnego sterowania IronCADem. Pełny katalog ma
265 rekordów z cenami; na końcu konfiguracji jest częściowa wycena okuć.
[Wdrożenie i aktualizacja](docs/STUDIO_VERCEL.md).

[Interfejs i proces Studio](docs/STUDIO_UX_DESIGN.md): kompas, narzędzia 3D,
spójne kroki i kierunek dalszego rozwoju, wraz z przeglądem bibliotek UI/UX.

Studio ma teraz [krok 6 — zatrzaski i zawiasy na złączach](docs/WIZARD_CLOSURES.md):
liczba, równy rozstaw i omijanie uchwytów, z zachowaniem draftu oraz podglądem 3D.

Budujemy konfigurator skrzyń: od wyboru konstrukcji i wymaganego wnętrza,
przez części i ich montaż, do kontrolowanego projektu IronCAD, snapshotu
oraz zestawienia materiałów i firmowego Excela. Obliczenia mają wykonywać
skrypty; AI pomaga w propozycjach i wyjątkach przez te same operacje.

**Stan: 27.10.2026 — prototyp, bez odbioru produkcyjnego.** Aktualne Studio
jest na gałęzi `codex/roc42-catalog-continuation`. `main` zawiera wcześniejszą
integrację T1/T2; ten push nie scala ani nie nadpisuje innych gałęzi.

## Start dla udreka13

Przyjmij zaproszenie do prywatnego repozytorium i pobierz właściwą gałąź:

```powershell
git clone --branch codex/roc42-catalog-continuation https://github.com/qoopercodding/RockPro.git
cd RockPro
```

Przy istniejącym checkoutcie najpierw zachowaj swoją pracę, potem pobierz
zmiany i przełącz się na tę gałąź. Nie resetuj lokalnych zmian:

```powershell
git fetch origin
git switch codex/roc42-catalog-continuation
git pull --ff-only
```

Przeczytaj [AGENTS.md](AGENTS.md) i [zasady rozwoju](docs/DEVELOPMENT.md).
Pracujemy na kopiach CAD, jednym wykonawcą SDK. Nie zmieniamy oryginałów,
archiwalnych snapshotów ani prywatnej bazy drugiego wdrożenia.

## Uruchomienie Studio — przeglądarka i Python

Studio korzysta z lokalnego HTTP, Three.js i standardowej biblioteki Pythona.
Do oglądania kreatora i gotowych siatek nie trzeba uruchamiać IronCADa ani
podawać klucza AI. Zalecany Python 3.12 x64 i aktualna przeglądarka z WebGL.

Z głównego folderu repozytorium utwórz venv, jeśli jeszcze go nie masz:

```powershell
py -3.12 -m venv Integracja\.venv
cd Integracja
.\.venv\Scripts\python.exe -m rockpro_cad.reference_studio --bundle "C:\RockPro-data\model-library-20261026" --previews "C:\RockPro-data\family-3d-20261027\index.json"
```

Ścieżki powyżej to przykładowa lokalizacja danych, nie pliki dołączone do Gita.
Potrzebne są osobno przekazane prywatne pakiety:

- `model-library-20261026`: manifest, inwentarze `native-02`, standardy
  `working-standard-v1` i opcjonalne obrazy wzorców;
- `family-3d-20261027`: `index.json` oraz wskazane w nim względne foldery
  z `model.json` i `geometry.bin`.

Obecny launcher wymaga pakietu `--bundle` także dla kreatora. Bez tych danych
nie uruchomisz pełnego Studio z samego klona; poproś prowadzącego o paczki.
Nie zastępuj ich sztucznymi źródłami ani nie commituj modeli klienta.

Serwer wypisze własny adres `http://127.0.0.1:<port>/<sesja>/` i otworzy
przeglądarkę. Z galerii wybierz **Nowa konstrukcja · kreator 1–5**.
Możesz też dopisać `wizard.html` do adresu sesji. Adres z komputera autora
nie zadziała na Twoim komputerze. Zatrzymanie serwera: Ctrl+C w jego terminalu.

## Co już działa

| Obszar | Obecny zakres |
|---|---|
| Galeria wzorców | Siedem źródłowych modeli w sześciu grupach, rzeczywiste siatki, zmiana nominalnego gabarytu i ruchy zespołów; Workstation ma cztery wysuwane moduły |
| Krok 1 | Dokładnie trzy typy: Skrzynia, Szafa, Skrzynia 3-elementowa; brak podtypów i wariantu dwojga drzwi |
| Krok 2 | Skrzynia: wieko na zawiasach albo zdejmowane. Szafa: jedna przednia powłoka otwierana lub zdejmowana. Typ 3-elementowy: zdejmowany przód i góra; współpraca pokryw i zależności otwierania |
| Krok 3 | Wymiary wnętrza korpusu, grubość sklejki, wysokość/głębokość pokryw, aktualizowany schemat 3D. Przód wariantu 3-elementowego automatycznie licuje z górą |
| Krok 4 | Baza 14 pozycji i opcjonalny pakiet innych projektów (lokalnie +39, razem 53); rendery, kategorie, filtr pochodzenia i wybór wersjonowanych definicji |
| Krok 5 | Płynny drag and drop, obrót środkowym przyciskiem, 1–16 uchwytów/ściankę, symetria, równe rzędy zawiasów na styku sekcji, wstępne ostrzeżenia i zapis |
| Draft | Zapis/odczyt w SQLite, historia rewizji, konflikt starszego zapisu, odzyskiwanie przeglądarki oraz JSON. Format aktualny: `rockpro.configurator/3`; stare formaty są zachowane i konwertowane jawnie jako nowe |
| Dotychczasowy dodatek | C# / WinForms, Python MCP, karty projektów, układ, snapshoty i ograniczone operacje na znanym szkielecie; pełne prototypy CAD to osobny tor od Studio |

**XYZ oznaczają obecnie wnętrze samego korpusu, nie całej skrzyni z pokrywami.**
Pokrywy mają własne wymiary; nominalny gabaryt zamkniętej konstrukcji jest
pokazany oddzielnie. Zielona sklejka: `#408080`.

Szczelina złącza i docięcie sklejki mają wynikać z wybranego okucia/profilu.
Nie są ręcznym dodatkiem do gabarytu. Na razie biblioteka montażowa nie jest
podłączona: wyniki mają status „do ustalenia po wyborze okucia”, nie fikcyjne
zero. Płyty podglądu nie są formatkami produkcyjnymi. Zatwierdzony montaż przy złączach,
obróbki, kompletny plan CAD, generowanie ICS z kreatora i synchronizacja firmowego Excela
**nie są jeszcze wdrożone**.

Dostępna biblioteka i ograniczenia wyboru: [krok 4](docs/WIZARD_PARTS_SELECTION.md).
Rozmieszczanie, liczby i symetria: [krok 5](docs/WIZARD_PLACEMENT.md).
Sterowanie, biblioteki i rzędy zawiasów: [interakcje Studio](docs/STUDIO_INTERACTION.md).
Odczyt innych otwartych projektów i rozszerzona paleta: [warianty źródłowe](docs/STUDIO_SOURCE_PARTS.md).

Dokładniej: [aktualne wymiary i złącza](docs/WIZARD_JOINT_DIMENSIONS.md),
[trzy typy](docs/WIZARD_THREE_TYPES.md), [galeria 3D](docs/ALL_REFERENCE_PREVIEWS.md).
[Opis pierwszego kreatora](docs/WIZARD_STEPS_1_3.md) zachowuje również historyczny
zakres v1 — aktualne ograniczenia mają pierwszeństwo.

## Następne prace

1. Przyjąć pełny katalog części od Tomka: SKU, jednostki zakupowe, modele CAD,
   zgodność wersji, ramy montażu, wymagane wycięcia i dane połączeń.
2. Powiązać koncepcyjnie rozmieszczone zawiasy/zatrzaski ze złączami sekcji,
   potwierdzić ramy i przestrzeń ruchu, generować wycięcia oraz przerwy profili
   z tej samej kotwy co okucie. Rozszerzyć bibliotekę zweryfikowanych obrysów.
3. Wyliczać szczeliny, osadzenie profili i docięcie sklejki z konkretnego
   szablonu montażowego wewnątrz ustalonego gabarytu. Brak danych blokuje CAD.
4. Transport/koła i sparowane górne gniazda, podpory, teleskopy oraz logo klienta.
5. Review konkretnej rewizji i adapter kompletnej rodziny do IronCAD 2023:
   wykonanie na nowej kopii, pomiary, zapis/otwarcie, snapshot oraz foldery.
6. BOM roboczy na jedną skrzynię i całe zlecenie, a potem integracja z realnym
   firmowym Excelem. Czekamy na jego strukturę i zasady współdzielenia;
   nie odgadujemy kolumn ani nie nadpisujemy ręcznych ustaleń.

Cały kierunek: [proces w 11 krokach](docs/CUSTOM_CASE_WORKFLOW.md) i
[architektura konfiguratora](docs/CASE_CONFIGURATOR_ARCHITECTURE.md).
Trzeba oddzielać działający podgląd, kod/test offline, dowód CAD i odbiór konstruktora.

## Dodatek w IronCAD

Osobno od Studio: Windows x64, wybrana wersja IronCAD z ICAPI SDK oraz kompilator
.NET Framework. Docelowe stanowisko firmy: **2023 PU1 SP1**; część późniejszych
modeli źródłowych i eksportów pochodzi z 2027. Nie oznacza to, że ich ICS
otworzy się w 2023. [Macierz zgodności](docs/IRONCAD_2023_COMPATIBILITY.md).

Zapisz pracę i zamknij IronCAD przed instalacją/rejestracją:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -Python python -IronCADYear 2023 -InstallAddin
```

Dla stanowiska developerskiego 2027 użyj `-IronCADYear 2027`. Skrypt instaluje
zależności natywnego backendu, konfiguruje ścieżki, buduje i rejestruje DLL.
Uruchom host normalnie jako ten sam użytkownik; **Dodatki → RockPro CAD**.
Po instalacji nie przenoś checkoutu. Demo `Integracja/skeleton/demo/` to znany
szkielet, nie kompletny generator wszystkich rodzin.
Szczegóły: [HANDOVER](HANDOVER.md), [AUTOSTART](AUTOSTART.md).

## Kod i weryfikacja

- `Integracja/rockpro_cad/studio_parts.py` i `reference_studio/parts-picker.js`: katalog oraz wybór okuć w kroku 4.
- `Integracja/rockpro_cad/studio_placement.py`, `reference_studio/placement-editor.js` i `placement3d.js`: kotwy, grupy, wstępna kontrola i interakcje kroku 5.
- `Integracja/rockpro_cad/configurator.py`: reguły kroków 1–3, nominalna geometria,
  walidacja i rewizje draftów; `reference_studio.py`: lokalne trasy HTTP.
- `Integracja/rockpro_cad/reference_studio/wizard*`: kreator i jego schemat 3D.
- `family_concepts.py`, `reference_studio/app.js`, `reference3d.js`: galeria
  i źródłowe podglądy; `scripts/prepare_workstation_preview.py`: konwersja siatek.
- `Integracja/rockpro_cad/mcp`: wspólna SQLite i usługi; `core_case`: kontrakty
  i wykonanie CAD; `addin`: C# / WinForms. Nie twórz drugiej bazy w frontendzie.

Testy kreatora z katalogu `Integracja`:

```powershell
.\.venv\Scripts\python.exe -m unittest rockpro_cad.mcp.test_configurator rockpro_cad.mcp.test_reference_studio -v
```

Pełna regresja z katalogu głównego:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1
```

Ostatnia pełna regresja: PASS — repository, backend, parts, core-design,
core-contracts, qa i harness. UI/WebGL, zapis/odczyt draftu i JSON również
sprawdzone lokalnie. Wyniki lokalne nie potwierdzają instalacji na nowym
stanowisku ani produkcyjnej poprawności konstrukcji. Prywatne raporty
`artifacts/verification/20261027T144729496423Z/` nie należą do repozytorium.
Modele, biblioteki geometrii, SQLite, snapshoty, logi, SDK i wygenerowane DLL
pozostają poza tym pushem; dane wymieniamy osobnym kanałem.

## Linear — gdzie śledzić pracę

[Projekt RockPro CAD](https://linear.app/rock-pro/project/rockpro-cad-d99cc3102643/overview)
— zaloguj się do workspace **Rock_Pro**. Zaproszenie GitHub nie daje dostępu do
Linear; potrzebne jest osobne zaproszenie od właściciela workspace.

Przed zadaniem przeczytaj wymagania, zależności i kryteria odbioru. Po pracy
powiąż commit/PR z zadaniem i podaj wynik odpowiednich testów. Nie oznaczaj
odbiorów konstruktora jako ukończonych samym testem. Punkty wejścia:
[ROC-45 — mapowanie wzorców](https://linear.app/rock-pro/issue/ROC-45),
[ROC-41 — wycięcia i styki](https://linear.app/rock-pro/issue/ROC-41),
[ROC-42 — manifest części](https://linear.app/rock-pro/issue/ROC-42).
Statusy sprawdzaj bezpośrednio w Linear; starsze lokalne raporty są historyczne.
