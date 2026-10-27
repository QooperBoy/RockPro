# Indywidualny proces konfiguracji skrzyni — wymagania i realizacja

27.10.2026. Wymagania użytkownika: jedenaście etapów, od typu konstrukcji do
wstępnego zapotrzebowania w firmowym Excelu. Ten dokument jest specyfikacją do
wdrożenia; nie oznacza wdrożenia całego kreatora, synchronizacji ERP ani generowania
dowolnej rodziny w IronCAD. Aktualny działający zakres:
[siedem podglądów źródłowych](ALL_REFERENCE_PREVIEWS.md).

Wdrożony pierwszy przyrost: [kreator kroków 1–3](WIZARD_STEPS_1_3.md) z grafem
pokryw, wymiarami sekcji, podglądem 3D i trwałym zapisem draftów. Pozostałe
punkty tego dokumentu opisują docelowy zakres, nie gotową integrację.

Aktualizacja zakresu: [trzy główne typy, bez podtypu](WIZARD_THREE_TYPES.md).
Krok 1 wybiera Skrzynię, Szafę lub Skrzynię 3-elementową. Krok 2 określa
otwieranie ich ustalonych sekcji; wcześniejsza swobodna liczba pokryw jest
archiwalnym wymaganiem, nie opcją obecnego interfejsu.

Wdrożono również [krok 4 — bazę i wybór części](WIZARD_PARTS_SELECTION.md).
Wybór zapisuje rodzaje okuć; ich liczby i rozmieszczenie pozostają kolejnym etapem.

## Nawigacja kreatora

| Krok | Ekran i decyzje konstruktora | Wynik i zależności |
|---|---|---|
| 1 | Główny typ konstrukcji: skrzynia, szafa lub skrzynia 3-elementowa | ID rodziny i wersja reguł; jawna dostępność podglądu, planowania i adaptera CAD |
| 2 | Otwieranie ustalonych sekcji wybranego typu, strona zawiasów lub zdejmowanie i współpraca dwóch pokryw | Graf sekcji i złączy, linie podziału, kierunki ruchu, wstępne strefy zawiasów i zamków |
| 3 | Wymagane wnętrze oraz wymiary i parametry każdej sekcji, grubości i materiały, półki, pianki i prześwity | Wymiarowany układ sekcji, wynikowy obrys sklejki i gabaryt; parametry mają polskie opisy |
| 4 | Wybór części z biblioteki Tomka; dopuszczalne SKU i warianty | Przypięta rewizja katalogu, koszyk definicji części i lista braków danych montażowych |
| 5 | Uchwyty: ściany, liczba na ścianę, orientacja, linia, symetria lub układ indywidualny; także wskazanie/zmiana stref zawiasów | Wystąpienia z kotwami na konkretnych ścianach, relacje rozmieszczenia i powiązane wycięcia |
| 6 | Zatrzaski i zawiasy: zatwierdzenie propozycji wynikającej z kroków 1–2, liczby, pozycji, par i doboru SKU | Okucia przypisane do konkretnych złączy, dopasowane połówki, obróbki sklejki i przerwy profili |
| 7 | Podstawa i transport: koła, podpory, nóżki, piętrowanie, teleskop i kółka walizkowe | Konfiguracja transportu; koła i górne gniazda współdzielą rozstaw, podpory uwzględniają obrys profili |
| 8 | Dodatki i oznakowanie, np. logo zleceniodawcy jako naklejka | Plik grafiki i jego hash, ściana, pozycja, fizyczny rozmiar, liczba i sposób wykonania |
| 9 | Przegląd całego draftu: otwarcie, warstwy, przekrój/widok ściany, wymiary, lista części, konflikty i braki | Akceptacja konkretnej rewizji koncepcji; oddzielne zgłoszenia braków i odstępstwa konstruktora |
| 10 | Przekazanie do wybranej wersji IronCAD, kontrolowany zapis, snapshot oraz uporządkowany folder projektu | Plan, ID operacji, nowa kopia ICS, raport pomiarów, zapis/otwarcie i kwit snapshotu; bez nadpisywania oryginałów |
| 11 | Wstępna lista elementów, liczba zamawianych skrzyń i przekazanie informacji do firmowego Excela | Rewizjonowany BOM roboczy, ilości jednostkowe/łączne, statusy, link do folderu i kwit eksportu/synchronizacji |

