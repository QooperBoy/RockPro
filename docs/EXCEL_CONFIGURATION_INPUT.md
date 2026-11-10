# ROC-18 — wejście Excel

Techniczny przepływ: arkusz XLSX → podgląd i błędy → jawny zapis układu ze
sprawdzeniem wersji → istniejący konfigurator. Import nie uruchamia CAD ani
nie zatwierdza rodziny produkcyjnej. Korzysta z tej samej SQLite co UI i MCP.

## Pliki wejściowe

examples/excel-input/RockPro_poprawny.xlsx jest szablonem i poprawnym przykładem.
RockPro_bledny.xlsx zawiera count=0; RockPro_graniczny.xlsx zawiera x=5000 mm.
Arkusz zawiera jeden panel Konfiguracja. Wpisz project_id z get_project oraz
expected_layout_revision z get_layout. Wersja 0 oznacza układ jeszcze niezapisany.

Pole / Wartość / Jednostka są nagłówkami w A4:C4. Wiersze poniżej zawierają
parametry układu. Czwarta kolumna zawiera opisy. Jednostki wymiarów: mm, cm, m;
liczba urządzeń: szt. Teksty, pola techniczne i wartości logiczne nie mają
jednostek. Wpisuj rzeczywiste liczby i TRUE/FALSE, bez formuł.

Format liczbowy komórki służy prezentacji: nie zmienia jednostki z kolumny C.
Wymagane pola nie są uzupełniane po cichu. Kontrola geometrii i proporcji
pokrywy pochodzi z istniejącego layout.calculate_layout.

Pokrywa 25 mm w przykładzie pokazuje kontrakt wejścia; brak wybranego zawiasu
pozostaje ostrzeżeniem konfiguratora. To nie jest zwymiarowanie gotowego prototypu
650 × 500 × 381 mm ani potwierdzenie montażu konkretnego okucia.

## Użycie

Podgląd:

    powershell -NoProfile -File scripts/Import-ExcelConfiguration.ps1 -File examples/excel-input/RockPro_poprawny.xlsx

Polecenie zapisuje byte-identyczną kopię wejścia pod jego SHA256 w lokalnym,
ignorowanym Integracja/imports. Odpowiedź JSON zawiera valid, errors,
source_sha256, project_id, expected_layout_revision i obliczony layout.

Po sprawdzeniu podglądu:

    powershell -NoProfile -File scripts/Import-ExcelConfiguration.ps1 -File <arkusz.xlsx> -Apply -ProjectId <ID> -ExpectedRevision <wersja> -ExpectedSourceSha256 <SHA-z-podgladu>

MCP udostępnia preview_excel_configuration(path) oraz
import_excel_configuration(project_id,path,expected_revision,expected_source_sha256).
Ścieżka musi znajdować się w Integracja/imports. Inne argumenty są odrzucane.

## Wersje, powtórzenia i konflikty

- Podgląd czyta jeden ograniczony plik i nie zapisuje projektu.
- Zapis ponownie liczy hash; zmiana pliku po podglądzie daje EXCEL_SOURCE_CHANGED.
- Wersja z arkusza musi odpowiadać argumentowi expected_revision. Równoległa
  zmiana układu daje LAYOUT_CONFLICT bez nadpisania konfiguracji.
- Jedna transakcja zapisuje układ, oryginalne bajty XLSX, wersję schematu,
  źródłowy SHA, znormalizowany SHA konfiguracji i zdarzenie historii.
- Powtórzenie tego samego pliku zwraca poprzedni wynik z reused=true.
  historical=true oznacza, że od tej pory istnieje nowszy układ; import nie cofa go.
- Arkusz ze zmienionym formatowaniem/jednostką, lecz równoważną konfiguracją,
  zachowuje nową wersję źródła bez kolejnej kopii tej samej konfiguracji.
- Import nie odświeża expected_revision w tle i nie omija konfliktów.

## Ograniczenia i sprawdzenia

Obsługiwany jest prosty format v1, jeden arkusz A1:D200, plik do 2 MB i pakiet
do 16 MB po rozpakowaniu. Formuły, makra, zewnętrzne linki, powtórzone pola,
nieznane jednostki i deklaracje encji XML są odrzucane. Nie ma zależności od
zainstalowanego Excela ani bibliotek arkuszowych w wykonawcy Python.

Testy obejmują trzy przykłady, równoważne jednostki, formatowanie, granice,
duplikaty, zachowanie oryginału w SQLite, CAS, zmianę pliku po podglądzie,
błędny projekt, odmowę formuł/ścieżek i rollback po awarii zapisu.

Weryfikacja nie wymaga otwierania ani modyfikowania modelu CAD.

PASS: pełny harness, kompilacja dodatku i kontrole UI — artifacts/verification/20261024T213039539715Z/results.json.
PASS: rzeczywisty wrapper PowerShell uruchomił podgląd poprawnego XLSX. Import SQLite/CAS sprawdzono na izolowanej bazie; CAD nie był potrzebny.
