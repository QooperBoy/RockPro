# Roboczy standard montażu nowych rodzin

26.10.2026: użytkownik polecił zebrać pytania na jutro i traktować dotychczasowy
montaż jako standard roboczy. Pytania Q01–Q26 są w Linear ROC-45, termin
27.10.2026. Dotyczą siedmiu nowych modeli, materiałów, pasowania, funkcji wnętrza
i produkcji. Do jutrzejszego mapowania nie przypisujemy nieznanym funkcjom
fikcyjnych odpowiedzi. Nowe modele rozwijamy w 2027; odtworzenie 2023 odłożono.

`core_case/working_mounts.py` zapisuje przypięty do SHA źródła i bajtów inwentarza
stan wszystkich części/zespołów: hierarchię, surowe nazwy, macierze montażu,
obrysy lokalne i dostępną historię operacji. Zachowuje odbicia i jawne braki
odczytu. Klucz referencji zawiera SHA i ścieżkę, ponieważ warianty mogą mieć
ten sam FileGUID. Nie jest to jeszcze identyfikator wystąpienia w nowym projekcie.

Planer potrafi wyliczyć przesunięcie komponentu wraz z potomkami, bez skalowania
okuć i brył urządzeń. Rozróżnia geometrię ramy od natywnej kotwy/PositionTransform;
wykonawca musi osobno uwzględnić offset kotwy i zweryfikować rzeczywisty CAD.
Obróbka wewnątrz przenoszonej części pozostaje w jej hierarchii. Powiązania
między różnymi częściami wymagają jawnego właściciela — nie są zgadywane.

Status `provisional_source_standard` oznacza montaż odziedziczony ze wzorca,
do późniejszego uzupełnienia. `requires_plywood_cutout=unknown` nie oznacza NIE.
To nie wykonywalny szablon, zakupowy BOM, odbiór technologii ani nośności.
Nie rozszerza endpointów MCP ani zainstalowanej DLL. Kontrakty bazowe i ich
bramki pozostają w mocy. Dane rzeczywistych modeli są tylko w `artifacts/`.

Kolejność dalszych prac: powiązanie okuć i obróbek → pomiar obrysu sklejki oraz
światła komór → ograniczone W/D/H i próba powrotu → moduły wnętrza i transportu
→ eksporty produkcyjne → odbiór konstruktora. Moduł kół zawiera również gniazda
i podpory w etapie 6. Wspólna reguła nie zmienia samoczynnie liczby uchwytów
ani rodzaju zdejmowanej czapki na pokrywę zawiasową.

Testy `test_working_mounts.py`: rozdzielenie rewizji o wspólnym GUID, integralność
źródła/inwentarza, przeniesienie w odbitym układzie, zachowanie nieruchomych
części i danych wejściowych, odmowa skalowania/NaN/brakującej hierarchii.
