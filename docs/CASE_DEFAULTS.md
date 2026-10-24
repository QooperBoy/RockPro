# Ustalenia użytkownika — aktualizacja 24.10.2026

Sklejka: RGB(64,128,128), #408080, ICAPI COLORREF 0x808040, zmierzone z T_1.

## Pokrywa — obowiązująca reguła

Pokrywa jest płytka, parametryczna. Zwykle ma 10–15% **wysokości korpusu**;
planer przyjmuje 12%, a domyślny górny limit wynosi 15%.
Minimum wynika z pionowego miejsca na zamontowanie zawiasu, złącza,
grubości płyty i niezbędnych luzów. Nie liczymy 3 × szerokość okucia.
Szerokość gniazda na poziomym dachu nie wyznacza wysokości ściany pokrywy.

Jeżeli wybrane okucia nie mieszczą się w limicie, zgłaszamy konflikt.
Dobieramy inny wariant okuć lub konstruktor jawnie dopuszcza odstępstwo.
Nie powiększamy automatycznie korpusu dla uzyskania procentu. Odstępstwo
pozwala zmienić proporcję, ale nie pozwala naruszyć minimum montażowego.

To zastępuje wcześniejszą, błędną zasadę 3 × szerokość i wynik 408 mm.
Historyczne modele i raporty pozostają zachowane jako historia, nie domyślne.

## Inspiracja rzeczywistym EB-L630U

Odczyt płyt z kopii modelu T_1: ściana pokrywy 63,2 mm i dach 9,8 mm,
czyli 73 mm; szczelina pomiędzy płytami korpusu i pokrywy około 8 mm.
Nasz RP_LidHeight obejmuje również tę strefę złącza, zatem odpowiednik wynosi
około 81 mm. Odczyt i macierze: artifacts/eb-l630u-prototype-20261024-01/reference_read.json.

Górna połówka obecnego zawiasu 270836 sięga około 67 mm ponad podział.
Z dachem 9,8 mm i luzem 2 mm wymaga około 80 mm wysokości parametrycznej.
Prototyp 02 ma więc 81 mm pokrywy, 300 mm korpusu, 381 mm obrysu płyt.
To jawne odstępstwo (27%) inspirowane wzorcem, po poleceniu użytkownika,
a nie nowy domyślny procent. Korpus nie został sztucznie powiększony.
H2026 nadal nie jest zamontowany.

## Implementacja

mcp/lid_policy.py wyznacza minimum z wymaganych wysokości montażowych,
sprawdza limit 15% i jawne odstępstwo; choose_lid_height proponuje 12%.
Konfigurator ma minimum montażowe zawiasu (0 oznacza jeszcze niewybrany
zawias), wysokość pokrywy i pole odstępstwa konstruktora.
Backend nie traktuje starego pola lid_hardware_width jako minimum wysokości.
Starsze układy bez nowych pól zachowują dotychczasową geometrię.
Nowa konfiguracja zachowuje przestrzeń urządzeń poniżej podziału.

Walidator profili pozwala na płytkie pokrywy z dodatnią długością każdego
odcinka; nadal odmawia wariantów, gdzie RP_LidHeight - RP_JointGap <= 60 mm.
To ograniczenie obecnej rodziny profili, a nie uniwersalny zakaz płytszych pokryw.

Minimum i limit są egzekwowane przez generator/backend. Bezpośrednia edycja
parametrów w IronCAD wymaga ponownej walidacji. Notatka sceny opisuje wyjątek.
Kompilacja dodatku nie przeładowuje DLL w działającym IronCAD.

Weryfikacja korekty: PASS natywny i rzeczywisty widok przód/tył.
PASS harness, kompilacja i formularze: artifacts/verification/20261024T154630321496Z/.
Plik końcowy: Prototyp_02_plytka_pokrywa/RockPro_EB-L630U_650x500x381_final.ics.

## Uchwyty do podnoszenia — obowiązująca reguła

Domyślnie cztery całe H7159: po dwa na dwóch przeciwległych ścianach bocznych,
prostopadłych do ściany z zawiasami. W naszym układzie zawiasy są z tyłu (Y=D),
uchwyty na lewej i prawej ścianie (X=0 oraz X=L). Ich zewnętrzne strony mają
normalne odpowiednio -X i +X; obrót zachowuje pion uchwytu, bez odbicia/skali.
Nie wystarczy symetria dwóch uchwytów na jednej płaszczyźnie.

Opcja konstruktora **liczba uchwytów na ścianę: 1 albo 2**. Zlecenie „jeden
uchwyt” dla tego układu oznacza po jednym na obu przeciwległych ścianach,
wyśrodkowanym na każdej (łącznie dwa), chyba że konstruktor wyraźnie zmieni
schemat. Domyślnie po dwa: środki na D/4 i 3D/4 (łącznie cztery). Przy jednym
środek D/2. Wysokość środka B/2; położenia zależą od wymiarów skrzyni.

Agent przyjmuje ten wybór jako jawną konfigurację projektu, zapisuje go w
raporcie i przekazuje do SDK. Wąska ściana może wymagać wariantu po jednym.
Generator zgłasza brak miejsca; nie skaluje okucia, nie zmniejsza odstępów
poniżej sprawdzanego minimum i nie zmienia sam liczby wybranej przez konstruktora.
Obecne reguły H7159 używają kołnierza 161 × 107 mm, odsadzenia od krawędzi
minimum 35 mm i przerwy pomiędzy kołnierzami minimum 20 mm.

Kod: core_case/handle_rules.py; wykonawca scripts/prototype_epson_case.py:
--handles-per-wall 1 lub 2, --handle-asset i --handle-datum z przypiętym SHA.
Liczba jest wyborem generatora (zmiana wymaga nowej generacji); położenia
mają natywne wyrażenia parametrów. Nie jest to jeszcze pole działającego panelu.
Nowa wersja zachowuje zieloną sklejkę i pokrywę 81 mm; poprzednie pliki pozostają.
