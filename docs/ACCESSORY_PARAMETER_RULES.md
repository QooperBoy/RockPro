# Globalne zasady parametryzacji osprzętu — 28.10.2026

Obowiązują we wszystkich rodzinach RockPro: w planie, kreatorze, tabeli parametrów
CAD i podglądzie. To specyfikacja wspólnego standardu; zapis nie oznacza dodania
wszystkich kontrolek do obecnego generatora ani zmiany istniejących ICS.

Pierwsza wdrożona kopia T1: [T1_ACCESSORY_PARAMETERS.md](T1_ACCESSORY_PARAMETERS.md).
Rozstawy, marginesy i oba tryby mają dowód natywny z zapisem/otwarciem;
liczba części w tej kopii pozostaje stała. Standard dla pozostałych rodzin
i kontrolki kreatora nadal wymagają osobnego wdrożenia.

## Wspólne znaczenie parametrów

- Każda grupa ma stabilny identyfikator, SKU/recepturę, fizyczną sekcję i bazę
  montażową. Parametry są przypisane do grupy, nie do numeru pozycji w drzewie.
- Odległości podajemy w mm. Opis wskazuje konkretną ściankę, jej brzeg i kierunek.
  Na ściance używamy lokalnych osi U/V; X/Y dotyczą płaszczyzny podstawy/dachu.
  Pozycję prostopadłą do powierzchni wyznacza receptura zapewniająca licowanie.
- **Rozstaw** to odległość między odpowiadającymi sobie kotwami montażowymi.
  **Margines od brzegu** to prześwit od zewnętrznego skraju całego okucia do
  brzegu gotowej ścianki danej sekcji. Nie utożsamiać go z odsunięciem kotwy,
  środkiem siatki ani krawędzią wycięcia. Baza i skraje pochodzą z danego SKU.
- Nazwy i komentarze są po polsku, np. „Rozstaw zawiasów”, „Margines lewy
  uchwytów”, „Rozstaw kół X”. Komentarz podaje bazę pomiaru, jednostkę, zakres
  i informację, czy wartość jest sterująca, czy wyliczona.

### Jeden tryb sterowania, bez sprzecznych więzów

Dla rzędu wybieramy jawnie jeden tryb:

1. **Od brzegów:** liczba elementów i marginesy od obu brzegów są sterujące;
   równy rozstaw jest wyliczany. Symetria może wiązać oba marginesy.
2. **Z rozstawu:** liczba, rozstaw i położenie środka grupy są sterujące;
   marginesy wynikają z nich i są sprawdzane.

Nie traktować jednocześnie liczby, obu marginesów i rozstawu jako niezależnych
sterowań. Pola wyliczone są tak oznaczone; UI nie pozwala ich nadpisywać bez
zmiany trybu. Konstruktor może jawnie wybrać układ niesymetryczny/indywidualny.
Zmiana rozmiaru nie zmienia po cichu trybu, liczby ani żądanych odstępów.

Przy osi ścianki od 0 do L i zewnętrznych skrajach okucia względem kotwy
`[u_min, u_max]`, marginesy `b_lewy`, `b_prawy` dają:

```text
u_pierwszy = b_lewy - u_min
u_ostatni  = L - b_prawy - u_max
rozstaw   = (u_ostatni - u_pierwszy) / (liczba - 1)  # dla liczba > 1
u_i       = u_pierwszy + i * rozstaw
```

Dla jednej sztuki steruje położenie lub jawne centrowanie; rozstaw nie występuje,
a wynikowe marginesy są wyliczone i sprawdzane względem wymaganych minimów.
Domyślne centrowanie uwzględnia asymetryczne skraje okucia względem kotwy,
nie sam origin modelu. Nie dzielimy przez zero i nie udajemy, że dwoma dowolnymi
marginesami można niezależnie sterować jedną sztuką. Przesunięcie ma jawne pole.
W trybie z rozstawu: `u_i = środek_grupy + (i - (liczba-1)/2) * rozstaw`.
Po obrocie okucia trzeba uwzględnić skraje w jego rzeczywistej orientacji.

## Zawiasy

Parametry każdej linii: liczba zawiasów, rozstaw, margines od pierwszego
i drugiego brzegu ścianki, tryb sterowania, symetria oraz identyfikator złącza.
Kierunek rzędu wynika z wybranego złącza — także dla pionowych klap/szaf.
Położenie względem podziału sekcji i wysokości obu połówek określa receptura;
nie wolno dowolnie przesuwać zawiasu poza złącze, aby ukryć kolizję.
Górny i dolny prześwit do brzegów ścianek/profili jest wyliczany i kontrolowany
osobno dla obu połówek, także gdy kierunek rzędu jest pionowy.