Klient, zlecenie, nazwa projektu i liczba skrzyń są metadanymi dostępnymi od
początku; krok 11 je potwierdza. Zlecenie może zawierać kilka wariantów skrzyń,
każdy z własną ilością. Liczba urządzeń w jednej skrzyni jest osobnym polem.
Nie mnożymy dwukrotnie ilości zlecenia i wariantu.

Można wracać do poprzednich ekranów i zapisywać niekompletny draft. Zmiana typu,
podziału sekcji lub katalogu nie usuwa po cichu pracy: pokazuje elementy wymagające
ponownego przypisania i dezaktualizuje zależne kontrole, plan CAD oraz zestawienie.
Liczba ekranów kreatora nie zmienia sześciu organizacyjnych etapów sceny CAD
opisanych w [CASE_STRUCTURE.md](CASE_STRUCTURE.md).

## Typ konstrukcji a model referencyjny

Rodzina opisuje budowę i obsługiwane reguły, podtyp — konkretną topologię otwierania,
a istniejący model — przykład lub źródło części. Wing, Martin i nazwa urządzenia
nie zastępują typu konstrukcji. Siedem wzorców oraz T1/T2 pozostają materiałem do
mapowania reguł; nie deklarujemy dziewięciu gotowych generatorów. Nowy wariant
może mieć podgląd bez dostępnego adaptera CAD. Brak adaptera blokuje krok 10,
ale nie zapis koncepcji ani listy nieustalonych pozycji.

Nowe konstrukcje domyślnie mają zieloną sklejkę #408080. Reguła płytkiej górnej
pokrywy 10–15% z minimum montażowym zawiasu dotyczy odpowiedniego podtypu T1;
nie skraca automatycznie wysokiej zdejmowanej czapki ani drzwi szafy.

## Sekcje, złącza i sposób otwierania

Każda sekcja ma stabilne ID, rolę, lokalny układ współrzędnych, wymiary,
ścianki i parametry. Złącze wskazuje dwie sekcje oraz powierzchnie, kontur
łączenia, strefy montażowe, kierunek otwierania i regułę ruchu. Typ złącza:
stałe, zawiasowe, zdejmowane lub wysuwane. Wiele wiek oznacza wiele złączy,
nie jedno globalne pole wysokości pokrywy.

Relacje obejmują: otwieranie niezależne, wspólny ruch oraz wymaganą kolejność
(np. zdejmij osłonę przed wysunięciem wkładu). Cykl w kolejności otwierania
jest konfliktem. Deklaracja takiej relacji nie zatwierdza mechanizmu ani
rzeczywistego toru ruchu; to osobne dane i kontrola CAD.

Krok 2 tworzy propozycje stref okuć. Krok 5 może wskazać ścianę zawiasów,
a krok 6 finalizuje zawiasy i zamki w jednym widoku złączy. Uchwyty już podczas
kroku 5 uwzględniają znane i zarezerwowane strefy zawiasów. Dopóki brak SKU
lub wymiarów strefy, układ ma status wymagający sprawdzenia. Zmiana zawiasu
w kroku 6 ponownie sprawdza uchwyty; nie tworzy zbędnego wycięcia jako obejścia.

Automatyka proponuje pozycje na liniach łączenia, uwzględniając rodzaj złącza,
orientację, profile, dostęp do obsługi, narożniki i strefy ruchu. Nie każda linia
podziału wymaga zawiasu albo zatrzasku. Dwie połówki okucia mają jedną relację
montażową i osobne przypisanie do odpowiednich sekcji. Przesunięcie złącza
przelicza obie połówki oraz ich obróbki.

