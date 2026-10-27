# Studio — krok 5: rozmieszczenie okuć

Aktualizacja 27.10: wszystkie 39 części źródłowych mają rzeczywistą geometrię
3D w rozmieszczaniu i podczas przeciągania. Szczegóły ram prezentacji i podczęści:
[STUDIO_SOURCE_PARTS.md](STUDIO_SOURCE_PARTS.md). Historyczne opisy znaczników
poniżej odnoszą się do wcześniejszego checkpointu lub braku siatki.

27.10.2026. Działający planer koncepcyjny i interaktywny podgląd WebGL,
bez uruchamiania IronCAD. Operuje wyłącznie częściami wybranymi w kroku 4.
Późniejszy przyrost: [płynny ruch, środkowy przycisk, więcej uchwytów
i rzędy zawiasów](STUDIO_INTERACTION.md).
[Import z pozostałych projektów](STUDIO_SOURCE_PARTS.md) dodaje lokalnie 39
wariantów źródłowych do palety; niepotwierdzone ramy używają znaczników.

## Użycie

1. W kroku 4 wybierz np. H7159. Przejdź do kroku 5.
2. Przeciągnij jego kartę na zewnętrzną ściankę podglądu. Można też kliknąć
   kartę i ściankę lub użyć przycisku „Dodaj na wybranej ściance”.
3. Domyślnie uchwyty tworzą układ po dwa na przeciwległych bokach. Wybranie
   jednego oznacza po jednym wyśrodkowanym na każdej ściance: łącznie dwa.
   Wybierz parę ścian prostopadłych do ściany zawiasów; aplikacja nie odgaduje
   potwierdzonej strefy zawiasu z samego SKU. Domyślny korpus ma parę lewa/prawa.
4. Włącz/wyłącz przeciwległą ściankę i symetrię. Układ ręczny może mieć przesunięty
   środek rzędu; niezależne pozycje tworzy się jako osobne pojedyncze grupy.
5. Złap okucie w podglądzie, aby przestawić całą grupę. Dla symetrycznej pary
   ruch poziomy zmienia rozstaw, pionowy wspólną wysokość. Jedna symetryczna
   sztuka pozostaje na środku; pion można przesuwać.
6. Parametry lub lista grup pozwalają wybrać, obrócić, przestawić i usunąć grupę.
   „Zakończ wstawianie / obracaj widok” wyłącza wstawianie kliknięciem.
7. Zapisz draft lub wyeksportuj JSON. Rozmieszczenie jest objęte istniejącymi
   rewizjami SQLite/CAS i odzyskiwaniem przeglądarki.

Panel rozróżnia liczbę **na jedną ściankę**, sumę grupy i liczbę definicji SKU.
Nie są to ilości zakupowe. Grupa uchwytów zapisuje `handles_per_wall` jawnie,
obecnie w zakresie 1–16. Pozostałe okucia mogą mieć 1–16 sztuk na ściankę, w pojedynczym, równym lub
symetrycznym rzędzie. Cała koncepcja: maksymalnie 32 grupy i 256 wystąpień.

## Kotwy i geometria

Draft `rockpro.configurator/3` ma opcjonalne pole `placements` z grupami:

```json
{"id":"carry-1","part_id":"H7159","revision":1,
 "section_id":"body","face":"left","u":0.5,"v":0.5,
 "rotation_deg":0,"pattern":"symmetric","count_per_wall":2,
 "handles_per_wall":2,"opposite_wall":true,"spread":0.5}
```

`u/v` i `spread` są udziałami wymiarów **zewnętrznej ścianki konkretnej sekcji**,
0–1, bez powiększania sekcji. Dla symetrii środek rzędu wynosi 0,5; `spread`
określa odległość skrajnych środków jako część szerokości ścianki. Wysokość
jest wspólna. Na górze/dole druga oś biegnie w głąb płyty. Ramy są prawoskrętne,
normalna skierowana na zewnątrz; przeciwległe ramy są przeliczane tak, by
odpowiadające sobie uchwyty zachowywały tę samą pozycję wzdłuż korpusu.

`studio_placement.py` wyprowadza dostępne ścianki z rzeczywistych paneli
schematu. Nie dodaje powierzchni w miejscu otwarcia. Interakcja raycast odrzuca
wnętrza i wąskie krawędzie sklejki. Nie można złapać okucia przez przeciwległą
nieprzezroczystą płytę. Markery są dziećmi grup sekcji, więc podążają za otwieraniem.
Zmiana wymiarów przelicza pozycje; gotowy model okucia zachowuje rozmiar.

