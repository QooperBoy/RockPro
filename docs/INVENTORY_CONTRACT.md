# ROC-31 — magazyn i rezerwacje

Backend `mcp/inventory_service.py` korzysta ze wspólnej SQLite. Rozróżnia fizyczny
stan partii, aktywne rezerwacje, wydanie, zużycie, zwrot i potwierdzone dostawy.
Nie tworzy rzeczywistych stanów ani dostaw na podstawie domysłów.

`inventory_command` przyjmuje jawny action, unikalny operation_id i expected_revision.
Cała operacja ma BEGIN IMMEDIATE; powtórzenie identycznego ID zwraca kwit bez
ponowienia skutków, a zmiana treści pod tym samym ID jest błędem. Rewizja dotyczy
partii, a dla receive — dostawy. Rezerwacja ma ID i powiązanie plan_id; samo
powiązanie jest oświadczeniem operatora, nie uwierzytelnionym zatwierdzeniem planu.

Partia zawiera id, item_id, unit (piece/sheet/offcut), location, on_hand,
dimensions_mm (null dla piece lub [L,W,T] dla płyt), condition
(usable/quarantine/scrap), scope (source_input/synthetic_test).
Każda fizyczna resztka ma osobne ID i ilość 1. Identyfikatory są techniczne ASCII.

Wolny stan = fizyczny on_hand − aktywne held; kwarantanna i złom nie są wolne.
Issue odejmuje od on_hand i zmienia held na issued. Consume zmienia issued na
consumed bez ponownego odejmowania. Cancel działa tylko dla held. Return zwraca
wyłącznie niewykorzystaną ilość issued, maksymalnie quantity − returned.
Anulowanie i zwrot consumed są odrzucane; błąd nie modyfikuje salda/historii.

Dostawa ma ID, item_id, unit, quantity, due_date, confirmation_reference i scope.
Do chwili receive nie zwiększa fizycznego stanu. Receive tworzy nową partię,
odejmując przyjęcie od outstanding tej samej dostawy; nie pozwala przyjąć nadmiaru.
Confirmation_reference jest zachowanym oświadczeniem, nie dowodem od dostawcy.

`get_inventory` rozdziela on_hand/reserved/free i outstanding dostaw.
`get_inventory_history` pokazuje kwity operacji; limity odpowiedzi są jawne.
API/MCP i testy backendu są gotowe. Przyrost ekranu odczytu opisano poniżej;
operacje magazynowe w UI i pilotaż rzeczywistego magazynu pozostają NOT RUN.

PASS: sześć testów izolowanej SQLite, w tym dwóch równoczesnych rezerwujących
tę samą resztkę (jeden zwycięzca), brak podwójnego odejmowania, odmowa cofnięcia
zużycia, częściowy zwrot, replay, dostawa/przyjęcie i kwarantanna.


## 25.10 — podgląd magazynu w źródłowym dodatku

Nowa pozycja Magazyn w panelu otwiera InventoryForm. Jest dostępna niezależnie
od wybrania projektu, bo magazyn jest wspólny. Czyta te same get_inventory
oraz get_inventory_history przez operatorowy MCP; nie ma drugiej bazy w C#.
Nie wpisano stanów klienta ani dostaw na podstawie przykładów.

Cztery zakładki pokazują partie/resztki z fizycznym, zarezerwowanym i wolnym
stanem, rezerwacje/wydania, potwierdzone dostawy z przyjętą i oczekującą ilością
oraz historię kwitów. Każda partia ma jednostkę, wymiary, lokalizację, warunek,
rewizję i jawne pochodzenie. Zielony wyróżnia dodatni stan wolny, pomarańczowy
brak wolnego, czerwony kwarantannę/złom. Stany rezerwacji mają podpis i kolor.
Nie sumujemy arkuszy, sztuk i resztek ani nie odejmujemy rezerwacji drugi raz.

