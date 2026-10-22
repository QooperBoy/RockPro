# Koła i gniazda piętrowania — blokowany podgląd offline

**W0968Z / PN - W0968Z jest gniazdem (miseczką) pod koło**, nie kołem. Lokalny
`hardware-reference.json` i [katalog producenta Penn Elcom, 2019, str. 108](https://media.penn-elcom.com/pdf/Penn%20Elcom%20-%20European%20Catalogue%202019.pdf)
identyfikują miseczkę o obrysie 136×90 mm. Kod, producent i wariant zakupowy
czterech kół w CAD są **nieustalone**. Nie przypisujemy im kodu gniazda.

## Zapisane wystąpienia

Źródło: lokalny `artifacts/core-native/source-poses.json`; odczyt historyczny ze
zmodyfikowanego dokumentu, `disk_equivalence=not_proven`.

| Grupa | ID | Zapisane dane |
|---|---|---|
| Gniazda na pokrywie | 13226, 13231, 13236, 13241 | Cztery macierze i lokalne bbox |
| Koła, `Assembly1` pod zespołem `koła` 526 | 594, 678 | Dwie macierze i bbox |
| Pozostałe koła `Assembly1` | 9098, 9115 | Bbox istnieją, **macierze świata są null** po błędzie `improper ICAPI rotation` |
| Podkładki montażowe `Część33` | 695, 698 | Dwa osobne elementy; nie są kołami i nie tworzą par z gniazdami |

Środki światowych bbox gniazd tworzą pełny symetryczny prostokąt **611×433 mm**
w skrzyni 914×602 mm: marginesy X po **151,5 mm**, Y po **84,5 mm**. Uwzględniamy
duże niezerowe lokalne współrzędne importowanych gniazd; ich początek zespołu
nie jest środkiem geometrycznym ani potwierdzoną kotwą styku.

Nie ma dowodu czterech par koło–gniazdo. Dwa znane środki bbox kół wypadają w
przednich ćwiartkach. W porównaniu ze środkami bbox odpowiednich gniazd różnią
się w X około **+12,766 mm** i **−14,841 mm**, a w Y około **−14,638 mm**.
To różnice **kandydatów opartych na bbox**, nie dowód fizycznego niedopasowania:
środek bbox całego skrętnego koła nie musi być jego punktem podparcia.
Źródłowych różnic nie uśredniamy ani nie naprawiamy przesunięciem.

## Czysty podgląd

`wheels_sockets.preview_wheels_sockets(wheel_rows, socket_rows, case_min,
source_size, target_size)` używa wyłącznie ID, całej macierzy i lokalnego bbox.
Macierze są w konwencji wektorów wierszowych; osie świata i skrzyni są zgodne,
wszystkie długości w mm. Brakujące macierze kół pozostają brakujące.

Reguła przewidywania zachowuje orientację i gabaryt: delta XY wynika z ćwiartki
i zmiany szerokości/głębokości. Gniazda dodatkowo przesuwają się o ΔH, koła
zachowują wysokość względem niezmiennej podłogi. Pełna symetria gniazd jest
sprawdzana przez odbicie kompletnych współrzędnych względem każdej osi X/Y.
Zapisane indywidualne offsety pozostają zachowane.

Wynik ma zawsze `status=blocked`, `occurrences=[]` i `production_approved=false`.
`predicted_occurrences` pokazuje tylko znane całe elementy, a `candidate_pairs`
to niezatwierdzone skojarzenia ćwiartek bbox. Nie tworzymy brakujących macierzy,
kotew styku ani czterech sztucznych potwierdzonych par. Nie obliczamy nośności,
otworów, BRep, promienia koła ani ruchu skrętnego.

```powershell
& '..\Integracja\.venv\Scripts\python.exe' scripts/preview_wheels_sockets.py `
  --poses artifacts/core-native/source-poses.json `
  --catalog docs/catalog/hardware-reference.json `
  --case-min 558.0497847073995 896.4261794940822 -1503.0399167133687 `
  --source-size 914 602 352 --target-size 1100 720 410 `
  --output artifacts/wheels-sockets-offline-B.json
```

CLI czyta tylko jawne ścieżki wejściowe i zapisuje wyłącznie nowy plik. Nie
otwiera ścieżek osadzonych w JSON ani dokumentów CAD.

## Dowody i następny krok

- **PASS offline:** trzy smoke testy: brakujące macierze bez zgadywania,
  przewidywany resize i zachowanie orientacji, odmowa błędnego/asymetrycznego
  wejścia. Polecenie: `python -m unittest discover -s Integracja/rockpro_cad/core_case
  -p 'test_wheels_sockets.py' -v`; raport `artifacts/wheels-sockets-smoke.txt`.
- **Braki:** świeże cztery macierze kół z zachowaną surową parzystością,
  identyfikacja kół, jawne lokalne kotwy X/Y styku oraz cztery mapowania par,
  powiązanie ze źródłem. Dopiero te dane pozwolą ocenić wspólne kotwy i symetrię
  pełnego zbioru. Podkładki pozostają osobnym zakresem, bez pomijania ich w BOM.
- **NOT RUN:** świeży odczyt CAD, kopiowanie, resize i zapis/otwarcie ICS.
  Podgląd nie zatwierdza dopasowania, stateczności ani gotowości produkcyjnej.

Dane klienta i wyniki JSON pozostają lokalnie w ignorowanym `artifacts/`.
