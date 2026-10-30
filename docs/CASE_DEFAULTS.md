# Ustalenia użytkownika — aktualizacja 26.10.2026

Sklejka: RGB(64,128,128), #408080, ICAPI COLORREF 0x808040, zmierzone z T_1.

## Pokrywa — obowiązująca reguła

Pokrywa jest płytka, parametryczna. Zwykle ma 10–15% **wysokości korpusu**;
planer przyjmuje 12%, a domyślny górny limit wynosi 15%.
Minimum wynika z pionowego miejsca na całe górne połówki zamków i zawiasów,
złącza, górnego profilu, grubości płyty i niezbędnych odstępów.
Nie liczymy 3 × szerokość okucia. Samo zmieszczenie zawiasu w płycie nie wystarcza:
jego skraj nie może wejść w obszar górnego profilu lub narożnika.
Szerokość gniazda na poziomym dachu nie wyznacza wysokości ściany pokrywy.

Jeżeli wybrane okucia nie mieszczą się w limicie, zgłaszamy konflikt.
Dobieramy inny wariant okuć lub konstruktor jawnie dopuszcza odstępstwo.
Nie powiększamy automatycznie korpusu dla uzyskania procentu. Odstępstwo
pozwala zmienić proporcję, ale nie pozwala naruszyć minimum montażowego.

To zastępuje wcześniejszą, błędną zasadę 3 × szerokość i wynik 408 mm.
Historyczne modele i raporty pozostają zachowane jako historia, nie domyślne.

## Historyczna inspiracja EB-L630U — prototypy 02/03

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

## Korekta po ocenie użytkownika 26.10.2026 — prototyp 05

Użytkownik wskazał nakładanie górnych połówek okuć na profil wieka i polecił
podwyższyć pokrywę oraz dodać progi na przyszłość. Aktualny wariant ma pokrywę
115 mm przy korpusie 300 mm (obrys płyt 415 mm). To jawnie dopuszczone odstępstwo;
81 mm pozostaje wyłącznie wartością historycznych plików.

Dla kompletu 17251S + 270836 + EG-0113 próg wynosi 110 mm:
`ceil(max(69.854, 67.01) + 35 + 5)`. Bierzemy pełne okucia, górny profil i 5 mm
odstępu między niezależnymi elementami. Wybrana pokrywa 115 mm daje około 10,15 mm
nad zamkiem. Po zmianie katalogu należy podać zmierzone skraje nowego okucia;
brak tych danych blokuje wyliczenie progu, zamiast przyjmować zero.

Prototypowy generator stosuje `core_case/machining_rules.py`; nie zmienia to
automatycznie już załadowanego dodatku ani nie blokuje ręcznego wpisania złej
wartości w IronCADzie. Parametry edytowane ręcznie wymagają ponownej walidacji.
Szczegóły i dowody: [T1_MACHINING_PROTOTYPE.md](T1_MACHINING_PROTOTYPE.md).

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

Aktualizacja Studio 27.10.2026: konstruktor może jawnie wybrać **1–16 uchwytów
na ściankę w grupie**, z równym rozstawem i opcjonalną symetrią. Domyślnie nadal
2 na każdej z dwóch przeciwległych ścian. `handles_per_wall` oznacza liczbę
na jedną ściankę. Poniższa opcja 1/2 i parametry CLI opisują osobny, dotychczasowy
natywny generator T1; nie rozszerzono go automatycznie do wszystkich liczności.
Szczegóły Studio: [sterowanie i linie zawiasów](STUDIO_INTERACTION.md).

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


## Wymagania montażowe 30.10.2026: liczność i podwozie

- Liczba okuć wynika z dostępnego miejsca na konkretnej ścianie i sekcji:
  `n * szerokość_montażowa + (n - 1) * odstęp + margines_lewy + margines_prawy <= długość_dostępna`.
  Dla zera elementów nie stosuj wyrazu `(n - 1)`. Szerokość oznacza pełny,
  sztywny obrys montażowy okucia, nie szerokość samego otworu w sklejce.
  Sprawdź także wysokość, środek rzędu, faktyczny rozstaw osi i znane strefy
  zajęte przez profile, narożniki i inne okucia. Rzędu nie wolno zaakceptować
  tylko dlatego, że spełnia bilans długości. Strefy kolizji zależą od wysokości.
- Rozdziel pojemność geometryczną od liczby przygotowanych wystąpień CAD.
  Komunikat podaje przyczynę i maksymalną liczbę przy danych warunkach.
  Nie skaluj SKU i nie zmieniaj żądanej liczby po cichu. Nieprawidłowy rząd
  zachowuje ostatni poprawny stan; niezależne poprawne rzędy nadal się przeliczają.
  Zmiana liczby obejmuje okucia oraz ich otwory i przerwy w profilach.
- Podpory dolne i koła tworzą jeden logiczny moduł transportowy. Długość,
  szerokość, grubość i odsunięcia podpór są parametryczne; koła pozostają
  sztywne i podążają za kotwami podpór. Płyta montażowa koła dotyka spodu
  podpory, podpora dotyka dna i kończy się przed strefą profilu krawędziowego.
  Sprawdź oba kierunki zmiany wymiarów, styk montażowy i zapis/otwarcie.
- Test natywny działającego kontrolera nie zastępuje testu autostartu po restarcie
  ani testu zmiany przez rzeczywistą tabelę parametrów i przycisk Zastosuj.
