# Hisense R002 — działające parametry montażu w IronCAD 2027

R002 rozszerza sprawdzony snapshot R001 o **28 regulacji montażowych**.
Łącznie tabela parametrów sceny ma **34 pozycje**. To natywne wyrażenia
sterujące położeniami geometrii; zmiana rozstawu lub wysokości nie wymaga agenta.
28 pól jest pogrupowanych nazwami według części, sekcji i ściany. Wszystkie
mają polskie komentarze, jednostki i zalecenia montażowe.

## Dostępne regulacje

| Grupa | Parametry |
|---|---|
| Zamki z przodu i tyłu, niezależnie | `RP_ZamkiPrzod_Rozstaw`, `RP_ZamkiPrzod_Przesuniecie`, `RP_ZamkiPrzod_Pion`; analogicznie `Tyl` |
| Pary uchwytów korpusu z przodu i tyłu | `RP_UchwytyPrzod_Rozstaw`, `RP_UchwytyPrzod_Przesuniecie`, `RP_UchwytyPrzod_Wysokosc`; analogicznie `Tyl` |
| Każdy z ośmiu uchwytów H7159 | `RP_Uchwyt{sekcja}{sciana}{pozycja}_Pozycja` i `_Wysokosc` |

Przykłady pojedynczych uchwytów:

- `RP_UchwytKorpusPrzodLewy_Wysokosc`: tylko lewy uchwyt przedniej ściany.
- `RP_UchwytKorpusPrzodPrawy_Pozycja`: odległość środka od lewego boku w osi X projektu.
- `RP_UchwytCzapkaPrawa_Pozycja`: odległość środka od przedniej krawędzi w osi Y.
- `RP_UchwytKorpusLewa_Wysokosc`: wysokość środka bocznego uchwytu nad spodem dna.

Stała rama projektu: przód = ujemna strona Y, lewa = ujemna strona X,
góra = dodatnia strona Z. Strony nie zmieniają nazw po obrocie kamery.
Wysokość uchwytu czapki liczy się od dolnej krawędzi sklejki czapki, a korpusu
od spodu sklejki dna; kół nie wlicza się do tej wysokości.

Domyślne równania utrzymują zależność od gabarytów oraz rozstawów par.
Wpisanie liczby do pojedynczego uchwytu zastępuje jego domyślną zależność:
można zrobić układ asymetryczny. Przywrócenie samego układu symetrycznego
wymaga ponownego wpisania równania lub skorzystania z początkowej kopii projektu.

## Powiązania geometryczne

Wspólny opis wystąpienia steruje 20 jednostkami montażowymi:
8 kompletnymi uchwytami i 12 połówkami sześciu zamków. Połówki zamka zachowują
wspólny rozstaw i przesunięcie. Jednocześnie porusza się **56 obróbek**:
12 otworów pod zamki, 8 pod uchwyty i 36 wycięć w profilach złącza.
Przekroje profili i geometria katalogowych okuć nie są skalowane.

439 nazw części/grup wskazuje funkcję, kod, sekcję, ścianę i pozycję.
Nieustalone role podczęści i SKU są oznaczone do identyfikacji; etykieta
nie zastępuje stabilnego ID. W wersji R002 zmieniły się ID czterech
odtworzonych profili; aktualna mapa zachowuje powiązanie ze źródłem.

## Istotne szczegóły wykonawcy

- Nowy ekstrudowany profil początkowo udostępnia zastępczy sześcienny SizeBox.
  Najpierw trzeba wygenerować bryłę części, dopiero potem resetować SizeBox
  i wiązać wymiary. Inaczej przypisanie szerokości skaluje przekrój.
- Kolejność operacji profili może zmienić się po przebudowie. Używaj jawnej
  mapy źródłowy ID operacji → nowy ID, nie przypisania po numerze w historii.
- Cztery profile złącza są odtwarzane z oryginalnych konturów, aby pozbyć się
  starych konkurencyjnych relacji. Test mierzy granice ich brył oraz każdy kontur.
- Zmiana nazw nie może zmieniać parametrów ani geometrii. Nazwy użytkownika
  nie są kluczem logiki. Kontrola zapisu/otwarcia obejmuje ponowną edycję montażu.

## Weryfikacja i granice

Natywne próby obejmują początkowy układ, niezależne rozstawy i pozycje, pionowe
odsunięcie zamków, połączenie zmiany gabarytów z montażem, powrót do ustawień,
ponowne otwarcie i ponowną edycję. W każdej próbie sprawdzane są 383 części
fizyczne oraz położenie, orientacja i niezmienność krzywych 56 obróbek.
Prywatne wyniki i dokładne ścieżki są w projekcie lokalnym, poza Gitem.

Zalecane odległości w komentarzach nie są blokadami tabeli IronCAD.
Dowolne ręczne wartości wymagają kontroli montażu; testy nie stanowią pełnej
analizy kolizji bryłowych ani zatwierdzenia CNC.
Liczba okuć pozostaje zgodna ze wzorcem: 3 zamki na przodzie, 3 z tyłu,
8 uchwytów łącznie. Zmiana liczby, swobodny obrót oraz wybór innego SKU
wymagają kolejnego przyrostu generatora. Nie dodano pozornych pól liczby.
Ogólny generator Studio i zgodność tej wersji z 2023 nie są częścią tego adaptera.

Przygotowanie planu: `scripts/prepare_tv_mounting.py`.
Wykonawca: `scripts/native/TelevisionMounting2027.cs`.
Nazwy i widok: `scripts/native/PresentTelevisionMounting2027.cs`.
Adapter uruchamia się przez istniejący lokalny runner, na oddzielnej kopii,
z blokadą pojedynczego wykonawcy CAD i kontrolą niezmienności źródła.
