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


## 25.10 — operatorowy podgląd propozycji w WinForms

W widoku Magazyn przycisk „Propozycje zakupowe” otwiera PurchaseProposalForm.
Okno wczytuje wybrany zestaw UTF-8 JSON (z BOM lub bez, maks. 2 MiB) z dokładnie
trzema polami: requirements, offers i policy według powyższego kontraktu.
Import nie uruchamia solvera ani nie zapisuje stanów. Przykład wyłącznie
syntetyczny: Integracja/rockpro_cad/examples/purchase-input.synthetic.json.
Nie zasila magazynu — wynik zależy od bieżących danych o tym samym scope.
Oczekiwane 75/100 wymaga także opisanego stanu 20 i dostawy 30; pusty magazyn
nie jest zastępowany fixturem.

Po jawnym przeliczeniu preview_purchases odczytuje wspólny magazyn ROC-31.
C# nie powtarza obliczeń pieniężnych: pokazuje wyniki tego samego solvera.
Tabela wymagań zawiera niedobór, termin i ilość opcji danego wiersza. Jawny
wybór wiersza pokazuje opcje z pełnym netto/brutto/transportem, ilością,
nadwyżką, datą i ograniczeniami oraz rozliczenie źródeł zapasu/dostaw.
Nie ma automatycznego wyboru ani akceptacji całego koszyka.

Dalsze zakładki pokazują niepełne/odrzucone oferty, źródłowe warunki ofert
(MOQ, paczki, ważność, czas, dostępność i czytelne progi cenowe), powiązania
oraz hashe źródła/wyniku i politykę faktycznie użytą. Brak dostawcy lub ID
nie zmienia się w fikcyjną ofertę. Pozycja oferty w pliku jest numerowana dla
człowieka od 1; surowy offer_index w kontrakcie/eksporcie pozostaje od 0.
Nazwy brakujących pól są przetłumaczone.

Data bilansu, waluta i limity są jawnie edytowalne po imporcie. Zmiana pola
unieważnia wynik i eksport; nie przelicza niczego w tle. Magazyn pochodzi
z odczytu bieżącego, nie z historycznego odtworzenia na datę polityki.
Limit gotówki i transport nadal dotyczą opcji, bez potwierdzenia globalnego
budżetu/konsolidacji. Informacja jest stale widoczna w oknie.

Eksport tworzy wyłącznie nowy szkic JSON (CreateNew), z hashami, wejściami,
polityką użytą i wynikiem proposal_only. Nie nadpisuje starego pliku. Nie
wystawia zamówienia, nie zmienia magazynu i nie nadaje production_approved.
Błąd lub odpowiedź sprzeczna z zakresem propozycji blokuje wynik. Niepełna
struktura wejścia jest odrzucana przed aktywacją formularza; nie wywołuje
backendu i nie zostawia starego wyniku po zmianie języka.

PASS: pełny harness/build/UI PL/EN przy skali 100/150:
artifacts/verification/20261025T131118330552Z/results.json.
Dziewięć testów backendu zakupów obejmuje teraz też prawdziwy dispatch MCP
na izolowanej SQLite: 75 przy zadanych stanach, 100 po nowej rezerwacji,
nowy input_sha i identyczny SHA bazy po samym podglądzie. Testy okien mają
backend testowy i jawne syntetyczne dane; obejmują 75/100, pełny koszt,
null dostawcy, błędy, zmiany polityki, zakres proposal_only, UTF-8/BOM oraz
odmowę nadpisania eksportu. Zrzuty głównego widoku i zakładek sprawdzone w
artifacts/purchase-ui-20261025/.

NOT RUN: nowa DLL w rzeczywistym IronCAD, oferty/BOM klienta, uzgodnione limity
i odbiór zakupów. Nie instalowano dodatku i nie wykonywano operacji CAD.
Ostatni odczyt procesu hosta: PID 20328 nadal Responding=false, bez tytułu okna;
nie uruchamiano kolejnego. Konektor Linear nadal nie udostępnia Rock_Pro.
Całego ROC-32 nie oznaczono Done.
