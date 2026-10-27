# Studio — działający kreator kroków 1–3

Aktualny zakres: [trzy typy bez podtypów i licowanie przodu](WIZARD_THREE_TYPES.md).
Poniższy opis dokumentuje wcześniejszy przyrost w formacie v1; jego dodatkowe
podtypy i wariant dwojga drzwi zostały wycofane z obecnego kreatora.

27.10.2026. Zakres: nowy draft konstrukcji i edytowalny schemat sekcji 3D.
Nie generuje ICS, nie montuje okuć ani nie zapisuje BOM do Excela.

## Uruchomienie i obsługa

Uruchom Studio zgodnie z [ALL_REFERENCE_PREVIEWS.md](ALL_REFERENCE_PREVIEWS.md).
W nagłówku galerii wybierz **Nowa konstrukcja · kreator 1–3** lub otwórz
`wizard.html` pod adresem swojej sesji. Biblioteka siedmiu wzorców pozostaje
osobnym widokiem, dostępnym z nagłówka kreatora.

1. **Typ i podtyp:** skrzynia, szafa, workstation lub walizka. Podtypy obejmują
   wieko górne, zdejmowaną czapkę, układ góra/przód, klapę przednią, dwoje drzwi
   oraz własny podział. **Zastosuj typ i podtyp** jawnie zastępuje układ pokryw
   ustawieniami początkowymi; wymiary korpusu pozostają zachowane.
   Przejście **Dalej** również stosuje oczekujący wybór podtypu/liczby pokryw.
   Zapis i eksport nie pomijają niezastosowanego wyboru — pokazują komunikat.
2. **Wieka i współpraca:** od jednej do czterech sekcji. Każda ma nazwę, ścianę,
   tryb zawiasowy/zdejmowany i krawędź osi. Na jednej ścianie można utworzyć
   kilka skrzydeł dzielących szerokość płaszczyzny z zachowaną szczeliną.
   Współpraca: niezależna, razem, kolejno lub własna lista poprzedników.
   Zmiana liczby/ściany/sposobu otwierania przełącza odpowiednio na własny podział.
3. **Wymiary:** X/Y/Z wymaganego wnętrza korpusu, grubość sklejki, szczelina
   koncepcyjna i osobna wysokość/głębokość każdej pokrywy. Pozostałe wymiary
   sekcji wynikają z płaszczyzny połączenia i liczby skrzydeł; pokazujemy je
   jawnie w tabeli. Nie zmniejszamy wnętrza, aby pomieścić dodatkową sekcję.

Własne pokrywy mogą być na górze, z przodu, z tyłu, z lewej lub prawej strony.
Górne wieko na zawiasach domyślnie ma 45 mm przy korpusie 350 mm. Wyższe niż
15% wysokości korpusu skrzyni/workstation wymaga zaznaczenia odstępstwa
konstruktora, zapisywanego jako `height_override`. Zdejmowana czapka ma osobny
domyślny wymiar i nie podlega temu ograniczeniu T1. Dolna granica 2× grubość
sklejki jest wyłącznie granicą geometrii schematu, nie sprawdzonym minimum
montażowym konkretnego zawiasu.

## Podgląd

Nowy `wizard3d.js` generuje lekkie płyty z wymiarów i grafu, zamiast deformować
siatki starego modelu źródłowego. Zielony korpus i nieco jaśniejsze pokrywy
mają krawędzie i osobne grupy ruchu. Osie: Z do góry, X szerokość, przód w -Y.
Suwaki przedstawiają obrót schematyczny lub odsunięcie pokrywy zdejmowanej.

Tryb „razem” synchronizuje procent otwarcia; nie zatwierdza sprzężenia
mechanicznego. Przy zależności najpierw trzeba całkowicie otworzyć poprzednika.
Nie można zamknąć go, gdy sekcja zależna jest otwarta. „Otwórz wszystkie” pokazuje
stan końcowy, nie animację kolejności. Cykl zależności blokuje poprawny podgląd
i zapis. Edycja topologii/wymiarów zeruje otwarcia i przelicza model. Ruch kamery
oraz prezentacyjne otwarcia nie są wymiarami draftu.

