# Przyjmowanie nowych wzorców skrzyń

Nowy ICS trafia najpierw do lokalnego rejestru wzorców, nie od razu do
wykonywalnego szablonu. Dokumenty źródłowe i inwentarze klienta pozostają
w ignorowanym `artifacts/`, razem z hashem ZIP-a i każdej rewizji.

Aktualna decyzja użytkownika: nowe siedem wzorców rozwijamy w IronCAD 2027.
Odtworzenie od zera na 2023 jest późniejszą pracą. Nie rozszerza to wcześniejszych
dowodów zgodności T1/T2 i nie oznacza, że nowe pliki otwierają się w 2023.

## Przebieg

1. `scripts/survey_model_bundle.py`: porównanie rozpakowanych plików z każdym
   plikiem ZIP-a przez SHA256 i rozmiar. Zmieniony plik blokuje zgodność.
2. `scripts/stage_verified_bundle.py`: odtworzenie oryginalnej rewizji ZIP-a
   do nowego katalogu, gdy rozpakowane modele były dalej edytowane. Nigdy
   nie nadpisuje katalogu docelowego ani bieżących modeli użytkownika.
3. `scripts/run_bundle_survey.py`: jawny PID i rok hosta, wspólna blokada CAD,
   nowe kopie tylko do odczytu, metadane hierarchii i operacji oraz obrysy brył.
   Nie wykonuje Save, Update ani regeneracji cech. Domyślnie zamyka własne
   kopie i sprawdza zachowanie kontekstu. `--keep-open` jest osobnym trybem
   jawnie zleconego przeglądu: pokazuje i pozostawia udane kopie.
4. `scripts/summarize_model_bundle.py`: spis części i etykiet katalogowych
   do uzupełnienia przez konstruktora. Porównanie z przypiętymi inwentarzami
   T1/T2 dotyczy nazw, nie zatwierdzonej tożsamości SKU lub zamienności.
5. Dla wybranej rodziny: potwierdzenie funkcji komponentów, osi, materiałów,
   wymiarów użytkowych, parowania okuć i obróbek. Dopiero potem ograniczony
   planer i wykonawca oraz próba zmiany/powrotu w docelowym IronCADzie 2023.

Brak danych o wymaganym wycięciu oznacza BRAK DANYCH, nigdy automatyczne NIE.
Ujemne cechy wewnątrz gotowego okucia nie dowodzą wymagań obróbki sklejki.
Kontur montażowy nie może być zastąpiony obrysem części. Zagnieżdżone części
okucia, połowy zamków i zespoły grupujące nie są automatycznie pozycjami BOM.

Nazwy elementów, macierze, ID oraz historia pochodzą z konkretnego hasha ICS.
Obrys światowy z przekształcenia lokalnego AABB jest konserwatywny; cały
obrys sceny może zawierać urządzenie, scenę renderingu i osprzęt referencyjny.
Nie jest wymiarem zamkniętej skrzyni ani dowodem braku kolizji.

## Checkpoint 26.10.2026

Pakiet lokalny: `artifacts/model-library-20261026/`.

- PASS: ZIP i pierwszy odczyt rozpakowanych siedmiu ICS były zgodne.
- PASS: SDK 2027 odczytał 2829 części i ich obrysy. Odczyt historii był
  częściowy w pięciu modelach; braki zachowano jawnie. Kopie zamknięte,
  oryginalny kontekst zachowany, brak zapisu CAD.
- ZMIANA REWIZJI: trzy rozpakowane pliki zmieniły hash po pierwszym odczycie.
  Kolejny odczyt został prawidłowo zatrzymany przed otwarciem. Nowe kopie
  przygotowano z niezmienionego ZIP-a; aktualnych plików nie zastąpiono.
- FAIL: próba otwarcia wszystkich siedmiu oryginalnych ICS w 2023 PU1 SP1,
  API 25.0.12.18734: Invalid file format / Shape Load Failed. Brak zmiany
  geometrii i zapisu; wszystkie komunikaty zamknięto. Tymczasowe AddOny Count=0.
- PASS: wszystkie siedem wzorców ponownie otwarto w nowym hoście 2027
  (API 29.0.2.20605) na kopiach do przeglądu; istniejące dokumenty użytkownika
  zachowano. Dane dwóch wariantów mogą mieć ten sam FileGUID, więc ich
  identyfikacja wymaga pełnej ścieżki i hasha. GUID nie jest kluczem deduplikacji.
- NOT RUN: parametryzacja i walidacja zmian tych siedmiu modeli, zapis/ponowne
  otwarcie oraz odbiór konstruktora. Przygotowanie inwentarza nie realizuje tych etapów.

Odczyt 2027 nie zastępuje otwieralnego wzorca 2023. Błąd otwarcia nie dowodzi
sam z siebie konkretnej wersji zapisu ani przyczyny niezgodności. Nie zmieniać
metadanych wersji jako sposobu naprawy. Brak otwieralnego źródła blokuje
wykonawcę danej rodziny, lecz nie blokuje analizy wcześniej odczytanych danych.

## Weryfikacja

Roboczy standard źródłowych ram i planowania ruchu komponentów:
[WORKING_MOUNT_STANDARD.md](WORKING_MOUNT_STANDARD.md). Pytania do wszystkich
nowych rodzin zebrano w ROC-45 na 27.10.2026. Odroczenie odpowiedzi nie oznacza
zatwierdzenia brakujących wymiarów, obróbek ani funkcji elementów.

`scripts/test_model_bundle.py` sprawdza wykrycie edycji źródła, odtworzenie
oryginału bez nadpisania pracy, brak dublowania identycznie nazwanej części
i zespołu w liczniku kandydata oraz przeliczenie obrysu przy odbiciu.
Weryfikację sprzątania i kolejki utrzymuje `scripts/test_t2_native_queue.py`.
To narzędzia developerskie; nie dodano nowego endpointu MCP ani instalowanej DLL.
