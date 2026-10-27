# Studio — części z pozostałych otwartych projektów

Aktualna preferencja konstruktora: widoczność ograniczona do kompletnych części.
Źródłowe komponenty/połówki, nieokreślone zespoły i niekompletne reprezentacje
są ukryte w bibliotece, paletach i 3D. Dane historyczne są zachowane.
Wielobryłowy kompletny uchwyt lub koło pozostaje jedną widoczną częścią.

## Aktualizacja: rzeczywiste modele w kroku 5

Siatki wszystkich 39 nowych wariantów są teraz podłączone do rozmieszczania
na ściankach i podglądu pod kursorem. Zachowują metry, geometrię, kolory źródła
i skalę 1:1; przesunięcie/obrót całej części nie zmienia jej wymiarów.
Współdzielone bufory GPU ograniczają koszt powtarzania uchwytów. Wybieranie
korzysta z obrysu rzeczywistej siatki, a nie dawnego prostokąta 64 × 44 mm.

Generator: `scripts/prepare_source_part_meshes.py <lokalny-pakiet>`. Czyta
wyłącznie zachowane eksporty i indeks renderów; nie łączy się z IronCAD.
Sprawdza SHA geometrii, źródłowe wiązanie oraz jawny wybór `node_ids`.
Siatki trafiają do `images/<ID>.mesh.json`, indeks obrazów dostaje SHA i URL.
Loader HTTP sprawdza plik i wiązanie źródła; błędna siatka nie udaje
poprawnego modelu, interfejs zgłasza błąd i pokazuje znacznik zastępczy.

Zakres geometrii odpowiada jawnie wybranym bryłom z renderu. Jeśli render
pokazywał jeden element z rozrzuconego zespołu, model również pokazuje ten
element. Panel podaje liczbę wyświetlanych i źródłowych brył. Profil zachowuje
całą długość wybranej źródłowej bryły, nawet gdy miniatura była kadrowana.
Nie wprowadzono automatycznego rozciągania profili ani kompletnych SKU.

Ramy podglądu są wstępne: jawny kierunek dla rozpoznanych części lub oś
najmniejszego rozmiaru dla pozostałych; baza na dominującej płaskiej powierzchni
(koła: górna płaszczyzna źródłowego zespołu). To wybór prezentacji, **nie
potwierdzona rama montażu**. Obrót w płaszczyźnie i strona ścianki działają
jak wcześniej. Definicje części, rewizje draftów i statusy zgód pozostają
niezmienione. Nie ma nowych wycięć w sklejce; wnęka okucia może być zasłonięta
nieobrobioną płytą. Kontrola kolizji nadal dotyczy wstępnych obrysów 2D.

PASS: syntetyczne testy wymiarów, transformacji, koloru, tożsamości i odmowy
błędnych buforów. PASS: przeglądarka — 39 rzeczywistych siatek, rzeczywisty
podgląd pod kursorem, wybieranie/Esc, zmiana wymiarów ze współdzieloną geometrią,
skala 1:1 i zapis/odczyt SQLite. Pełny harness PASS:
`artifacts/verification/20261027T183429439500Z/`. Dowody przeglądarki:
`artifacts/source-parts-3d-20261027/`. Natywne montowanie w CAD: NOT RUN
(nie jest częścią tej zmiany Studio).

## Poprzedni checkpoint: import i znaczniki

27.10.2026. Rozszerzenie biblioteki i kroku 5 na podstawie faktycznego
odczytu dziewięciu dokumentów IronCAD 2027 oraz przypiętych eksportów siedmiu
modeli. Lokalnie: **14 dotychczasowych pozycji + 39 wariantów źródłowych = 53**.
52 można wybierać; historyczny pusty 2643 pozostaje zablokowany.

## Odczyt CAD i pochodzenie

`scripts/native/SurveyOpenParts.cs` działa przez istniejący pojedynczy most
SDK/lock. Sprawdził 4100 węzłów w dziewięciu otwartych scenach: hierarchię,
nazwy, lokalne ID, transformacje oraz obrysy dostępnych brył. Nie otwierał,
nie zamykał, nie aktywował, nie regenerował i nie zapisywał dokumentów.
Stan dokumentów/aktywnej sceny oraz hashe dysku zostały zachowane. Odbiór PASS,
tymczasowy wpis mostu usunięty (`remaining_count=0`).

Sześć dokumentów miało `Modified=true`. Odczyt nazw i struktur z pamięci nie
ustanawia zgodności ich geometrii z dyskiem. Do renderów i zachowanych modeli
części wykorzystano istniejące, przypięte eksporty M01–M07. Nie przedstawiamy
ich jako świeżej tessellacji niezapisanych zmian. Warianty z nowych rewizji
w pamięci wymagają osobnego zatwierdzenia i odczytu na kopii.

Prywatne dowody: `artifacts/other-project-parts-20261027/native-01/`:
`result.json`, `compile.json`, `addon_cleanup.json`. Raport zawiera dane klientów
i nie jest publikowany w Git.

## Import i granice definicji

`scripts/import_studio_source_parts.py` przyjmuje pakiet źródeł, indeks podglądów,
raport natywny i NOWY katalog wyjściowy. Sprawdza manifest źródeł, SHA inwentarza,
SHA bufora geometrii i powiązanie modelu. Nie zmienia wejść.

