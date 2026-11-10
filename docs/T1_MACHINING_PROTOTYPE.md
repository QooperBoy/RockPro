# T1 — prototyp obróbek, 26.10.2026

Rezultat: nowa kopia skrzyni 650 × 500 × 415 mm, zielona sklejka #408080,
cztery uchwyty H7159 na przeciwległych ścianach, zamki 17251S, zawiasy 270836.
Korpus ma 300 mm, pokrywa została podwyższona z 81 do 115 mm na wyraźne polecenie
użytkownika. Próg 110 mm wynika z pełnej górnej połówki zamka (69,854 mm ponad
krawędź korpusu), górnego profilu (35 mm) i odstępu 5 mm. Wybrana wysokość zostawia
około 10,15 mm. To jawne odstępstwo od domyślnych 10–15%, bez powiększania korpusu.
Prototyp nie oznacza odbioru produkcyjnego ani doboru nośności.

## Wykonane obróbki

48 natywnych ujemnych cech w 13 częściach:

| Element | Sklejka | Profile złącza | Etap |
|---|---:|---:|---|
| 4 uchwyty H7159: otwory i płytkie odciążenia kołnierza | 8 | 0 | Uchwyty |
| 2 zamki 17251S, po dwie połówki | 4 | 4 | Zamki i zawiasy |
| 2 zawiasy 270836, po dwie połówki | 4 | 4 | Zamki i zawiasy |
| 4 górne gniazda kół | 4 | 0 | Koła i gniazda |
| Obustronne podfrezowania 8 krawędzi płyt | 16 | 0 | Profile |
| Dopasowanie czoła 4 ścian pokrywy do dna kanału | 4 | 0 | Profile |

Kontury bazowe pochodzą z rzeczywistych cech ujemnych zachowanej wersji konstruktora,
a nie z prostopadłościennych obrysów okuć. Kopiowane są kompletne szkice z łukami;
operacje na wylot i kieszenie o ograniczonej głębokości dotyczą wyłącznie wskazanej
płyty/profilu. Kieszeń pod kołnierz H7159 to pochodny kontur 136 × 84 mm, głębokość
1,25 mm; otwór na wylot pozostaje 130 × 78 mm. Usuwa to wykrytą kolizję
wyoblenia korpusu uchwytu bez odsuwania okucia od ściany ani zmiany jego geometrii.
Pochodny kontur i naddatki wymagają odbioru konstruktora przed produkcją. Nie przebudowujemy
wnętrza katalogowego okucia. Stare, odsunięte pozycje otworów wzorca nie są kopiowane:
nowe pozycje wylicza wspólna kotwa montażu. Dla zamków skorygowano też wysokość
montażu względem rzeczywistej krawędzi płyty.

## Powiązania i obsługa

`scripts/prototype_t1_machining.py` generuje plan dla jednej przypiętej pary źródeł
(SHA256), z jawnie wskazanymi ID części i szablonów. Lokalna karta czterech SKU zawiera
`plywood_cutout_requirement=required`, informację o obróbce profili oraz wersję
szablonu; nie jest to migracja produkcyjnej bazy katalogowej. Biblioteka innych modeli
nie jest automatycznie dopuszczona. `scripts/native/T1MachiningPrototype.cs`
kopiuje cechy przez SDK wewnątrz IronCAD i zapisuje natywne wyrażenia położenia.
`scripts/run_t1_machining_job.py` używa istniejącego, lokalnego mostu DLL o sprawdzanym
hashu, jednego mutexu CAD oraz usuwa własny tymczasowy AddOn. DLL producenta ani
prywatne modele nie są dodawane do Git.

Parametry sceny:

| Parametr | Znaczenie |
|---|---|
| `RP_Length`, `RP_Depth`, `RP_BaseHeight`, `RP_LidHeight` | Gabaryty korpusu i pokrywy |
| `RP_HandleOffset` | Przesunięcie pary uchwytów wzdłuż każdej ściany |
| `RP_HandleHeightOffset` | Przesunięcie uchwytów względem połowy wysokości korpusu |
| `RP_LatchInset` | Odsunięcie obu zamków od skrajów ściany |
| `RP_HingeInset` | Odsunięcie obu zawiasów od skrajów ściany |
| `RP_DisplayGap` | Rozsunięcie wizualne pokrywy, nie luz technologiczny |
| `RP_JointGap` | Odległość krawędzi sklejki: 8,63 mm dla zmierzonej pary profili |
| `RP_Thickness` | 9,8 mm dla tego przebadanego przekroju |

