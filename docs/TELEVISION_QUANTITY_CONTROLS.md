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
