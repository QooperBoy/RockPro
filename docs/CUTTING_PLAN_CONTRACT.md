# ROC-30 — neutralny rozkrój i niezależna kontrola

`mcp/cutting_plan.py` dostarcza neutralny JSON/CSV, referencyjny first-fit oraz
niezależny weryfikator drzewa cięć gilotynowych. Nie jest postprocesorem maszyny
ani potwierdzoną integracją z instalacją WoodLAB PLAN; lokalny PLAN jest niedostępny.
Próba profilu importu i rzeczywistego rzazu/marginesów pozostaje NOT RUN.

Wejście to zahashowane zapotrzebowanie ROC-29, fizyczne arkusze o unikalnych ID
oraz jawna technologia: id, profile_revision, kerf_mm (>0), trim_mm w kolejności
lewy/prawy/dolny/górny, cut_type=guillotine. Arkusz ma materiał, wykończenie,
technologię, grubość, długość/szerokość, grain i datę dostępności.

Plan jest związany hashem wszystkich wejść. Każdy węzeł `cut` dzieli cały
pozostały prostokąt na dwie części z utratą rzazu; rekurencyjny odczyt od korzenia
daje kolejność cięć. Liście `part` odwołują się do grupy BOM i jawnego obrotu,
`waste` opisuje pozostały prostokąt. Nie dopuszczamy nakładania przez osobne
swobodne współrzędne. Weryfikator wylicza je sam z drzewa.

Kontrola porównuje dokładne ilości i wymiary technologiczne, materiał/grubość,
grain po obrocie, politykę obrotów, termin dostępności, marginesy i rzaz.
Wynik zawiera położenia z liniami źródłowych zleceń oraz kolejność pełnych cięć.
Tolerancja liczbowa wynosi 0,000001 mm. Referencyjny solver ma limit 2000 formatek,
500 arkuszy, 30 s i głębokości drzewa. Może nie znaleźć istniejącego rozwiązania;
nie deklaruje optimum. Timeout nie publikuje częściowego planu jako poprawnego.

`export_cutting_csv` wymaga jawnego mapowania kolumn w zweryfikowanym profilu
producenta; wynik machine_ready=false. Nie wysyła danych do maszyny/producenta.

PASS: pięć testów obejmuje 2 × 500 mm na 1000 mm z rzazem 3 mm (odmowa), poprawny
arkusz 1003 mm, ilości, duplikację arkusza, grain/obrót, termin, marginesy,
zmianę wejścia po planie i timeout. Wszystkie próby używają technologii testowej.
NOT RUN: akceptacja technologii klienta, PLAN i wykonanie na maszynie.
