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
Brak nowego ekranu magazynowego: API/MCP i testy są gotowe, UI i pilotaż magazynu NOT RUN.

PASS: sześć testów izolowanej SQLite, w tym dwóch równoczesnych rezerwujących
tę samą resztkę (jeden zwycięzca), brak podwójnego odejmowania, odmowa cofnięcia
zużycia, częściowy zwrot, replay, dostawa/przyjęcie i kwarantanna.