Historia pokazuje stan zapisany w chwili operacji, nie bieżące saldo. UTC jest
czytelne w dwóch wierszach, pełny znacznik pozostaje w tooltipie. Wybrany kwit
można odczytać wraz z hashem polecenia; to dane operatora, nie uwierzytelniona
akceptacja. Domyślny limit to 100 ostatnich wpisów, jawnie zmieniany do 500.

Nowe dane trafiają do tabel dopiero po powodzeniu obu odczytów. Błąd historii
nie miesza nowego salda ze starą historią: pozostawia poprzedni widok z ostrzeżeniem
o nieaktualności. Zmiana języka nie usuwa tego ostrzeżenia ani nie ponawia
odczytu. Są to dwa sekwencyjne zapytania; nie deklarujemy atomowego snapshotu
współbieżnie zmienianego magazynu. Przed decyzją należy odświeżyć widok.

Ten przyrost wyłącznie odczytuje. Rejestrowanie, rezerwowanie, wydawanie,
zużywanie, zwroty i przyjmowanie dostaw przez przyciski UI są dalszym krokiem;
backend operatora ma te transakcje, lecz okno ich nie wykonuje.

PASS: pełny harness/build/UI PL/EN przy skali 100/150, artifacts/verification/20261025T102449640088Z/results.json.
Izolowane okna sprawdzają 8 fizycznie / 3 zarezerwowane / 5 wolne,
kwarantannę bez wolnego stanu, osobne 25 oczekujących dostawy, historię,
pochodzenie syntetyczne, brak zapisów, obsługę pustej bazy/błędu oraz kontynuacje
na wątku właściciela. Dane qa/fixtures/inventory-ui.json wygenerowano rzeczywistymi
transakcjami backendu w tymczasowej SQLite, nie z bazy klienta.
Zrzuty wszystkich zakładek sprawdzono w artifacts/inventory-ui-20261025/.

NOT RUN: nowa DLL w rzeczywistym IronCAD i odbiór magazyniera. Nie rejestrowano
DLL ani nie dotykano modeli, prywatnej bazy czy zachowanego wdrożenia. Zmian
nie przesłano do Linear — dostępny konektor nadal nie widzi Rock_Pro.
Nie oznaczono całego ROC-31 Done.


## 25.10 — odczyt pojedynczego wyniku i powiązanie przyjęcia

get_inventory_operation(operation_id, command=None, expected_revision=None)
odczytuje konkretny zachowany kwit niezależnie od limitu listy historii. Nie
uruchamia polecenia ponownie. Opcjonalne command i expected_revision należy
podać razem; serwer oblicza ten sam hash co zapis i odmawia obcego polecenia
lub rewizji (INVENTORY_RECEIPT_COMMAND_MISMATCH). Klient C# nie musi odtwarzać
kanonizacji JSON ani SHA w osobnej implementacji.

found=false i receipt=null oznaczają brak zapisu w chwili odczytu. Nie oznacza
to zgody na nowy operation_id: wcześniejsza operacja może nadal czekać na commit.
command_matches=true występuje tylko przy znalezionym kwicie i porównaniu
pełnego polecenia/rewizji; bez danych porównawczych pozostaje null.
To narzędzie operatora readonly; statycznej allowlisty agenta nie rozszerzano.

Nowe kwity receive zawierają powiązaną dostawę z ID, received, outstanding
i rewizją po przyjęciu. Kwit delivery pokazuje outstanding już od utworzenia.
Nie modyfikujemy starych kwitów ani nie dopisujemy domyślnych referencji do
historycznych przyjęć bez powiązania. Odczyt kwitu, historia i idempotentny
replay odmawiają uszkodzonej struktury/tożsamości/pól zatwierdzenia. To kontrola
kontraktu danych, nie podpis ani ochrona przed skoordynowaną edycją całej bazy.

Przy identycznym created_at historia używa kolejności zapisu w dzienniku,
a nie leksykograficznego ID (operation-10 nie jest starsze od operation-9).
Nie zmienia to zapisanych znaczników czasu ani historycznych danych.

