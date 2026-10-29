# Prototyp parametryczny skrzyni telewizyjnej — IronCAD 2027

Bieżące rozszerzenie: [R002 — 34 parametry i sterowanie montażem](TELEVISION_MOUNTING_CONTROLS.md).
Poniższy opis sześciu parametrów dotyczy bazowej rewizji R001; R002 dodaje
rzeczywiste rozstawy i pozycje okuć oraz czytelne nazwy drzewa.

Osobny adapter developerski odtwarza dziesięć płyt sklejki i wiąże wymiary
54 elementów konstrukcyjnych z parametrami sceny. Zachowuje geometrię okuć,
wkładów, profili i logo z przypiętej rewizji źródła. Nie jest automatycznym
importerem dowolnego ICS ani produkcyjnym generatorem tej rodziny w Studio.
Prywatne mapowanie, geometria i wyniki natywne pozostają poza Gitem.

## Parametry użytkownika

### Czytelne drzewo sceny — wymaganie 29.10.2026

Nazwy wystąpień muszą wskazywać rodzaj części, kod katalogowy, sekcję,
ścianę oraz pozycję w ustalonej ramie projektu. Przykłady:

- `Uchwyt H7159 — korpus — przód — lewy`
- `Profil EG-0100 — czapka — tył — góra`
- `Narożnik C1341-30-33 — czapka — przód/lewa — góra`
- `Zamek L905/915 — przód — środkowy — połówka czapki`

Grupa również opisuje zawartość, np. `Profile krawędziowe EG-0100 — czapka`.
Nazwy ogólne lub sam kod nie spełniają wymagania. Powtarzalne części rozróżnia
pozycja lub numer w rzędzie, liczony od jawnie opisanej krawędzi. Wkłady, dociski
i elementy o niepotwierdzonej funkcji wymagają identyfikacji; brak wiedzy należy
oznaczyć wprost. SKU i źródłowe/natywne ID pozostają w mapie niezależnie od nazwy.
Logika nie może wyszukiwać elementu po etykiecie użytkownika.

W r001 poprawiono nazwy dziesięciu płyt i głównych sekcji; pozostała część
drzewa nadal wymaga tej migracji. Zmiana etykiet wymaga kontroli, czy natywne
odwołania wyrażeń i zapis/ponowne otwarcie pozostały poprawne.

### Wymagane rozszerzenie montażu — 29.10.2026

Wersja r001 ma sześć głównych parametrów i **nie realizuje jeszcze** poniższego
sterowania okuciami. Jest to wymaganie następnej rewizji, a nie opis gotowych funkcji.

| Grupa | Parametry do udostępnienia |
|---|---|
| Zamki na każdej linii złącza | Liczba kompletnych zamków, rozstaw równy/ręczny, margines lewy/prawy, przesunięcie rzędu, odległość od linii podziału |
| Uchwyty na każdej ścianie/sekcji | Liczba, wysokość środka, położenie wzdłuż ściany, rozstaw, symetria i obrót dopuszczalny przez montaż |
| Pozostałe elementy | Odpowiednie dla ich funkcji kotwy, odsunięcia, orientacja, liczba i symetria; przekrój lub grubość tylko dla materiału konstrukcyjnego |

Podstawą jest wspólny opis wystąpienia: ID, SKU, sekcja/ściana, kotwa montażowa,
reguła rozmieszczenia i ID powiązanych obróbek. Parametry powinny sterować tym
opisem, a wykonawca tworzyć części oraz wycięcia z tego samego planu. Dwie
połówki zamka zachowują parę i wspólną pozycję wzdłuż złącza. Nie oferować
niezależnego przesuwania samego otworu ani skalowania katalogowego okucia.

Zmiana liczby wymaga dodania/usunięcia właściwych wystąpień i ich obróbek.
Jeżeli wymaga przebudowy przez wykonawcę, interfejs musi to jasno wskazywać;
nie przedstawiać jej jako zwykłego, działającego natywnie parametru długości.
Testy muszą obejmować przesunięcie jednego rzędu, niezależną wysokość uchwytów,
różne rozstawy i liczby, kompletność otworów, brak kolizji oraz zapis/otwarcie.

### Parametry dostępne w r001

