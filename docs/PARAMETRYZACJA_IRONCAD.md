# Parametryzacja skrzyni w IronCAD

Zacznij od jednej rodziny skrzyń i jednego natywnego pliku ICS. Wymiary wpisuj na poziomie sceny, a części powiąż z nimi przez równania. Po zmianie gabarytu konstruktor powinien móc przewidzieć, co się przesunie, oraz sprawdzić wynik na kopii.

## 1. Ustal model i punkty odniesienia

1. Zapisz wyjściowy ICS jako nową kopię roboczą. Zanotuj rodzinę, rewizję, wersję IronCAD i położenie pliku źródłowego. Dla T1 zacznij od właściwej wersji parametrycznej. T2 ma osobny układ sekcji i złączy. Zobacz [analizę T2](T2_REFERENCE_ANALYSIS.md) i [zgodność wersji](IRONCAD_2023_COMPATIBILITY.md).
2. W tabeli parametrów wybierz korzeń sceny. Spisz nazwy, wartości, równania i komentarze. Następnie włącz „Pokaż parametry podrzędne wybranego kształtu” i przejrzyj dół, pokrywę oraz przykładowe okucie. Licz osobno parametry użytkownika i techniczne zależności części.
3. Ustal osie skrzyni: X lewa–prawa, Y przód–tył, Z od dołu w górę. Wymiary podawaj w mm. Zdefiniuj początek układu, płaszczyznę styku sekcji i płaszczyzny symetrii. Przy opisie każdej wysokości wskaż obie powierzchnie pomiaru.

## 2. Ułóż tabelę

Demo Epson ma sześć parametrów sceny. Używaj ich zapisanych nazw, jeśli model już odwołuje się do nich w równaniach. Polski wariant T1 opisany w dokumentacji miał **12 parametrów sceny**. Ich nazwy pochodzą z [PARAMETERS_PL](../Integracja/rockpro_cad/core_case/t1_mounting.py). Ten zapis nie jest odczytem każdego rozesłanego ICS.

| Kolejność | Pole | Demo Epson | Polski T1 |
| --- | --- | --- | --- |
| 1 | Długość obrysu sklejki X | `RP_Length` | `RP_Dlugosc` |
| 2 | Głębokość obrysu sklejki Y | `RP_Depth` | `RP_Glebokosc` |
| 3 | Wysokość korpusu Z do linii podziału | `RP_BaseHeight` | `RP_WysokoscKorpusu` |
| 4 | Wysokość pokrywy Z. W polskim T1 obejmuje szczelinę połączenia | `RP_LidHeight` | `RP_WysokoscPokrywy` |
| 5 | Grubość sklejki, mierzona prostopadle do płyty | `RP_Thickness` | `RP_GruboscSklejki` |
| 6 | Fizyczna szczelina między krawędziami sklejki, zajmowana przez profile złącza | — | `RP_SzczelinaPolaczenia` |
| 7 | Prezentacyjne uniesienie pokrywy. Ustaw 0 przy pomiarze zamkniętej skrzyni | `RP_DisplayGap` | `RP_RozsunieciePokrywy` |
| 8–9 | Przesunięcie uchwytów w osi Y i w pionie. W T1 pion jest liczony od połowy wysokości korpusu | — | `RP_PrzesuniecieUchwytow`, `RP_PodniesienieUchwytow` |
| 10–11 | Odsunięcia osi zamków i zawiasów od odpowiadających krawędzi | — | `RP_OdsuniecieZamkow`, `RP_OdsuniecieZawiasow` |
| 12 | Luz podpór i przerw profili przy zawiasach, zgodnie z wariantem T1 | — | `RP_LuzMontazowy` |

W komentarzu używaj formatu **co to jest · oś i jednostka · od czego mierzysz · co zmienia**. W polach wpisywanych ręcznie umieść tylko wartości sterujące, a wyniki pokazuj jako obliczenia. Lokalnych parametrów położenia części używanych przez równania nie edytuj z poziomu karty projektu.

