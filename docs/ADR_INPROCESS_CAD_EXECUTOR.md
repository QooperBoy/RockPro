# Decyzja robocza: wykonawca CAD wewnątrz IronCAD-a

Stan: **propozycja potwierdzona ograniczonym POC A/B, nie wdrożona architektura produkcyjna**.
Data: 22.10.2026. Bieżący przyrost: zatrzaski 17251S, dwa rozmiary kopii.

## Powód

Zewnętrzny klient Python i oficjalny interop C# otrzymywały `E_NOINTERFACE`.
Ten sam `IZBaseApp` odczytany przez obsługiwany AddOn wewnątrz działającego
hosta zwrócił wersję API. Publikacja interfejsu w prywatnym ROT nie wystarczyła
do przekazania go do klienta. Nie traktujemy kolejnej rejestracji metadanych
ani zamiany języka klienta jako potwierdzonej naprawy.

Szczegółowe dowody: [runbook połączenia](ICAPI_CONNECTION_RUNBOOK.md).

## Proponowany podział

```text
UI RockPro / klient AI
        |
        v
MCP + istniejąca SQLite + dziennik operacji
        |
        | jawne, zwalidowane polecenie i wersje danych
        v
Wykonawca wewnątrz dodatku IronCAD
        |
        | szeregowo, na właściwym wątku hosta
        v
Kopia ICS -> pomiar -> zapis -> ponowne otwarcie -> raport
```

- Python zachowuje obliczenia układów, reguły symetrii, przygotowanie planu,
  bazę projektów i komunikację z modelem. Nie przekazujemy mu wskaźników COM
  między procesami jako wymaganego mechanizmu działania.
- Dodatek wykonuje ograniczony zestaw operacji CAD. Wątek rozmowy, oczekiwanie
  na model AI i przeszukiwanie internetu nie mogą blokować wątku CAD.
- AI proponuje wariant i parametry. Kod oblicza macierze, kontroluje symetrię
  i wykonuje montaż. Wynik modelu nie jest sam w sobie zgodą na wykonanie.
- Używamy istniejących wersji projektu, układu, snapshotów i dziennika.
  Nie tworzymy drugiej bazy w dodatku ani równoległej historii bez powiązania.

## Granica polecenia

Przyszła komunikacja lokalna może używać nazwanego potoku ograniczonego do
bieżącego użytkownika. Na obecnym etapie nie ma jeszcze takiego serwera.
POC uruchamia jeden stały helper; nie jest ogólnym narzędziem wykonania kodu.

Polecenie powinno zawierać:

- `operation_id`, wersję kontraktu oraz oczekiwane rewizje projektu i układu;
- PID/sesję hosta i dokładny kontekst dokumentu;
- SHA źródła, wersję manifestu i identyfikatory zatwierdzonych assetów;
- zwalidowany plan w mm, ramy współrzędnych i grupy symetrii;
- nowy katalog wynikowy pod katalogiem operacji, bez nadpisywania snapshotu.

Wykonawca ponownie sprawdza te dane. Nie przyjmuje dowolnego kodu Python/C#,
nazwy metody, ścieżki DLL, polecenia systemowego ani niesprawdzonego pliku
do załadowania. Docelowa lista poleceń ma być jawna i wersjonowana.

## Kolejność i odzyskiwanie

Jedna operacja modyfikująca CAD na host. UI i AI korzystają z tego samego
wykonawcy oraz kontroli rewizji. Konflikt zatrzymuje zapis; klient nie pobiera
automatycznie nowego tokenu i nie powtarza starego polecenia.

Granice etapów: kontrola wejścia, otwarcie własnej kopii, montaż, pomiar,
zapis, ponowne otwarcie, snapshot i rejestracja wyniku. Żądanie anulowania
obsługujemy między wywołaniami CAD; nie obiecujemy przerwania trwającego COM
ani nie kończymy procesu IronCAD w celu anulowania zadania.

Po niejednoznacznym błędzie najpierw sprawdzamy dziennik i własne pliki.
Nie ponawiamy importu, który mógł już dodać części. Sprzątanie dotyczy wyłącznie
dokumentów i wpisów dodatku z potwierdzoną własnością. Nieznane pozostają.

## Warunek przyjęcia decyzji

Przebieg `latch17251-inprocess-native-20261022-09` potwierdził montaż
rzeczywistych zatrzasków, symetrię, jedną zmianę wymiarów, zapis/otwarcie
i zamknięcie własnych kopii. Ten wynik uzasadnia wydzielenie działającego
wykonawcy do stałego dodatku; nie oznacza, że został już podpięty do MCP.
Pełny transport,
instalacja i odbiór u RockPro są kolejnymi zadaniami, a nie częścią tego POC.
