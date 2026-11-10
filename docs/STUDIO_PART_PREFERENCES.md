# Ulubione i częstotliwość wyboru części

Gwiazdkę można ustawić na karcie części w kroku 4 kreatora oraz przy wierszu
w Katalogu firmowym. Ustawienie zapisuje się w lokalnej bazie SQLite Studio,
nie w pliku Excela ani wyłącznie w pamięci konkretnej przeglądarki.

Domyślne „Polecane” w kreatorze ustawia najpierw ulubione, potem części
najczęściej wybierane w zapisanych projektach. Dostępne są również sortowanie
według częstotliwości lub nazwy oraz filtr „Tylko ulubione”. Filtry działają
łącznie z kategorią, źródłem, wyszukiwaniem i zaznaczonymi częściami.

Licznik to liczba różnych zapisanych draftów, w których wybrano dany
`part_id`, z uwzględnieniem historii ich rewizji. Kolejne zapisy jednego
projektu nie zwiększają licznika tej samej części. Zachowujemy informację
o wcześniejszym wyborze także po usunięciu części z ostatniej rewizji.
Kopia zapisana jako nowy projekt liczy się oddzielnie. Samo otwarcie,
przeglądanie, podgląd lub dodanie gwiazdki nie jest użyciem.

Jest to historia wyboru, nie liczba zamontowanych egzemplarzy, zakupów,
zleceń produkcyjnych ani potwierdzenie kompatybilności. Ulubione nie są
automatycznie dodawane do skrzyni i nie obchodzą filtrów kompletnych części.

W Katalogu firmowym proponowane są najpierw pozycje oznaczone gwiazdką.
Katalogowe rekordy `company-*` nie mają jeszcze historii zapisanych BOM-ów,
więc nie przypisujemy im sztucznej częstotliwości na podstawie oglądania
zdjęć lub niezatwierdzonych kandydatów geometrycznych. Gwiazdka wariantu
źródłowego nie oznacza automatycznie gwiazdki podobnego SKU; dwa rekordy
z takim samym kodem, ale z osobnych kolumn Excela pozostają oddzielne.

Backend: `part_preferences.py`, tabela `studio_part_preferences` w istniejącej
bazie projektów. API `GET parts/preferences` i `POST parts/preferences`
przyjmuje wyłącznie znany `part_id` oraz wartość bool `favorite`.
Zapis ma tę samą kontrolę lokalnego origin/session co pozostałe komendy
Studio. Usunięcie definicji z katalogu nie kasuje zachowanej preferencji.

Frontend: wspólny `part-preferences.js`, aktualizacja po zapisie projektu,
odświeżenie przy powrocie do okna oraz komunikacja między kartami. Wybór
filtra/sortowania kreatora jest częścią istniejącego kontekstu nawigacji.
Nie dodano zależności zewnętrznych i nie zmieniono kontraktu draftu.

Sprawdzenia:
- testy backendu: trwałość, idempotencja, różne projekty versus rewizje,
  historia wcześniejszego wyboru, walidacja i brak zmian w danych projektu;
- test przeglądarki: gwiazdki obu katalogów, domyślne propozycje,
  sortowanie częstotliwości, filtr, nowy kontekst przeglądarki, odrębne
  warianty, jasny/nocny i mobile;
- kontrola: te operacje nie tworzą ruchów magazynowych ani rewizji projektu.

Przy sprawdzeniu powrotu z biblioteki wzorców wykryto również odwołanie
do nieistniejących tam uchwytów paneli kreatora. Aktualizację tych uchwytów
ograniczono do strony kreatora; nawigacja i przywracanie filtrów przeszły test.

Prywatne dowody i kopia bazy sprzed migracji:
`artifacts/favorites-20261028/`. Test przeglądarkowy przywraca poprzedni
stan testowanych gwiazdek, zamiast pozostawiać przypadkowe ulubione.
