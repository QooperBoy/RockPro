# Studio — krok 6: zatrzaski i zawiasy na złączach

27.10.2026. Dostępny w kreatorze po rozmieszczaniu uchwytów na ściankach.
Wybierz rodzaje okuć w kroku 4, uchwyty rozmieść w 5, zamknięcia w 6.

## Zachowanie

- Linie wynikają z nominalnego styku korpusu i konkretnego wieka, wspólnych
  płaszczyzn oraz faktycznie istniejących płyt. Nie powstaje linia montażu
  na pustej/otwartej ścianie. Zawiasy są dostępne po stronie z kroku 2,
  zatrzaski na pozostałych krawędziach. Wieko zdejmowane ma tylko zatrzaski.
- Każdy rząd ma stałe ID, `seam_id`, część/referencję rewizji, 1–16 okuć,
  minimalne odsunięcie skrajnych osi, rezerwę i jawne omijanie uchwytów.
  Zmiana wymiarów przelicza pozycje bez skalowania okuć. Zmiana strony
  otwierania może unieważnić linię; rząd pozostaje do jawnego poprawienia.
- Domyślnie solver zachowuje równy rozstaw. W dopuszczalnym zakresie dobiera
  największy rozstaw i przesunięcie najbliższe środka, omijając uchwyty
  oraz wcześniej rozwiązane rzędy. Bada zdarzenia przecięcia przedziałów,
  nie próbuje przypadkowych pozycji. Pojedyncze okucie jest możliwie blisko
  środka. Odległości liczone są w mm na danej linii.
- Obrysy uchwytów pochodzą ze znanych definicji albo zweryfikowanych siatek
  podglądu. Dla nieznanego obrysu pozostaje umowny rozmiar i ostrzeżenie.
  Rezerwa jest parametrem koncepcji, nie tolerancją produkcyjną.
- Brak miejsca oznacza `closure_no_space` i brak wystąpień tego rzędu.
  Definicja rzędu zostaje w drafcie, wymiary skrzyni nie zmieniają się.
  Wyłączenie omijania pokazuje konflikt, nie zatwierdza układu.
- Za mało miejsca po stronie korpusu lub wieka daje osobne ostrzeżenie.
  Program nie podwyższa automatycznie pokrywy i nie zmienia korpusu.

## Części i podgląd

Dla kompletnego wpisu katalogowego wybiera się jedną definicję. Dla źródłowego
komponentu należy jawnie wybrać dwie różne części tej samej rodziny, obie
z kroku 4: pierwsza na korpusie, druga na wieku. UI i backend wymagają obu
referencji/rewizji. Nie dopasowujemy ich automatycznie po podobnej nazwie.
Taki wybór jest propozycją konstruktora, nie zatwierdzeniem zgodności pary,
pełnego SKU ani ilości zakupowej. Obie definicje są liczone oddzielnie;
liczba rzędu oznacza liczbę par. Usunięcie którejkolwiek części z kroku 4
usuwa zależny rząd po istniejącym potwierdzeniu użytkownika.

Źródłowe połówki mają rzeczywiste siatki i podążają za swoimi sekcjami.
Kompletny model referencyjny jest dzielony prezentacyjnie według środka
lokalnego obrysu fizycznych podczęści: podczęści pozostają całe, nie przecinamy
ich trójkątów. Bez siatki pozostaje jawny znacznik zdjęciowy. To nie jest
potwierdzona kinematyka ani ustalona oś konstrukcyjnego zawiasu.

Linie zatrzasków są pomarańczowe, zawiasów niebieskie. Kliknięcie wystąpienia
rzędu otwiera jego formularz. Pozycje na złączu edytuje się liczbą, rezerwą
oraz wyborem linii; nie można odłączyć rzędu swobodnym przeciągnięciem.
Stary `joint_line` z kroku 5 nadal jest odczytywany bez migracji.

## Dane i granice

W `rockpro.configurator/3` dodano opcjonalny wariant istniejącej listy
`placements`: `pattern=closure_line`. Zapis SQLite, rewizje, eksport/import
JSON zachowują komplet pól. Brak pola w historycznych draftach działa jak
wcześniej. Nie zmieniono definicji części ani zgód produkcyjnych.

Nowe moduły: `studio_closures.py`, `reference_studio/closure-editor.js`.
Integracja: `studio_placement.py`, `placement3d.js`, `wizard.js`.

Kontrola dotyczy statycznych obrysów na wspólnej płaszczyźnie w zamkniętej
koncepcji. Nie jest dokładnym testem brył, kolizji ruchu, profili i nitów.
Nie generuje wycięć ani nowych modeli ICS. W rodzinie 3-elementowej ten krok
obejmuje złącza korpusu z pokrywami; osobny styk dwóch pokryw nie jest
zastępowany wymyśloną ścianą korpusu.

## Weryfikacja

PASS: testy topologii trzech rodzin, równych rozstawów i zmiany wymiarów,
omijania uchwytów, niemożliwych układów, zakresów/liczb i jawnych par.
PASS: przeglądarka — formularz kroku 6, zatrzaski, strona zawiasów,
pary źródłowe 3D, ruch podczęści z odpowiednią sekcją, zapis/wczytanie SQLite.
Pełny harness PASS: `artifacts/verification/20261027T185526440339Z/`;
po doprecyzowaniu solvera wykonano ponownie testy zmienionego modułu i UI.
Dowody lokalne: `artifacts/studio-step6-20261027/`.
Natywna integracja CAD / nowe wycięcia: NOT RUN, poza tym przyrostem Studio.
