# Profile i wzmocnienia — inwentarz offline

Źródło: zapisane `artifacts/core-native/source-poses.json` oraz istniejący
[katalog części](catalog/hardware-reference.json). Reguły zmiany długości i
sztywnego ruchu odpowiadają [założeniom rdzenia](CORE_CASE_DESIGN.md).
Bez odczytu CAD, bez projektowania
przekrojów, otworów ani historii części.

| Kod katalogowy / nazwa CAD | Zespoły | Fizyczne części | Dostępne macierze świata | Polityka docelowa |
|---|---:|---:|---:|---|
| EG-0500/1 / EG-0500_1 | 1 | 4 | 4 | Długość cięcia zmienna, przekrój zachowany |
| EG-0500/2 / EG-0500_2 | 1 | 4 | 4 | Długość cięcia zmienna, przekrój zachowany |
| EG-0113 | 2 | 16 | 8 | Długość cięcia zmienna, przekrój zachowany |
| B1930 | 2 | 4 | 2 | Całe sztywne okucie, bez skalowania |

Łącznie **28 części fizycznych w sześciu zespołach**. Nie liczymy kontenerów jako
dodatkowych części. B1930 to kątownik wzmacniający, nie profil do wydłużania i nie
zawias. EG-0500/1 i /2 tworzą katalogową parę pióro–rowek; identyfikacja nazwy nie
potwierdza przekroju konkretnej geometrii ani styku w źródle.

## Uzupełnienie źródeł producenta — 22.10.2026

Oznaczenia EG-0500/1, EG-0500/2 i EG-0113 występują w oficjalnych produktach
Penn Elcom; nie są wyłącznie kodami wewnętrznymi tego CAD. Poniższe dane są
nominałami katalogowymi, nie pomiarem źródłowych części ani wyborem długości
zakupowej. Sufiksy CAD `_1`/`_2` nadal wymagają powiązania z konkretnym przekrojem.