## Rozmieszczanie części

Przeciąganie z katalogu wybiera ścianę lub złącze, nie dowolne XYZ. Zapisujemy
lokalne u/v, normalną i obrót, odniesienie do krawędzi/środka oraz regułę kotwy:
stały odstęp, udział wymiaru albo odległość od złącza. Symetria i wspólna linia
mają stabilny identyfikator grupy. Tryb indywidualny zachowuje jawny wybór
konstruktora; zmiana wymiarów nie przywraca domyślnej symetrii.

Domyślne uchwyty: dwa na każdej z dwóch przeciwległych ścian prostopadłych
do ściany zawiasów. Możliwy jeden centralny na każdej; inny układ jest jawnie
zapisanym wyborem. Gotowych okuć nie skalujemy. Uchwyty, zawiasy, zamki i gniazda
zabierają ze sobą wersjonowane obróbki wymaganych płyt/profili. Ukrycie warstwy
nie usuwa obróbki; usunięcie wystąpienia wymaga przeliczenia zależnych operacji.

Katalog Tomka zostanie przyjęty przez osobny import: zachowane źródło → identyfikacja
SKU → jednostka zakupowa → zasób CAD i zgodność 2023 → siatka/miniatura → ramy
montażowe i wycięcia → weryfikacja. Brak danych oznacza `unknown`, a nie brak
wymaganego wycięcia. Używamy reguł z [ROC41_CUTOUTS_AND_JOINTS.md](ROC41_CUTOUTS_AND_JOINTS.md).

Logo jest osobnym dodatkiem: naklejka, nadruk lub inna technologia. Sam obraz
podglądowy nie tworzy kieszeni, frezowania ani pozycji materiałowej o odgadniętych
wymiarach. Format druku, naddatek i technologia mogą pozostać do potwierdzenia.

## Rewizje, zapis i foldery

Rozwijamy nowy wersjonowany `ConceptSpec`; nie dodajemy nieznanych pól do obecnego
ścisłego `rockpro.concept-draft/1` ani `CaseSpec v1`. Migracja starego szkicu jest
jawna; nie wylicza topologii i kotew z samych macierzy podglądu.

Projekt koncepcyjny, zatwierdzenie, plan, model CAD, snapshot i BOM mają oddzielne
ID/rewizje oraz powiązania. Zapis wymaga `expected_revision`. Wynik sprawdzenia
dotyczy konkretnej rewizji i źródeł. Edycja po akceptacji nie zmienia zaakceptowanej
historii. Wspólne dane i dziennik są w istniejącej SQLite, nie w pamięci widoku.

Krok 10 tworzy nowy plik roboczy; po poprawnym zapisie/ponownym otwarciu rejestruje
snapshot z SHA i eksportem podglądu. Błąd zapisu nie może dać statusu „gotowy model”.
Jeden wykonawca CAD, odzyskiwanie po ID operacji, brak powtórzenia niejednoznacznego
zadania. Pakiet do Excela można przygotować mimo awarii połączenia z Excelem;
nie ponawiamy przez to generowania modelu.

Proponowana struktura w skonfigurowanym katalogu projektów:

```text
Klienci/<klient-ID>/<zlecenie-ID>/<wariant-ID>/
  01_wejscie/                 # zachowane materiały i źródła
  02_koncepcja/rev-0001/      # specyfikacja, grafiki i podgląd
  03_cad/robocze/             # edytowane kopie, nie archiwum
  03_cad/snapshoty/<ID>/      # zapisany model, SHA i raport
  04_dokumentacja/<rewizja>/
  05_zestawienia/<rewizja>/   # BOM roboczy/potwierdzony i eksport
  06_integracje/excel/        # pakiety, kwity, konflikty
```

Identyfikatory są trwałe; czytelna nazwa klienta może być etykietą. Rejestr
wiąże folder z projektem, zamiast odtwarzać tożsamość z nazwy. Ścieżki tworzy
backend wyłącznie pod wybranym katalogiem bazowym, z ochroną przed kolizją nazw
i nadpisaniem. Snapshot nie jest kopią roboczą. Ten plan nie uruchamia teraz
operacji zapisu w otwartych dokumentach użytkownika.

