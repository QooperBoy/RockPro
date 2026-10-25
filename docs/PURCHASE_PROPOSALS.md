# ROC-32 — propozycje zakupów

`preview_purchases` czyta wspólny magazyn ROC-31 i nie zapisuje zamówień.
Wymagania mają scope, bindings do źródłowych rewizji/BOM i lines:
id, item_id, unit (piece/sheet), quantity, required_date. Arkusz to zatwierdzony
SKU określonego formatu, nie przeliczenie powierzchni BOM na liczbę płyt.
Dobór ilości płyt powinien pochodzić ze zweryfikowanego rozkroju.

Policy: as_of_date, currency, max_surplus_units, max_cash_gross,
approved_substitutes (mapa oryginał → dopuszczone zamienniki).
Wolny stan jest brany raz, już po rezerwacjach. Potwierdzone dostawy liczą się
tylko do właściwego terminu i tylko w outstanding, bez przyjętej już ilości.
Wymagania są bilansowane kolejno według terminu; tej samej dostawy nie liczymy dwa razy.

Oferta: id, item_id, unit, supplier, currency, quote_date, valid_until,
pack_size, moq, lead_days (kalendarzowe), available_quantity, price_breaks
([{min_quantity,unit_net}]), shipping_net, tax_percent. Braki reprezentuje null;
niepełna, przeterminowana lub obca waluta bez kursu nie daje wybranej propozycji.
To wejściowe oświadczenia operatora, nie automatyczna weryfikacja dostawcy.

Porównanie obejmuje zakup po zaokrągleniu do paczki/MOQ i ilości na progach,
cenę netto, pełny transport i podatek, wydatek brutto, nadwyżkę, termin oraz
ograniczenia gotówki/zapasu/dostępności. Obliczenia kwot używają Decimal.
Nie zatwierdza zamienników samodzielnie ani nie dokonuje zakupów.

Granica przyrostu: propozycje są osobne dla wiersza/terminu; nie deklarujemy
globalnego optimum, skonsolidowanego transportu ani zaakceptowanego wspólnego
budżetu. Limity są sprawdzane dla opcji; akceptacja zestawu pozostaje operatorem.
Nie mamy rzeczywistych cenników, limitów klienta ani odbioru zakupów (NOT RUN).

PASS: 6 testów. Przykład odbioru: 120 zamków − 20 wolnych − 30 na czas = 70,
paczka 25 → zakup 75. Dostawa spóźniona → zakup 100. Sprawdzone także koszty
transportu/VAT, progi, limity, brakujące oferty, zamienniki i brak podwójnego
bilansowania stanów/dostaw.


## 25.10 — niepełne tożsamości ofert

Przed podłączeniem UI odtworzono błąd: null w id lub supplier przerywał całe
obliczenie przed klasyfikacją niepełnej oferty. Brak item_id/unit mógł usuwać
ofertę z widoku bez informacji o przyczynie. Nowe globalne offer_issues pokazuje
każdą niepełną ofertę, jej oryginalny indeks w tablicy, zachowane ID (także null)
i brakujące pola. Nie wymyślamy ID, SKU, dostawcy ani jednostki.

Oferty dające się przypisać do wymagań zachowują także dotychczasowy
rejected_offers. Niepełna obca oferta nie zatrzymuje poprawnej propozycji
z kompletnego źródła. Tokeny identyfikatorów są sprawdzane po wykryciu null;
nieprawidłowa struktura/nieznane pola nadal dają błąd kontraktu.

PASS: 8 testów zakupów, w tym regresje braków ID/dostawcy/SKU/jednostki,
niepełnej obcej oferty i zachowanie przykładu 75/100. Nowe przypadki najpierw
odtworzyły błędy starej wersji. Pełny harness PASS:
artifacts/verification/20261025T125223511578Z/results.json.
Brak ofert klienta i odbioru zakupów nadal pozostaje jawny. Następny krok to
operatorowy podgląd wejść, ograniczeń, braków i opcji z tego samego solvera.
