# ROC-22 / etap 1 — karta, etapy i historia zmian

Zakres: optymistyczna kontrola zapisów karty projektu i poszczególnych etapów,
historia zmian oraz obsługa konfliktu w dodatku. Nie obejmuje trwałej kolejki CAD,
odzyskiwania przerwanych operacji ani formalnego wydania dokumentacji produkcyjnej.

## Reguły

- UI i AI używają tego samego backendu MCP/SQLite.
- Każda karta i każdy etap mają własny numer `revision`.
- Aktualizacja wymaga wersji odczytanej przed edycją (`expected_revision`).
- Konflikt nie zmienia danych, wersji, historii ani etapów zależnych.
- Automatyczne unieważnienie etapu również podnosi jego wersję. Przypisanie nowej
  kopii CAD podnosi wersję karty, aby stary formularz nie przywrócił starego źródła.
- Zapis, historia i unieważnienie zależności należą do jednej transakcji.
- Informacja o aktorze/kliencie w historii jest deklaracją klienta, nie dowodem
  uwierzytelnienia ani podpisem konstruktora.
- Status `approved` nadal oznacza deklarację ręczną; nie zastępuje walidacji CAD.

## Test użytkownika (na projekcie testowym)

1. Otwórz kartę w dodatku, zanotuj wersję i zmień notatkę bez zapisywania.
2. Drugi klient MCP odczytuje kartę i zapisuje inną notatkę z otrzymaną wersją.
3. Zapisz stary formularz. Powinno pojawić się porównanie wartości początkowych,
   Twoich i aktualnych; niezapisany tekst ma pozostać dostępny.
4. Zamknij porównanie bez przeładowania. Ponowny zapis nie może omijać konfliktu.
5. Świadomie wczytaj aktualne dane, wprowadź uzgodnioną zmianę i zapisz.
   Numer wersji wzrasta; historia pokazuje wartości przed i po.
6. Powtórz konflikt dla jednego etapu. Zapis innego etapu nie powinien powodować
   sztucznego konfliktu; wersja każdego widocznego wiersza musi odpowiadać temu,
   co faktycznie odczytano dla tego wiersza.
7. Otwórz etap Materiały, a w drugim kliencie zmień liczbę skrzyń na karcie.
   Materiały stają się nieaktualne; stary formularz etapu nie może tego nadpisać.
8. Otwórz historię zmian w osobnym oknie. Sprawdź czas, obiekt, wersje, deklarowany
   kanał i wartości. Brak pełnego obrazu w starych wpisach nie może być uzupełniany
   domysłem.

Wynik odbioru: OK albo numer kroku, oczekiwany/rzeczywisty wynik i zrzut ekranu.
Odbiór tego etapu nie zamyka całego ROC-22 ani końcowego odbioru MVP.

## Wdrożenie

Backend i DLL muszą być aktualizowane razem: stary klient nie ma tokenów wersji.
Przed aktualizacją zachować bazę przez SQLite backup oraz poprzedni kod/DLL.
Nie podmieniać backendu pod nadal działającym starym dodatkiem. Rejestracja nowej
DLL i restart dopiero po bezpiecznym zamknięciu IronCAD z zapisanymi dokumentami.
Nie wycofywać migracji przez nadpisanie bazy starszą kopią, jeśli powstały nowe dane.

## Kontrakt MCP

- `get_project(project_id)` zwraca spójną kartę i etapy z ich `revision`.
- `save_project` aktualizuje istniejącą kartę wyłącznie z `expected_revision`.
  Utworzenie nowego projektu dopuszcza brak wersji lub zero.
- `set_stage` wymaga wersji konkretnego etapu, nie wersji całej karty.
- `get_history(project_id, limit, before_id)` zwraca zdarzenia i kursor
  `next_before_id`; limit 1–200. UI pokazuje ostatnie 200 wpisów i sygnalizuje
  dostępność starszych. Stare wpisy nie mają dorabianego obrazu before/after.
- Konflikt: odpowiedź MCP `isError=true`, JSON z kodem `PROJECT_CONFLICT`
  lub `STAGE_CONFLICT`, wersją oczekiwaną, aktualną i aktualnym obiektem.
  Nie ponawiać automatycznie zapisu z nowym tokenem.
- Po aktualizacji serwera klient AI powinien ponownie pobrać `tools/list`.

## Weryfikacja 21.10.2026

- PASS: pełny harness `Verify.ps1 -WithAddinBuild -WithUiChecks`, dowody
  `artifacts/verification/20261021T130734633320Z` (ignorowane przez Git).
- PASS: niezależny reviewer; 35 testów backendu, audyt transakcji i poprawki
  synchronizacji widocznych wartości z tokenami wersji.
- PASS: migracja lokalnej bazy zachowała wszystkie wcześniejsze kolumny i dane
  3 projektów, 27 etapów, 6 snapshotów, 13 zdarzeń, 1 układu i 4 wersji układu.
- PASS w IronCAD 2027: uruchomienie dodatku, odczyt karty testowej, konkurencyjny
  zapis przez prawdziwe MCP stdio, konflikt v1/v2, porównanie trzech wartości,
  zachowanie szkicu i ponowna blokada starego zapisu.
- W teście wizualnym znaleziono przycięte nagłówki. Poprawka automatycznej
  wysokości i zawijania przeszła harness; końcowa ocena wizualna wymaga
  przeładowania DLL. Nie utożsamiać kompilacji z przeładowaniem hosta.
- Pełny ręczny odbiór etapów i historii pozostaje według instrukcji powyżej.
  Nie wykonywano nowych zmian geometrii ani testów odzyskiwania CAD.

Lokalny backup przed migracją: `artifacts/roc22-predeploy` (poza Git).
