# Profile i wzmocnienia — pełna skrzynia v2, 24.10.2026

Przyrost ROC-16/ROC-17: do nowej kopii skrzyni 2000 × 3000 × 4000 mm dodano
24 profile i 8 sztywnych wzmocnień. Pięć czystych źródłowych części katalogowych
wyeksportowano ze świeżej zapisanej rewizji Epson. Prywatne ID, macierze, eksporty
i hashe pozostają w `artifacts/profiles-2000x3000x4000-20261024-01/`.

## Kod i kontrakt

- `core_case/profile_rules.py`: jawne reguły 16 EG-0113, 4 EG-0500_1,
  4 EG-0500_2, 4 B1930 i 4 B1121. Właściwe obroty, symetria i kierunki cięcia.
  Ograniczony parser arytmetyki bez exec/eval.
- `scripts/extend_case_profiles.py`: przypięty hash skrzyni, raport i pięć assetów;
  ukryta praca wyłącznie na nowej kopii, blokada wykonawcy, zapis i ponowne otwarcie.
  Istniejący katalog wyjściowy jest odrzucany. Domyślnie PLAN ONLY; wykonanie
  wymaga `--native`. Jedna operacja zapisuje CAD.
- `core_case/test_profile_rules.py`: cztery testy niezależnych równań krawędzi,
  symetrii po resize, właściwych ram, sztywności wzmocnień i odmów.

Parametry nowego kontraktu `full_case_profiles_v2`: dotychczasowe sześć RP_*
oraz RP_JointGap, początkowo 8,63 mm. Nie zmieniono allowlisty starego adaptera,
MCP ani DLL. Szczelina konstrukcyjna jest oddzielna od RP_DisplayGap. Górne
ściany rozpoczynają się nad szczeliną; wysokość płyty wieka zmniejsza się o nią.
Obrys płyt zamkniętej skrzyni nadal ma 2000 × 3000 × 4000 mm.

EG-0113 ma przekrój 35 × 35 mm; zachowano przekroje obu EG-0500.
Po imporcie IZSizeBox.Reset(false) normalizuje współrzędne części. Konieczne
jest także jawne wyzerowanie lokalnej kotwy przez SetAnchorTransform przed
przypisaniem pozycji: PositionTransformComponentExpression opisuje pozycję
kotwy, a nie zawsze translację macierzy części. Pierwszy przebieg ujawnił ten
błąd; zmodyfikowaną kopię zachowano w `failed_case_firstpass`, bez PASS.

Wszystkie importy poprzedzają zapis zależności, bo potrafią zmieniać pamięć
podręczną zależności ICAPI. Po związaniu geometria aktualizuje się natywnie:
część HeightExpression steruje długością profilu, a równania pozycji utrzymują
jego środek na krawędzi. Wzmocnienia mają wyłącznie równania położenia.

## Bieżący dowód

Wynik użytkowy jest w workspace:
`projekty/Skrzynia_2000x3000x4000/Wersja_02_profile_parametryczne/`.
Główny plik: `RockPro_2000x3000x4000_profile_i_wzmocnienia.ics`.
Obok znajduje się `PROJEKT.md` i `profile_build_report.json`.

PASS natywny: parametry docelowe, resize X/Y/Z i szczeliny, powrót, zapis/otwarcie.
Sprawdzono wszystkie nowe 32 części, przekroje i orientacje, każdą płytę,
poprzednie kotwy okuć oraz obrys płyt. Zmiana parametrów nie przepisuje równań
ani położeń przez skrypt. Źródłowa skrzynia i pięć assetów pozostały niezmienione;
własne dokumenty operacji zamknięto. Następnie jawnie otwarto wynik do oglądania.

PASS offline: pełny harness w
`artifacts/verification/20261024T135734442404Z/results.json`.
Polecenie: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Verify.ps1 -Python .\Integracja\.venv\Scripts\python.exe`.

To prototyp, nie awans całego manifestu Epson ani odbiór produkcji. Reguły
końcówek zostawiają proste zakończenia i odsadzenia; dokładne styki, mocowania,
wycięcia oraz ocena nośności należą do dalszej technologii/ROC-41. Pozostałe
rodziny, w tym zawiasy i koła, pozostają kolejnymi etapami.