Błędne dane mają czerwony komunikat „Nieaktualny podgląd”. Poprzedni poprawny
schemat nie staje się dowodem poprawności błędnej edycji. Gabaryt obejmuje
zamknięte sekcje, bez profili, kół, okuć, pianek i luzów produkcyjnych.

## Draft i trwałość

Format `rockpro.configurator/1` jest odrębny od `rockpro.concept-draft/1`
dotychczasowej galerii oraz `CaseSpec v1`. Nie zgadujemy topologii ze starego
podglądu; nie zmieniamy jego kontraktu. Niekompletne przyszłe kroki 4–11 są
dozwolone; zapis nie oznacza gotowości CAD/produkcji.

**Zapisz draft** zapisuje w tej samej lokalnej SQLite co `project_store`:

- `configurator_drafts`: bieżąca treść, nazwa i rewizja;
- `configurator_draft_versions`: zachowane kolejne wersje, data i SHA treści.

To koncepcje sprzed etapu CAD, więc zapis nie tworzy fikcyjnej karty projektu
z odgadniętą ścieżką ICS ani nie zmienia istniejących kart/snapshotów.
Powiązanie z kartą projektu przy wykonaniu CAD jest dalszym etapem.

Zapis wymaga `expected_revision` w transakcji `BEGIN IMMEDIATE`. Stary zapis
z drugiego okna zwraca HTTP 409, nie nadpisuje treści i nie jest automatycznie
ponawiany. Można wczytać bieżący stan albo użyć **Zapisz jako nowy**.
Lista prezentuje ostatnie 100 draftów; starsza historia nadal pozostaje w bazie.

Przeglądarka zachowuje awaryjnie bieżący stan i flagę niezapisanych zmian
w localStorage. Nie zastępuje to zapisu w SQLite. Zastąpienie niezapisanej pracy
przy wczytaniu, nowym draftcie lub imporcie wymaga potwierdzenia w interfejsie.
Eksport JSON przenosi koncepcję; import tworzy nowy, niezapisany draft, bez
przejęcia identyfikatora lub rewizji rekordu w bazie. Obsługiwany rozmiar: 32 KB.

## API lokalne

- GET `wizard/options`, `wizard/drafts`, `wizard/drafts/<id>`.
- POST `wizard/preview`: walidacja i obliczenie schematu, bez zapisu do bazy.
- POST `wizard/save`: `draft`, `id` (null dla nowego) i `expected_revision`.

Zapisy zachowują istniejącą kontrolę Origin, tokenu sesji i rozmiaru żądania.
Nie ma dowolnych ścieżek plików, uruchamiania skryptów ani zleceń CAD w HTTP.

## Dowody

- PASS: testy domeny i SQLite: zachowanie wnętrza, sekcje i złącza, podział
  skrzydeł, zależności/cykle, odstępstwo wysokości, historia i konflikt rewizji,
  odmowa zapisu błędnego draftu i kontrakt HTTP.
- PASS: rzeczywisty WebGL i interfejs: kroki 1–3, osobne głębokości pokryw,
  wspólny ruch i kolejność, cykl, zapis/odczyt SQLite, konflikt drugiego okna,
  eksport/import JSON, odtworzenie po przeładowaniu, stałe ID sekcji,
  szafa z dwojgiem drzwi, jeden canvas i układ 430 px bez przepełnienia.
- Dowody prywatne: `artifacts/wizard-20261027/browser-report.json` i PNG.
  Test przeglądarkowy używa oddzielnej bazy w tym folderze.
- PASS: pełny harness `artifacts/verification/20261027T134934429188Z/`:
  repository, backend, parts, core-design, core-contracts, qa i harness.
- PASS: wejście z głównej galerii do kreatora i WebGL bez błędów JS;
  `artifacts/wizard-20261027/production-studio.png`. Przed pierwszym otwarciem
  nowego zapisu zachowano lokalny snapshot istniejącej SQLite w tym samym
  prywatnym folderze dowodów. Wersje testowe nie zasilały bazy klienta.
- CAD/native, zakupowy BOM i Excel: NOT RUN, poza zakresem tego przyrostu.
