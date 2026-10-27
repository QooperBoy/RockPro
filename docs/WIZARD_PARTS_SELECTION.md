# Studio — krok 4: baza części i wybór okuć

27.10.2026. Krok 4 działa w `wizard.html` po typie, otwieraniu i wymiarach.
To wybór definicji do koncepcji. Rozmieszczanie na ścianach, liczby wystąpień,
kotwy oraz generowanie obróbek należą do następnego przyrostu.

## Istniejące dane

Biblioteka korzysta z zachowanego `docs/catalog/hardware-reference.json`
(rozpoznanie katalogowe z 21.10.2026), definicji prototypu zawiasu 27095
z `core_case/t1_mounting.py` oraz opisanej referencji koła z modelu Epson.
Nie pobiera nowych modeli, nie wykonuje SDK i nie uznaje dawnych opisów
za aktualną zgodę na produkcję. Pełny katalog firmy od Tomka nadal jest potrzebny.

| Kategoria | Pozycje |
|---|---|
| Uchwyty | H7159, H2026 |
| Zamki/zatrzaski | 17251S; alias CAD 17251S_1 nie jest osobnym zamkiem |
| Zawiasy | 27095, 270836, 2643 |
| Profile | EG-0113, EG-0500/1, EG-0500/2; aliasy z podkreśleniem są wyszukiwalne |
| Narożniki/wzmocnienia | 410429, B1930, B1121 |
| Piętrowanie | W0968Z |
| Koła | Referencja zespołu Epson, bez potwierdzonego SKU |

Łącznie 14 pozycji; 13 można zaznaczyć. 2643 jest widoczny, ale zablokowany:
w źródle to pusty zespół, więc nie przedstawiamy go jako dostępnej geometrii.
Koło ma wewnętrzne ID `source-caster-epson`, `sku=null` i nieznaną jednostkę
zakupową. Nie wymyślamy kodu, nośności ani dostępności magazynowej.

Nazwy/kody odnoszą się do rodzin i wariantów źródłowych. Nie odgadujemy sufiksów
wykończenia. Wszystkie pozycje mają `automatic_placement_approved=false`
i `production_approved=false`. Informacja o wycięciu rozróżnia wymagane
wycięcie od braku danych; nieznane nie oznacza niewymagane. Historyczna
obróbka T1 nie zatwierdza montażu tego SKU w dowolnej nowej konstrukcji.

## Interfejs

- Wyszukiwanie po kodzie, nazwie, kategorii, producencie i aliasie CAD.
- Kategorie oraz filtr „Pokaż tylko wybrane”.
- Karta części: opis, status wycięcia i danych montażowych, źródło oraz uwagi.
- Zaznaczanie rodzajów części i usuwanie z podsumowania przy modelu.
- Ostrzeżenie o brakującej połówce pary profili EG-0500 oraz o wybranym
  zawiasie przy zdejmowanych pokrywach. Program nie dodaje pary automatycznie.

Wybór części nie dodaje wystąpień do 3D, nie zmienia gabarytu ani nie zeruje
prezentacyjnego otwarcia i kamery. Zmiana typu konstrukcji zachowuje koszyk;
wybory są ponownie opisywane ostrzeżeniami, zamiast być po cichu usuwane.

Szczeliny i docięcia pozostają nieustalone. Po wyborze części komunikat
wymaga rozmieszczenia i potwierdzenia danych montażowych; samo zaznaczenie
profilu nie wystarcza do wyliczenia poprawnego połączenia. Nie powiększamy
gabarytu i nie wpisujemy fikcyjnego zera.

## Kontrakt i zapis

`studio_parts.py` jest adapterem istniejącej biblioteki. Kategorie używają
`part_registry`, więc zachowują wspólne rodziny i etapy CAD/obserwatora.
GET `wizard/parts` zwraca katalog `rockpro.studio-parts/1`, rewizję/hash,
definicje oraz jawny brak podłączonego magazynu i rozmieszczania.

Draft `rockpro.configurator/3` dostał opcjonalne, jawnie rozpoznane pole:

```json
{"hardware":[{"part_id":"H7159","revision":1}]}
```

Starszy v3 bez tego pola działa jako pusty wybór, bez wymuszonej konwersji.
Nie zmieniamy `CaseSpec` ani formatu dawnej galerii. Wybór ma stabilne ID
definicji i rewizję. Nie ma ilości zakupowej, pozycji świata ani ściany.
Nieznany ID/rewizja, duplikat, niedozwolona pozycja lub dopisane pola są
odrzucane. Aliasy służą wyszukiwaniu, nie tworzą nowych definicji.

Wybór przechodzi przez dotychczasowy zapis SQLite/CAS, historię rewizji,
odzyskiwanie przeglądarki oraz eksport/import JSON. Bieżące definicje mają
rewizję 1; przyszły import powinien zachowywać stare rewizje i podnosić numer
zmienionej definicji. To wersjonowane referencje, nie dowolny plik ICS z klienta.

`hardware_summary` w odpowiedzi planera pokazuje wybrane definicje i ostrzeżenia,
ale `placement_status=not_started`, `purchase_bom_ready=false`, `cad_ready=false`.
Suma wybranych rodzajów nie jest liczbą zamontowanych części ani zakupowym BOM.

## Weryfikacja

PASS: testy katalogu, aliasów, braku zgód, odmowy nieznanych definicji/rewizji,
duplikatów i pustego modelu; zapis i ponowny odczyt wyboru, zgodność starego v3,
brak wpływu na płyty/gabaryty oraz kontrola par profili.

PASS: przeglądarka/WebGL — wyszukiwanie, kategorie, checkboxy, blokada 2643,
usuwanie, filtr wybranych, zachowanie kamery/otwarcia/geometrii, SQLite i JSON,
zmiana typu bez utraty koszyka, nieznany SKU koła i układ 430 px.
Dowody prywatne: `artifacts/wizard-parts-20261027/browser-report.json` i PNG;
testowa baza jest odrębna od danych użytkownika.

Pełna regresja PASS: `artifacts/verification/20261027T150909063856Z/`.
Rozmieszczenie, natywny montaż, wycena/magazyn i produkcja: NOT RUN, poza zakresem.
