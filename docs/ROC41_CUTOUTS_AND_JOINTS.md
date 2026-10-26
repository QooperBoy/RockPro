# ROC-41 — wycięcia okuć i pasowanie profili

Data: 26.10.2026. Status: częściowo wdrożony prototyp natywny T1.
48 obróbek, powiązania parametrów i testy zapisu/otwarcia opisuje
[T1_MACHINING_PROTOTYPE.md](T1_MACHINING_PROTOTYPE.md).
Poniższy plan nadal obejmuje szerszą bibliotekę, obsługę ręcznej edycji i podgląd;
nie wszystkie jego kryteria odbioru są zakończone.
Rozwinięcie [ROC-41](https://linear.app/rock-pro/issue/ROC-41/po-mvp-wyciecia-pod-okucia-i-styki-profili-aluminiowych)
na podstawie trzech oznaczeń użytkownika i doprecyzowania o bibliotece oraz etapach.
Identyfikatory M01–M08 i N01–N02 poniżej są
lokalnymi pozycjami planu, nie numerami nowych zgłoszeń Linear.
Publikacja w Rock_Pro: PENDING_ACCESS; dostępny konektor zwraca tylko Modivo.

## Wymagania i wzorzec

1. **Uchwyt i wycięcie stanowią jedno powiązanie montażowe.** Każdy SKU/wariant
   ma własny kontur, promienie, głębokość i dopuszczalne materiały/grubości.
   Zmiana położenia lub orientacji uchwytu aktualizuje wycięcie. Wymiana SKU
   zmienia szablon wycięcia, a usunięcie uchwytu usuwa tylko przypisaną obróbkę.
2. **Zatrzask ma własny zestaw obróbek.** Może obejmować obie strony złącza,
   sklejkę i wskazane odcinki profili. Nie zakładać, że wystarczy jeden otwór
   prostokątny ani że każda połówka wymaga tego samego wycięcia.
3. **Złącze wynika z przekrojów i baz montażowych.** Sklejka ma prawidłowo
   wejść w profil; zamknięcie ustala para profili. Krawędź sklejki nie może
   zatrzymać zamknięcia przed właściwym zetknięciem metalowych powierzchni.
   Przerwy, podfrezowania i zakończenia profili muszą być parametryczne.
4. **Uchwyt nie nachodzi na zawias.** Dobór i położenie uwzględniają skraj
   zawiasu, jego mocowania oraz przestrzeń ruchu. Nie naprawiać kolizji
   dodatkowym przypadkowym wycinaniem płyty/profilu. Utrzymać żądaną liczbę
   uchwytów i symetrię; brak miejsca oznacza konflikt lub propozycję innego SKU.
5. **Konstruktor zna wymagane obróbki już przy doborze części.** Wspólna
   biblioteka pokazuje, czy element wymaga wycięcia w sklejce, jaki szablon
   stosuje i czy dane są zweryfikowane. Brak informacji nie oznacza braku wycięcia.
6. **Etap dodaje okucie razem z jego wycięciami.** Dotyczy uchwytów, zatrzasków
   i każdej kolejnej rodziny wymagającej obróbki. Dodatek, obserwator i podgląd
   korzystają ze wspólnej definicji powiązań i rozszerzalnej kolejności etapów.

Użytkownik wskazał model `AI_CAD/T_1/Epson EB-L630U.ics` jako poprawny wzorzec
konstruktora. Dwie podane ścieżki są identyczne: to jeden wskazany plik, a nie
dwa niezależne dowody. Zrzut opisuje role 1/2/3, ale nie daje wymiarów,
tolerancji ani pewnego przypisania do rewizji pliku. Nie wyliczać ich z pikseli.
Pełna ścieżka, hash i materiał graficzny pozostają w prywatnym
`artifacts/roc41-planning-20261026/`. Aktualizacja: odczyt kopii T1 i zachowanej
wersji z H7159 wykonany przez SDK w `artifacts/roc41-native-20261026/`.

Zakres dotyczy obróbki płyt i wskazanych profili; gotowe uchwyty i zamki
pozostają sztywne. Nie przebudowujemy historii wnętrza modeli katalogowych.

## Co już istnieje, a co trzeba dodać

| Istniejący element | Znaczenie i luka |
| --- | --- |
| `core_case/contracts.py` | Wersje, źródła wymiarów i obrysy urządzenia/wnętrza/sklejki/transportu. Brak kontraktu konturów obróbki i pasowań. |
| `core_case/planner.py` | Plan obliczany przed CAD, kontrola mieszczalności i ręcznych zmian. Trzeba rozszerzyć o technologię, nie przenosić obliczeń do UI lub agenta. |
| `core_case/profile_rules.py` | Długości i pozycje profili oraz `RP_JointGap`; brak szczegółowych zakończeń i wycięć. |
| `core_case/catalog_assets.py` | Wersjonowane źródła okuć i ramy. Należy powiązać z osobną wersją szablonu montażowego. |
| `part_registry.py` | Wspólne rodziny i etapy podglądu. Obróbka jest operacją na części, nie nową zakupową częścią BOM. |
| Wykonawca, rewizje i obserwacja zmian | Zachować jednego wykonawcę, kopie, hash źródła, obsługę konfliktów i odzyskiwania. |

Obecne `RP_JointGap=8.63 mm` odtwarza odstęp płyt konkretnego wzorca.
Nie jest uniwersalnym luzem między metalowymi powierzchniami. `RP_DisplayGap`
jest wyłącznie odsunięciem prezentacyjnym i nie może zmieniać rozkroju.
Obecne stałe odsadzenia w `profile_rules.py` są regułami prototypu, nie
zatwierdzonym rozwiązaniem dla dowolnego SKU i dowolnej grubości sklejki.

## Proponowany kontrakt

Wprowadzić wersjonowane dane montażowe, współdzielone przez planer i CAD:

- **MountingTemplate**: SKU i rewizja okucia, źródło/hash konturu, lokalna rama
  montażu, dozwolone grubości/materiały, wariant lewy/prawy, kontury linii/łuków,
  operacje przelotowe lub kieszenie, głębokości, minimalne odstępy i status
  weryfikacji. Rysunek montażowy lub zmierzony wzorzec zastępuje zgadywanie z bbox.
- **MountInstance**: trwałe ID wystąpienia okucia, kotwa w układzie ściany,
  orientacja, grupa symetrii, docelowe części i wersja szablonu. Kontur nie
  przechowuje niezależnej, ręcznie kopiowanej pozycji.
- **MachiningFeature**: stabilne ID, właściciel `mount_instance_id` albo
  `joint_instance_id`, jawny `target_part_id`, typ, kontur, głębokość i tolerancje.
  Identyfikatory ścian BRep nie zastępują trwałych identyfikatorów części.
- **JointTemplate**: konkretna para profili i przekroje, bazy styku, zakres
  grubości płyty, głębokości osadzenia, luz pary, odsunięcia krawędzi sklejki,
  podfrezowania oraz reguły zakończeń/naroży. Uszczelka tylko w wariancie,
  który faktycznie ją przewiduje.

### Biblioteka ogólna i wczesna informacja dla konstruktora

Rozszerzyć wspólny katalog elementów konstrukcyjnych, powiązany z biblioteką
urządzeń przez projekt i jego specyfikację. Urządzenie transportowane, okucie
katalogowe i wystąpienie okucia w skrzyni pozostają odrębnymi obiektami.
Nie tworzyć drugiej niezależnej bazy wiedzy w viewerze lub dodatku C#.

Kolumna UI **„Wycięcie w sklejce”** odzwierciedla wersjonowane pole
`plywood_cutout_requirement`: `required` (tak), `none` (nie), `conditional`
(zależy od montażu), `unknown` (brak danych). Dotychczasowe wpisy bez danych
migrować do `unknown`, nigdy domyślnie do `none`. Dla `conditional` reguła
rozstrzyga wymaganie według wariantu, podłoża i grubości; nierozstrzygnięta
reguła blokuje wykonanie technologiczne. Wstępna koncepcja może pozostać
widoczna z jawnym brakiem danych.

Pole uzupełniają `mounting_template_id/version`, źródło konturu, zakres
grubości/materiałów oraz status weryfikacji. Informacja o wycięciu sklejki
nie zastępuje listy wszystkich operacji: część może wymagać obróbki profilu,
otworów mocujących albo kieszeni mimo braku dużego wycięcia w sklejce.
`required` bez właściwego szablonu nie jest gotowością do generowania.

Już przy wyborze elementu pokazać: obróbkę, docelowe płyty/profile, strefę
montażową i brakujące dane. Zmiana pozycji/rozmiaru skrzyni zmienia wystąpienie
i jego obróbki; zmiana wersji katalogu wymaga jawnej aktualizacji projektu,
nie zmienia historycznych projektów w tle.

Bibliotekę budować na reprezentatywnych gotowych skrzyniach: zacząć od
wskazanych T1, T2 i T4, następnie uzupełniać do kilku–kilkunastu dostarczonych
wzorów. Zapisać macierz rodzina skrzyni × SKU × grubość × wariant montażu,
pozytywne i błędne przypadki oraz odnośnik do rewizji źródłowej. Powtarzalność
w wielu modelach wspiera regułę, ale nie zastępuje potwierdzenia tolerancji.
Nie uzależniać pierwszego POC od zebrania całej próbki i nie zgadywać danych
brakujących projektów.

To propozycja rozszerzenia schematu. Obecny kontrakt i allowlista starego
wykonawcy nie zmieniają się automatycznie; nowy zakres wymaga nowej wersji
i jawnych możliwości szablonu. Stary prototyp nadal ma ograniczenia technologii.

Dla punktów konturu w lokalnej ramie montażowej obowiązuje przekształcenie:

`p_target = inverse(T_target_world) * T_mount_world * p_mount`

Ta sama kotwa steruje sztywnym okuciem i jego obróbką w lokalnym układzie
docelowej płyty. Obrót nie skaluje konturu. Strona wykonania, kierunek normalnej
i głębokość są jawne; przeciwległa ściana nie oznacza automatycznego odbicia
asymetrycznego okucia. Kontury nominalne oddzielić od późniejszej kompensacji
narzędzia CNC, aby nie naliczać naddatku lub promienia frezu dwukrotnie.

## Obliczenia przed tworzeniem modelu

Docelowa kolejność:

`wymagania + rodzina + SKU → rozwiązanie wymiarów i złączy → kotwy okuć → plan obróbek → kontrola mieszczalności → plan zmian → CAD na kopii → pomiar i zapis/otwarcie → podgląd/BOM/rewizja`

1. Jawnie wskazać, co jest wymaganiem: minimalne wnętrze, docelowy gabaryt
   transportowy lub obie granice. Rozróżnić gabaryt płyt od obrysu profili,
   okuć i kół. Konflikt wymagań zwraca błąd oraz konkretną przyczynę.
2. Rozwiązać zamknięty przekrój złącza: ustalić położenie pary profili, potem
   końce i osadzenie płyt. Odstęp płyt jest wynikiem tej geometrii.
   Osobno przechowywać odstęp płyt, luz styku profili i tolerancję osadzenia.
3. Wyliczyć formatki, długości cięcia, końcówki i podfrezowania. Cięcie 45°
   nie jest regułą dla każdego naroża: decyduje konkretny przekrój i wzorzec.
   Zmienia się długość/obróbka profilu; jego przekrój pozostaje katalogowy.
4. Wyznaczyć kotwy, wycięcia i rezerwy na miski okuć po wewnętrznej stronie.
   Kontrolować odległość od krawędzi, profili, przegród, pianki i urządzeń.
   Sprawdzać poprawność konturu oraz pozostały materiał, nie sam bbox.
   Dla uchwytu i zawiasu uwzględnić kołnierze, mocowania i przestrzeń ruchu
   obu elementów. Dopuszczalny skraj uchwytu wyznaczyć z rzeczywistego skraju
   strefy zawiasu i wymaganego odstępu, w tej samej ramie montażowej. Nie
   zakładać zerowego luzu ani styku krawędzi jako reguły uniwersalnej.
   Preferować bezkolizyjny wariant katalogowy i dozwolone położenie przed
   dodawaniem obróbek; nie zmieniać samowolnie liczby uchwytów. Przesunięcie
   zawiasu musi unieważnić zależne rozmieszczenie uchwytów i plan ich wycięć.
5. W razie braku miejsca odmówić wykonania i wskazać konflikt. Nie powiększać
   skrycie korpusu/pokrywy, nie ścieńczać płyty ani nie skalować katalogu.

Nowe reguły mają rozszerzać istniejący etap planowania. Kolejność warstw w
panelu nie musi być kolejnością obliczeń: otwory muszą być znane przed
wykonaniem płyt, choć uchwyty są pokazywane w etapie 5. Etap 6 nadal wspólnie
obejmuje koła i gniazda; prezentacja nie zmienia planu produkcyjnego.

### Rozszerzalne etapy i zsynchronizowany podgląd

Wersjonowany rejestr etapów ma stabilne `stage_id`, zależności `depends_on`,
etykietę, kolor i kolejność prezentacji wyliczaną z zależności. Kolejność
1–6 istniejących etapów zachować dla dotychczasowej wersji; nowe rodziny mogą
rozszerzać graf bez zmiany tożsamości starych zdarzeń. Cykle i nieznane
zależności odrzucać. Etapy montażowe nie zastępują statusów całego zlecenia
(np. dokumentacja, materiały, produkcja).

Planować operacje wcześniej, lecz prezentować je jako pakiet właściciela:
`okucie + jego MachiningFeature[] + zmienione części docelowe`. Wycięcie
dziedziczy etap/kolor wyróżnienia po okuciu; sama sklejka zachowuje materiał.
Techniczna kolejność SDK może najpierw wyciąć płytę, a później wstawić okucie.
Etap uznać za ukończony dopiero po obu operacjach i ich kontroli. Błąd jednej
z nich pozostawia etap nieukończony i poprzednią poprawną rewizję.

W podglądzie jawnie rozróżnić:

- **Etapy budowy:** przed etapem uchwytów płyta nie ma ich wycięć; wejście
  w etap pokazuje uchwyty oraz odpowiadającą im obrobioną płytę. Analogicznie
  dla zatrzasków. Cofnięcie przywraca geometrię poprzedniego etapu podglądu.
- **Widoczność gotowego modelu:** ukrycie uchwytu pozostawia jego rzeczywisty
  otwór w gotowej płycie. Filtr widoczności nie usuwa obróbki ani nie zmienia ICS.

Otwór jest zmianą geometrii płyty, nie oddzielną siatką do włączenia/wyłączenia.
Eksport powinien dostarczać warianty geometrii etapów albo kontrolowane
przeliczenie siatki na podstawie aktywnego zbioru operacji. Zapisać hash tego
zbioru, rewizję, wersję rejestru, ID właścicieli i części docelowych. Nie
maskować otworów prostokątnymi nakładkami. Przy wyłączeniu jednego właściciela
zachować obróbki pozostałych, również gdy kontury się przecinają; współdzielona
obróbka potrzebuje jawnej reguły współwłasności, nie dopasowania po położeniu.

Podgląd etapów jest rekonstrukcją planu, jeśli nie ma pomiarów pośrednich CAD;
nie przedstawiać go jako nagrania rzeczywistego przebiegu. Zdarzenia wykonawcy
wiązać przez `operation_id`, `mount_instance_id`, `feature_id`, `target_part_id`
i rewizję. Obserwator pokaże podoperacje i czasy bez podwójnego sumowania.
Zmiana wariantu lub pozycji musi unieważnić zależne siatki i odbiory. Nowa
wersja definicji dociera wspólnie do dodatku, obserwatora i viewera.

## IronCAD i wykonalność

Dokumentacja potwierdza operacje odejmowania, wyrażenia parametrów oraz
wycięcia zespołu ze wskazanym zakresem części. To podstawa rozwiązania,
nie dowód poprawnego działania nowego powiązania w naszym modelu.

Preferowany pierwszy POC: szkic konturu i ujemne wyciągnięcie w konkretnej
płycie, sterowane wspólnymi parametrami montażu. Lokalna biblioteka typów
ICAPI 29.0 zawiera `IZPartFeatureMgr.CreateExtrudeFeature(eOpType, ...)`,
`Z_SUBTRACT`, `IZSceneElement.PositionTransformComponentExpression` oraz
`IZPart.Boolean`. Próba natywna musi sprawdzić zależności szkicu/wyciągnięcia,
obrót, przeliczenie i trwałość po zapisaniu ICS.

`IZPart.Boolean` według opisu SDK absorbuje część narzędziową. Nie wolno
podawać jako narzędzia rzeczywistego uchwytu ani jego oryginału katalogowego.
Ewentualny wariant boolean używa osobnej bryły narzędziowej z zatwierdzonego
konturu; aktualizacja nie może kumulować starych otworów po przesunięciach.

Assembly Features / grupy katalogowe są alternatywą szczególnie dla zatrzasku
obejmującego kilka części. Wymagają sprawdzenia sterowania zakresem przez
naszą wersję API. Nie stosować automatycznie „wszystkie części” / nieograniczonego
cięcia przez scenę. SmartAssembly pomaga ustawiać i wiązać części, lecz samo
pozycjonowanie okucia nie dowodzi związania istniejącego wycięcia.

**Ruch ręczny:** wspólne parametry obejmują zmiany sterowane przez dodatek.
Osobno dowieść działania po ręcznym przesunięciu TriBallem. Jeżeli ruch zrywa
zależność, obserwator ma wykryć rozbieżność, zachować zmianę konstruktora i
uzgodnić nową kotwę wraz z wycięciami. Do rozstrzygnięcia blokować eksport
produkcyjny. Samo ostrzeżenie nie spełnia docelowego kryterium automatycznego
podążania otworu. Aktualizacja obu elementów ma być jednym planem zmiany,
bez zapętlania zdarzeń i bez nadpisywania ręcznych operacji na płycie.

## Zadania w kolejności zależności

Wszystkie pozycje mają status PLAN; nie zostały wdrożone ani odebrane.

| ID lokalne | Zadanie | Zależność | Kryterium ukończenia |
| --- | --- | --- | --- |
| M01 | Zmierzyć wzorzec konstruktora: uchwyt, zatrzask, przekrój zamknięcia | Dostęp do wskazanej rewizji | Kopia i hash źródła; SKU, ramy, kontury, głębokości i przekroje z wymiarami; oddzielone dane zmierzone od brakujących tolerancji. Nie zapisywać otwartego oryginału. |
| M02 | Dodać wersjonowany katalog szablonów montażowych i powiązania wystąpień | M01 | Kolumna wycięcia z czterema stanami i migracja braków do unknown; SKU/rewizja wybiera właściwy kontur i dozwolone płyty. Informacja dostępna przed generowaniem; stabilne ID i jawna lista celów, bez skali katalogu. |
| M03 | Rozszerzyć obliczenia złączy, gabarytów i stref uchwyt–zawias przed CAD | M02 | Wnętrze, formatki, profile i gabaryt końcowy są spójne; rozdzielone trzy rodzaje luzu. Konflikt uchwytu/zawiasu odrzucony bez dodatkowego przypadkowego wycinania, zmiany liczby uchwytów lub cichego powiększenia skrzyni. |
| M04 | Wykonać powiązane wycięcia pod uchwyty | M03 | Uchwyt i otwór podążają za zmianą wymiarów, położenia i obrotu na obu przeciwległych ścianach; działają 1/2 uchwyty na ścianę. Zmiana SKU/usunięcie nie zostawia starego wycięcia. |
| M05 | Wykonać wycięcia zatrzasków po obu stronach złącza | M04 | Każda połówka i jej kontur mają wspólną bazę zamknięcia; cięte są tylko jawnie wskazane płyty/profile. Rozwarcie prezentacyjne nie zmienia produkcyjnych konturów. |
| M06 | Wykonać osadzenia sklejki i zakończenia profili | M03, M05 | Przekrój zamknięcia zgodny ze wzorcem i danymi SKU, prawidłowe podfrezowania/końcówki i ciągłość osadzenia. Brak kolizji blokującej domknięcie, zachowany gabaryt. |
| M07 | Zintegrować rozszerzalny graf etapów, zmiany ręczne, podgląd i BOM | M04–M06 | Okucie i obróbki wchodzą w jednym etapie; cofnięcie etapu i ukrycie gotowego okucia mają różną, poprawną semantykę. Zależne siatki, awarie, zapis/otwarcie i nowa rodzina bez osobnych klasyfikatorów w UI sprawdzone; brak fikcyjnej pozycji zakupowej wycięcia. |
| M08 | Rozbudować bibliotekę na reprezentatywnych gotowych skrzyniach | M01, M02; dalsze wzory po dostarczeniu | Macierz pokrycia T1/T2/T4 i kolejnych modeli, wersje źródeł, potwierdzone reguły oraz jawne braki. Powtórzone SKU nie tworzą kopii tej samej definicji; konflikt wariantów nie jest scalany automatycznie. |

M08 można rozwijać równolegle organizacyjnie z M03–M07; komplet kilkunastu
wzorów nie jest warunkiem pierwszego wdrożenia jednego zweryfikowanego SKU.
To opis niezależności prac, nie uruchomienie dodatkowego wykonawcy CAD.

### Nice to have — transport bagażowy

| ID lokalne | Zadanie przyszłe | Zakres i kryterium |
| --- | --- | --- |
| N01 | Uchwyt bagażowy/teleskopowy | Osobna rodzina od uchwytów do noszenia; rzeczywisty SKU, pozycja złożona/wysunięta, skok katalogowy, mocowania, rezerwa wewnętrzna i powiązane wycięcia. Korzysta z M02/M03/M07. |
| N02 | Koła bagażowe wpuszczane w skrzynię | Rzeczywisty wariant koła z obudową, wycięcia płyt/profili i podparcie; wspólna geometria transportu z N01, oś toczenia, prześwit i gabaryt. W etapie kół, ale bez automatycznego wymagania gniazd do piętrowania. Nośność do potwierdzenia. |

Obie pozycje są odłożone na przyszłość. Wzorzec T2 jest kandydatem do odczytu
rozwiązania; nie oznacza zatwierdzenia jego okuć do każdej nowej skrzyni.

Powiązania z istniejącą kolejką: ROC-42 (wzorzec), ROC-17 (katalog), ROC-16
(płyty/profile), ROC-40 (zmiany ręczne), ROC-20 (wykonawca), ROC-19 (testy),
ROC-21 (dokumentacja). Ten zakres jest fundamentem technologii kolejnych rodzin;
nie kopiować do T2/T4 starych uproszczeń lub jednej stałej szczeliny.

## Sprawdzenia odbiorowe

- **Offline:** błędne/otwarte kontury, zła grubość lub głębokość, brak SKU,
  nakładające się operacje, zbyt mały odstęp od krawędzi, niezgodna para profili,
  oba rodzaje gabarytu, jednostki mm/metr, lewa/prawa ściana, symetria i `DisplayGap`.
- **Native:** jeden uchwyt na kopii płyty, potem dwie przeciwległe ściany,
  zatrzask na złączu i odcinek zamknięcia. Przesunięcie, obrót, resize, zmiana
  SKU, usunięcie oraz powrót A→B→A; pomiar konturów/głębokości i ręczny TriBall.
- **Trwałość:** zapis i ponowne otwarcie, kolejny ruch po otwarciu, brak osieroconych
  lub zdublowanych operacji, niezmienione źródła, awaria/ponowienie bez podwójnego cięcia.
- **Odbiór technologiczny:** konstruktor/technolog potwierdza tolerancje,
  minimalny pozostały materiał i próbkę spasowania. AABB i wygląd nie wystarczą.
- **Uchwyt–zawias:** brak kolizji korpusów, kołnierzy i przestrzeni ruchu;
  wariant graniczny ze zbyt małą rezerwą odrzucony. Przesunięcie zawiasu,
  uchwytu lub zmiana SKU przelicza zależności, zachowuje symetrię i liczbę.
- **Biblioteka i etapy:** stary wpis bez pola to unknown; conditional wymaga
  rozstrzygnięcia. Wejście/cofnięcie etapu obsługuje okucie i otwór razem,
  zwykłe ukrycie okucia nie zasklepia płyty. Zmiana kolejności nie rozrywa
  zależności; częściowo nieudany etap nie pokazuje OK. Zachowane obróbki innych
  właścicieli, poprawne unieważnienie cache i spójne rewizje trzech interfejsów.

Pierwszy przyrost wykonawczy po planie: M01 oraz POC jednego uchwytu z ujemnym
wyciągnięciem na kopii jednej płyty. Nie trzeba czekać na cały katalog, aby
sprawdzić mechanizm API; taki POC nie zamyka M04 ani odbioru całej skrzyni.

## Źródła sprawdzone 26.10.2026

- [IronCAD — Expressions](https://www.ironcad.com/support/2023/IRONCAD_Help/Content/3D_Design_Environment/Assembly_Part_Operations/Expressions.htm): zależności parametrów, jawne jednostki i wewnętrzny układ metr/radian/kg.
- [IronCAD — Assembly Feature Group / Smart Assembly](https://www.ironcad.com/WhatsNewArchive/IronCADV9/getting_started.htm): historyczna dokumentacja grup katalogowych zawierających części i odejmowanie materiału; nie traktować jej jako dowodu bieżącej integracji SDK.
- [IronCAD TechBase — Assembly Feature: Extruded Cut](https://techbase.ironcad.jp/portal/en/kb/articles/creating-an-assembly-feature-extruded-cut): wyciągnięcie odejmujące w zespole, kierunki/głębokość i zakres Selected Parts.
- Lokalna instalacja IronCAD 2027: sygnatury i opisy biblioteki typów ICAPI 29.0 oraz przykład `ICAPI/Samples/C#/SelectionTool/SelectionTool.cs` (`CreateProfile`, `CreateExtrudeFeature`). Obecność API nie zastępuje testu natywnego.
- Kod i ograniczenia: [profil v2](CASE_PROFILES_V2.md), [kontrakt](CASE_CONTRACT.md), [architektura rdzenia](CORE_CASE_DESIGN.md), [zmiany ręczne](NATIVE_MANUAL_CHANGES.md).