PASS: 10 testów backendu magazynu, w tym odczyt starego wyniku poza limitem
historii, porównanie polecenia/rewizji, brak ponownego skutku po utracie
odpowiedzi, powiązanie dostawy, kolejność równych czasów i odmowa uszkodzonego
kwitu bez zmiany sald. Pełny harness PASS:
artifacts/verification/20261025T104845768001Z/results.json.
UI poleceń, odtworzenie oczekującego polecenia po restarcie oraz pilot
magazyniera nadal pozostają następnym krokiem; nie jest to pełny ROC-31 Done.


## 25.10 — trwałe żądania operatora przed transakcją

Nowy inventory_intents.py zapisuje w tej samej SQLite niezmienne polecenie,
operation_id, expected_revision, hash oraz deklarowane actor/decision_reference.
prepare_inventory_command tworzy prepared bez rezerwowania lub zmiany stanu.
Potwierdza kształt żądania, nie przyszłą dostępność materiału. Właściwe reguły
magazynu i CAS są ponownie sprawdzane dopiero przy wykonaniu.

execute_inventory_intent używa istniejącego inventory_command. Zmiana salda,
kwit i stan committed są zapisywane w jednej transakcji. Powtórzenie identycznego
ID zwraca zapisany wynik, bez ponownego skutku. Dwa równoczesne wykonania nie
rezerwują resztki dwa razy. Również stara ścieżka inventory_command odmawia
wykonania ID anulowanego/odrzuconego żądania oraz podmiany treści pod tym ID.
Bezpośrednie historyczne operacje pozostają czytelne i nie są przepisywane.

get_inventory_intent i list_inventory_intents pozwalają odnaleźć żądanie po
zamknięciu formularza lub restarcie klienta. Utrata odpowiedzi po commit daje
przy odczycie committed z kwitem; błąd o nieznanym wyniku przed commit pozostawia
prepared. Odczyt nie uruchamia żadnego wykonania. Nie nadajemy nowego ID w tle.
Stan prepared jest obserwacją, nie zapewnieniem, że inny proces nie wykonuje
właśnie transakcji.

Jednoznaczna odmowa biznesowa/CAS daje rejected z diagnostyką, bez zmiany
pierwotnego polecenia ani rewizji. cancel_inventory_intent wymaga hasha i
anuluje wyłącznie niewykonane prepared; nie cofa zapasu, wydania ani zużycia.
Wyścig anulowania z wykonaniem ma jeden wynik końcowy. Zmiana danych wymaga
jawnego nowego żądania; zatwierdzonych stanów nie poprawiamy automatycznie.
Uszkodzona treść/wiązanie lub niespójność committed/kwitu blokuje odczyt i replay.
Są to kontrole kontraktu, a nie podpisy ani uwierzytelnione zgody produkcyjne.

PASS: 10 testów trwałych żądań oraz 10 dotychczasowego magazynu. Obejmują
przygotowanie bez skutku, odczyt przez nowe połączenie, dwa wykonania, utratę
odpowiedzi przed/po commit, CAS, anulowanie, wyścig cancel/execute, korupcję oraz
SQL trigger odmawiający zapisu kwitu: saldo wycofane, committed niewykazane.
Pełny harness PASS: artifacts/verification/20261025T112059746286Z/results.json.
Dodatkowy zestaw 28/28 inventory_intents + inventory_service + agent_server
PASS po doprecyzowaniu regresji; nowe operacje zapisu są jawnie odmawiane AI.
Nie rozszerzano statycznej allowlisty agenta.

Formularz poleceń jest następnym przyrostem. Obecny ekran InventoryForm nadal
wyłącznie czyta dane. Nie wykonywano poleceń na magazynie klienta, operacji
CAD ani rejestracji DLL. Pełny pilot ROC-31 pozostaje NOT RUN.