Zmiana gabarytu, liczby lub rozstawu przesuwa wspólnie obie połówki, powiązane
wycięcia i zakończenia profili. Przerwa profilu jest wyznaczana z ZEWNĘTRZNEGO
obrysu zawiasu oraz wymaganego luzu, nigdy z mniejszego otworu w sklejce.

## Uchwyty

Parametry grupy: liczba na ściankę, rozstaw, marginesy od bocznych brzegów,
wysokość montażu względem dolnego brzegu tej ścianki oraz tryb i symetria.
Wysokość może być sterowana od brzegu lub jako udział wysokości sekcji;
tryb i wynikowe odległości muszą być jawne. Sprawdzać też dolny i górny prześwit.

Domyślnie po dwa na przeciwległych bokach prostopadłych do ściany zawiasów.
Konstruktor może wybrać 1–16 na ściankę, jeśli jest miejsce; jedna sztuka jest
domyślnie wyśrodkowana. Przy symetrii przeciwległe ściany korzystają ze wspólnej
liczby, wysokości i rozstawu. Odbijamy układ kotew, nie geometrię katalogowego
uchwytu. Wycięcie i podfrezowanie podążają za jego kotwą oraz orientacją.

## Koła i górne elementy pod koła — dwa kierunki X/Y

Parametry układu: liczba i układ kół, **Rozstaw kół X**, **Rozstaw kół Y**,
marginesy od czterech brzegów podstawy, środek układu i tryb sterowania.
Dla układu 2 × 2 kotwy mają współrzędne `cx ± rozstaw_X/2`, `cy ± rozstaw_Y/2`.
W obu kierunkach niezależnie stosujemy regułę: sterują marginesy albo rozstaw,
a pozostałe wielkości są wyliczone. Nie przenosić długości skrzyni na obie osie.

Górne gniazda/miski lub profile pod koła, zależnie od konstrukcji, tworzą
**sparowany układ piętrowania**. Ich pozycje X/Y są wyliczone z odpowiadających
kół, a nie wpisywane jako niezależny, konkurencyjny rozstaw. Punktem odniesienia
jest miejsce osadzenia koła w górnym elemencie dla ustalonej orientacji
piętrowania, nie dowolny origin zespołu koła. Uwzględniać offset kół skrętnych
i transformacje obu części. Z zewnętrznego obrysu nie wywodzić konturu otworu.

Położenie Z wynika z powierzchni montażu: koła pod podstawą/podporami,
a górne elementy na górnej powierzchni właściwej sekcji. Podpory, gniazda
i ich wycięcia przeliczają się razem z układem. Górne listwy/profile pod koła
mają również parametry długości i zakończeń wynikające z ich funkcji.
Profile krawędziowe obudowy nadal wynikają z jej gabarytu i reguły licowania.

Fizycznie koła i podpory należą do Podstawy (cały nieruchomy korpus), górne
gniazda do właściwego Wieka, jeśli na nim są montowane. Jedna pokrywa oznacza
wyłącznie Wieko 1; Wieko 2/3 tworzymy tylko przy rzeczywistej drugiej/trzeciej.
Zachowują wspólny etap transportu i powiązania między zespołami.

## Kontrola poprawności

- Sprawdzać skraje całych okuć, prześwity między nimi, narożniki, profile,
  strefy pracy zawiasów oraz miejsce na wycięcia i mocowanie.
- Minimalne marginesy/luz wynikają z konkretnego zestawu. Nie stosować jednego
  niezmierzonego progu do wszystkich SKU. Brak danych blokuje zatwierdzenie układu.
- Konflikt nie może prowadzić do skalowania katalogowych części, zmiany liczby,
  samoczynnego powiększenia skrzyni lub rozłączenia układu kół i gniazd.
- Weryfikować zmiany obu osi osobno i łącznie, rozstawu, marginesów, liczności,
  trybu symetrii oraz powrót i zapis/reopen. Sprawdzać faktyczny CAD i wycięcia,
  nie tylko tabelę liczb lub podgląd.

Powiązane zasady: [CASE_DEFAULTS.md](CASE_DEFAULTS.md),
[CASE_STRUCTURE.md](CASE_STRUCTURE.md), [STUDIO_INTERACTION.md](STUDIO_INTERACTION.md).