Rozpoznano 39 surowych kodów części. Dla każdego wybrano jeden jawny wariant
z konkretnego poddrzewa zapisanej rewizji. Inne wystąpienia zachowano w raporcie
pokrycia z osobnymi ścieżkami/źródłami. **Nie uznano geometrii za identyczną po
nazwie** i nie zsumowano liści jako produktów zakupowych.

Nowe ID `source-…` wynikają z SHA źródła, SHA inwentarza i ścieżki korzenia.
Dotychczasowe ID/revizje 14 definicji nie uległy zmianie. Każdy nowy wariant ma
`sku=null`, `catalog_code_raw`, rewizję 1, hash definicji, `mounting_status=unknown`,
`cutout_status=unknown`, `purchase_unit=null` oraz obie zgody automatycznego
montażu/produkcji ustawione na false. To kandydaci do koncepcji, nie przyjęcie SKU.

Kod 38081 jest grupowany z gniazdami do piętrowania (funkcja pokazana w katalogach
Adam Hall), a nie ze wzmocnieniami. Pozostałe niepotwierdzone funkcje, np. 205,
220, 3453, 87952, 88001D i E2215, pozostają w osobnej kategorii do potwierdzenia.
Nie przypisano im na tej podstawie etapu produkcyjnego.

Przykładowe dodatkowe kody: H7165/10Z, 37033/37034, F1692, C1341-30-33,
C1346, C1351, 41076, 41202, EG-0100/0300/0425/0581, W0962, 38081,
oraz oddzielne komponenty 17251S, 27083, 2643, 2605 i L905-915.
Nazwy CAD nie potwierdzają sufiksu wykończenia, nośności ani jednostki zakupowej.

## Katalog i krok 5

- Krok 4: filtr biblioteki bazowej / wariantów źródłowych oraz projektów M01–M07.
  Filtr projektu oznacza **zaobserwowanie kodu** w tym projekcie. Podpis obrazu
  podaje projekt rzeczywiście wybranego wariantu; nie obiecuje zgodności innych.
- 39 nowych renderów ma powiększenie. Dla rozproszonych zespołów pokazano
  opisaną podczęść; dla profili opisany fragment. Pełne wybrane poddrzewa
  zachowano w prywatnym pakiecie modeli. Liczba brył jest widoczna w szczegółach,
  osobno od liczby kompletnych produktów.
- Krok 5: wybrane warianty są w palecie, można wskazać ściankę, liczbę,
  symetrię, obrót i zapisać rozmieszczenie. Nazwy pokazują kod źródłowy, nie hash ID.
- Nowe warianty bez potwierdzonej ramy montażu używają **znacznika z renderem**.
  Nie ustawiamy bryły w domniemanej ramie wyprowadzonej z bbox. Istniejące
  przypięte siatki H7159/17251S w bazowej bibliotece zachowują swój osobny tor.
- Źródłowe zawiasy/zamki są oznaczone jako komponenty/zespoły, nie komplet SKU.
  Nie są automatycznie dodawane jako kompletny zawias do `joint_line`; backend
  również odrzuca taką próbę. Nadal można rozmieścić znacznik do przeglądu.
- Wybór zespołu i jego osobno wybranego podzespołu zgłasza ostrzeżenie przed
  podwójnym naliczeniem. Zapis draftu/JSON zachowuje dokładne ID i rewizje.

## Lokalne pakiety

`artifacts/studio-project-parts/`: `catalog.json`, `models/<ID>/model.json`,
`geometry.bin`, `images/index.json`, PNG oraz mapowanie renderowania.
Oryginały i pakiet roboczy zachowano; wcześniejszy przyrost jest w
`artifacts/studio-project-parts-before-nested/`.

`source_parts.py` wykrywa domyślny pakiet. Launcher może wskazać go przez
`--source-parts <catalog.json>` albo `ROCKPRO_SOURCE_PARTS`. Obrazy są pobierane
z sąsiedniego `images/`, sprawdzane przez istniejący loader SHA i udostępniane
tylko w sesji lokalnej. Brak pakietu pozostawia bibliotekę bazową.
Pakiet i eksporty klienta nie są commitowane; do przekazania na inne stanowisko
trzeba zachować je osobno. Dane pochodzenia w odpowiedzi HTTP nie zawierają
absolutnych ścieżek klienta.

## Sprawdzenie

PASS: natywny odczyt 9 scen / 4100 węzłów i zachowanie stanu/dysku.
PASS: 39 testów Studio/importu — hashe i wiązania, odmowa błędnego odczytu,
brak promowania zgód/SKU, zachowanie starych definicji i blokada automatycznego
montażu komponentu jako całego zawiasu.
PASS: przeglądarka — 53 wpisy, 39 dekodowanych renderów, filtry, źródłowy H7165/10Z
(4/ściankę), koło, osobny komponent, zapis SQLite i ponowne wczytanie.
Pełna regresja: `artifacts/verification/20261027T182440357005Z/`.
Raport i obrazy: `artifacts/other-project-parts-20261027/`.

Natywne wstawianie nowego wariantu, nowe ramy montażowe, wycięcia i zgoda
konstruktora: NOT RUN / wymagają osobnego odbioru.
