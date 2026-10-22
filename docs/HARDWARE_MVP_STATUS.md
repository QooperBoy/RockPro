# Okucia — zakres i dowody MVP

Ten dokument oddziela obliczony plan od rzeczywiście zapisanego modelu CAD.
Stan odbioru odnosi się do konkretnego przebiegu, nie do wszystkich przyszłych
wymiarów ani do gotowości produkcyjnej. Bieżące modele i raporty klienta są
lokalne, w ignorowanym `artifacts/`; nie należą do paczki kodu w Git.

| Rodzina | Co mamy | Potwierdzenie | Kolejny krok |
|---|---|---|---|
| Narożniki 410429 | Osiem źródłowych części, zachowane warianty i orientacje; reguła zmiany położenia względem naroży | Model A: natywny zapis i otwarcie PASS. Pełny odbiór wariantu B i powrotu C nie jest ukończony | Odbiór zmiany wymiarów i wyglądu |
| Uchwyty H7159 | Kopiowanie całych zespołów i symetryczna para w osobnym POC | Historyczny POC A/B/powrót oraz pokaz wnętrza mają zapisane raporty; nie oznacza to integracji wszystkich okuć w jednym generatorze | Włączenie potwierdzonego assetu do wspólnego montażu |
| Zatrzaski 17251S / 17251S_1 | Dwie rzeczywiste pary na kopiach A 914×602×352 i B 1100×720×410 mm; połówki przemieszczane razem | Świeży odczyt czterech zespołów, montaż, całe obrysy/orientacje, symetria, zapis/otwarcie PASS w przebiegu `latch17251-inprocess-native-20261022-09`. Własne dokumenty zamknięte; źródło niezmienione | Ocena wyglądu przez użytkownika, następnie włączenie wykonawcy do stałego dodatku |
| Zawiasy 270836 / 270836_góra | Podgląd dwóch par, wspólnego ruchu połówek i zmiany gabarytu | Trzy podstawowe testy obliczeń PASS. Podgląd jest zablokowany do świeżego potwierdzenia transformacji źródła; montaż natywny NOT RUN | Potwierdzenie orientacji przez API, potem montaż na kopii |
| Kątowniki B1930 | Rozpoznana osobna rodzina wzmocnień | B1930 nie jest zawiasem; nie wolno podstawiać go do planera zawiasów | Osobne reguły wzmocnień |
| Koła i gniazda W0968Z | Rozpoznane cztery gniazda i cztery zespoły kół; podgląd symetrycznej siatki gniazd | Trzy podstawowe testy obliczeń PASS. Brakuje transformacji dwóch kół i kotew styku; podgląd zablokowany, montaż natywny NOT RUN | Odczyt brakujących transformacji i potwierdzenie par koło–gniazdo; środek obrysu nie zastępuje punktu styku |
| Profile i wzmocnienia | Podgląd 28 części w sześciu zespołach; profile wydłużane przy stałym przekroju, B1930 przemieszczane sztywno | Uruchomienie podglądu PASS. Dziesięć brakujących macierzy; brak potwierdzonych osi cięcia i przypisania krawędzi. Resize zablokowany | Świeży odczyt; potwierdzenie przekrojów, osi wydłużania, długości i zakończeń |

## Zasady odbioru następnego przyrostu

1. Okucie jest kompletną częścią albo zespołem. Nie edytujemy jego otworów,
   nitów, szkiców ani historii modelowania.
2. Sprawdzamy tożsamość źródła, orientację, środek obrysu i położenie względem
   ściany/krawędzi. Symetria obejmuje całą grupę, nie tylko jej średni środek.
3. Połówki jednego zatrzasku lub zawiasu zachowują wspólny ruch i wzajemne
   położenie. Symetrię należy oceniać na ustalonych punktach montażowych;
   początek lokalnego układu części nie musi pokrywać się z jej środkiem.
4. Wystarczą podstawowe sprawdzenia: wariant bazowy, jedna zmiana gabarytu,
   zapis i ponowne otwarcie. Wygląd ocenia użytkownik; dalsze testy wynikają
   z konkretnego błędu. Nie dodajemy rutynowych audytów BRep.
5. Wszystkie zmiany trafiają do nowych kopii. Własne dokumenty zamykamy także
   po błędzie, zachowując zmodyfikowany prototyp w osobnym pliku. Nie zamykamy
   nieznanych dokumentów użytkownika i nie aktywujemy okien.

## Bieżący problem połączenia

Szczegóły diagnozy i dokładny stan prób są w
[LATCH_PLACEMENT_POC.md](LATCH_PLACEMENT_POC.md).
Program działa, lecz zewnętrzny dostęp do `IZBaseApp` zwraca `E_NOINTERFACE`.
Potwierdzono rozbieżność między wymaganiem metadanych 12.0 w komponentach ATL
a metadanymi 29.0 w instalacji. Samo utworzenie lokalnych metadanych zgodności
nie potwierdziło naprawy działającego hosta. Nie podłączamy eksperymentalnego
narzędzia zgodności automatycznie do instalatora.