| Potwierdzona strona produktu | Dodatkowe dane przekroju na stronie producenta | Opublikowany odnośnik modelu |
|---|---|---|
| [EG-0500/1-2M — pióro](https://www.penn-elcom.com/pl_en/9-5mm-tongue-extrusion-mates-with-eg-0500-2-2m-groove-extrusion-eg-0500-1-2m) | Otwarcie 9,5 mm, głębokość otwarcia 18,5 mm, grubość 1,5 mm, ramię 20 mm; odcinek 2 m. Jawnie parowany z EG-0500/2-2M. | [View 3D Drawing](https://www.3dcontentcentral.com/download-model.aspx?catalogid=6237&id=944122) |
| [EG-0500/2-2M — rowek](https://www.penn-elcom.com/lc/9-5mm-groove-extrusion-mates-with-eg-0500-1-2m-tongue-extrusion-eg-0500-2-2m) | Otwarcie 9,5 mm, głębokość otwarcia 16,5 mm, grubość 1,5 mm, ramię 20 mm; odcinek 2 m. Jawnie parowany z EG-0500/1-2M. | [View 3D Drawing](https://www.3dcontentcentral.com/download-model.aspx?catalogid=6237&id=943659) |
| [EG-0113-2M — kątownik](https://www.penn-elcom.com/cn/single-angle-extrusion-with-35mm-legs-2m-long-eg-0113-2m) | Ramiona 35 mm, promień 2 mm, odcinek 2 m. Promień nie oznacza grubości ścianki. | [View 3D Drawing](https://www.3dcontentcentral.com/download-model.aspx?catalogid=6237&id=939958) |

Linki modeli pochodzą bezpośrednio z kart producenta. Próba ich odczytu zakończyła
się odpowiedzią 502 lub brakiem dostępnej kopii w narzędziu przeglądania; **nie
pobrano i nie zweryfikowano pełnego przekroju ani modelu 2D/3D**. Same tabele
wymiarów nie opisują wszystkich promieni, rowków i tolerancji. Znalezienie tych
źródeł nie usuwa blokady osi cięcia, styku ani kotew źródłowego CAD i nie zmienia
statusu katalogu na zatwierdzony do automatycznego montażu.

## Co wiadomo, czego nie wolno zgadnąć

Każda połówka EG-0500 ma w lokalnym bbox dwa odcinki o rozpiętości Z około
914 mm i dwa około 596 mm. To **rozpiętości współrzędnej bbox**, nie dowód osi
wyciągnięcia, długości między płaszczyznami cięcia ani sposobu wykonania naroży.
Nie podstawiamy automatycznie wymiaru skrzyni jako długości cięcia.

EG-0113 ma różne zapisane odcinki, m.in. w pokrywie 542, 845,611, 854 i 48,148688 mm,
a w bazie 536, 884, 895 i 188,842 mm (rozpiętości lokalnego Z bbox). Nazwa nie
uprawnia do zrównania tych wartości. Bez przypisania części do krawędzi nie
rozstrzygamy, czy różnica wynika z cięcia, ręcznej zmiany lub konkretnej roli.

Brakuje macierzy EG-0113: **9028, 9031, 9037, 9043, 9053, 9056, 9065, 9071**;
B1930: **9437, 9446**. Stary czytnik zgłosił `improper ICAPI rotation` i nie
zapisał tych macierzy. Pozostałe zapisane macierze nie dowodzą zachowania surowej
parzystości całego źródła. Dokument był zmodyfikowany w pamięci, a zgodność ze
źródłem dyskowym ma status `not_proven`.

## Kotwy i reguła resize

Podgląd wylicza 12 **kandydatów krawędzi zewnętrznego obrysu skrzyni** na podstawie
jawnego minimum XYZ i rozmiaru: cztery wzdłuż każdej osi. Dla każdej podaje ID,
oś oraz oba końce źródłowe i docelowe. To przecięcia płaszczyzn obrysu, a nie
potwierdzone linie kontaktu profili z płytami.

Każda część pozostaje z `edge_binding=null`, `confirmed_cut_axis=null` oraz
`target_cut_length_mm=null`. Aby powiązać profil z krawędzią, potrzeba jawnie:

- ID krawędzi i orientacji przekroju względem ścian;
- osi długości profilu i obu datumów końców, w tym odsunięć/cięć naroży;
- parametru długości lub potwierdzonej metody zmiany całego odcinka przy stałym przekroju;
- dla EG-0500: poziomu i parowania wspólnego interfejsu zamknięcia.

Wtedy długość odcinka wynika z datumów krawędzi i stałych odsunięć końców, a
nie ze skalowania trzech osi. Przekrój i jego rozmiary pozostają zachowane.
B1930 otrzymuje wyłącznie sztywny ruch od potwierdzonej kotwy. Jego zespołowy bbox
obejmuje dwie rozstawione sztuki; nie jest rozmiarem pojedynczego kątownika.

## Uruchomienie i wynik

```powershell
& '..\Integracja\.venv\Scripts\python.exe' scripts/preview_profile_inventory.py `
  --poses artifacts/core-native/source-poses.json `
  --catalog docs/catalog/hardware-reference.json `
  --case-min 558.0497847073995 896.4261794940822 -1503.0399167133687 `
  --source-size 914 602 352 --target-size 1100 720 410 `
  --output artifacts/profiles-braces-offline-B.json
```

Program czyta wyłącznie jawne pliki wejściowe; nie używa ścieżek osadzonych w JSON.
Zapisuje wyłącznie nowy plik i nie nadpisuje wcześniejszych wyników. Wynik ma
`status=blocked`, `occurrences=[]`, `production_approved=false`; nie generuje
geometrii. Raport zawiera inwentarz, polityki, brakujące macierze, źródłowe bbox,
ostrzeżenia oraz niepowiązane kandydaty krawędzi.

**PASS offline:** jedno wykonanie na zapisanym raporcie: 28 części, sześć
kontenerów, dziesięć brakujących macierzy, 12 kandydatów krawędzi. Bez nowej
rozbudowanej suite. **NOT RUN:** świeży odczyt CAD, zmiana długości profilu,
montaż wzmocnień i zapis/otwarcie ICS. Brakujące dowody blokują resize tych części.

Dane klienta i pełne wyniki pozostają lokalnie w ignorowanym `artifacts/`.
