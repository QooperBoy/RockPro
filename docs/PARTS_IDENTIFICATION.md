# Identyfikacja rodzin części — wynik researchu

Stan 21.10.2026. Rozpoznano 12 kodów katalogowych (dwie połówki EG-0500 liczone oddzielnie) z głównego drzewa modelu. Poniżej są identyfikacje kodów i funkcji, nie zatwierdzona biblioteka do automatycznego montażu. Parametry wiercenia, konkretne warianty i zgodność geometrii wymagają dalszej walidacji.

| Kod / alias CAD | Rozpoznanie | Producent i źródło | Uwagi |
|---|---|---|---|
| EG-0500_1 | Profil zamykający męski | [Penn Elcom](https://www.penn-elcom.com/ad/flight-case-hardware/extrusions?manufacturer=Penn+Elcom&p=2&view_all=true) | Przekrój nominalny pod płytę 9,5 mm; para z EG-0500/2. Oznaczenie CAD _1 dopasowane do /1; przed automatyzacją potwierdzić przekrój. |
| EG-0500_2 | Profil zamykający żeński | [Penn Elcom](https://www.penn-elcom.com/es/extrusion-de-ranura-de-9-5-mm-compatible-con-extrusion-de-lengueta-por-ejemplo-0500-1-2m-por-ejemplo-0500-2-2m) | Rowek 9,5 mm; para z EG-0500/1. Nie utożsamiać głębokości rowka z grubością płyty. |
| EG-0113 | Kątownik ochronny krawędzi | [Penn Elcom](https://www.penn-elcom.com/flight-case-hardware/extrusions/single-angle-extrusions?p=2) | Rodzina profilu o ramionach 35 mm. Model ma odcinki różnej długości, a nie jedną sztangę. |
| 410429 | Narożnik kulkowy trójramienny | [Adam Hall](https://www.adamhall.com/shop/en/flight-case-material/corners-l-corners/ball-corners) | Wariant pod kątownik 35 mm, 9 otworów. Kod i rola rozpoznane; nie certyfikuje zgodności geometrii modelu. |
| B1930 | Kątownik wzmacniający z przetłoczeniami | [Penn Elcom](https://www.penn-elcom.com/4-hole-brace-with-strengthening-ribs-355mm-x-40mm-b1930) | Katalog: 4 otwory, stal 1,2 mm, 35,5 × 40 mm. Wymiary katalogowe nie są automatycznym pomiarem obrysu po obrocie. |
| B1121 | Kątownik wzmacniający czterootworowy | [Penn Elcom](https://www.penn-elcom.com/4-hole-brace-31-2mm-x-40mm-b1121) | Katalog: 31,2 × 40 mm, 4 otwory, stal 1,2 mm; nakładany na profile 30 × 30 mm. Inny wariant niż B1121/20. |
| 2643 | Mały zawias typu L | [Adam Hall](https://www.adamhall.com/shop/es/piezas-de-flightcase/bisagras-y-bloqueos/bisagras) | Katalog: szerokość 48 mm. W tym modelu wpis 2643 jest pustym zespołem, bez dzieci; nie liczyć jako aktywnego fizycznego zawiasu. |
| H2026 | Uchwyt narożny | [Penn Elcom](https://www.penn-elcom.com/us/corner-handle-with-tight-radius-h2026-series) | Rodzina o małym promieniu wewnętrznym 1 mm. Sufiks wykończenia nie wynika z nazwy CAD. |
| H7159 | Uchwyt wpuszczany ze sprężynami | [Penn Elcom](https://www.penn-elcom.com/heavy-duty-medium-recessed-handle-with-rivet-protection-h7159-series) | Rodzina z ochroną nitów, podwójną sprężyną i 10 otworami. Wariant wykończenia/nośność całego montażu wymagają odrębnej weryfikacji. |
| 17251S, 17251S_1 | Duży zamek motylkowy | [Adam Hall](https://www.adamhall.com/shop/as-en/flight-case-material/latches/butterflies/318/17251-s) | Katalog: miseczka stopniowana 14 mm, sprężyna. Górę i dół modelu traktować jako podzespoły jednej pary; nie sumować jako czterech kompletnych zamków. |
| 270836, 270836_góra | Zawias z ogranicznikiem pokrywy | [Adam Hall](https://www.adamhall.com/shop/pl/materialy-flightcase/zawiasy-i-ograniczniki/ograniczniki-w-miseczce) | Duży, stopniowany. W modelu rozdzielony na górę i dół. Nie przypisywać funkcji Click-Stop wariantu 270837 do 270836. |
| PN - W0968Z | Wpustowa miseczka pod koło do piętrowania | [Penn Elcom](https://www.penn-elcom.com/de/flightcase-material/rollen-rader/einbauschalen-fur-rollen) | Katalog producenta 2019 podaje 136 × 90 mm. Model ma ten sam rzut. Nie oznacza to sprawdzenia dopasowania konkretnego koła ani nośności stosu. |

## Co rozpoznano w pozostałych pozycjach

- `konstrukcja`: zespoły płyt konstrukcyjnych góry i dołu.
- `Srodek`: piana na projektor, przegroda na pilot oraz przegroda mała i duża. Brak potwierdzenia gatunku pianki.
- `koła`: cztery złożenia kół oraz dwie podkładki montażowe. Sam kod zakupowy koła, jego producent i nośność są nieustalone.
- `Zespół1`: importowane obiekty SKP; prawdopodobnie urządzenie referencyjne. Dokładnego produktu nie potwierdzają nazwy ani opisy BOM.
- `Część2648`: własna bryła z wycięciem, nie katalogowe okucie. Nie przypisano materiału ani funkcji bez dowodu.

## Wnioski dla integracji

1. Rozdzielić definicję produktu od jego wystąpień i od technicznych węzłów geometrii. Jeden zamek ma wiele elementów, a połówki pokrywy/dołu tworzą parę.
2. W źródle pola BOM są puste; nazwy katalogowe występują w drzewie. Nie tworzyć identyfikacji wyłącznie przez automatyczne odczytanie BOM.
3. Materiały CAD są niespójne z katalogami: liczne stalowe okucia oznaczono aluminium, płyty mają etykietę PVC. Oddzielić materiał modelu od materiału zakupowego, nie poprawiać oryginału automatycznie.
4. Wpis 2643 jest pustym zespołem; obecność nazwy nie dowodzi obecności fizycznego zawiasu.
5. Importowane obrysy bywają puste albo skrajnie nieprawidłowe. Walidować rozmiary przed planowaniem skrzyni.
6. Automatyczne wstawianie jest wyłączone w danych referencyjnych. Następny etap: zgodność modelu z rysunkiem, lokalne osie, płaszczyzna mocowania, wycięcia i parowanie.

## Pliki

- [Strukturalny katalog referencyjny](catalog/hardware-reference.json): nazwy PL/EN, aliasy, funkcje, źródła i status weryfikacji.
- Szczegółowe dane konkretnego modelu pozostają lokalnie: `Integracja/parts/Epson_rozpoznanie_czesci.html`, `.md`, `Epson_czesci_do_opisania.csv`, `Epson_identification.json`, `Epson_native_inventory.json` w lokalnym wdrożeniu autora.

## Weryfikacja

Odczytano API do głębokości 5, zapisano 1143 węzły i sklasyfikowano wszystkie 24 grupy nazw głównego drzewa. To odczyt ograniczony głębokością, nie pełna rekursja wszystkich operacji wewnętrznych. Dane katalogowe pochodzą ze stron i katalogów producentów. Oględziny wykonywano w otwartym źródle tylko do odczytu; nie zapisano źródłowego ICS. Nie zmieniono kodu dodatku ani schematu bazy. Raport nie jest produkcyjnym BOM.
