# Język interfejsu i pomoc w RockPro CAD

## Cel

Każdy widok powinien wyjaśniać: do czego służy, co wpisać lub wybrać,
co zrobi przycisk oraz czego dana funkcja jeszcze nie wykonuje. Krótkie
instrukcje pozostają widoczne; podpowiedzi po najechaniu uzupełniają szczegóły.

Interfejs obsługuje polski i angielski. Zmiana języka nie tłumaczy danych
użytkownika, nie zapisuje projektu i nie zmienia modelu CAD. Klucze MCP,
parametry RP_*, osie, wersje oraz ścieżki plików pozostają niezmienione.

## Zasady redakcyjne

- Nazwy działań opisują rezultat: zapis danych, odczyt CAD albo utworzenie kopii.
- „Zatwierdzenie ręczne” nie oznacza automatycznej kontroli konstrukcji ani
  zgody na produkcję.
- Historia zmian danych i archiwalne kopie CAD są różnymi funkcjami.
- „Dostępne”, „częściowo dostępne” i „planowane” opisują zakres implementacji,
  a nie bieżącą dostępność IronCAD lub jego licencji.
- Przy konflikcie wyjaśniamy, że dane nie zostały nadpisane i gdzie pozostaje
  niezapisany tekst. Nie sugerujemy automatycznego połączenia zmian.
- Instrukcje posługują się językiem konstruktora. Techniczne kody i szczegóły
  diagnostyczne pozostają dostępne do zgłoszenia błędu.
- Wymiary urządzenia, dostępne wnętrze i zewnętrzny gabaryt płyt muszą mieć
  odrębne etykiety. Uproszczony podgląd nie jest dokumentacją produkcyjną.

## Odbiór

1. Otwórz każdy widok po polsku i po angielsku. Sprawdź tytuł, cel, instrukcję,
   etykiety pól, przyciski, podpowiedzi i komunikaty ograniczeń.
2. Zmień dane karty bez zapisywania i przełącz język. Dane oraz bazowa wersja
   muszą pozostać takie same. Analogicznie sprawdź statusy i parametry.
3. W konfiguratorze ustaw orientację, liczbę urządzeń i komorę na akcesoria.
   Zmiana języka nie może zmienić wybranego wariantu, wymiarów ani kolejności
   rankingu objętości.
4. Otwórz historię, szczegóły kopii CAD i porównanie konfliktu w obu językach.
   Nazwy i notatki użytkownika mają pozostać w oryginalnym języku.
5. Sprawdź oba języki przy typowym skalowaniu Windows oraz po zmniejszeniu okna:
   nagłówki tabel, instrukcje i działania muszą być czytelne i dostępne przez scroll.
6. Zamknij i otwórz dodatek: wybrany język powinien zostać zapamiętany.

Testy programu i oględziny w rzeczywistym IronCAD raportujemy oddzielnie.

## Wynik wdrożenia 21.10.2026

- PASS: pełny harness `20261021T132929833334Z` oraz niezależny przegląd agenta.
- PASS: testy zmiany języka zachowują szkice karty i etapów, starsze tokeny
  wersji, wymiary, orientację i stan niezapisanego układu.
- PASS w IronCAD 2027: karta PL/EN, etapy EN, historia i porównanie przed/po EN,
  konfigurator i podgląd EN, dostępne funkcje PL/EN, powrót do polskiego.
- Poprawiono ucięty napis angielskiego przycisku: `Refresh`; szczegóły w tooltipie.
- Nowa DLL została skopiowana do istniejącego lokalnego wdrożenia po zamknięciu
  hosta; poprzednia kopia w `artifacts/ui-language-predeploy` (poza Git).
- Nie zmieniono geometrii, bazy ani danych projektów podczas oględzin.
- NOT RUN: pełna macierz skalowania DPI oraz ręczny odbiór każdego dialogu
  w obu językach. Diagnostyczne błędy backendu i techniczny JSON zachowano.

## Potwierdzenie zapisu układu

Po potwierdzonym zapisie w bazie konfigurator pokazuje przez 8 sekund zielone powiadomienie: numer wersji, ścieżka SQLite zwrócona przez backend i przycisk kopiowania ścieżki. Status pod przyciskami jest zielony. Błąd lub konflikt nie pokazuje sukcesu. Edycja pól ukrywa poprzednie potwierdzenie. Zapis układu nie tworzy pliku ICS; służy do tego osobna operacja tworzenia szkieletu na kopii.

Weryfikacja 21.10.2026: PASS pełny harness `20261021T141250140083Z` oraz natywny test w IronCAD 2027. Zapis niezmienionego układu projektu testowego zwiększył wersję 10 → 11 i wyświetlił zielony popup z pełną ścieżką faktycznej bazy SQLite oraz zielony status. Nowa DLL i backend zostały wdrożone po zamknięciu hosta. Lokalny backup kodu, bazy, poprzedniej DLL i źródłowego ICS: `artifacts/save-feedback-checkpoint` (poza Git).
