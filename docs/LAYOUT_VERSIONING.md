# Wersjonowanie układów i snapshoty CAD

## Kontrakt

`get_layout(project_id)` zwraca bieżące `revision`, `sha256`, `spec` oraz obliczenia. Niezapisany układ ma revision 0. `get_layout(project_id, revision=N)` odczytuje historyczną specyfikację; obliczenia są wykonywane bieżącą wersją algorytmu. Historyczny snapshot przechowuje również rzeczywiste parametry CAD i raport pomiarów.

`save_layout(project_id, spec, expected_revision=N)` wymaga wersji odczytanej przed edycją. W transakcji SQLite BEGIN IMMEDIATE sprawdza aktualny numer i dopisuje nowy rekord `layout_versions`. Tabela `layouts` pozostaje bieżącym widokiem dla kompatybilności danych. Stara baza migruje zapisany układ do wersji 1 bez zmiany specyfikacji. Migracja jest addytywna i idempotentna.

Konflikt zwraca błąd narzędzia MCP z kodem tekstowym `LAYOUT_CONFLICT`, wersją oczekiwaną i aktualną. Nie zmienia danych, historii ani etapów. Nie ponawiaj zapisu automatycznie i nie podstawiaj aktualnej wersji bez porównania zmian. UI zachowuje edytowane pola i wyświetla instrukcję odświeżenia. Starszy klient bez expected_revision otrzyma błąd zamiast nadpisania danych.

SHA256 liczymy z kanonicznego JSON specyfikacji (UTF-8, posortowane klucze). Wersji nie edytuje ani nie usuwa żadne narzędzie MCP; nie jest to ochrona WORM przed ręczną edycją SQLite.

## Powiązanie CAD

Konfigurator zapisuje układ, następnie przekazuje otrzymany `layout_revision` do `change_dimensions_on_copy`. Worker odczytuje tę konkretną wersję i porównuje pełny zestaw sześciu parametrów z żądaniem przed uruchomieniem CAD. Po pomiarze, zapisie i ponownym otwarciu kopii snapshot otrzymuje `layout_binding`: revision, sha256 i pełną specyfikację. Powiązanie trafia do SQLite oraz report.json. Historia UI pokazuje numer wersji i szczegóły.

Jeśli podczas pracy CAD ktoś zapisze nowszy układ, snapshot nadal wskazuje wersję wejściową; nowszy układ nie jest cofany. Zmiana przypisanego źródła projektu w trakcie operacji blokuje rejestrację/awans źródła. Oddzielne archiwum ICS i kontrola SHA256 pozostają zachowane.

Stare snapshoty i ręczne operacje CAD bez jawnego layout_revision są oznaczone jako niepowiązane. Nie przypisujemy im najnowszego układu przez domysł.

## Zakres ochrony

Optymistyczna kontrola wersji dotyczy układu urządzeń (UI i AI używają tego samego backendu). Karta projektu i ręczne statusy etapów nadal nie mają własnego tokenu rewizji; nie należy przedstawiać tej zmiany jako ochrony wszystkich pól aplikacji. Istniejąca blokada COM serializuje operacje natywne.

## Weryfikacja i wdrożenie

`test_versions.py` sprawdza migrację starego układu, dwa równoczesne zapisy, brak skutków ubocznych konfliktu, historyczny odczyt i pinning podczas symulowanej równoległej edycji, odrzucenie niezgodnych parametrów przed CAD oraz kontrakt MCP. Fixture snapshotu w teście jednostkowym nie jest prawdziwym ICS.

Uruchom scripts/Verify.ps1 z opcjami -WithAddinBuild -WithUiChecks. Test natywny raportuj osobno. Backend i DLL wdrażaj razem po zachowaniu kopii bazy i bezpiecznym zamknięciu hosta; stara DLL nie wysyła tokenu expected_revision. Przy wycofaniu wersji zachowaj nową bazę jako archiwum i nie zastępuj jej starszą kopią bez oceny nowszych danych.

## Wynik próby 21.10.2026

- PASS: audyt repozytorium, testy backendu/QA/harness, kompilacja dodatku i testy formularzy przez scripts/Verify.ps1.
- PASS: migracja istniejącego układu użytkownika do v1; cztery urządzenia 400 × 220 × 80 mm, orientacja YXZ, piętrowanie Z.
- PASS: rzeczywisty IronCAD 2027, nowa kopia ICS, przebudowa, pomiar przed zapisem i po ponownym otwarciu. Źródło niezmienione; archiwum SHA256 verified.
- PASS: snapshot przypięty do v1; po kolejnym zapisie identycznej specyfikacji jako v2 snapshot nadal ma v1 i pierwotny hash. Stary token v1 odrzucony po utworzeniu v2.
- PASS: nowa DLL zarejestrowana i załadowana (InitSelf w logu hosta). Baza oraz poprzedni kod zostały zachowane lokalnie poza Git.
- PASS: po zamknięciu okna powitalnego wykonano test w UI hosta: formularz odczytał v2, drugi klient MCP zapisał identyczną specyfikację jako v3, zapis z formularza zwrócił LAYOUT_CONFLICT i zachował pola. Baza pozostała na v3, bez dodatkowej wersji po konflikcie.
- PASS: tabela historii w IronCAD pokazuje powiązany snapshot jako v1 oraz starszy jako Niepowiązany; walidacja passed i integralność verified. Wymiary użytkownika nie zmieniły się w próbie konfliktu. Dowód lokalny: artifacts/ui_versions_acceptance.json.

Raporty lokalne: artifacts/verification/20261021T113017680230Z oraz artifacts/native_versions.json (nie publikować ścieżek klientów i modeli w Git). Testy jednostkowe obejmują prawdziwe równoczesne transakcje SQLite, ale symulują CAD; wyżej wymieniona próba natywna została wykonana oddzielnie.
