# Studio — trzy typy i licowanie przodu

Aktualizacja: [szczelina i docięcie jako wynik doboru okucia](WIZARD_JOINT_DIMENSIONS.md).
Ręczna szczelina została usunięta; obecny format draftu to v3.

27.10.2026. Zmiana wymagań po obejrzeniu kreatora: brak wyboru podtypu.
Zastępuje wcześniejszy katalog typów/podtypów w kroku 1.

## Obecne typy

| Typ | Sekcje i otwieranie |
|---|---|
| Skrzynia | Korpus i jedno górne wieko: otwierane na zawiasach po jednej stronie lub zdejmowane; wybór w kroku 2 |
| Szafa | Korpus i jedna powłoka przednia, otwierana na zawiasach z lewej/prawej albo zdejmowana |
| Skrzynia 3-elementowa | Korpus, zdejmowana góra i zdejmowany przód |

Nie ma podtypów, dwojga drzwi ani swobodnego dodawania kolejnych pokryw.
Liczba i ściany sekcji wynikają z typu; backend sprawdza tę samą regułę co UI.
Biblioteka siedmiu istniejących modeli pozostaje zachowana jako zbiór wzorców.

W kroku 2 można nazwać sekcje, wybrać zdejmowane wieko dla Skrzyni, ustawić stronę zawiasów dla elementu otwieranego
oraz współpracę dwóch zdejmowanych pokryw. W kroku 3 pozostają wymiary wnętrza
korpusu, sklejka i osobne wysokość góry/głębokość przodu (dopasowanie złączy jest wynikiem późniejszego doboru okuć). Wysokość
przedniej powłoki jest wynikiem powiązania, nie niezależnym wymiarem do ręcznego
wyrównywania. Reguła płytkiego wieka i jawnego odstępstwa dotyczy typu Skrzynia;
nie ogranicza wysokości zdejmowanej góry w konstrukcji 3-elementowej.

## Usunięty uskok

Poprzednio przód miał wysokość samego korpusu, a górna pokrywa znajdowała się
wyżej. Dla konstrukcji 3-elementowej:

```text
H_korpusu_zewn = H_wnętrza + 2 × grubość_sklejki
H_przodu = H_korpusu_zewn + H_górnej_pokrywy
Z_dół_przodu = Z_dół_korpusu
Z_góra_przodu = Z_góra_górnej_pokrywy
```

Reguła buduje rzeczywiste płyty podglądu, nie tylko opisy wymiarów. Przód rośnie
po zmianie góry; wymagane wnętrze i korpus nie są po cichu powiększane.
Szczelina koncepcyjna między przodem a korpusem/górą pozostaje zachowana.
To schemat bez montażowych tolerancji i profili aluminiowych, nie odbiór CAD.

## Drafty i archiwum

Nowy format: `rockpro.configurator/2`, bez pola `subtype`. Format v1 i jego
historia w SQLite nie są przepisywane. Klucz odzyskiwania w przeglądarce ma
wersję v2; stary klucz v1 pozostaje zachowany.

Wczytanie archiwalnego draftu pokazuje wybór pobrania oryginalnego JSON albo
jawnego przekształcenia jako nowej koncepcji. Dawny układ góra/przód staje się
typem 3-elementowym: obie pokrywy są zdejmowane, a przód zostaje wyrównany.
Konwersja nie przejmuje ID ani rewizji starego rekordu. Dwoje drzwi i inne układy
spoza trzech typów są odrzucane z informacją o zachowaniu oryginału.
Backend odmawia zapisu v2 nad archiwalnym rekordem nawet z poprawną rewizją.

## Sprawdzenie

- PASS: testy trzech typów, odmowy podtypu/dwojga drzwi, wysokości rzeczywistych
  płyt i zachowania wnętrza po zmianie parametrów; zapis, rewizje i konwersja.
- PASS: przeglądarka/WebGL — brak selektora podtypu, dokładnie trzy typy,
  szafa ze zdejmowanym frontem, dwie zdejmowane pokrywy, licowanie siatek po
  zmianie parametrów, zapis/odczyt, JSON v2, zachowanie v1 i układ 430 px.
- Prywatne dowody: `artifacts/wizard-three-types-20261027/`, w tym
  `browser-report.json` i `flush-3d.png`. Testy zapisują do izolowanej SQLite.
- PASS: pełna regresja `artifacts/verification/20261027T143225058126Z/`
  oraz wejście do głównego Studio — trzy typy, trzy sekcje wariantu
  zdejmowanego i brak selektora podtypu (`production-studio.png`).
- CAD/native i generowanie ICS: NOT RUN, poza zakresem tej poprawki Studio.

Aktualizacja: tryb „Wieko zdejmowane” w typie Skrzynia zapisuje się w drafcie
i pokazuje odsunięcie wieka w górę bez obrotu. Powrót do zawiasów zachowuje
wybraną stronę osi. Testy zapisu, odtworzenia i WebGL: PASS; dowody prywatne
w `artifacts/wizard-removable-lid-20261027/`. Pełna regresja:
`artifacts/verification/20261027T143857690685Z/`.