Start osobnego serwera `/Automation` wymagał ręcznego potwierdzenia wersji
testowej i zakończył się przekroczeniem czasu; nie należy ponawiać go w pętli
pod nieobecność użytkownika. Alternatywa w trakcie sprawdzania to mały,
udokumentowany dodatek wykonywany wewnątrz działającego hosta. Ta ścieżka
wykonała już natywny POC A/B zatrzasków. **Nie oznacza to naprawy zewnętrznego
COM ani podpięcia stałego wykonawcy do MCP.**

Przebieg `09` zachował foreground, kontekst i SHA źródła w obu fazach;
wcześniejsze nieudane próby i komunikat wymagający zamknięcia przez użytkownika
pozostają w logach. Oba ICS i osobne snapshoty są lokalnie w katalogu przebiegu.
Skrzynie mają 10 prostych płyt zastępczych, 8 rzeczywistych narożników oraz
4 całe zespoły połówek zatrzasków. Nie zawierają jeszcze wszystkich profili
i pozostałego wyposażenia Epsona. A/B jest regeneracją z wymiarów, bez trwałych
wiązań natywnych. Wygląd: **NOT RUN**; gotowość produkcyjna: **niezatwierdzona**.

## Krótki odbiór użytkownika

1. Otwórz lokalny `POC_zatrzaski_A_914x602x352.ics` z przebiegu `09`.
   Sprawdź dwie pary zatrzasków na przedniej ścianie i ich położenie przy podziale
   pokrywy. Nie otwieraj oryginału do tego testu.
2. Zamknij A i otwórz `POC_zatrzaski_B_1100x720x410.ics`. Sprawdź zachowanie
   wielkości okuć, parowania połówek i symetrii. Środki obu grup pozostają
   około 150 mm od odpowiednich bocznych krawędzi.
3. Przekaż uwagi o wyglądzie i osadzeniu. Nie oczekuj jeszcze automatycznego
   przeliczenia tych okuć po ręcznej zmianie tabeli parametrów tego POC.

## Kostka 1000 × 1000 × 1000 mm

Przebieg `artifacts/cube1000-native-20261022-01/`: **PASS**.
Zewnętrzny gabaryt konstrukcji ze sklejki wynosi 1000 mm w każdej osi;
okucia mogą wystawać poza ten obrys. Model zawiera 10 płyt zastępczych,
8 rzeczywistych narożników 410429, 4 całe połówki zatrzasków 17251S
oraz 2 całe uchwyty H7159. Uchwyty umieszczono symetrycznie na przedniej
ścianie, na połowie wysokości dolnej części skrzyni. Nie wykonano wycięć.

Pomiary całych okuć, symetria, zapis i ponowne otwarcie: PASS.
Źródło niezmienione, pomocnicze dokumenty zamknięte. Niezapisana scena
użytkownika zachowana. Po odbiorze, na wyraźne polecenie użytkownika,
osobno otwarto `delivery/RockPro_skrzynia_1000x1000x1000.ics` i celowo
pozostawiono tylko ten wynik do oglądania. To wyjątek od zamykania własnych
prototypów dotyczący wskazanego pliku, nie zgoda na pozostawianie helperów.

Runner obsługuje teraz opcjonalne `--single-size 1000 1000 1000`
i `--handle-proof` ze sprawdzonym raportem H7159. Domyślne A/B pozostaje.
Jawne `--preserve-dirty-context` zachowuje niezapisany dokument, także pustą
scenę: przytrzymuje jej referencję COM i kontroluje stan zamiast wymuszać zapis.
Nie deklaruje zgodności niezapisanej pamięci z plikiem na dysku.

## Kod i dalsza praca

- [Reguły narożników](../Integracja/rockpro_cad/core_case/corner_mount.py)
- [Reguły zatrzasków](../Integracja/rockpro_cad/core_case/latch_placement.py)
- [Wykonawca zatrzasków](../Integracja/rockpro_cad/core_case/latch_native.py)
- [Runner A/B](../scripts/accept_latch17251_poc.py)
- [Podgląd zawiasów](HINGE_PLACEMENT_POC.md)
- [Podgląd kół i gniazd](WHEELS_SOCKETS_POC.md)
- [Inwentarz profili i wzmocnień](PROFILES_BRACES_POC.md)
- [Proponowany wykonawca wewnątrz CAD](ADR_INPROCESS_CAD_EXECUTOR.md)
- [Katalog części](PARTS_CATALOG_PLAN.md)

Nie oznaczaj całego ROC-17 jako ukończonego na podstawie oddzielnego POC.
Nie utożsamiaj planu offline, działającego MCP ani kompilacji dodatku
z potwierdzeniem działania montażu w IronCADzie.
