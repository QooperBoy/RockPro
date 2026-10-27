# Studio — panele, rozmiar podglądu i tryb nocny

Przejścia stanów na desktopie są animowane przez 190 ms (ease-out): menu
pełne/ikony/ukryte, zwijanie ustawień i 3D. Interpolowana jest rzeczywista
szerokość kolumn, a tekst menu łagodnie zanika. Zwykły resize w obrębie
tego samego stanu nadal bezpośrednio śledzi kursor. Szybka zmiana kierunku
rozpoczyna przejście od bieżącego rozmiaru, bez kolejki animacji. Preferencja
`prefers-reduced-motion` wyłącza animację; wąski mobilny układ pozostaje bez
animacji kolumn. PASS: próbki kolejnych klatek potwierdzają rozmiary pośrednie
menu, edytora i 3D; przywracanie i niezmienność draftu sprawdzone osobno.
Dowody: `artifacts/panel-motion-20261027/`.

Aktualizacja sterowania: przyciski Menu/Ustawienia/Podgląd 3D usunięte.
Przeciągnięcie krawędzi wykonuje resize oraz snap do ikon/ukrycia. Uchwyty
są niezależne od ukrywanego panelu i pozostają przy krawędziach do jego
przywrócenia. Granica formularza pozwala schować formularz w lewo lub 3D
w prawo; po ukryciu 3D uchwyt na prawym brzegu przywraca go ruchem w lewo.
Menu przeciągnięte do małej szerokości przechodzi w ikony, dalej do ukrycia;
uchwyt przy lewym brzegu rozwija je ponownie. Strzałki i Home nadal działają.
PASS: trzy ukrycia/przywrócenia przeciąganiem i niezmieniony draft.
Dowody: `artifacts/edge-only-panels-20261027/`. Starsze opisy przycisków są historyczne.

Aktualny wzorzec zmiany rozmiaru: wyłącznie trzy jednakowe uchwyty na granicach
(menu/edytor/3D), z jedną obsługą pointer capture i strzałek. Usunięto osobne
suwaki menu i wysokości 3D. Podgląd nie zawiera kart „Sekcje i otwieranie”
ani „Status techniczny podglądu”. Ikony otwarcia/zamknięcia pozostają.
Ograniczenia techniczne są nadal w dokumentacji i szczegółowych walidacjach.
PASS: identyczne style uchwytów w obu motywach, trzy przeciągnięcia, brak
duplikatów, otwarcie/zamknięcie i niezmienność draftu; dowody lokalne
`artifacts/consistent-splitters-20261027/`. Starsze opisy suwaków poniżej są historyczne.

Aktualizacja: menu ma trzy tryby (pełne → ikony → całkowicie ukryte),
własny suwak szerokości 160–320 px i pamięć wybranego trybu. Przycisk Menu
w nagłówku przywraca dostęp również po pełnym ukryciu. Ukrycie 3D usuwa cały
prawy panel, a formularz zajmuje dostępną szerokość. Container queries dobierają
kolumny filtrów, kart i edytorów do rzeczywistego miejsca, niezależnie od
szerokości całego monitora. Usunięto zbędny opis pojedynczego wieka z kroku 1.
PASS: przeglądarka — wszystkie tryby menu, suwak, pełne ukrycie 3D, rozszerzenie
formularza, trwałość preferencji, zachowanie draftu i mobile. Dowody:
`artifacts/studio-fluid-layout-20261027/`.

27.10.2026. Kontrolki w nagłówku są niezależne od danych projektu:

- Menu zwija się do wąskiego paska ikon/numerów etapów; przycisk Menu je rozwija.
- Ustawienia zwija/przywraca panel bieżącego kroku.
- Podgląd 3D minimalizuje prawą część do nagłówka z przyciskiem przywracania.
- Granicę panelu ustawień można przeciągać; klawiatura: strzałki lewo/prawo,
  Home. Szerokość jest ograniczona tak, by zostawić przestrzeń na model.
- Uchwyt pod podglądem i suwak „Wysokość 3D” zmieniają wysokość 260–900 px.
  Strzałki góra/dół i Home obsługują uchwyt bez myszy. Przy niskim podglądzie
  narzędzia przechodzą w poziomy pasek, aby nie wychodzić poza obszar 3D.

Zapis preferencji: `rockpro.studio.layout.v1` w localStorage. Nie jest częścią
draftu, nie zmienia wymiarów, okuć, rewizji ani zapisanych projektów. Zmiana
proporcji kadru zachowuje kierunek patrzenia i dopasowuje odległość kamery.
Zminimalizowany podgląd wstrzymuje rendering do przywrócenia.

Tryb jasny/nocny przełącza się u góry. Wybór jest zapisany w
`rockpro.studio.theme`. Wspólny motyw obejmuje kreator, bibliotekę, pola,
przyciski, karty, statusy, pomoc i tła scen 3D. Barwy geometrii i oryginalnych
obrazów referencyjnych pozostają danymi źródłowymi; nie odwracamy ich kolorów.
Sceny kreatora i interaktywnej biblioteki reagują również na przełączanie
motywu już po załadowaniu. Motyw nie steruje wyglądem programu IronCAD.

Kontrola nakładania: nagłówek, narzędzia, kostka, jej lista widoków,
długie nazwy i karty przy szerokościach 1920/1366/1024/800/390 px. Długie nazwy
są ograniczone do dwóch linii, pełny tekst jest w title. Pasek narzędzi nie
nakłada się na kostkę nawet przy wysokości 280 px. Mobilna nawigacja zachowuje
przyciski układu i motywu w nagłówku. Poprawiono dodatkowe jasne powierzchnie
podglądu biblioteki (`three-settings`, wynik szkicu, etykiety i chipsy).

PASS: test przeglądarkowy — zwijanie/przywracanie, przeciąganie separatora,
zmiana szerokości klawiaturą, wysokość 3D, niska przestrzeń robocza,
zachowanie draftu, brak renderowania po minimalizacji, motyw na obu ekranach,
trwałość preferencji oraz testy kolizji prostokątów UI na pięciu szerokościach.
PASS: 11 testów serwera Studio. Dowody: `artifacts/studio-panels-night-20261027/`.
Natywny CAD: NOT RUN / poza zakresem tej zmiany interfejsu.

Pełna regresja PASS: `artifacts/verification/20261027T202502603373Z/`.
