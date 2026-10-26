# RockPro CAD

Dodatek do IronCADa: panel C# / WinForms, backend Python MCP i SQLite oraz
narzędzia do parametryzowania skrzyń. Aktualna gałąź `main` łączy T1, T2
oraz narzędzia biblioteki modeli. To nadal prototyp rozwijany z konstruktorem.

## Szybki start dla udreka13

1. Przyjmij zaproszenie do prywatnego repozytorium GitHub. Przygotuj Windows x64,
   Git, Python 3.12 x64, IronCAD z lokalnym ICAPI SDK i kompilator .NET Framework 4.x.
2. Pobierz projekt do stałego folderu; przed instalacją zapisz pracę i zamknij IronCAD:

```powershell
git clone https://github.com/qoopercodding/RockPro.git
cd RockPro
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -Python python -IronCADYear 2027 -InstallAddin
```

3. Skrypt tworzy `Integracja/.venv`, instaluje zależności, konfiguruje lokalne
   ścieżki, buduje DLL i rejestruje dodatek dla bieżącego użytkownika.
   Dla stanowiska 2023 użyj `-IronCADYear 2023`; wymagany jest 2023 PU1 SP1.
   **Nowe siedem wzorców rozwijamy w 2027; nie otwierają się w 2023.**
4. Uruchom wybraną wersję IronCADa zwykłym skrótem, jako ten sam użytkownik
   co instalator. W scenie 3D otwórz **Dodatki → RockPro CAD → Połącz / Odśwież**.
   Po instalacji dodatek ładuje się przy starcie hosta; panel otwierasz przyciskiem.
5. Na początek otwórz `Integracja/skeleton/demo/RockPro_Epson_szkielet_MVP.ics`
   w 2027, utwórz kartę projektu i przypisz zapisany model. Sprawdź odczyt
   parametrów oraz zmianę na kopii. Demo ma 10 płyt; pełne T1/T2 to osobne narzędzia
   developerskie, wymagające prywatnej paczki źródeł i manifestów od prowadzącego.

Nie przenoś katalogu po rejestracji DLL. Jeśli brakuje przycisku, sprawdź wynik
instalatora, restart hosta i `Integracja/rockpro_cad/logs/addin.log`.
Szczegóły instalacji: [HANDOVER](HANDOVER.md); aktualne rozróżnienie wersji:
[zgodność 2023](docs/IRONCAD_2023_COMPATIBILITY.md). Starsze opisy instalacji
2027 nie zastępują jawnego wyboru `-IronCADYear`. Dla narzędzi SDK uruchamianych
z terminala ustaw też `$env:ROCKPRO_IRONCAD_YEAR="2027"`; panel wybiera wersję sam.

## Co już działa, a co dalej

- **Panel i backend:** karta projektu, konfigurator układu, SQLite, historia
  rewizji/snapshotów oraz operacje na znanym szkielecie. Panel uruchamia MCP
  lokalnie; do jego działania nie potrzeba klucza AI. [Układ i zakres](LAYOUT.md).
- **T1 / SDK 2023:** ograniczony prototyp z polskimi parametrami, sześcioma grupami,
  okuciami i 24 powiązanymi obróbkami; testy zmiany wymiarów i powrotu przeszły.
  [Struktura i wycięcia](docs/CASE_STRUCTURE.md).
- **T2 / SDK 2023:** regulacja głębokości/wysokości, ruch czapki, klapy i racka,
  uchwyty z wycięciami; szerokość pozostaje stała. Testy geometrii i zachowania
  okuć przeszły. [Prototyp T2](docs/T2_PARAMETRIC_PROTOTYPE.md).
- **Biblioteka / SDK 2027:** odczyt siedmiu nowych modeli, inwentarze i kandydaci
  części katalogowych. To jeszcze nie gotowe parametryczne szablony tych rodzin.
  [Przyjmowanie wzorców](docs/MODEL_LIBRARY_INGESTION.md).

Do zrobienia: połączenie pełnych generatorów z panelem/MCP, dalsza parametryzacja
nowych rodzin w 2027 i późniejsze odtworzenie dla 2023, zatwierdzenie bibliotek
okuć/obróbek, trwałość parametrów pełnych prototypów po zapisie i ponownym otwarciu,
oraz dopięcie produkcyjnego BOM, rysunków/formatek i odbioru u konstruktora.
Wyniki lokalnych prób nie zastępują sprawdzenia na stanowisku współpracownika.

## Linear — zadania i postęp

**[Projekt RockPro CAD w Linear](https://linear.app/rock-pro/project/rockpro-cad-d99cc3102643/overview)**

Zaloguj się i przyjmij osobne zaproszenie do workspace **Rock_Pro**. Dostęp do
GitHuba nie nadaje dostępu do Linear; jeśli nie widzisz projektu, poproś jego
właściciela o zaproszenie. W projekcie przejdź do listy zadań i filtruj po statusie.
Przed pracą czytaj opis, kryteria odbioru, zależności i komentarze. Po pracy dodaj
link do commita/PR oraz wynik testów; wymaganych odbiorów konstruktora nie zamykaj
samym wynikiem testu.

Punkty wejścia: [ROC-42 — manifest części](https://linear.app/rock-pro/issue/ROC-42),
[ROC-41 — wycięcia i styki profili](https://linear.app/rock-pro/issue/ROC-41),
[ROC-22 — akceptacje, historia i odzyskiwanie](https://linear.app/rock-pro/issue/ROC-22).
[Porównanie Linear z kodem](docs/LINEAR_CONTINUATION_20261024.md) jest raportem
historycznym z 24.10.2026; bieżące statusy sprawdzaj bezpośrednio w Linear.

## Kod i sprawdzenia

- `Integracja/rockpro_cad/addin` — dodatek C# i rejestracja.
- `Integracja/rockpro_cad/mcp` — backend i SQLite.
- `Integracja/rockpro_cad/core_case` oraz `scripts` — reguły, wykonawcy SDK i testy.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1 -IronCADYear 2027
```

To testy bez sterowania CAD; próby natywne wykonuj osobno na kopiach, pojedynczym
wykonawcą. Zacznij od [AGENTS.md](AGENTS.md) i [DEVELOPMENT](docs/DEVELOPMENT.md).
Modele klientów, ich inwentarze, bazy, logi, DLL i lokalna konfiguracja pozostają
poza Gitem. SDK pochodzi z instalacji IronCAD; zależności Pythona są przypięte.