| Parametr sceny | Znaczenie |
|---|---|
| `RP_SzerokoscSkrzyni` | Zewnętrzna szerokość obrysu sklejki, bez wystających okuć |
| `RP_GlebokoscSkrzyni` | Zewnętrzna głębokość obrysu sklejki, bez wystających okuć |
| `RP_WysokoscDolu` | Wysokość dolnego zespołu sklejki, bez kół |
| `RP_WysokoscCzapki` | Wysokość zdejmowanej górnej osłony, bez szczeliny złącza |
| `RP_UniesienieCzapki` | Rozsunięcie prezentacyjne osłony w pionie; 0 oznacza zamknięcie |
| `RP_OdsuniecieWkladow` | Pomocnicze odsunięcie wkładów zachowane ze wzorca |

Wymiary te **nie są wymiarami wewnętrznymi ani gabarytem telewizora**.
Grubości, przekroje profili i gabaryty okuć nie podlegają skalowaniu.
Model ma wysoką zdejmowaną osłonę, więc nie stosuje się do niego domyślnej
proporcji płytkiej pokrywy zawiasowej. Zmiana rodzaju osłony wymaga innego układu.

## Wycięcia i położenia

Nie wycinać panelu na podstawie obrysu kołnierza okucia. Dla użytych połówek
L905/915 źródło zawiera osobne profile `HWDrill`: należy kopiować właściwy
kontur montażowy, z zachowaniem zaokrągleń i ramy współrzędnych. Drugi,
większy profil tego samego okucia nie jest zamiennikiem pierwszego konturu.
Adapter dobiera połówki osobno do górnej i dolnej płyty oraz do każdej ściany.
Położenie otworu korzysta z tej samej kotwy co okucie; wymiar otworu jest stały.

Natywna kontrola porównuje ramę świata, długości wszystkich krzywych, stan
operacji odejmowania i brak jej wyłączenia. Sama obecność nazwy otworu w drzewie
nie oznacza poprawnego wycięcia. Kontrola dotyczy 12 obróbek w czterech płytach.
Nowy SKU wymaga własnego konturu i ponownej kontroli technologicznej.

Stare relacje wymiarowe źródłowych płyt przy regeneracji przywracały poprzednie
formuły pozycji. Z tego powodu płyty powstają jako nowe ekstrudowane części,
z kopiami rzeczywistych konturów. Raport zachowuje mapę stary ID → nowy ID.
Nie usuwa się relacji ani części w oryginale.

Przy określaniu osi wzrostu trzeba składać obrót operacji z obrotem części.
Samo użycie ramy części zamieniało wysokość i głębokość dwóch obróconych wkładów.
Test regresji używa różnych przyrostów tych wymiarów; jednakowe przyrosty
maskowały ten błąd.

## Uruchomienie i granice

`scripts/prepare_tv_parametric.py` przygotowuje plan wyłącznie z lokalnego,
wcześniej przejrzanego odczytu. Odmawia innej rewizji źródła i niepełnego
zestawu 12 obróbek. Plików klienta nie należy dodawać do repozytorium.

`scripts/native/ParametrizeTelevision2027.cs` działa przez istniejący runner
`scripts/run_t1_machining_job.py`, jeden host 2027 i jedną blokadę wykonawcy CAD.
Pracuje na kopii, odmawia nadpisania pliku wyjściowego, bada zwiększenie oraz
zmniejszenie wymiarów, uniesienie osłony, zapis/otwarcie i ponowną zmianę.
`scripts/native/ValidateTelevisionCuts2027.cs` sprawdza zapisany wynik i przygotowuje
widok porównawczy wycięć. Szczegóły ścieżek i wyników są w prywatnym projekcie.

Weryfikacja matematyki bez IronCAD:

```powershell
Integracja/.venv/Scripts/python.exe -m unittest discover -s scripts -p test_tv_parametric_math.py -v
```

Mapowanie 383 części fizycznych nie oznacza 383 osobnych kodów zakupowych.
Podczęści uchwytów, zamków, nitów i logo zachowują tożsamość źródłową; pełne
uzgodnienie SKU z katalogiem firmy i zatwierdzenie produkcyjne pozostają osobno.
Pomocnicze wkłady oraz ich gniazda wymagają odbioru konstruktora. Zmiany poza
przedziałami zapisanymi w polskich komentarzach parametrów wymagają kolejnego testu.
