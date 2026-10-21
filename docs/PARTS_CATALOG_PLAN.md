# Następny etap: katalog części przed automatyzacją okuć

## Kolejność

1. Odczyt drzewa wskazanego modelu bez zmiany źródła: identyfikatory węzłów, ścieżki, liczba wystąpień, przynależność góra/dół. Oddzielne zestawienie zespołów i fizycznych elementów zapobiega podwójnemu liczeniu.
2. Dla każdej rodziny: polska i angielska nazwa, funkcja, producent, numer katalogowy, potwierdzone źródło danych, materiał, masa i wariant. Nazwa CAD pozostaje osobnym polem; podobnych sufiksów nie scalać automatycznie.
3. Geometria i montaż: rzeczywisty obrys, lokalne osie i transformacje, płaszczyzna mocowania, odsadzenie od krawędzi, otwory, wycięcia i przestrzeń ruchu. Sam SizeBox może być zerowy lub szczątkowy w importowanych złożeniach; nie używać go bez weryfikacji jako gabarytu części.
4. Reguły zgodności: pary zamka i profilu, połówki zawiasów, narożniki, koła i gniazda piętrowania, dopuszczalne grubości płyt. Dla koła i gniazda wspólna pozycja X/Y oraz kontrola kierunku i nośności.
5. Konstruktor potwierdza mapowanie rodzin. Niepewne pozycje pozostają niezweryfikowane i nie są automatycznie dobierane.
6. Pierwsza automatyzacja: jedna potwierdzona rodzina narożników na kopii szkieletu. Odbiór po zmianie X/Y/Z, zapis i ponowne otwarcie. Dopiero potem uchwyty, zamki, profile, koła i gniazda.

## Model danych

`part_definition` opisuje rodzinę i wersję katalogową; `cad_occurrence` opisuje konkretne wystąpienie w modelu. Rozdzielić tożsamość części, jej wariant i pozycję. Zapisane ID CAD są lokalne dla dokumentu; nie traktować ich jako uniwersalnego identyfikatora katalogowego. Zachować pochodzenie danych, poziom pewności i osobne zatwierdzenie konstruktora.

## Pierwszy odczyt 21.10.2026

Odczyt API modelu Epson do głębokości 3: 218 węzłów; 36 bezpośrednich węzłów pod górą/dołem, pogrupowanych do 24 nazw z uwzględnieniem zespołu. To inwentaryzacja drzewa, nie kompletny BOM. Zawiera m.in. konstrukcję, zespół urządzenia, wnętrze i okucia. Nazwy 410429, B1930, H7159, 17251S i 270836 wymagają potwierdzenia funkcji i danych katalogowych.

Lokalne surowe dane oraz CSV są w sąsiednim wdrożeniu autora w `Integracja/assembly_audit.json` i `Integracja/parts/Epson_czesci_do_opisania.csv`. Nie są publikowane w Git. Źródłowy ICS nie został zmodyfikowany przez odczyt.

## Wykonany research identyfikacyjny

Wynik identyfikacji kodów i funkcji: [PARTS_IDENTIFICATION.md](PARTS_IDENTIFICATION.md). Katalog referencyjny PL/EN z aliasami i źródłami: [hardware-reference.json](catalog/hardware-reference.json). To podstawa do dalszej weryfikacji geometrii i reguł mocowania; żaden wpis nie jest jeszcze dopuszczony do automatycznego wstawiania.

## Modele, harness i wiedza dla kolejnych agentów — projekt 21.10.2026

Status: propozycja architektury, nie wdrożony runtime agentowy. Istniejący harness
`scripts/Verify.ps1` sprawdza kod; nie jest jeszcze harness-em identyfikacji i montażu części.
Nie zmieniamy obecnej integracji WinForms → MCP → Python/ICAPI → IronCAD ani jednej bazy SQLite.

