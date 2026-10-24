# ROC-25 — do trzech wariantów z ograniczeniami

preview_device_layouts(record, spec, allowed_orientations, allowed_arrangements,
removal_clearance_mm=0, max_external_mm=None) korzysta z istniejącego solvera
layout._calculate_layout. Wymiary xyz pochodzą z rekordu urządzenia, nie z
ręcznie podmienionych liczb w spec. Listy dozwolonych orientacji i kierunków
są jawne. Brak dozwolonej konfiguracji daje manual_design_required.

Dla każdego wariantu solver sprawdza obrysy, przegrody i kolizje. Dodatkowo
sprawdzany jest pionowy tor wyjmowania każdego urządzenia w +Z, z zadanym luzem
chwytu XY. Pokrywa musi być całkowicie otwarta lub zdejmowana. Tor nie może
przecinać drugiego urządzenia ani przegrody/wyposażenia. Jest to kontrola AABB,
a nie symulacja ruchu pokrywy, przewodów i gotowych okuć w CAD.

Równoważne geometrie są usuwane, wyniki sortowane po objętości i ograniczone
do trzech. Gdy wykonalny jest tylko jeden wariant, odpowiedź zawiera jeden.
Każdy ma uzasadnienie, zakres kontroli, pełny edytowalny layout.spec oraz hash
źródłowego rekordu i identyfikator propozycji. Zmiana źródła zmienia identyfikator.

Braki i sprzeczności wymiarów blokują obliczenie. Wartości niepotwierdzone mogą
posłużyć do jawnej propozycji, ale każda taka propozycja ma
DEVICE_DIMENSIONS_UNCONFIRMED w release_blockers. Żaden wariant sam nie daje
production_approved. Nie ma automatycznego zapisu ani wyboru.

Konstruktor może zmienić spec/orientację w istniejącym konfiguratorze lub
odrzucić wszystkie propozycje. Zapis wybranego/zmienionego spec korzysta ze
zwykłego save_layout z odczytanym expected_revision. Nie odświeżamy rewizji
w tle. Nowe ograniczenia są dostępne w MCP; aktualnie otwarta DLL nie została
przeładowana i jej starszy przycisk minimum 18 kombinacji nie udaje nowego
sprawdzenia dostępu. Odbiór nowej pełnej ścieżki UI pozostaje osobnym krokiem.

PASS w pięciu testach: limit trzech / pojedynczy wariant, jawne dozwolone
orientacje i gabaryty, blokada piętrowania i niewystarczającego luzu chwytu,
brakujące/niepotwierdzone dane oraz identyfikacja źródła bez zapisu.
Rzeczywisty rekord Epson odczytany z katalogu dał dwie różne propozycje dla
XYZ/YXZ i X/Y przy granicy 650×500×381 mm. Dowód offline:
artifacts/overnight-20261024/epson-layout-variants.json. To gabaryty propozycji
solverowej; nie jest to zmiana ukończonego modelu CAD.

Pełny harness po przyroście: PASS, artifacts/verification/20261024T214830686049Z/results.json.
