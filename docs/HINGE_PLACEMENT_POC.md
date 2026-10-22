# Kandydat zawiasów 270836 — podgląd offline

**B1930 jest kątownikiem wzmacniającym, nie zawiasem.** Potwierdzają to lokalny
`docs/catalog/hardware-reference.json`, mapa rodzin w `manifest.py` oraz
[oficjalny katalog Penn Elcom](https://www.penn-elcom.com/4-hole-brace-with-strengthening-ribs-355mm-x-40mm-b1930).
Historyczny `source-poses.json` zawiera dwa zespoły B1930: 9439 `[0,5]` i 9427
`[1,5]`, po dwie części. Nie tworzą one czterech połówek zawiasów. CLI dla B1930
zwraca `PART_IS_BRACE_NOT_HINGE`, bez planu montażu.

Właściwy wpis katalogu to **270836 / 270836_góra**, zawias z ogranicznikiem
pokrywy. Zapisane cztery zespoły:

| Strona | Pokrywa | Baza | Wspólny początek świata XYZ [mm] |
|---|---|---|---|
| Lewa | 13076 `[0,11]` | 13075 `[1,13]` | 712,866795; 1509,135984; −1262,789917 |
| Prawa | 12953 `[0,10]` | 12952 `[1,12]` | 1326,866794; 1509,135984; −1262,789917 |

Początki nie są symetryczne względem środka skrzyni. Rzeczywiste środki lokalnych
bbox mają przesunięcie X około **−4,8170105 mm**. Po transformacji środki całych
złożeń są symetryczne; planer zachowuje ten jawny offset i niczego nie uśrednia.
Nie utożsamiamy środka bbox z osią obrotu zawiasu ani potwierdzonym stykiem.

## Mały planer

`hinge_placement.plan_hinge_pairs(source_rows, case_min, source_size, target_size,
source_lid_height=104.13, source_pose_verified=False)` przyjmuje cztery wiersze
`id`, `role` (`lid`/`base`), `side` (`left`/`right`), `matrix_world_mm`,
`local_bounds_mm` (minXYZ + maxXYZ). Długości są w mm, macierze używają wektorów
wierszowych i translacji w ostatnim wierszu. Rama skrzyni jest osiowa w świecie.

Obie połówki każdej pary dostają wspólną translację: lewa `[0,ΔD,ΔH]`, prawa
`[ΔW,ΔD,ΔH]`, przy stałej wysokości pokrywy. Przed i po zmianie sprawdzane są
symetria całych środków bbox, wspólny początek danej pary i sztywność macierzy.
Plan zachowuje źródłowe orientacje oraz indywidualne offsety. Nie ma odczytu BRep,
otworów, śrub ani szkiców. Nie rozwiązuje ruchu otwierania i kolizji mechanizmu.

Domyślnie wynik ma `status=blocked`, `occurrences=[]`, a przewidywane pozycje są
w `predicted_occurrences`. `source_pose_verified=True` jest jawnym oświadczeniem
wywołującego wymagającym niezależnego dowodu surowych orientacji i parzystości.
CLI nigdy nie ustawia tej flagi dla obecnego historycznego formatu. Niezależnie
od niej `production_approved=false` i `native_proof=NOT_RUN`.

## Powtarzalny podgląd bez CAD

```powershell
& '..\Integracja\.venv\Scripts\python.exe' scripts/preview_hinge_placement.py `
  --poses artifacts/core-native/source-poses.json `
  --catalog docs/catalog/hardware-reference.json --part-code 270836 `
  --case-min 558.0497847073995 896.4261794940822 -1503.0399167133687 `
  --source-size 914 602 352 --target-size 1100 720 410 `
  --output artifacts/hinge270836-offline-B.json
```

`--part-code B1930` daje podgląd odmowy błędnej klasyfikacji. Wejścia to wyłącznie
jawne ścieżki argumentów. Program nie otwiera ścieżek zapisanych wewnątrz JSON i
zapisuje wyłącznie nowy plik, odmawiając nadpisania.

## Dowody i konkretne braki

- **PASS offline:** trzy smoke testy: identyczny rozmiar z domyślną blokadą,
  wspólny resize par i symetria bbox, odmowa błędnych/asymetrycznych wejść.
  `python -m unittest discover -s Integracja/rockpro_cad/core_case -p
  'test_hinge_placement.py' -v`; raport `artifacts/hinge-placement-smoke.txt`.
- Zapis CAD pochodzi ze zmodyfikowanego dokumentu w pamięci;
  `disk_equivalence=not_proven`. Połówki bazowe mają ostrzeżenia starego czytnika
  `improper ICAPI rotation` dla macierzy rodzica. Zapisane macierze świata nie
  dowodzą zachowania surowej parzystości; podgląd nie usuwa tych ostrzeżeń.
- Potrzebne przed aktywnym montażem: świeże macierze świata z zachowaną
  parzystością i jednoznaczne powiązanie odczytu ze źródłem. Następnie osobny aktor
  natywny wykonuje kopię, podstawową kontrolę rozmieszczenia oraz zapis/otwarcie.
- **NOT RUN:** świeży odczyt, natywne kopiowanie, resize i zapis/otwarcie ICS.
  Podgląd historyczny nie zatwierdza całego modelu ani szablonu produkcyjnego.

Dane klienta i wygenerowane raporty pozostają lokalnie w ignorowanym `artifacts/`.
