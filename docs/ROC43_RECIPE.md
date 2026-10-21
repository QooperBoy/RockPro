# ROC-43 — syntetyczna recepta wejściowa

`tests/core_design/synthetic_template.json` jest zamrożonym wejściem do czystego
`rockpro_cad.core_case.plan_case(request)`. Wersje: schema `1`, template
`synthetic-roc43-v1`, rule pack `synthetic-roc43-rules-v1`. Adapter testowy przekazuje
ją jako `request.template_recipe`, obok `spec`, `manifest` i `scenario`.
Recepta zawiera 37 ról i domyślnie 67 fizycznych wystąpień. Pusty zespół pozostaje
osobną pozycją inwentarza. Nie jest to zatwierdzony katalog ani odczyt wzorca Epson.

Recepta zawiera reguły wejściowe, wymiary syntetycznych części, punkty montażowe,
ramy, odsunięcia, liczności, parowania i zakresy wyjątków. Nie zawiera współrzędnych
wynikowych przypadków ani selekcji po `case_id`. Niezależne liczby oczekiwane są
zamrożone w `cases.json`; planner nie może importować fixture, oracle ani specimen.
Oracle nie może generować oczekiwań przez interpretację recepty. Zgodność obu
zapisów jest sprawdzeniem ich spójności, nie dowodem implementacji generatora.

Interpreter ma używać wyłącznie zamkniętej listy `expression_language.op_allowlist`
i jawnych selektorów wejścia. `ref` wskazuje pole specyfikacji albo wcześniej
zdefiniowaną nazwę `derived`; nie jest wyrażeniem języka Python. Listy i drzewa
operacji są danymi. Nie wolno stosować `eval`, `exec`, shell, importów z danych,
dowolnych wywołań funkcji ani dynamicznego dostępu do właściwości obiektów.
Nieznana operacja, referencja lub wersja, cykl, zła arność, boolean w polu liczbowym,
NaN/inf i dzielenie przez zero muszą blokować plan. Kolejność `derived` jest jawna.
Nazwy obrotów, definicji, ram i grup muszą istnieć i być unikalne.

`q` to obrys urządzenia po wyborze orientacji; jego bryłę obrysową umieszczamy z
obrotem identity. `comp*` to komora urządzeń po uwzględnieniu głębokości i wysokości
akcesoriów, przed dodaniem ściany bocznej. `internal` dodaje tę ścianę i przestrzeń
akcesoriów. W/D/H to obrys sklejki; B = H − L. W syntetycznym kontrakcie lokalne
wnętrze zaczyna się w początku closed bez przesunięcia o grubość sklejki. Płyty
leżą symetrycznie wokół płaszczyzn montażu. To uproszczenia testowe, nie reguły
produkcyjnych połączeń. Obsługiwane dwa urządzenia i dwa dzielniki są jawnym
zakresem tej wersji, a nie domyślną regułą dla dowolnej liczby urządzeń.

Macierze są zapisane wierszami; kolumny ramy są lokalnymi osiami u/v/n w closed
XYZ. Punkt spełnia P = O + R·uvn. Obrót wystąpienia jest już obrotem katalogu do
closed: nie mnożymy go ponownie przez obrót ramy. Wszystkie obroty muszą być
ortogonalne z determinantą +1. Kolejność naroży: (0,0), (W,0), (0,D), (W,D).
Naroża wieka mają dodatkowy właściwy obrót o 180° wokół lokalnego X; normalna
katalogowa Z jest skierowana w dół. Geometryczne odbicie przez skalę ujemną jest
niedopuszczalne. Identyfikator wystąpienia to `group_id/indeks`, od 1.

Zwykły uchwyt jest wycentrowany na przedniej ścianie korpusu. Dla 2/3/4 uchwytów
`scenario_contract` definiuje wspólny wzór z odsadzeniami 100 i 260 mm; środkowy
element nieparzystego wzoru leży na W/2. Kolejne obrysy szerokości 150 mm wymagają
co najmniej 10 mm przerwy, a wysokość 80 mm musi zmieścić się na ścianie. Wzór,
który nie mieści się na ścianie, jest odrzucany. Wyjątek pojedynczego uchwytu
narożnego dotyczy wyłącznie grupy `corner-handle` i jej stabilnej ramy. Osobny
syntetyczny identyfikator zgody dotyczy wyłącznie wymienionych grup wnętrza oraz
ich lokalnych środków symetrii. Żaden wyjątek nie wyłącza kompletności grup,
właściwego obrotu, kontroli liczb ani rozliczenia części.

Resize zmienia W/D/H, B, przestrzeń internal = [W−2T, D−2T, H−2T], ramy i części
zależne od obrysu. Obrysy urządzeń,
akcesoriów i dzielników zachowują lokalne położenia wynikające ze specyfikacji;
insert/foam/custom/import podążają za środkiem nowego korpusu. Całościowa,
zatwierdzona zmiana odsadzenia grupy braces zastępuje domyślne 80 mm i pozostaje
przy kolejnym resize. Samowolna zmiana jednego członka jest konfliktem.
Powrót liczności do 1 przywraca tryb centered, 2 używa mirrored_pair, 3/4
centered_pattern. Operacja reconcile przyjmuje zatwierdzone parametry całych
grup braces/handles oraz dodany element z kotwą. Dla dodatkowej syntetycznej
kostki 20 mm dozwolone reguły kotwy są jawnie wyliczone w recepturze jako
`W/2`, `D/2`, `base_height/4`. Są to etykiety zamkniętej mapy, nie kod do
wykonania. Przy resize przeliczamy ich zapisane drzewa operacji, zachowujemy
zgodę i dodajemy część do inwentarza oraz obrysu. Brak kotwy blokuje uzgodnienie.

Parowanie zamków i zawiasów porównuje wszystkie trzy współrzędne closed;
koła i gniazda porównują X/Y. Szczelina prezentacji przesuwa jedynie wskazane
grupy wieka w podglądzie. Operacja display odczytuje `scenario.display_gap`,
a bez tego wejścia używa `spec.display_gap`. Nie zmienia punktów closed, par ani gabarytu
transportowego. Gabaryt ten jest sumą obrysów AABB wszystkich przekształconych
syntetycznych wystąpień, nie dodanym arbitralnie stałym naddatkiem.

Recepta jawnie dopuszcza wspólne symboliczne położenie insert/foam/custom/import
oraz styki montażowe połówek okuć i profili zamykających. Sam AABB nie zatwierdza
kolizji. Wycięcia, szczegółowe styki profili, nośność, podparcie piętrowania,
montaż i zapis/otwarcie w IronCAD pozostają poza dowodem tego TDD. Zmiana danych
recepty nie implementuje interpretera, generatora ani wykonawcy CAD.

## Aktualny runtime

Interpreter jest zaimplementowany w `core_case/expressions.py` i `planner.py`.
Kopia wejściowej recepty runtime znajduje się w `core_case/templates/prototype-v1.json`;
kod produkcyjny nie importuje oczekiwań testowych. Sam format opisany powyżej
nie stanowi dowodu natywnego CAD. Stan i ograniczenia: [CORE_PROGRESS.md](CORE_PROGRESS.md).