Wcześniejsza propozycja **28 pozycji** była szkicem docelowej karty. Jej rozszerzenia obejmują obliczane wnętrze X/Y/Z, wysokość zamkniętej skrzyni, wymiary i liczbę **urządzeń**, luz, przegrody, piankę, komorę akcesoriów, rozstaw kół i odsunięcia końców profili. Dodawaj tylko pola używane przez daną rodzinę. Dane urządzenia i układu mogą zostać w konfiguratorze, jeśli ICS potrzebuje jedynie wynikowych wymiarów.

## 3. Powiąż geometrię w kolejności zależności

1. **Dół, pokrywa i płyty.** Obie sekcje korzystają ze wspólnego X/Y. Wysokości są osobne, a położenie pokrywy wynika z płaszczyzny styku. Ustal, które płyty zachodzą na które. Dla prostego szkieletu z równą grubością T wolne wnętrze X/Y to X − 2T i Y − 2T, a wolne Z to wysokość zamkniętej sklejki minus grubości dna i wieka. Dla profili wchodzących do środka, wręgów lub innego złącza sprawdź rzeczywisty prześwit. Odsunięcie pokazowe nie zwiększa wnętrza.
2. **Profile i narożniki.** Zakotwicz narożniki na przecięciach właściwych powierzchni. Profil prowadź wzdłuż krawędzi, a długość wyprowadź z odległości między jego końcami pomniejszonej o oba odsunięcia. Zmieniaj długość profilu przy zachowaniu jego przekroju.
3. **Uchwyty, zamki i zawiasy.** Przypisz każdemu wystąpieniu ścianę lub sekcję, punkt odniesienia i orientację. Symetryczną parę na ścianie o długości L ustaw według odległości d oraz L − d od tej samej krawędzi. Połówki zamka lub zawiasu pozycjonuj względem tej samej płaszczyzny styku. Tam, gdzie wariant ma zweryfikowane wycięcie lub przerwę profilu, powiąż obróbkę z tą samą kotwą na właściwej części. Zmieniaj położenie całego okucia katalogowego i zachowuj jego istniejącą geometrię. Liczba okuć pozostaje decyzją konstruktora. Jeśli zestaw przestaje się mieścić, zgłoś konflikt.
4. **Koła, gniazda i wyposażenie.** Koła oraz odpowiadające im gniazda na górze korzystają ze wspólnych współrzędnych X/Y w układzie zamkniętej skrzyni. Po obliczeniu wnętrza sprawdź urządzenia, pianki, przegrody i komorę na akcesoria. Wynik sprawdź również pod kątem zakładania pokrywy oraz wkładania i wyjmowania urządzenia.

Przykład różnicy między rodzinami: [montaż T1 w IronCAD 2023](T1_2023_MOUNTING_REPAIR.md) opisuje rzeczywiste kotwy, wycięcia i polskie parametry. [Prototyp obróbek T1](T1_MACHINING_PROTOTYPE.md) opisuje inny wariant i jego zakres. Przed kopiowaniem równań porównaj sekcje, osie i jednostki konkretnego ICS.

## 4. Odbierz zmianę na kopii

1. Przy zamkniętej skrzyni zapisz wartości bazowe i zmierz obrys sklejki oraz grubość. Zmień X o 20 mm na kopii, zastosuj zmianę i przebuduj model. Przy odbiorze nowego szablonu sprawdź również Y oraz jedną wysokość w osobnych próbach.
2. Zmierz wynik. Dół i pokrywa mają spójny obrys, T pozostaje stałe, pary zachowują symetrię, a profile swoje przekroje. Jeśli rodzina ma wspólne wycięcia lub gniazda kół, sprawdź odpowiednio ich położenie względem okucia lub osi koła. Sprawdź, czy model mieści wybrane wyposażenie.
3. Przywróć wartości bazowe i porównaj obrys oraz położenia. Zapisz zmieniony wariant pod nową nazwą, otwórz go ponownie i sprawdź wartości oraz równania. Jeśli scenariusz obejmuje przekazanie na produkcję, konstruktor osobno zatwierdza dokumentację 2D, formatki, obróbki i BOM z tej samej rewizji.

Szerszy przepływ od wyboru rodziny do zestawienia materiałów opisuje [workflow RockPro Studio](CUSTOM_CASE_WORKFLOW.md).
