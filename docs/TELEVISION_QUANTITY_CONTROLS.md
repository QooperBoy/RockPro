> Aktualizacja 31.10.2026: użytkownik wycofał parametryzację liczby okuć.
> Pola liczności opisane poniżej dotyczą zachowanych modeli historycznych.
> Nie rozwijać ani nie przenosić tego mechanizmu do nowych modeli. Wymiary,
> położenie i powiązane wycięcia pozostają w zakresie. Patrz CASE_DEFAULTS.md.

# Hisense R003 — liczba bocznych okuć

Rozszerzenie R002 na nowej kopii aktualnego modelu użytkownika. Snapshot
zachowuje jego zmianę głębokości do 772 mm i pozostałe wartości/równania.
Nie zmienia oryginału ani modeli otwartych wcześniej. R002 pozostaje dostępna.

## Obsługa

Tabela sceny otrzymuje sześć bezwymiarowych parametrów liczby:

- `RP_UchwytyKorpusLewa_Liczba`, `RP_UchwytyKorpusPrawa_Liczba`;
- `RP_UchwytyCzapkaLewa_Liczba`, `RP_UchwytyCzapkaPrawa_Liczba`;
- `RP_ZamkiLewa_Liczba`, `RP_ZamkiPrawa_Liczba`.

Liczba dotyczy jednej ściany i wskazanej sekcji, nie sumy całego projektu.
Uchwyty: całkowite 1–4; zamki: 0–4 kompletnych par. Domyślnie po 2.
Przód = ujemne Y, lewa = ujemne X. Boczne rzędy biegną wzdłuż głębokości Y.

Każdy rząd ma oddzielny rozstaw skrajnych osi. Środek uchwytów i wysokości
korzystają z istniejących parametrów pojedynczych uchwytów; opis określa teraz
środek rzędu. Jedna sztuka jest wyśrodkowana, większe liczby rozstawione równo.
W tej nowej kopii boczne uchwyty korpusu obniżono domyślnie do połowy wysokości,
aby pozostawić miejsce na nowe boczne zamki przy złączu.

## Mechanizm i zależność od dodatku

Gabaryty bazowego modelu pozostają sterowane natywnymi parametrami IronCAD.
Pozycje dodatkowych bocznych okuć, ich aktywność oraz dopasowanie wycięć
synchronizuje osobny komponent C# `RockPro Ilość okuć`.
To nie jest natywny szyk z nieograniczoną licznością ani działanie agenta AI.
Przygotowano po cztery wystąpienia; nadmiarowe wystąpienia i obróbki są
wygaszane. Nie traktuj zapisanych wygaszonych rezerw jako zakupowego BOM.

Komponent reaguje na zmianę parametrów w aktywnym oznaczonym dokumencie.
Obce dokumenty bez jawnego manifestu nie są zmieniane. Zakres i odstępy są
sprawdzane przed przełączeniem wygaszenia. Błąd jest pokazywany w tekstowym parametrze `RP_IloscOkuc_Status` oraz
zapisywany w `quantity-errors.log` obok DLL; nie ma osobnego panelu błędów.
Niepoprawny wpis należy poprawić, nie traktować widocznego stanu jako odbioru.

Bez uruchomionego komponentu plik zachowuje ostatnio zapisany układ, ale sama
zmiana pól liczby, rozstawu lub gabarytów nie przeliczy dodatkowych bocznych rzędów. W szczególności nie deklaruj
takiego działania na komputerze odbiorcy mającym sam plik ICS.

Budowanie: `Integracja/rockpro_cad/addin/Build-MountCounts.ps1`.
Rejestracja per-user dla 2027: `Install-MountCounts.ps1`; osobny GUID i DLL,
bez zastępowania istniejącego RockPro CAD. Po restarcie hosta służy do
automatycznego ładowania. Test bieżącego hosta i test autostartu po restarcie
muszą mieć oddzielne dowody.

## Powiązane obróbki