## BOM roboczy i Excel jako firmowy rejestr

Zapotrzebowanie widać już w draftcie; krok 11 przekazuje rewizję roboczą po
zarejestrowaniu wyniku CAD. `draft`, `needs_review`, `confirmed`, `superseded`
to statusy BOM, niezależne od poprawności danych, odbioru CAD i zgody produkcyjnej.
Pozycja może mieć znaną ilość, ale niepotwierdzone SKU lub technologię.
Nieznana ilość jest pusta z przyczyną; nie zamieniamy jej na zero.

Wiersz ma: ID pozycji, SKU i rewizję definicji, nazwę PL, jednostkę, ilość na
skrzynię, liczbę skrzyń danego wariantu, ilość łączną, źródło obliczenia,
status ilości/SKU/technologii oraz powiązane wystąpienia. Nagłówek zawiera
klienta, zlecenie, wariant, rewizję koncepcji/BOM, snapshot i SHA modelu,
czas, autora wpisu oraz link do folderu. Excel może dostać podsumowanie zlecenia
i odrębne pozycje poszczególnych wariantów.

Jednostki i sposób liczenia:

- Okucie kupowane w komplecie liczymy raz, zgodnie z jednostką katalogową;
  jego połówki, śruby lub potomne bryły CAD nie są automatycznie zakupami.
- Profile mają liczbę odcinków, długości cięcia i sumę długości; liczba sztang
  handlowych wymaga danych o dostępnej długości i rozkroju.
- Sklejka ma formatki i materiał/grubość; liczby arkuszy nie wyliczamy z samego
  obrysu ani powierzchni bez rozkroju, technologii i dostępnych resztek.
- Naklejki i inne dodatki mają własną jednostkę oraz liczbę, także przy wielu
  naklejkach na skrzynię. Ilości materiałów, urządzeń i skrzyń są odrębne.

`ilość łączna = ilość na skrzynię × liczba skrzyń wariantu`. Odpad, naddatki
i opakowania zakupowe są oddzielnymi regułami; nie zwiększają skrycie liczby
zamontowanych elementów. Wstępny BOM nie rezerwuje magazynu, nie zleca zakupów
i nie zastępuje potwierdzonych wymiarów technologicznych z
[CUTTING_BOM_IMPORT.md](CUTTING_BOM_IMPORT.md).

SQLite przechowuje wersje projektu, pochodzenie obliczeń i dziennik integracji.
Excel pozostaje istniejącym firmowym rejestrem/ERP — nie tworzymy konkurencyjnej
kopii jego sald i ręcznych decyzji. Własność pól ustalimy po odczycie arkusza:
proponowane po stronie RockPro są rewizja modelu/BOM, ilości obliczone, linki
i status eksportu; po stronie firmy np. numer zlecenia, terminy i status realizacji.
Zmienione ręcznie pole nie jest automatycznie nadpisywane.

Etapy integracji:

1. Mapowanie rzeczywistego Excela i próbny eksport do osobnego pliku zgodnego
   z jego kolumnami. CSV/XLSX jest wymianą danych, nie działającą synchronizacją.
2. Jednokierunkowy zapis kontrolowanych tabel/kolumn: podgląd różnic, kopia
   bezpieczeństwa w trybie plikowym, potwierdzenie zapisu i odczyt kontrolny.
   Nie przepisujemy całego skoroszytu z formułami, VBA lub zewnętrznymi linkami.
3. Opcjonalne dwukierunkowe uzgadnianie wybranych pól po ustaleniu właściciela
   każdego z nich; konflikt trafia do rozstrzygnięcia, nie wygrywa ostatni zapis.

