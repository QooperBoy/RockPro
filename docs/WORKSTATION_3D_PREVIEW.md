# Workstation — interaktywny podgląd z modelu źródłowego

27.10.2026. Rozwinięcie [Studio wzorców](REFERENCE_STUDIO_PROTOTYPE.md).

## Co działa

- Rzeczywiste siatki 453 części modelu M04, około 852 tys. trójkątów, z kolorami
  źródła. Bez zastępowania okuć prostopadłościanami.
- Obrót, zoom, dopasowanie kamery, ukrywanie/pokazywanie osłon.
- Cztery osobne suwaki prezentacyjnego wysuwu 0–500 mm, wspólne wysunięcie
  i schowanie oraz powrót do źródłowych wymiarów.
- Każdy moduł łączy siedem części szuflady i cztery części wkładu z właściwego
  poziomu. Ruch obu poddrzew jest wspólny. Rozpoznanie nie opiera się na kolorze.
- Zmiana zewnętrznego obrysu sklejki w zakresie 80–140% wzorca. Wzorzec ma
  około 792 × 739,096 × 876,852 mm w osiach źródła. Koła nie wchodzą w ten obrys.
- Sztywne okucia przesuwają się bez skalowania; profile zmieniają długość przy
  stałym przekroju; płyty zmieniają dwa wymiary przy zachowaniu grubości.
- Opcjonalny stan podglądu w szkicu JSON: gabaryt, cztery wysuwy i widoczność
  osłon, przypięte do tego samego SHA źródła. Starszy szkic bez niego nadal działa.

## Znaczenie wymiarów i granica dowodu

To podgląd koncepcji oparty na geometrii źródła. Przekształcenie siatek nie jest
przeliczeniem historii CAD: kontury otworów, dokładne złącza, prowadnice i kolizje
wymagają osobnego planu i wykonawcy. Zakres 80–140% służy temu prototypowi, nie
jest zatwierdzonym zakresem konstrukcyjnym. Zakres wysuwu również nie potwierdza
skoku fizycznych prowadnic, nośności ani bezpieczeństwa przy otwartych półkach.

Wymiary w polu podglądu dotyczą obrysu sklejki. Formularz po prawej nadal zapisuje
wymagane wolne wnętrze; nie deklarujemy, że wystawione wymaganie już mieści się
we wszystkich komorach. Nie mylić tych dwóch zestawów wartości.

Użytkownik potwierdził funkcję wysuwanych półek. Mapowanie czterech zespołów,
wkładów i osi −Y wynika z ich hierarchii, poziomów oraz płaszczyzn frontów;
jest roboczym mapowaniem podglądu, nie zatwierdzeniem mechanizmu produkcyjnego.
Wszystkie prywatne ścieżki, ID i przypięcia pozostają w `artifacts/`.

## Przygotowanie i uruchomienie

`scripts/native/ExportReferenceMeshes.cs` eksportuje Web Viewer z nowej kopii
tylko do odczytu w jawnie sprawdzonym procesie. Nie wywołuje Save/Update ani
regeneracji. Sprawdza hash źródła, kopii oraz zachowanie istniejących dokumentów.
Używa istniejącego developerskiego mostu i globalnej blokady wykonawcy CAD.

`scripts/prepare_workstation_preview.py` przyjmuje eksport, jego raport,
inwentarz oraz jawne mapowanie i tworzy nowy folder `model.json/geometry.bin`.
Sprawdza hashe, ścieżki hierarchii, macierze i kompletność siatek. Eksporter usuwa
myślniki/podkreślenia z niektórych etykiet; wiązanie zachowuje natywne ID,
hierarchię i ramy, a zgodność nazw uwzględnia tylko tę konkretną normalizację.

Z katalogu `Integracja`:

```powershell
.\.venv\Scripts\python.exe -m rockpro_cad.reference_studio --bundle "<pakiet wzorców>" --workstation "<folder model.json i geometry.bin>"
```

Siatki i dane klienta są lokalne; nie trafiają do Gita ani zewnętrznego serwera.
Poprzedni tryb Studio bez argumentu `--workstation` nadal udostępnia galerię.

## Sprawdzenia

- PASS: eksport SDK 2027 API 29.0.2.20605, źródło/kopia niezmienione, kontekst
  zachowany, własna kopia zamknięta, brak zapisu ICS. Pierwsza próba odrzucona
  przez kontrolę PID przed otwarciem źródła; dowód odmowy zachowano.
- Testy Python: `python -m unittest rockpro_cad.mcp.test_reference_studio -v`.
- Reguły przekształceń: `node scripts/test_workstation_preview.mjs` z repozytorium.
- Testy przeglądarki sprawdzają siatki i ruch; nie zastępują testów przebudowy CAD.

PASS: 8 testów Python/HTTP oraz reguły geometrii JavaScript. PASS próba WebGL
w Chrome: 453 siatki, cztery moduły po 11 części, gabaryt 892 × 800 × 950 mm,
brak zmiany skali 363 sztywnych części, ruch tylko wybranej półki o 300 mm,
osłony, powrót macierzy do wzorca, odtworzenie podglądu z JSON i szerokość mobilna.
Brak błędów konsoli. Raport: `browser-result.json` i obrazy `preview-extended.png`
oraz `preview-mobile.png` w podanym niżej katalogu dowodów.

Dowody prywatne: `artifacts/workstation-3d-20261027/`.
Native resize/save/reopen dla M04: NOT RUN — ten przyrost nie modyfikuje CAD.