Nowe otwory wykorzystują dokładne kontury dostępnych operacji R002 przez
`CopyCurvesTo`; bez odczytu surowych buforów splajnów i bez skalowania SKU.
Nowe boczne zamki są obróconymi kopiami kompletnej pary źródłowej. Dwa otwory
w sklejce oraz wycięcia obu profili zachowują wspólną kotwę. Zmniejszenie liczby
wygasza również niepotrzebne otwory. Przednie i tylne rzędy R002 pozostają.

## Weryfikacja

Dowody lokalne: `artifacts/tv-counts-20261030/`. Oddzielnie zapisuj wynik
sprawdzenia geometrii, zapisu/otwarcia, autonomicznej synchronizacji liczby
oraz rejestracji/autostartu. Kontrola obrysów i konturów nie zastępuje pełnej
analizy kolizji BRep, nośności ani zatwierdzenia CNC. Zwiększenie głębokości
i liczby okuć nie tworzy trzech stanowisk telewizorów ani separatorów.

Uwagi wykonawcze: porównanie w wyrażeniach IronCAD używa `==`, nie `=`.
Samo zapisanie niepoprawnego wyrażenia przez SDK nie jest dowodem jego
wyliczenia. Kontrola porównuje rzeczywiste położenie każdego okucia z
niezależnie wyliczonym rozstawem. Wygaszenie przełączane jest zbiorczo przez
`SetSuppressStateMultiple`; przebudowywane są docelowe płyty/profile, a nie
wszystkie importowane bryły katalogowe. Kontroler sprawdza również stan
wygaszenia po cofnięciu operacji. Zbiorcze wywołanie SDK jest sprawdzane; gdy
nie przełącza stanu elementu, stosowane jest jawne SetSuppressState.

## Powtarzalne wykonanie

`scripts/prepare_tv_counts.py` przygotowuje prywatny, przypięty plan dla
zachowanego snapshotu użytkownika. `scripts/run_tv_quantity_pipeline.py PLAN
NOWY_FOLDER_DOWODOW` uruchamia kolejno `ConstructTvQuantities2027.cs` oraz
`CompleteTvQuantityModel2027.cs`. Etap pierwszy zapisuje wyłącznie części i
kontury ze statusem CONSTRUCTED_NEEDS_MATING_AND_TESTS. Dopiero drugi nadaje
powiązania geometryczne, wykonuje próby i zapisuje model do oceny.

Manifest v2 w pliku ICS zawiera stabilne ID, ramy okuć, lokalne punkty
odniesienia obróbek i oryginalne długości krzywych. Punkt odniesienia
wylicza się z linii/okręgów konturu; filletowe łuki zachowuje CopyCurvesTo
bez przybliżania i bez surowych buforów splajnów. Przesunięcie otworu jest
sprawdzane względem rzeczywistego okucia, nie początku lokalnej ramy feature.
Nazwy w drzewie można zmieniać: nie są kluczami logiki.

Każda wersja kontrolera ma nazwę zestawu wynikającą z hasha źródła, co zapobiega
użyciu wcześniej załadowanej DLL przez CLR. Instalator sprawdza hash i hosta,
rejestruje osobny komponent per-user; nie przeładowuje głównego RockPro CAD.

## Odbiór 30.10.2026

Powtarzalny potok od zachowanego oryginału: `artifacts/tv-counts-20261030/pipeline-01`.
Etap konstrukcji PASS, następnie osiem prób geometrii/montażu/zapisu/otwarcia PASS.
Osobny test zmieniający wyłącznie pola liczby i głębokości: automatyczne cztery
sztuki PASS, błąd dla pięciu PASS, automatyczny powrót do dwóch i zapis PASS.
Dowody `live-read4`, `live-error`, `live-save2`. Finalnie 49 parametrów, głębokość
772 mm i po dwie sztuki w sześciu bocznych rzędach. Maksymalny błąd punktu
montażowego wycięcia w ośmiu próbach: poniżej 0.000001 mm; jest to kontrola
przyjętych odniesień, nie deklaracja tolerancji wykonania produkcyjnego.

