# Prototyp parametryczny skrzyni telewizyjnej — IronCAD 2027

Osobny adapter developerski odtwarza dziesięć płyt sklejki i wiąże wymiary
54 elementów konstrukcyjnych z parametrami sceny. Zachowuje geometrię okuć,
wkładów, profili i logo z przypiętej rewizji źródła. Nie jest automatycznym
importerem dowolnego ICS ani produkcyjnym generatorem tej rodziny w Studio.
Prywatne mapowanie, geometria i wyniki natywne pozostają poza Gitem.

## Parametry użytkownika

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