Położenie okucia oraz jego obróbek wynika z tych samych parametrów. Transformacja
otworu uwzględnia układ lokalny części docelowej. Zmiana pozycji przez te parametry
działa również po zapisie/otwarciu ICS. **Swobodny ruch TriBallem nie ma jeszcze
obserwatora synchronizującego otwór** — może zerwać wyrażenia. Do edycji prototypu
używać parametrów sceny; automatyczny import ręcznych zmian pozostaje osobnym zadaniem.

Plan przypisuje obróbce `mount_key`, `target_id`, `template_id`, `stage_id` i
`through_target`. Etap obróbki jest etapem okucia, także dla gniazd w etapie 6.
To przygotowany kontrakt danych; istniejący zewnętrzny podgląd nie renderuje jeszcze
tych nowych ujemnych cech. Widok i dowód geometrii tej wersji są natywne w IronCAD.

## Pasowanie i granice

Zachowano przekrój EG-0500 i bazową odległość krawędzi sklejki 8,63 mm; to nie jest
luz pomiędzy metalowymi powierzchniami. Usunięto błędne przesunięcie poprzeczne
męskiego profilu o 1 mm. Żeński profil ma korektę osiową +0,05 mm. Kanał ma
9,5 mm: podfrezowanie po 0,2 mm z obu stron sklejki 9,8 mm zostawia język 9,4 mm.
Czoło ścian pokrywy skrócono o 0,1 mm, więc rzeczywista przerwa płyt wynosi
8,73 mm. Skrzynia nie została powiększona przez te operacje. Przerwy profili przy zamkach
i zawiasach są osobnymi obróbkami. Walidator odmawia innej grubości płyty i innej
szczeliny bez nowego pomiaru pasowania. Nie poszerza skrzyni i nie skaluje okuć.
Podfrezowania są obliczone dla tej pary profili; nie są uniwersalnym dopuszczeniem
wrębów/ukosów dla innych przekrojów.

Kontrola układu uwzględnia cały kołnierz uchwytu (161 × 107 mm), rezerwę 40 mm
przy krawędziach oraz rozstaw zamków i zawiasów. Jest to zachowawcza kontrola
montażu tego wariantu, nie pełna symulacja ruchu zawiasu czy otwarcia pokrywy.
Walidacja offline nie jest automatyczną blokadą dowolnej ręcznej edycji w IronCADzie.

## Dowody

Lokalne, ignorowane artefakty: `artifacts/roc41-native-20261026/`.

- `inspect-04`: odczyt aktualnego T1; okucia różnią się od wybranego prototypu.
- `inspect-saved`: odczyt zachowanej wersji z H7159 i 17251S.
- `build-full01`: historyczny pierwszy przyrost 24 cech.
- `build-full03`: aktualne 48 cech, pokrywa 115 mm, podfrezowania i korekta pasowania.
- `fit-full03`: PASS, brak przecięć w 26 jawnie sprawdzonych parach.
  Nie jest to twierdzenie o sprawdzeniu wszystkich możliwych par w złożeniu.
- `verify-full01`: A → B → A → ponowne otwarcie; pozycje 24 obróbek i 12 połówek/okuć,
  niezmieniona liczba ścian 11 obrobionych części.
- `verify-full02`: dodatkowa zmiana parametrów po ponownym otwarciu i powrót do A.
- `verify-final`: aktualny test A → B → A → ponowne otwarcie → B → A,
  68 pozycji, wymiary kieszeni i podfrezowań, topologia 13 części i 26 par pasowania
  w każdym wariancie. Wariant B: 720 × 560, korpus 320, pokrywa 125 mm, przesunięte okucia.
- Wszystkie własne robocze dokumenty zamknięte. Oryginały pozostały niezmienione;
  otwarty niezapisany DiGiCo nie był zapisywany ani zamykany.
- Finalny plik w `projekty/Epson_EB-L630U/Prototyp_05_pokrywa115_wyciecia/`
  w nadrzędnym obszarze roboczym, pokazany w IronCADzie wraz z zapisem widoku PNG.

Brak wdrożenia nowej wersji zainstalowanego dodatku, brak odbioru konstruktora,
brak certyfikacji produkcyjnej. Różowa skrzynia z odłączanymi pokrywami jest kolejnym
etapem zgodnie z poleceniem użytkownika.

## Sprawdzenie kodu

PASS: `scripts/Verify.ps1`, wszystkie siedem grup offline; dowód
`artifacts/verification/20261026T113912850394Z/results.json`.
Nowe testy obejmują przekształcenia układów, brak skalowania konturów,
powiązania etapów, kolizje kołnierzy, granice pokrywy i brak danych nowego SKU.
Pierwsze uruchomienie harnessu podczas zajętego mutexu CAD wykazało błędy
blokady; właściwy przebieg wykonano po zakończeniu operacji CAD.

Snapshot Git przed zmianą: `codex/snapshot-before-t1-machining-20261026`.