Repozytorium/backend/parts/core-design/core-contracts/QA/harness PASS:
`artifacts/verification/20261030T161032006612Z`. Natywne dowody są oddzielne od
offline harness. Zarejestrowano kontroler per-user dla 2027; bieżąca sesja
działa, restart/autostart nadal NOT RUN, aby zachować niezapisane projekty.

Budowanie tej wersji: `Build-MountCounts.ps1 -OutputFolder bin-counts-v8-2027`;
rejestracja: `Install-MountCounts.ps1 -BinaryFolder bin-counts-v8-2027`. Plik ICS,
snapshot, mapa ID i parametry CSV są w lokalnym folderze projektu, poza Gitem.

Diagnostyka przed finalnym potokiem jest zachowana w prywatnych artifacts.
Wykryto m.in. odrzucanie wyrażeń przez SDK bez wyjątku, konflikt tożsamości
wcześniej załadowanej DLL, nieskuteczne zbiorcze wygaszenie i odczyt hasha
otwartego ICS bez FileShare.Write. Finalny kontroler oblicza pozycje w C#,
sprawdza stany po zbiorczym wywołaniu i w razie potrzeby ustawia je indywidualnie;
pliki hashuje z FileShare.ReadWrite/Delete. Nie promowano błędnych prób jako
gotowych modeli.


## Poprawka R004: pojemność ścianki i wspólne podwozie

Reguła liczności dla dodatniej liczby `n`:

```
n * w + (n - 1) * g + m_lewy + m_prawy <= L
```

`w` to pełna szerokość montażowa sztywnego okucia w kierunku rzędu;
`g` to minimalny odstęp, `m` margines krawędzi, a `L` dostępna długość.
Dla jednakowych marginesów maksymalna pojemność wynosi
`floor((L - 2*m + g)/(w + g))`, co najmniej zero. Dodatkowo kontrolowane są
rzeczywiste położenie środka i rozstaw osi: skrajny obrys musi pozostać w
marginesach, a odstęp sąsiednich osi wynosi co najmniej `w + g`.
Pojemność geometryczna i liczba zbudowanych wystąpień CAD to osobne wartości.

Dla istniejącego bocznego rzędu H7159: L=772 mm, w=161 mm, g=m=12 mm.
Cztery sztuki zajmują minimum 704 mm, pięć 877 mm. Przy rozstawie skrajnych
osi 532 mm cztery sztuki mają odstęp osi 177,33 mm, wymagany co najmniej 173 mm.
Wystąpienia rezerwowe w R003/R004 nadal ograniczają model do czterech na rząd;
na większej ściance kontroler rozróżnia tę granicę od braku miejsca.

Nieprawidłowy rząd zachowuje ostatnią poprawną geometrię i zgłasza błąd.
Pozostałe poprawne rzędy są stosowane wraz z obróbkami. Parametr żądanej
liczby nie jest automatycznie przycinany. Przy wpisie 5 widoczny stan ostatniej
poprawnej liczby nie jest akceptacją pięciu okuć. Po zapisie/otwarciu status
kontrolera nadal sygnalizuje ten problem.

Ta walidacja rzędu nie jest pełnym testem wszystkich kolizji BRep ani
wielorzędowym algorytmem omijania dowolnych innych okuć. Znane strefy profili,
narożników i pozostałych części muszą stanowić wejście rozszerzanego planera;
nie wolno deklarować ich sprawdzenia na podstawie samego bilansu długości.

Podwozie R004 ma dwa podłużne wsporniki 120 mm × (głębokość dna − 70 mm)
× 18 mm i cztery sztywne koła. Pięć parametrów `RP_Podwozie_*` reguluje
szerokość/grubość podpory, margines końca, odsunięcie od boku i odsunięcie osi
koła od końca podpory. Wsporniki dotykają dna; płyty kół dotykają spodu
wsporników i mieszczą się w ich obrysie. Grupa ma wspólną receptę montażową
w manifeście i jest przeliczana przez ten sam kontroler. Nie jest to fizyczne
związanie mechaniczne/nośnościowe ani skalowanie zespołu kół.

