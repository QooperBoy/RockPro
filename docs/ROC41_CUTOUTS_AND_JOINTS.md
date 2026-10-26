# ROC-41 — wycięcia okuć i pasowanie profili

Data: 26.10.2026. Status: wymagania i plan implementacji, bez zmiany kodu CAD.
Rozwinięcie [ROC-41](https://linear.app/rock-pro/issue/ROC-41/po-mvp-wyciecia-pod-okucia-i-styki-profili-aluminiowych)
na podstawie trzech oznaczeń użytkownika. Identyfikatory M01–M07 poniżej są
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

Użytkownik wskazał model `AI_CAD/T_1/Epson EB-L630U.ics` jako poprawny wzorzec
konstruktora. Dwie podane ścieżki są identyczne: to jeden wskazany plik, a nie
dwa niezależne dowody. Zrzut opisuje role 1/2/3, ale nie daje wymiarów,
tolerancji ani pewnego przypisania do rewizji pliku. Nie wyliczać ich z pikseli.
Pełna ścieżka, hash i materiał graficzny pozostają w prywatnym
`artifacts/roc41-planning-20261026/`. Odczyt geometrii aktualnej sesji: NOT RUN.

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
5. W razie braku miejsca odmówić wykonania i wskazać konflikt. Nie powiększać
   skrycie korpusu/pokrywy, nie ścieńczać płyty ani nie skalować katalogu.

Nowe reguły mają rozszerzać istniejący etap planowania. Kolejność warstw w
panelu nie musi być kolejnością obliczeń: otwory muszą być znane przed
wykonaniem płyt, choć uchwyty są pokazywane w etapie 5. Etap 6 nadal wspólnie
obejmuje koła i gniazda; prezentacja nie zmienia planu produkcyjnego.

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
| M02 | Dodać wersjonowany katalog szablonów montażowych i powiązania wystąpień | M01 | Ten sam SKU/rewizja wybiera właściwy kontur i dozwolone płyty; brak danych blokuje obróbkę. Stabilne ID i jawna lista celów, bez skali katalogu. |
| M03 | Rozszerzyć obliczenia złączy i gabarytów przed CAD | M02 | Wnętrze, formatki, profile i gabaryt końcowy są spójne; rozdzielone trzy rodzaje luzu; konflikt gabarytu odrzucony bez cichego powiększenia. |
| M04 | Wykonać powiązane wycięcia pod uchwyty | M03 | Uchwyt i otwór podążają za zmianą wymiarów, położenia i obrotu na obu przeciwległych ścianach; działają 1/2 uchwyty na ścianę. Zmiana SKU/usunięcie nie zostawia starego wycięcia. |
| M05 | Wykonać wycięcia zatrzasków po obu stronach złącza | M04 | Każda połówka i jej kontur mają wspólną bazę zamknięcia; cięte są tylko jawnie wskazane płyty/profile. Rozwarcie prezentacyjne nie zmienia produkcyjnych konturów. |
| M06 | Wykonać osadzenia sklejki i zakończenia profili | M03, M05 | Przekrój zamknięcia zgodny ze wzorcem i danymi SKU, prawidłowe podfrezowania/końcówki i ciągłość osadzenia. Brak kolizji blokującej domknięcie, zachowany gabaryt. |
| M07 | Zintegrować zmiany ręczne, podgląd, BOM i odbiór całego przebiegu | M04–M06 | Ręczny ruch, ponowienie po błędzie, zapis/otwarcie i aktualizacja podglądu sprawdzone; obróbka przypisana do części i okucia, bez fikcyjnej pozycji zakupowej. |

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

Pierwszy przyrost wykonawczy po planie: M01 oraz POC jednego uchwytu z ujemnym
wyciągnięciem na kopii jednej płyty. Nie trzeba czekać na cały katalog, aby
sprawdzić mechanizm API; taki POC nie zamyka M04 ani odbioru całej skrzyni.

## Źródła sprawdzone 26.10.2026

- [IronCAD — Expressions](https://www.ironcad.com/support/2023/IRONCAD_Help/Content/3D_Design_Environment/Assembly_Part_Operations/Expressions.htm): zależności parametrów, jawne jednostki i wewnętrzny układ metr/radian/kg.
- [IronCAD — Assembly Feature Group / Smart Assembly](https://www.ironcad.com/WhatsNewArchive/IronCADV9/getting_started.htm): historyczna dokumentacja grup katalogowych zawierających części i odejmowanie materiału; nie traktować jej jako dowodu bieżącej integracji SDK.
- [IronCAD TechBase — Assembly Feature: Extruded Cut](https://techbase.ironcad.jp/portal/en/kb/articles/creating-an-assembly-feature-extruded-cut): wyciągnięcie odejmujące w zespole, kierunki/głębokość i zakres Selected Parts.
- Lokalna instalacja IronCAD 2027: sygnatury i opisy biblioteki typów ICAPI 29.0 oraz przykład `ICAPI/Samples/C#/SelectionTool/SelectionTool.cs` (`CreateProfile`, `CreateExtrudeFeature`). Obecność API nie zastępuje testu natywnego.
- Kod i ograniczenia: [profil v2](CASE_PROFILES_V2.md), [kontrakt](CASE_CONTRACT.md), [architektura rdzenia](CORE_CASE_DESIGN.md), [zmiany ręczne](NATIVE_MANUAL_CHANGES.md).