Klucz synchronizacji obejmuje projekt/wariant, rewizję BOM i ID pozycji; niezależny
`operation_id` i hash pakietu chronią przed duplikacją przy ponowieniu. Numery
wierszy i nazwy klientów nie są kluczami. Starsza rewizja pozostaje w historii,
nie podmienia bieżącej. Zajęty plik albo brak dostępu daje status oczekujący/błąd;
nie status „zsynchronizowano”. Skutki CAD i eksportu mają osobne kwity.
Konkretnego adaptera lokalnego/chmurowego nie wybieramy bez poznania środowiska.

## Przyrosty implementacyjne i odbiór

| Kolejność | Zakres | Kryterium odbioru |
|---|---|---|
| A | Kontrakt koncepcji, graf sekcji/złączy, możliwości rodzin, migracja i rewizje | Zapis/odczyt wielopokrywowego draftu; błąd cyklu; zmiana wymiarów zachowuje relacje; brak adaptera nie udaje gotowości |
| B | Kreator 1–3, trwały draft i edytowalna geometria sekcji | Można utworzyć wariant od typu do parametrów, cofnąć krok i odzyskać stan po ponownym otwarciu |
| C | Biblioteka i kroki 4–6; drag and drop na ściany/złącza | Zmiana kotwy przenosi okucie i jego obróbki; symetria/liczność zachowana; konflikt uchwyt–zawias widoczny |
| D | Transport, piętrowanie, logo i review 7–9 | Koło i gniazdo pozostają współosiowe; logo zachowuje fizyczny wymiar; akceptacja wiąże konkretną rewizję |
| E | Adapter jednej kompletnej rodziny, krok 10 i foldery | Od draftu do nowej kopii w IronCAD 2023, pomiary, zapis/otwarcie, snapshot i brak zmiany oryginału; potem osobne adaptery kolejnych rodzin |
| F | BOM roboczy, ilości i próbny eksport kroku 11 | Poprawne przeliczenie kilku wariantów; brak podwójnego liczenia; pozycje nieznane są jawne; zgodność z próbką firmowego arkusza |
| G | Automatyczna synchronizacja Excela | Ponowienie nie duplikuje; ręczne zmiany i formuły zachowane; konflikt, blokada pliku i brak dostępu nie gubią danych |

Prosty podgląd BOM i neutralny pakiet danych można rozwijać wcześniej,
równolegle z adapterem CAD; nie musimy czekać z całą architekturą na arkusz.
Końcowego mapowania nie zgadujemy. Rdzeń oblicza układ i zestawienia skryptami;
AI proponuje rozwiązania i pomaga przy wyjątkach przez te same operacje.

Do zebrania od firmy: pełna baza SKU wraz z jednostkami i zasobami CAD 2023;
przykładowy Excel z układem tabel/formuł oraz informacja, gdzie jest używany,
czy jednocześnie przez kilka osób, jakie pola można zmieniać i jak identyfikują
klienta/zlecenie/rewizję. Nie są potrzebne hasła ani tokeny w rozmowie.

## Wykorzystanie istniejących modułów

- Studio/Three.js: kamera, siatki, przełączanie źródeł i prototyp ruchów.
- `family_concepts.py`: obecny ścisły format szkicu; zachowany do migracji.
- `mcp/project_store.py`: istniejące ID projektu, klient, liczba skrzyń, rewizje,
  zdarzenia i snapshoty; nie tworzymy drugiego rejestru w interfejsie.
- `core_case` i rejestr części: plan, kotwy, powiązania obróbek, blokada CAD,
  dziennik operacji i kontrola niezmienności źródła.
- [INVENTORY_CONTRACT.md](INVENTORY_CONTRACT.md) i
  [MATERIAL_PLAN_REVISIONS.md](MATERIAL_PLAN_REVISIONS.md): istniejące transakcje
  magazynu i wersje planów; eksport roboczy do Excela ich nie wywołuje.

Weryfikacja dokumentu: przegląd aktualnych modułów i kontraktów, audyt repozytorium
oraz odnośników. Bez zmian runtime, zapisów CAD i dostępu do firmowego Excela.
