# Seria do przeglądu — 27.10.2026

Snapshot kodu przed pracą: `snapshot/studio-seria-20261027-792f40f`.
Na wyraźną prośbę użytkownika modele natywne wykonano w **IronCAD 2027**.

## Zapisane drafty Studio

W „Pliki i zapisane projekty” wybierz nazwę zaczynającą się od
„Przegląd 27.10”. Wszystkie pozycje zapisano w bazie Studio i wyeksportowano
do osobnych JSON-ów. Wymiary poniżej są wymaganym wnętrzem **korpusu**;
pokrywy są dodatkowymi sekcjami, nie wchodzą do tego wymiaru.

| Nr | Koncepcja | Wnętrze X × Y × Z [mm] | Pokrywy |
|---|---|---|---|
| 01 | Skrzynia transportowa | 600 × 500 × 800 | Górna 115 mm, zawiasowa |
| 02 | Skrzynia ze zdejmowaną górą | 750 × 500 × 900 | Górna 110 mm, zdejmowana |
| 03 | Szafa serwisowa | 700 × 500 × 900 | Przednia 110 mm, zawiasowa |
| 04 | Skrzynia trzyczęściowa | 800 × 500 × 800 | Górna 115 mm i przednia 110 mm |
| 05 | Wąska wysoka szafa | 400 × 450 × 1400 | Przednia 110 mm, zawiasowa |
| 06 | Głęboka skrzynia trzyczęściowa | 420 × 950 × 1000 | Górna 130 mm i przednia 110 mm |
| 07 | Szeroka skrzynia panoramiczna | 1500 × 450 × 800 | Górna 115 mm i przednia 110 mm |
| 08 | Płytka szafa | 900 × 300 × 1100 | Przednia 110 mm, zdejmowana |

Wszystkie: zielona sklejka #408080, nominalnie 9,8 mm. Domyślnie po dwa
uchwyty na każdym z przeciwległych boków. Wariant 08 ma jawnie po jednym
wycentrowanym uchwycie na bok, ponieważ boki są płytkie. Rzędy zatrzasków
i zawiasów korzystają z obecnej kontroli obrysów i równych rozstawów.
Nie wystąpiły nierozwiązane grupy ani ostrzeżenia o odstępach. Pozostają
ostrzeżenia `closure_reference`: dokładny montaż wymaga potwierdzenia.

## Zakres plików IronCAD

Modele 05 i 06 są nowymi, parametrycznymi **koncepcjami paneli**. Parametry
sceny i nazwy paneli są po polsku. Zmiana wymiarów korpusu, grubości i głębokości
pokryw aktualizuje rozmiary i położenia paneli. Przód trzyczęściowej skrzyni
licuje z górną płaszczyzną wieka. Rozmiary nie są formatkami produkcyjnymi.

**Nie przeniesiono jeszcze okuć, ich wycięć, profili, narożników, podstaw,
kół ani animacji do tych dwóch plików CAD.** Rozmieszczenia okuć pozostają
w draftach Studio. To nie jest ukończony eksport całego kreatora ani gotowy
projekt produkcyjny. Żaden odbiór konstruktora nie został oznaczony jako wykonany.

## Dowody

- `artifacts/studio-review-20261027/index.json`: identyfikatory i rewizje draftów.
- Foldery 01–08: draft, podgląd danych, formuły paneli, obrazy ze Studio
  w stanie zamkniętym i otwartym.
- `browser-results.json`: osiem scen, poprawne sekcje i widoczne wystąpienia,
  brak błędów JavaScript. Obrazy nie potwierdzają zatwierdzonej kinematyki.
- `native-07/result.json`: rzeczywisty IronCAD 2027; pomiar wszystkich paneli,
  zmiana wszystkich wymiarów, przywrócenie, zapis, ponowne otwarcie, ponowna
  zmiana wymiarów i pomiary. Stan dziewięciu wcześniej otwartych dokumentów
  zachowany. Nie zamykano cudzych niezapisanych dokumentów.
- `artifacts/verification/20261027T210518361688Z/results.json`: PASS pełnego
  harnessu offline. Pierwsza próba w sandboxie nie przeszła z powodu odmowy
  dostępu do plików tymczasowych; powtórzenie poza sandboxem przeszło.
- `scripts/test_studio_review_series.py`: osiem wariantów, formuły przy zmianie
  wymiarów, licowanie sekcji, brak duplikatów przy powtórzeniu i ochrona draftu
  zmienionego przez użytkownika. Testy korzystają z oddzielnej bazy.

Przy próbach natywnych wykryto dryf paneli przy skalowaniu wokół domyślnej
kotwy tworzonego wyciągnięcia. Adapter zeruje kotwę i transformację cechy
oraz jawnie ustawia skalowanie względem kotwy. Końcowe pomiary przeszły.
Nieudane próby zachowano w `native-01`–`native-03`; nie są finalnymi plikami.

## Powtórzenie i dalszy etap

`scripts/prepare_studio_review_series.py <nowy-folder-serii>` zapisuje nowe
drafty; powtórzenie z tym samym folderem używa istniejących identyfikatorów.
Nie uruchamiaj z nowym folderem tylko po to, żeby otworzyć już zapisaną serię.
Po zmianie draftu przez użytkownika skrypt zatrzymuje aktualizację zamiast
nadpisać jego pracę. Oryginały modeli nie są źródłem tego adaptera.

Adapter `scripts/native/StudioReview2027.cs` jest oddzielnym narzędziem
developerskim o kontrakcie `rockpro-studio-review-panels-v1`. Używa istniejącego
przypiętego mostka i blokady jednego wykonawcy CAD. Nie zmienia allowlist
ani kontraktów produkcyjnego MCP. Rejestr części i wycięcia nie mogą być
pominięte przy przyszłym rozszerzaniu go do pełnych projektów.

Następny etap: powiązany eksport pełnych okuć i ich operacji montażowych,
profile styków i luzowania sklejki, następnie podstawy i koła. Nietypowe półki,
walizkowy uchwyt, logo i integracja ERP/Excel nadal wymagają swoich etapów;
ta seria ich nie implementuje.
