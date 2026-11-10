# ROC-24 — filtry i ranking kandydatów rodzin

Narzędzie recommend_case_families(query, families) jest deterministyczne i działa
bez modelu AI, CAD i zapisu danych. query zawiera dimensions_mm w jawnej kolejności
XYZ, device_count i equipment. Profile rodzin mają stabilne ID, zakresy wymiarów
urządzenia, zakres liczby sztuk, obsługiwane wyposażenie, referencyjny przykład,
powiązanie project_id/revision_id/SHA i ograniczenia.

Brak wymiaru nie jest zgadywany. Każdy kandydat musi przejść wszystkie zakresy,
liczbę urządzeń i wyposażenie. Ranking to średnia względnej różnicy wymiarów XYZ
plus względna różnica liczby urządzeń względem przykładu. Niższa wartość oznacza
bliższy przykład; nie jest procentową oceną jakości konstrukcji. Remisy są
rozstrzygane po ID, więc kolejność wejścia nie zmienia wyniku.

Odpowiedź zawiera uzasadnienie, ograniczenia i źródłową rewizję każdego kandydata,
a dla odrzuconych profili powody odmowy. Pusta lista zgodnych profili daje
manual_design_required. Nie wybiera się rodziny i nie przyznaje zgody montażowej
ani produkcyjnej. Profile są jawnymi deklaracjami możliwości, nie dowodem odbioru.

benchmark_case_recommendations(families, cases) przyjmuje zamknięty zestaw
jawnie oznaczonych przykładów z hashem źródła. Zwraca wynik każdego przypadku,
liczbę trafień i top1_accuracy. Nie przyjmuje pustego benchmarku i nie tworzy
etykiet ani historycznej trafności. Trzeba odróżniać test algorytmu od pomiaru
na rzeczywistej, uprzednio oznaczonej historii RockPro.

PASS w pięciu testach funkcjonalnych: filtry/uzasadnienia, droga do ręcznego
projektu, deterministyczny ranking i brak mutacji, odmowa niekompletnych danych,
rozliczenie trafień/pomyłek zamkniętego testowego zestawu. Dane tych testów są
jawnie syntetyczne. Rzeczywisty historyczny benchmark pozostaje NOT RUN:
nie otrzymano zamrożonego zestawu z potwierdzonym wyborem rodziny. To bloker
zamknięcia całego ROC-24, a nie powód do wygenerowania fikcyjnej trafności.

Pełny harness: PASS, artifacts/verification/20261024T214444139483Z/results.json.
