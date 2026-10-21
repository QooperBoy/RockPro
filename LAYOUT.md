# MVP 0.4 — układ wyposażenia

W dodatku: **Układ urządzeń → Otwórz konfigurator 3D**. Wybierz wcześniej zapisaną kartę projektu z przypisanym szkieletem ICS.

## Zakres
- Jeden typ urządzenia, 1–30 sztuk na skrzynię. Liczba skrzyń na karcie projektu jest osobną wartością.
- Wymiary obrysu urządzenia X/Y/Z, sześć permutacji orientacji, układ wzdłuż X, Y albo Z.
- Odstęp między bryłami, rezerwa przy każdej ścianie, grubość przegrody (0 wyłącza).
- Opcjonalna komora z boku (+X) lub z tyłu (+Y). Podaj obrys zawartości, np. laptopa lub zwiniętych kabli. Przegroda komory ma grubość sklejki.
- Podgląd izometryczny oraz rzuty z góry i przodu. Obrys zewnętrzny jest kreskowany; urządzenia niebieskie, zawartość komory pomarańczowa, przegrody szare.
- Wymiary wnętrza i zewnętrznego szkieletu są pokazane osobno. Zewnętrzne = wewnętrzne + dwie grubości sklejki. Bez wystających okuć i kół.

## Dane i obliczenia
Panel WinForms → MCP stdio → `layout.py` → wspólna baza SQLite. Nowe narzędzia: `preview_layout`, `get_layout`, `save_layout` (łącznie 11). Nie ma osobnej bazy C# ani modelu AI wymaganego do obliczeń.

Wzdłuż wybranej osi wymagany obrys urządzeń wynosi `liczba × wymiar + (liczba − 1) × (luz + grubość przegrody)`. Rezerwa jest dodawana z obu stron na każdej osi. Komora może powiększyć pozostałe wymiary, jeśli zawartość jest większa od urządzeń. Backend kontroluje skończone liczby, zakresy, liczbę brył, mieszczalność i przenikanie osiowych obrysów. Styk powierzchni jest dozwolony.

`layouts` przechowuje bieżącą specyfikację projektu. Każdy zapis trafia też do tabeli `events` i ustawia etap układu na `review`, a etapy od konstrukcji dalej na `outdated`. Nie jest to snapshot CAD ani automatyczne zatwierdzenie projektu.

## Przekazanie do CAD
Przycisk **Utwórz szkielet na kopii ICS** zapisuje układ, przelicza sześć parametrów RP_* i wywołuje istniejącą walidowaną operację `change_dimensions_on_copy`. Zachowuje kontrolę manifestu dziesięciu płyt, zapis/otwarcie, oddzielne archiwum i projektową historię snapshotów.

Do ICS trafiają obecnie gabaryty szkieletu. Bryły wyposażenia, przegrody i boczna komora pozostają opisem układu oraz podglądem — nie są jeszcze wstawiane jako części CAD. Dowolny model WoodLAB nie jest obsługiwany. Podparcie pięter, sposób wkładania i wyjmowania, rzeczywisty profil urządzenia, pianki i wytrzymałość wymagają następnego etapu oraz oceny konstruktora.

## Testy
`python -m unittest discover -s Integracja/rockpro_cad/mcp -p "test_*.py"` — 19 testów, w tym permutacje 6 orientacji × 3 osie, komory, błędne liczby, wymiary zewnętrzne, SQLite i unieważnianie etapów. Osobno pozostaje 7 testów QA. Te testy nie zastępują próby UI i COM w IronCAD.

## Próba natywna — 21.10.2026
W IronCAD 2027 przetestowano zmianę z układu obok siebie na piętrowy, przegrodę 9 mm i komorę +X. Dwie bryły 345,4 × 241,9 × 88,2 mm dały wnętrze 514,4 × 340 × 245,4 mm i gabaryt 532,4 × 358 × 263,4 mm. Przycisk w UI zapisał SQLite i wygenerował nową kopię ICS. Kontrola geometrii po ponownym otwarciu: passed; oryginał niezmieniony; suma kontrolna snapshotu: verified. Dane tej próby są lokalne, poza repozytorium.

## Ranking objętości 0.4.2

Backend porównuje 6 orientacji × 3 kierunki rozmieszczenia (18 układów liniowych). Kryterium: objętość zewnętrznego szkieletu w litrach `V = X × Y × Z / 1 000 000`, z uwzględnieniem luzów, przegród, sklejki i komory. Nie jest to optymalizacja dowolnego pakowania przestrzennego ani ocena wytrzymałości.

Lista orientacji jest sortowana przy bieżącym kierunku, lista kierunków przy bieżącej orientacji. Po przeliczeniu zachowany jest wybrany klucz — zmiana kolejności nie zmienia urządzenia ani kierunku. Wybór najlepszego wariantu spośród 18 następuje przyciskiem „Zastosuj najmniejszą objętość”. Nie zmienia się samoczynnie po edycji wymiarów.

Zielony = najmniejsza objętość w danej liście, czerwony = największa, odcienie pośrednie = względny wynik `(V − Vmin)/(Vmax − Vmin)`. Remisy mają jednakowy kolor; gdy wszystkie objętości są równe, wszystkie są zielone. Warianty niedopuszczalne są na końcu, szare i opisane jako niedostępne. Każdy wariant pokazuje litry, skrajne także min/max. Objętość pod tabelą porównuje aktualny wybór z minimum wszystkich 18 kombinacji.
