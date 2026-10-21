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
