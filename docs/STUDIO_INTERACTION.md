# Studio — płynne rozmieszczanie i linie zawiasów

27.10.2026. Rozszerzenie kroku 5, bez natywnych zmian w IronCAD.
Studio zachowuje lokalny Three.js r180 (wersja/SHA/licencja w
`viewer3d/vendor/PROVENANCE.json`). Nie aktualizowano silnika.

## Biblioteki i wybór rozwiązania

| Narzędzie | Decyzja po sprawdzeniu dokumentacji autorów |
|---|---|
| [OrbitControls](https://threejs.org/docs/pages/OrbitControls.html) | Używane do obrotu, przesuwania i zoomu przez udokumentowane `mouseButtons`. Wspólna konfiguracja kreatora, galerii i Workstation. |
| [DragControls](https://threejs.org/docs/pages/DragControls.html) | Gotowy mechanizm przeciągania. Pozostawiono warstwę na Raycaster/ramach ścian, ponieważ okucie ma trzymać się powierzchni lub przypiętego złącza. Nie dodano zależności. |
| [TransformControls](https://threejs.org/docs/pages/TransformControls.html) | Przydatne w przyszłości do gizmo osi i skokowego przesuwania/obrotu. Nie wdrożono: obecny montaż nie wymaga swobodnej translacji XYZ ani skalowania okuć. |
| [three-mesh-bvh](https://github.com/gkjohnson/three-mesh-bvh) | Przyspiesza zapytania/raycast po siatkach. Kandydat dla przyszłego precyzyjnego wskazywania dużych modeli CAD. Obecnie chwytamy lekkie obrysy, więc BVH nie dodano. |
| [camera-controls](https://github.com/yomotsu/camera-controls) | Alternatywa z płynnymi przejściami kamery. Zachowano OrbitControls i usunięto konflikt jego bezwładności z przeciąganiem. Nie wdrożono. |

Nie ma połączenia z CDN w runtime. Obliczeń rozmieszczenia nie wykonuje AI.

## Sterowanie i płynność

- Środkowy: obrót. Prawy: przesuwanie. Rolka: zoom. Lewy: chwytanie okuć,
  wstawianie aktywnej części lub obrót pustego tła. Ustawienia są wspólne.
- Pozycja podglądu aktualizuje się w pętli renderowania, najwyżej raz na klatkę.
  Ruch zachowuje liczbę i symetrię. Paleta pokazuje półprzezroczyste znaczniki,
  istniejące grupy przesuwają swoje rzeczywiste siatki pod kursorem.
- Draft/backend nie zmieniają się podczas ruchu. Puszczenie zatwierdza intencję;
  Escape, utrata wskaźnika i nieprawidłowe miejsce przywracają stary układ.
- `stopOrbitMotion` opróżnia publiczny stan bezwładności bez skoku kamery,
  przed chwyceniem części i ręcznym dopasowaniem widoku.
- Raycast trafia w proste obrysy z kontrolą zasłonięcia przez sklejkę.
  Nie skanuje wszystkich trójkątów powtórzeń H7159.
- SKU współdzieli geometrię/materiały. Grupy kolorów powierzchni CAD zamieniono
  na kolory wierzchołków: jeden draw call na fizyczną podczęść. Nie zmienia to
  gabarytów ani trójkątów modelu.

Scena testowa z 8 H7159 wykazała 134 wywołania rysowania. To pomiar konkretnej
sceny, nie gwarancja FPS na każdym komputerze.

## Liczności

Studio: **1–16 uchwytów na ściankę w grupie**, nadal domyślnie 2 na dwóch
przeciwległych bokach. `handles_per_wall` pozostaje jawne i równe
`count_per_wall`. Pozostałe rzędy ścienne także mają 1–16 sztuk.
Limity 32 grup/256 wystąpień pozostają; części nie są skalowane.
Stary natywny generator T1 zachowuje odrębny kontrakt 1/2.

Symetria utrzymuje środek rzędu na połowie ścianki. Przesunięcie bocznej sztuki
zmienia rozstaw; środkowa sztuka nie zmienia rozstawu, ale może zmieniać wysokość.

## Zawiasy na styku

Nowy wariant grupy w opcjonalnym `placements` draftu v3:

```json
{"id":"hinges-1","part_id":"27095","revision":1,"pattern":"joint_line",
 "joint_id":"joint-id-wieka","hinge_count":3,"edge_inset_mm":80}
```

`studio_joints.py` wyprowadza linię z topologii: górne wieko → pozioma linia
przód/tył, przednia powłoka szafy → pionowa linia lewa/prawa, według kroku 2.
Szafa automatycznie obraca znak zawiasu o 90/270°. Zdejmowane sekcje nie mają
domyślnej linii zawiasów. Starsze grupy ścienne zachowano; przycisk konwersji
do rzędu jest jawny i zachowuje ID grupy.

1 zawias daje środek; dla n≥2 skrajne osie są odsunięte od końców o zadaną
wartość mm, a pozostałe dzielą odcinek równomiernie. Odsunięcie zachowuje się
przy resize. Zmiana strony w kroku 2 przenosi rząd; usunięcie dawnego ID złącza
wymaga jawnego ponownego przypisania. Przeciąganie istniejącego rzędu ogranicza
się do jego linii i zmienia wspólne odsunięcie skrajnych osi.

Zdjęciowy znacznik jest poglądowo podzielony na połowy przypięte do korpusu
i wieka. Podział 50/50 **nie jest pomiarem rzeczywistej osi**, ruchowym modelem
zawiasu ani zatwierdzeniem połówek katalogowych.
Ostrzeżenia obejmują zbyt krótką linię, odsunięcia, nakładanie znanych obrysów
i brak miejsca po stronie pokrywy. Rzeczywiste bazy, profile, ruch i wycięcia
wymagają potwierdzenia. Nie powiększamy sekcji, nie generujemy obróbek ani ICS.

## Sprawdzenia

PASS: 36 testów Studio/konfiguratora; pełny harness
`artifacts/verification/20261027T171424624872Z/`.
PASS: przeglądarka — 4 uchwyty/ściankę, wspólna geometria, MMB przy aktywnym
wstawianiu, ruch przed puszczeniem bez żądań HTTP, Escape, 3 równe zawiasy,
ruch obu połówek, strona, resize, SQLite/reload/JSON i ekran 430 px.
PASS: 5 porównań pozycji JS/Python (uchwyty, góra przód/tył, szafa lewa/prawa).
Dowody: `artifacts/studio-interaction-20261027/`.
Natywny montaż CAD i zgoda produkcyjna: NOT RUN / poza zakresem.
