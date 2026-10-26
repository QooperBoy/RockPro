# Przegląd roboczego montażu i importu paczek — 26.10.2026

Zakres: walidacja offline istniejących danych i planów. Nie zmieniono generatora
CAD, allowlisty MCP, modeli źródłowych, zainstalowanego dodatku ani bazy klientów.
Zastosowano repozytoryjne skille scope-check i verification. Stan bazowy:
7 testów obu dotkniętych modułów PASS.

## Naprawione błędy

1. **Sprzeczne ramy montażu przechodziły walidację.**
   `working_mounts.build_working_standard` sprawdzał osobno sztywność macierzy,
   ale nie sprawdzał, czy macierz lokalna złożona z ramą rodzica daje ramę świata.
   Dwa różne położenia tego samego elementu mogły więc dać sprzeczny plan ruchu.
   `_validate_hierarchy` sprawdza teraz tę relację dla całego drzewa (wektory
   wierszowe, translacje w mm, tolerancja bezwzględna 0,00001). Odbicia są
   dozwolone. Hierarchia nie może mieć części jako rodzica kolejnego węzła.
   Kolejność wierszy inwentarza nie wpływa na wynik.

2. **Wczytany standard można było planować bez ponownego sprawdzenia drzewa.**
   `plan_component_translation` budował słownik po ścieżce, więc powielona
   ścieżka nadpisywała w nim wcześniejszy węzeł. Nie sprawdzał też ponownie
   tożsamości referencji ani zgodności ram. Teraz przed obliczeniem odrzuca
   duplikaty, niepoprawne SHA, niespójny klucz SHA/ścieżka, błędne rodzicielstwo
   i sprzeczne ramy. Ograniczenie 20 000 węzłów / 40 poziomów odpowiada czytnikowi.
   Dalsza kontrola wykazała, że sama matematyczna spójność nie blokowała równoczesnej
   zmiany ramy lokalnej, świata i obrysu pod zachowanym SHA inwentarza.
   Dlatego `validate_working_standard(standard, inventory_bytes)` odbudowuje
   cały standard z przypiętych bajtów i porównuje jego dane 1:1. Planer wymaga teraz
   jawnego argumentu `inventory_bytes=...`; edytowalny hash zapisany w samym
   standardzie nie wystarcza. Wynik potwierdza powiązanie z inwentarzem, nie ponowny
   odczyt ICS ani zgodność z bieżącym stanem pamięci IronCAD. Przyszłe adnotacje
   konstruktora powinny być oddzielone od niezmiennego odniesienia źródłowego.

3. **Brak historii mógł być opisany jako kompletna historia.**
   `summarize_model_bundle.summarize` opierał `history_complete` tylko na braku
   wpisu o błędzie. Obecnie musi także istnieć lista `features` dla każdej części.
   Pusty odczyt nie daje kompletnej historii. Brak części generuje tabelę CSV
   z nagłówkiem zamiast wyjątku `flat[0]`, bez wymyślonego obrysu skrzyni.
   `world_box` odrzuca niepełne, nieliczbowe lub nieafiniczne macierze; takich
   obrysów nie zalicza się do poprawnych pomiarów.

4. **Sprawdzanie ścieżek ZIP nie obejmowało aliasów Windows.**
   Sama blokada `..` i ścieżek absolutnych nie obejmowała strumieni `plik:stream`,
   nazw urządzeń, końcowych kropek/spacji ani kolizji wielkości liter.
   `survey_model_bundle.archive_members` sprawdza teraz cały zestaw przed
   etapem zapisu. Odrzuca również dowiązania i plik będący równocześnie katalogiem
   nadrzędnym. `stage_verified_bundle.stage` wymaga pełnego pokrycia członków ZIP
   przez manifest, dokładnych rozmiarów i SHA. Weryfikuje SHA archiwum również
   po stagingu. Błąd walidacji wejścia nie tworzy katalogu wyjściowego.
   Niepowodzenie w trakcie zapisu może pozostawić niekompletny nowy katalog;
   nie wolno go traktować jako ukończonego stagingu ani nadpisywać przy ponowieniu.

## Dowody i granice

- PASS: 13 testów celowanych (`test_working_mounts`, `test_model_bundle`).
- PASS: ponowne odczytanie siedmiu zachowanych inwentarzy — 3427 węzłów,
  w tym 2829 części. Zgodność ram rodzic/świat przechodzi dla wszystkich.
- PASS: siedem wcześniej zapisanych standardów v1 nadal przyjmuje poprawny
  plan translacji komponentu. Nie trzeba zmieniać wersji danych ani ich geometrii.
- PASS: nazwy i kompletność rzeczywistego archiwum pasują do nowych reguł.
- Zachowano wszystkie zgłoszone braki odczytu historii; nie zamieniono ich na PASS.
- NOT RUN: operacje natywne CAD, parametryzacja W/D/H, zmiana biblioteki zakupowej,
  montaż na produkcji i zapis/ponowne otwarcie ICS. Żaden z tych wyników nie wynika
  z walidacji offline.

Prywatne końcowe dowody: `artifacts/night-research-20261026/mount-safety-rebind-tests.txt`
i `mount-safety-rebind-evidence.json`. Wcześniejsze `mount-safety-tests.txt`
i `mount-safety-evidence.json` dokumentują przyrost przed obowiązkowym ponownym
powiązaniem inwentarza. Oryginalne źródła i wcześniejsze raporty pozostały
niezmienione. Test syntetyczny odbicia poprawiono tak, aby lokalna rama zespołu
i jego rama świata opisywały ten sam rzeczywisty montaż; wcześniejszy test
odtwarzał właśnie niespójność, którą nowa walidacja wykrywa.

Kolejny przyrost: jawne mapowanie ról i właścicieli obróbek po ROC-45; dopiero
potem zakresy W/D/H i kontrolowane wykonanie na nowej kopii CAD.