Aktualizacja po realizacji etapu czytnika 21.10.2026: odczyt przez CLI, ograniczony
logger JSONL i testy są zaimplementowane w `Integracja/rockpro_cad/parts`.
Harness ma nowy krok `parts`. Kontrakt i odbiór: [DEVELOPMENT.md](DEVELOPMENT.md#czytnik-części--etap-przed-montażem-okuć).
Pozostała część tego rozdziału opisuje plan docelowy: nie ma jeszcze routingu modeli
w dodatku, klasyfikatora ani automatycznego montażu.

### Podział modeli do sprawdzenia na naszych danych

| Praca | Proponowany model / wysiłek | Dowód wyniku |
| --- | --- | --- |
| Odczyt API, liczenie wystąpień, transformacje, kolizje | Kod deterministyczny; bez LLM | Surowy pomiar, jednostki i test |
| Normalizacja aliasów, ekstrakcja katalogów, opis PL/EN | Sol medium | Źródło producenta i poprawny schemat |
| Implementacja adaptera, testów, reguł montażowych | Sol high | Testy i próba natywna na kopii |
| Niejednoznaczna geometria, parowanie podzespołów, architektura | Astra high; xhigh dla trudnych wyjątków | Hipoteza, dowody, jawne braki |
| Odbiór ważnej nowej reguły | Niezależny przegląd, np. Astra high | Własny odczyt i test, bez prawa zapisu CAD |

To hipoteza routingu, nie pomiar przewagi modeli. Dla każdego zadania zapisujemy dokładny
identyfikator modelu i ustawienia dostępne w uruchamiającym kliencie; nazw z Codex nie
przenosimy w ciemno do konfiguracji API. Porównujemy Sol i Astrę na tych samych wejściach,
mierząc poprawność, czas, liczbę wywołań i zużycie tokenów. Koszt wyliczamy tylko przy
znanych stawkach. Nie ustawiamy xhigh dla każdej operacji.

Podstawa ogólna, odczytana 21.10.2026: [dobór modeli](https://developers.openai.com/api/docs/guides/model-selection),
[jawny wybór modelu per agent](https://developers.openai.com/api/docs/guides/agents/models),
[ocena jakości agentów](https://developers.openai.com/api/docs/guides/evaluation-best-practices).

### Jeden przebieg

1. Odczyt: identyfikacja dokumentu, hash źródła, rewizja bazy, wersje dodatku i API.
   Odczyt ma limit czasu, głębokości i liczby węzłów; przekroczenie to wynik częściowy,
   nigdy udawany pełny BOM. Niepoprawny obrys wykluczamy z obliczeń.
2. Klasyfikacja: rodzina katalogowa, wariant i osobne wystąpienia CAD. Kandydat z samej
   nazwy nie jest zatwierdzoną geometrią. Materiał CAD i materiał katalogowy są oddzielne.
3. Plan: strukturalna lista proponowanych zmian z jednostkami, układem odniesienia,
   oczekiwaną rewizją i dowodem dla każdej reguły. Podgląd zmian przed wykonaniem.
4. Walidacja: schemat, dozwolone operacje, wymiary, zgodność wariantów i zatwierdzenie
   reguły montażu. Pobrane strony i maile traktujemy jako dane, nie instrukcje wykonania.
5. Wykonanie: jeden worker zapisujący CAD, na nowej kopii. Zadanie ma klucz idempotencji;
   powtórzenie po timeout nie może wstawić drugiego kompletu okuć. Przed zapisem ponownie
   sprawdzamy dokument i rewizję. Konflikt UI–AI wymaga jawnego rozstrzygnięcia.
6. Odbiór: pomiar po operacji, zapis, ponowne otwarcie, ponowny pomiar, snapshot i powiązanie
   z rewizją. Błąd pozostawia poprzednią poprawną kopię; odbiór nie oznacza automatycznego
   dopuszczenia na produkcję. Po awarii uzgadniamy stan ICS i SQLite przed ponowieniem.

Na MVP role odczytu, klasyfikacji i planowania mogą być etapami jednego agenta.
Osobny recenzent nie zapisuje CAD. Rozdzielamy kolejne agenty dopiero, gdy testy pokażą
korzyść; równoległe zapisy do jednego dokumentu są zabronione.

### Dziennik operacji

Proponowany format: zdarzenia JSONL w lokalnym, ignorowanym katalogu `artifacts/agent-runs/<run_id>/`.
To specyfikacja loggera do implementacji, nie deklaracja, że takie logi już powstają.

Każde zdarzenie: `schema_version`, `run_id`, `event_id`, `parent_event_id`, czas UTC,
`project_id`, `document_id`, rewizja wejściowa/wyjściowa, `actor`, model i wysiłek
(null przy operacji bez LLM), wersja promptu/reguł/kodu, nazwa operacji, oczyszczone
argumenty, czas trwania, wynik, błąd, referencje do dowodów i snapshotów wraz z hashami.
Dla prób zapisu również klucz idempotencji i stan rozpoczęta/zakończona/nieustalona.
Zapisujemy obserwowalne kroki i krótkie uzasadnienie decyzji, nie wewnętrzny tok rozumowania.
Tokeny i koszt zapisujemy, jeśli runtime je udostępnia; brak danych to null.

Surowe CAD, maile i ścieżki klienta pozostają lokalne. Logów i baz nie publikujemy w Git.
Do repo trafiają zanonimizowane przykłady, schematy, reguły i testy. Ustalamy retencję,
limity rozmiaru i dostęp do lokalnych dowodów przed wdrożeniem u RockPro.

### Wiedza i testy regresji

Agent nie uczy się trwale od samego zapisania logu. Sprawdzony przypadek zamieniamy
w wersjonowaną instrukcję, przykład i wykonywalny test. Nowa reguła przechodzi przegląd
i testy przed udostępnieniem jej wszystkim projektom. Nie poprawiamy automatycznie
instrukcji produkcyjnych na podstawie pojedynczej udanej próby.

Pierwsze przypadki z zakończonego researchu:

| Przypadek | Oczekiwany wynik testu |
| --- | --- |
| 2643, pusty zespół | Brak naliczenia fizycznego zawiasu |
| 17251S, połówki góra/dół | Poprawne pary i liczba kompletnych zamków |
| Stalowe okucie z materiałem CAD aluminium | Wykryty konflikt, bez automatycznej zamiany materiału |
| Import z błędnym SizeBox | Odrzucenie pomiaru, brak fikcyjnego gabarytu |
| Część2648, brak dowodu funkcji | Status nierozpoznane; bez zgadywania materiału |
| Limit głębokości odczytu | Jawny wynik częściowy |
| Ponowienie zapisu lub zmiana rewizji przez UI | Brak duplikatu albo jawny konflikt |
| Narożnik po zmianie X/Y/Z | Poprawna orientacja i mocowanie po ponownym otwarciu ICS |

Zestaw uczących przykładów oddzielamy od zestawu odbiorowego. Mierzymy osobno identyfikację
rodziny, wariant, liczenie kompletów i geometrię montażu. Niedozwolony zapis źródła,
obejście konfliktu lub użycie niezweryfikowanej części blokują odbiór niezależnie od średniej.
Do kodu wracają również przypadki błędne; pozytywny werdykt innego LLM nie zastępuje pomiaru.

### Kolejność wdrożenia

1. Uogólnić wykonany czytnik read-only, dodać schemat wyniku, ograniczenia i logger.
2. Zbudować mały zanonimizowany zestaw regresji z powyższych przypadków; porównać modele.
3. Zdefiniować kontrakt montażu jednej rodziny 410429: osie, płaszczyzny, odsadzenia,
   wariant i wymagany profil; potwierdzić zgodność geometrii z katalogiem.
4. Wprowadzić kontrolowane wstawianie narożników na kopii i testy zmian X/Y/Z.
   Dzisiejsza allowlista sześciu wymiarów nie daje jeszcze prawa do nowych operacji montażu;
   wymagają osobnego kontraktu, walidatorów i manifestu obsługi.
5. Dopiero po odbiorze rozszerzać zakres na uchwyty, zamki i parę koło–gniazdo.