Zmiana typu zachowuje grupy związane z dawnymi ID sekcji. Brak sekcji/ścianki
lub brak ściany pary daje `unresolved_groups` i ostrzeżenie; użytkownik może
wybrać nową ściankę lub usunąć grupę. Nie ma cichego przypisania do nowego wieka.
Nowe przeciągnięcie na nieistniejącą parę jest odrzucane bez zmiany grupy.
Usunięcie SKU w kroku 4 wymaga potwierdzenia usunięcia jego istniejących grup.

## Zakres kontroli i podglądu

- H7159: referencyjny obrys 161 × 107 mm. 17251S: 127 × 174,5 mm z eksportu
  obu poprawnie sparowanych połówek T1. 27095: 102 × 105 mm, jak w rozpoznaniu
  montażu T1. To obrysy do wstępnego planowania, nie kontury wycięć.
- Dla tych części sprawdzamy obrót 0/90/180/270°, granice ścianki i zachodzenie
  znanych obrysów na tej samej ściance, z jawną wstępną rezerwą 5 mm.
  Ostrzeżenie nie podmienia intencji konstruktora i nie blokuje zapisu koncepcji.
- Dla pozostałych SKU brak danych obrysu jest jawny. Umowny znacznik 64 × 44 mm
  nie jest pomiarem rzeczywistego okucia ani pozytywną walidacją kolizji.
- Zawias/zatrzask na ściance pozostaje nieprzypisany do złącza: ostrzeżenie
  `unbound_joint` w trybie ręcznym. Rząd `joint_line` wiąże się z linią styku,
  ale rzeczywisty montaż i wycięcia nadal wymagają potwierdzenia. Luzy profili,
  przestrzeń ruchu i kontrola narożników należą do następnego etapu.
- Lokalny pakiet ma siatki H7159 i 17251S. W pozostałych pozycjach podgląd
  pokazuje jawny znacznik z obrazem. To referencje, bez zatwierdzonego montażu.
  Przy braku pakietu cały interfejs działa z oznaczonymi znacznikami.
- `cad_ready=false`, `production_approved=false`, `cutouts_generated=false`.
  Szczelina złącza i docięcia pozostają nieustalone. Nie zapisujemy ICS.

## Lokalne zasoby i kod

`scripts/prepare_studio_part_meshes.py` tworzy w prywatnym pakiecie obrazów
siatki `rockpro.part-mesh/1` z jawnego mapowania korzeni i ram montażowych.
Sprawdza SHA bufora źródłowego, przelicza współrzędne i normalne; nie skaluje
brył, nie otwiera CAD i nie zmienia źródeł. T1 wymaga dla zamka pary korzeni
192 + 78, nie 192 + 380 (druga połówka po drugiej stronie skrzyni).
Mapowanie prywatne: `artifacts/wizard-placement-20261027/mesh-mapping.json`.
Pakiet: `artifacts/studio-part-images/`. Po ponownym renderowaniu miniatur
trzeba ponownie przygotować powiązane siatki.

`part_images.py` kontroluje SHA i pozostawanie siatki JSON w katalogu (limit
16 MB). Serwer ma jawną trasę `part-models/…`, a klient ponownie sprawdza SHA
przed dekodowaniem. Pliki i eksporty klienta pozostają poza Git.

Kod UI: `placement-editor.js`, `placement3d.js`; wspólny renderer `wizard3d.js`.
API podglądu zwraca sekcję `placement` (`rockpro.concept-placement/1`): dostępne
ramy, rozliczone wystąpienia, pozycje mm, liczniki i ostrzeżenia. Draft przechowuje
intencję, a nie przeliczone współrzędne świata. Starszy v3 bez rozmieszczenia działa.

## Sprawdzenia

PASS: 33 testy Studio/konfiguratora, w tym domyślne 4 uchwyty, wariant 2,
symetria, stałe gabaryty okuć po resize, odrzucanie nieznanych pól/ID/rewizji,
ostrzeżenia, brakujące ścianki i zapis SQLite. Pełny harness PASS:
`artifacts/verification/20261027T155058089117Z/`.

PASS: przeglądarka — rzeczywisty drag and drop z palety, złapanie i przesunięcie
istniejącej grupy, zmiana liczby, resize, 13/35 siatek części dla referencji,
ostrzeżenia o obrysach, SQLite, reload, eksport/import JSON, okucie podążające
za otwartym wiekiem i szerokość 430 px. Raport i obrazy:
`artifacts/wizard-placement-20261027/`.

Natywny CAD, wiercenia/wycięcia, wysłanie do IronCAD i akceptacja konstruktora:
NOT RUN — poza tym przyrostem.