Regresja użytkownika: kontroler nie był załadowany w nowym PID 31852, a jego
rejestracja COM była nieobecna w rejestrze widzianym przez hosta. Testy R003
wykonywano po ręcznym uruchomieniu kontrolera w poprzednim procesie; nie
obejmowały restartu ani rzeczywistego przycisku Zastosuj. Dodatkowo dawny
Apply odrzucał wszystkie rzędy przy jednym błędnym wpisie. To były braki
implementacji i zakresu weryfikacji, nie ręczne przestawienie okuć przez AI.

Dowody R004: `artifacts/tv-counts-20261030/snapshot-r003` (zmiany użytkownika),
`repair-r004` (pierwszy montaż), `check-r004b` (sześć prób geometrii, liczności,
wycięć i ponownego otwarcia). `Test-MountRowLayout.ps1` sprawdza jedenaście
przypadków rachunkowych bez hosta. Wyniki autostartu i UI zapisuj osobno.


Dodatkowa przyczyna wykryta podczas testu restartu R004: IronCAD zapisuje
włączenie aplikacji pod **dokładną nazwą** z klucza COM `Name`.
Instalator używał `RockPro Ilość okuć`, podczas gdy zarejestrowana nazwa to
`RockPro — Ilość okuć`. Wpis aplikacji miał LoadOnStartup=1, ale właściwa
pozycja w menedżerze była odznaczona. Poprawiono instalator, zachowując stary
wpis; nie usunięto wcześniejszych ustawień. Dowód różnicy zapisanej przez hosta:
`registry-enable.diff`. Samo utworzenie serwera COM nie potwierdza autostartu.

Rzeczywista tabela parametrów i przycisk Zastosuj: zmiana lewego rzędu uchwytów
korpusu z trzech do jednego przeliczyła okucia i wycięcia mimo pozostawienia
błędnego żądania pięciu uchwytów na prawej czapce. `ui-read/result.json`: jedna
aktywna sztuka, pozostałe poprawne rzędy zgodne, zero ręcznych wywołań Apply,
Start lub Load. Po teście przywrócono żądane trzy sztuki. To oddzielny dowód
od wcześniejszych prób setterów SDK.


Końcowy autostart R004 **PASS**: drugi pełny restart, PID 3364, automatycznie
załadowany zestaw `RockPro.MountCounts_5A6E91DC8DF2` 0.9.0.0, aktywny timer,
bez ręcznego Load/Start: `startup2-probe/result.json`. Końcowy odczyt
`final-read/result.json`: żądane/aktywne rzędy 3/3, 4/4, 1/1, 4/4, 5/4, 3/3.
Żądanie 5/4 jest jawnie błędne; cztery to ostatni poprawny stan, a nie
zaakceptowana realizacja piątki. Zapisano 54 parametry i zachowano oryginalne
żądanie użytkownika. Model jest do przeglądu, z jednym błędem liczności.

Offline siedem grup PASS: `artifacts/verification/20261030T214013773443Z`.
Wcześniejsze nieudane przebiegi zachowano: jeden zatrzymał się na uprawnieniach
katalogu tymczasowego sandboxa, drugi na globalnej blokadzie CAD, gdy testy
atrap uruchomiono podczas pracy natywnego wykonawcy. Końcowy przebieg wykonano
sekwencyjnie. Pierwszy pomocniczy zapis przed restartem po zamknięciu dokumentów
zgłosił null przy odczycie pustej listy SDK; snapshot i plik były już zapisane.
Kolejna próba obsłużyła null, potwierdziła zero dokumentów i zakończyła się PASS
(`pre-restart2`). Nie zmieniono kryteriów testów montażu dla uzyskania PASS.
