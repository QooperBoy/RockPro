> Aktualizacja 31.10.2026: użytkownik wycofał parametryzację liczby okuć.
> Pola liczności opisane poniżej dotyczą zachowanych modeli historycznych.
> Nie rozwijać ani nie przenosić tego mechanizmu do nowych modeli. Wymiary,
> położenie i powiązane wycięcia pozostają w zakresie. Patrz CASE_DEFAULTS.md.

# R005 — przenoszenie okuć razem z wycięciami

## Zakres

Hisense w IronCAD 2027, na nowej kopii R004. Sześć przenośnych rzędów:
UchwytyA/B/C/D oraz ZamkiA/B. H7159 i kompletne pary L905/915 pozostają sztywne.
Obróbki wykorzystują istniejące kontury konstruktora, bez rysowania zastępczych
prostokątów i bez skalowania SKU. Inny SKU/model wymaga sprawdzonej mapy ścian
oraz jego własnych obróbek; polecenie prepare nie jest importerem dowolnego ICS.

Wzorzec montażu odczytano z oficjalnej dokumentacji
[SmartAssembly Positioning](https://www.ironcad.com/support/2024/IRONCAD_Help/Content/3D_Design_Environment/Positioning_Objects/SmartAssembly_Positioning.htm)
i [Using the API](https://www.ironcad.com/support/2024/IRONCAD_Help/Content/Understanding_the_Basics/Using_the_API.htm),
a dostępne sygnatury sprawdzono w zainstalowanym SDK 2027. Implementacja używa
własnych ram i kontrolera ICAPI; nie tworzy natywnych więzów SmartAssembly.

## Parametry w tabeli sceny

| Pole dla uchwytów A (analogicznie B–D) | Znaczenie |
| --- | --- |
| RP_UchwytyA_Sciana | 1 przód, 2 tył, 3 lewa, 4 prawa, 5 góra, 6 dno |
| RP_UchwytyA_Sekcja | 1 korpus, 2 czapka; góra wymaga 2, dno wymaga 1 |
| RP_UchwytyA_Liczba | 0–4 całych okuć w tym rzędzie, dodatkowo ograniczone miejscem |
| RP_UchwytyA_SrodekU | Środek rzędu na wybranej ścianie [mm] |
| RP_UchwytyA_Rozstaw | Rozstaw skrajnych osi [mm]; 1 sztuka jest w środku |
| RP_UchwytyA_PozycjaV | Wysokość na pionowej ściance lub druga współrzędna góry/dna [mm] |

ZamkiA/B mają Sciana, Liczba, SrodekU, Rozstaw oraz Pion. Nie mają selektora
sekcji: jedna para łączy korpus i czapkę. Dopuszczalne są pionowe złącza 1–4;
zatrzask na środku górnej płyty bez złącza jest odrzucany. Pion to odsunięcie
od rzeczywistej linii styku. Dopuszczalne odsunięcie pionowe ogranicza połowa aktualnej szczeliny między sklejkami (w tym przykładzie około ±4,32 mm). Każda para obejmuje dwie połówki i osiem obróbek.

Liczba dotyczy **rzędu**, nie sumy wszystkich okuć na ścianie. Historyczne dwa
uchwyty z przodu/tyłu oraz trzy oryginalne zamki na tych złączach pozostają
osobnymi rzędami; są uwzględniane jako przeszkody. W przykładzie przód ma
2 oryginalne + 3 uchwyty A, a tył 3 oryginalne + 2 zamki A. Nie przedstawiaj
wartości Liczba=3 jako łącznej liczby wszystkich uchwytów na tej ścianie.

Dawne parametry nazwane Lewa/Prawa są zachowane dla historii. Dawne pola liczby
są aliasami nowych rzędów, a nie selektorami ścian. Steruj polami RP_UchwytyA_*
itd.; nie edytuj historycznych aliasów zamiast nowych kontrolek.

## Kierunki U/V

| Ściana | U | V |
| --- | --- | --- |
| Przód | w prawo / +X | w górę / +Z |
| Tył | w prawo patrząc z tyłu / −X | w górę / +Z |
| Lewa | od tyłu ku przodowi / −Y | w górę / +Z |
| Prawa | od przodu w głąb / +Y | w górę / +Z |
| Góra | od lewej do prawej / +X | od przodu w głąb / +Y |
| Dno | od lewej do prawej / +X | od tyłu ku przodowi / −Y |

U odnosi się do obrysu skrzyni. V pionowej ściany jest liczone od dolnej krawędzi
jej sklejki; Pion zamków od złącza. Kamera nie zmienia znaczenia ścian.

## Mini skrypt

Z katalogu źródła, w istniejącym venv:

```powershell
Integracja/.venv/Scripts/python.exe scripts/remap_tv_mounts.py set --model "C:/pelna/sciezka/RockPro_Hisense85_r005_sciany_IC2027.ics" --row UchwytyA --wall przod --section 1 --count 3 --u 1011.5 --v 200 --spread 500
```

Drugi przykład — jeden uchwyt w górnej płycie:

```powershell
Integracja/.venv/Scripts/python.exe scripts/remap_tv_mounts.py set --model "C:/pelna/sciezka/RockPro_Hisense85_r005_sciany_IC2027.ics" --row UchwytyA --wall gora --section 2 --count 1 --u 600 --v 386
```

Skrypt wybiera jedyny proces 2027; opcjonalny --pid podaje się przed set/prepare.
Zmienia tylko jawnie dozwolone parametry w otwartej kopii, bez ręcznego Apply.
Działający kontroler przelicza geometrię. Zapis pliku wykonaj po sprawdzeniu
przez Ctrl+S. Sam wynik set oznacza przyjęcie parametrów, nie odbiór montażu;
sprawdź RP_IloscOkuc_Status.

Jednorazowe przygotowanie nowej kopii znanego R004:

```powershell
Integracja/.venv/Scripts/python.exe scripts/remap_tv_mounts.py prepare --source "C:/pelna/sciezka/RockPro_Hisense85_r004_montaz_IC2027.ics" --output "C:/pelna/sciezka/nowa_kopia.ics"
```

Źródło i jego niezapisane zmiany trafiają do nowego snapshotu. Wynik prepare
ma status CONSTRUCTED_NEEDS_NATIVE_TESTS; testy w hoście są osobnym etapem.
Wykonanie wymaga SDK i kontrolera zbudowanego przez Build-MountCounts.ps1
-OutputFolder bin-counts-v10f-2027. Instalacja: Install-MountCounts.ps1
-BinaryFolder bin-counts-v10f-2027, po zapisaniu i zamknięciu dokumentów.

## Mechanizm

Manifest v3 opisuje ramy ścian, stabilne ID docelowych sklejek/profili,
instancje całych okuć i lokalne wzorce obróbek. Kontury CopyCurvesTo są
przygotowywane we właściwych częściach, a ich wystąpienia przełączane przy
zmianie ściany. Stara sklejka odzyskuje materiał; nowa otrzymuje otwór. Zamki
przełączają też przerwy obu profili. Rezerwowych wygaszonych operacji nie liczymy
jako aktywnego BOM. Wygaszenie i pozycja należą do jednej recepty montażowej.

Kontroler sprawdza pojemność, rzeczywisty rozstaw, margines 35 mm, odstępy
12 mm, wysokość oraz znane obrysy uchwytów/zamków. Odrzucony rząd zachowuje
ostatni poprawny stan i nadal jest przeszkodą dla pozostałych. Zero wygasza
okucia i wszystkie związane wycięcia. To kontrola znanych obrysów montażowych,
nie pełny solver kolizji BRep ani zatwierdzenie nośności/CNC.

## Dowody

- artifacts/tv-wall-mounts-20261030T221544106900Z: konstrukcja kopii i snapshot.
- artifacts/tv-wall-check-01: sześć ścian uchwytu, cztery złącza zamka, pomiar
  usuniętej objętości sklejki/profili, właściciele otworów, kontury, gabaryty,
  zapis/otwarcie i przykład z kilkoma rzędami — PASS.
- artifacts/tv-wall-guards-02: kolizje, brak powierzchni/złącza, limit fizyczny
  i limit wystąpień; odrzucone rzędy zachowały położenie i wycięcia — PASS.
- Test-WallMountMath.ps1: 16 prób obliczeń bez CAD — PASS.
- artifacts/verification/20261030T222528983131Z: siedem grup offline — PASS.

Autostart i późniejszą zmianę wyłącznie parametrów zapisuj oddzielnie od
powyższych prób bezpośredniego Apply.


Końcowe blokady z kontrolerem 0.10: `artifacts/tv-wall-guards-04` — PASS,
w tym wyjście zamka poza strefę pionową złącza. Poprawka etykiet ogranicza
zmiany nazw do całych części i zespołów; importowane obiekty wewnętrzne
historii nie muszą obsługiwać zmiany Name. Nieudany przebieg guards-03
zachowano jako diagnostykę tego błędu; guards-04 po poprawce przeszedł.
Końcowy zestaw offline: `artifacts/verification/20261030T224106964744Z` — PASS.
Autostart końcowej kompilacji w nowym PID 27564: `tv-wall-startup-final` — PASS,
bez ręcznego Load/Start. Mini skrypt sam wykrył hosta i przeniósł rząd A na górę;
`tv-wall-live-roof-read` potwierdza jedną sztukę, otwór w płycie 11171 i rzeczywistą
macierz okucia, bez ręcznego Apply/Start. Następnie przywrócono przykład z przodem.

Końcowy zapis `tv-wall-final-visible`: PASS, 88 parametrów, rzeczywiste macierze zgodne, status OK. Ukryto szkice pomocnicze obróbek; zachowano natywne kontury. Przykład A: przód/korpus/3; przykład ZamkiA: tył/2.

Dodatkowo `tv-wall-old-panel-restored.json`: poprzednia płyta lewa 11201 po przeniesieniu A ma pełną objętość prostopadłościanu (różnica <0,01 mm³). To niezależny pomiar odzyskania materiału, nie sam odczyt flag wygaszenia.
