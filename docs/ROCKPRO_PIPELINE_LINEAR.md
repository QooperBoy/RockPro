# RockPro CAD — wdrożenie pełnego procesu

## Zadanie nadrzędne — Spiąć i odebrać proces od urządzenia do stolarni

Proponowany status początkowy: Backlog. Każdy etap wymaga sprawdzenia aktualnego stanu, uzupełnienia braków, integracji i odbioru. Istniejące prototypy stanowią punkt startu. Zamknięcie zadania nadrzędnego wymaga próby całego procesu.

### 1. Karta urządzenia i układ wspierane przez AI — nowe zadanie

Z rysunku, CAD lub wymiarów przygotować kartę z obrysem 3D, źródłami wymiarów, liczbą urządzeń, dopuszczalną orientacją, wymaganiami ochrony, pianką i miejscem na akcesoria. AI proponuje dane i wskazuje braki. Konstruktor zatwierdza kartę, a konfigurator zwraca obliczony obrys wymaganego wnętrza.

Odbiór: jeden rzeczywisty przykład przechodzi do doboru skrzyni. Brak krytycznego wymiaru blokuje zatwierdzenie.

### 2. Dobór szablonu i wariantu wnętrza — rozszerzenie ROC-24

Z zatwierdzonej karty automatycznie zaproponować pasujące wzorce. Uwzględnić pianki, przegrody, przedziałek i dostęp do urządzeń. Pokazać wymagane zmiany i przypadek braku dopasowania. Konstruktor wybiera wariant, który trafia do modelu 3D. Najpierw odbiór na jednej rodzinie. Rozszerzenie na pełną gamę po dostarczeniu wzorców przez RockPro, w powiązaniu z ROC-39.

### 3. Odbiór geometrii 3D — powiązać ROC-19 i ROC-34

Sprawdzić gabaryty, przenikanie, dostęp przy wkładaniu i wyjmowaniu oraz zamknięcie skrzyni. Konstruktor zatwierdza konkretną rewizję ICS albo zwraca model do korekty układu lub doboru szablonu. Odbiór: niezatwierdzona rewizja nie uruchamia przekazania rysunków ani zapotrzebowania.

### 4A. Dokumentacja i przekazanie do stolarni — rozszerzenie ROC-21

Z zatwierdzonej rewizji przygotować rzuty, przekroje, wymiary, listę formatek i potrzebne DXF. Oznaczyć projekt i rewizję. Konstruktor zatwierdza paczkę wydawaną stolarni. Odbiór na jednej rodzinie: paczka pozwala wykonać skrzynię pilotażową.

### 4B. Excel lub ERP oraz kolejka formatek — powiązać ROC-18 i ROC-29

Z tej samej rewizji wyliczyć liczbę części na skrzynię i całe zamówienie. Zapisać zapotrzebowanie oraz formatki z materiałem, grubością, wymiarami, ilością i identyfikatorem rewizji. Powtórzony eksport nie podwaja wpisów. Zmiana zatwierdzonej rewizji zastępuje wcześniejsze zapotrzebowanie w kolejce.

### 5. Wspólny rozkrój kilku zamówień — rozszerzenie ROC-30

Pobrać formatki zatwierdzonych skrzyń. Grupować według materiału i grubości. Uwzględnić arkusze, rzaz i dopuszczalny obrót. Proponować rozmieszczenie formatek, liczbę arkuszy i szacowany odpad. Stolarz zatwierdza plan. Odbiór: rozkrój obejmuje kilka zleceń, a każda formatka jest powiązana z właściwym projektem i rewizją.

## Zależności i końcowy odbiór

- 1 → 2 → 3. Po kroku 3 etapy 4A i 4B mogą przebiegać równolegle. Krok 5 korzysta z wyniku 4B.
- Przetestować jedno rzeczywiste zlecenie od rysunku urządzenia do paczki dla stolarni i zapisu w Excelu lub ERP. Dodać drugie zatwierdzone zlecenie i sprawdzić łączony rozkrój.
- Zmienić pierwszą skrzynię po akceptacji. Sprawdzić, czy po ponownej akceptacji rysunki, części i formatki wskazują nową rewizję i czy rozkrój nie liczy obu wersji.
- W Linearze podpiąć istniejące zadania do zadania nadrzędnego przez relacje, zachowując ich aktualne miejsce w projekcie. Stan każdego etapu potwierdzić przed oznaczeniem go jako ukończony.
