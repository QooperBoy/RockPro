# Studio — pełna konstrukcja skrzyni

## Zakres

Krok 7 „Konstrukcja i podstawa” dodaje do aktualnego draftu profile,
narożniki, wzmocnienia, podpory, koła i gniazda do piętrowania. Uchwyty
i kompletne zamki/zawiasy pozostają w krokach 5–6. Obecnie konstrukcja
obsługuje typ „Skrzynia” z jednym górnym wiekiem. Nie rozciąga tego
zestawu automatycznie na szafy ani skrzynie trzyczęściowe.

Pole opcjonalne `construction` w dotychczasowym schemacie
`rockpro.configurator/3` ma dokładnie trzy wartości bool:
`enabled`, `wheels`, `stacking`. Historyczne drafty bez tego pola
pozostają bez konstrukcji i nie są migrowane przy odczycie.
Nie powiększamy wymiarów po cichu, gdy zestaw się nie mieści.

## Składanie i geometria

- 16 krawędziowych odcinków EG-0113: dół, góra i pionowe krawędzie sekcji.
- Para profili EG-0500/1 i /2 wzdłuż styku; odcinki są dzielone przy
  istniejących zatrzaskach i zawiasach z rezerwą 5 mm.
- Osiem narożników 410429 z obrotami według sprawdzonego `corner_pose`.
  Brak odbijania i skalowania katalogowych okuć.
- Cztery wzmocnienia B1930 i cztery B1121 przy styku korpusu i wieka.
- Opcjonalnie dwie podpory ze sklejki 18 mm i cztery koła referencyjne.
  Podpory kończą się wewnątrz profili, z luzem 2 mm.
- Opcjonalnie cztery gniazda W0968Z z tej samej referencji. Koło i gniazdo
  współdzielą `stacking_pair`. Gniazdo licuje swoją płaszczyzną osadzenia
  z górną powierzchnią, a nie ze spodem sklejki ani skrajem bbox.

Jedynie profile zmieniają długość wzdłuż osi wyciągnięcia. Pozostałe części
są sztywnymi modelami. Podpory to projektowane płyty, nie zastępcze znaczniki
okuć. `structure3d.js` wczytuje pełne zapisane siatki, weryfikuje SHA-256
i zgłasza brak modelu. Nie zastępuje brakujących części niewidocznym proxy.
Ruch wieka obejmuje jego profile, narożniki, wzmocnienia i gniazda.

`scripts/prepare_studio_structure_meshes.py` odtwarza lokalne zasoby z
przypiętego eksportu T1. Weryfikuje konkretną sumę geometrii przed użyciem
stałych identyfikatorów. Zawias 270836 zawiera obie połówki jednego produktu,
a koło wszystkie osiem brył jednej jednostki. Nie są to rozrzucone zespoły
ani niezależne połówki do wyboru przez konstruktora.
Zamki i zawiasy są zakotwione pionowo względem źródłowej krawędzi korpusu
300 mm, zamiast środka ich asymetrycznego obrysu. Próg wieka 110 mm
korzysta z konserwatywnych zasięgów poprawionego prototypu, szerokości
górnego profilu i luzu; nie zmienia automatycznie wysokości korpusu.

Ramę `source.local` dopuszczono jedynie dla jawnych referencyjnych profili,
narożników, wzmocnień i gniazd. Nie zastępuje ram montażowych `mount.local_uvn`
w ręcznym rozmieszczaniu innych części i nie zatwierdza montażu produkcyjnego.
Lokalne zasoby prywatne pozostają w ignorowanym `artifacts/`.

## Zestawienie i zapis

`project_summary` jest wspólnym wynikiem backendu: liczy panele, kompletne
wystąpienia okuć, odcinki profili i podstawę. Frontend nie utrzymuje własnego
algorytmu liczności. Każda pozycja ma rodzinę i etap ze wspólnego rejestru;
gniazda i podpory należą do etapu kół. Nieużyte wybrane definicje są osobno
w `unplaced_selection`, nie zwiększają liczby sztuk.

Przykład E2E ma 76 elementów w 13 pozycjach: 10 paneli, 4 uchwyty,
2 zamki, 2 zawiasy, 32 odcinki profili, 8 narożników, 8 wzmocnień,
2 podpory, 4 koła i 4 gniazda. Liczba odcinków zależy od rozmieszczenia
okuć, więc nie jest stałym limitem projektu.

Zapis SQLite i eksport JSON zachowują kompletną receptę. Parametr URL
`?draft=<id>` otwiera zapisany projekt bez szukania go na liście. Jego
awaryjny zapis i kontekst są odseparowane od domyślnego draftu użytkownika.
Sidebar przenosi ten identyfikator do biblioteki i z powrotem.

## Sprawdzenia i granica gotowości

`rockpro_cad.mcp.test_studio_structure`: rodziny i liczności, właściwe
obroty, przerwy w profilach, powiązanie koło–gniazdo przy trzech rozmiarach,
podpory względem profili, odmowa nieprawidłowych zestawów i roundtrip SQLite.

Prywatny test przeglądarkowy znajduje się w
`artifacts/studio-complete-20261027/e2e.cjs`, wyniki w `e2e-results.json`.
Sprawdza dodanie konstrukcji przez przycisk, rzeczywiste modele zamiast
znaczników, zapis z potwierdzeniem nowej rewizji, eksport przez download,
zmianę wymiaru przez formularz, ruch części wieka przy nieruchomych kołach
oraz odtworzenie przez bezpośredni link w nowym kontekście przeglądarki.

To kompletna koncepcja części w Studio, nie projekt produkcyjny. Wycięcia
w sklejce, dokładne pasowanie przekrojów, certyfikowana nośność, kinematyka
zawiasów, nity i wkręty oraz pełny eksport tych wystąpień do CAD nadal
wymagają dalszego etapu. `production_approved` i `purchase_bom_ready`
pozostają false. Nie oznaczać tej pracy jako natywnej walidacji CAD.
