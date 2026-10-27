# Studio — panele, rozmiar podglądu i tryb nocny

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
