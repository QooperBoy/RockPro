# Modele producenta w Studio

Stan 28.10.2026: wszystkie 74 pobrane modele mają podgląd siatkowy i miniaturę.
81 definicji zachowuje odrębne warianty/rekordy katalogowe. Dane są wersjonowane
w `assets/supplier-parts/`; Studio i paczka Vercel korzystają z tego samego indeksu.
Oryginalne STEP/ZIP pozostają w lokalnej bibliotece `biblioteka_czesci/CAD_producenci`
workspace Ironcad. Do Git trafiają siatki i miniatury, nie archiwa klientów ani Excel.

W kroku 4 filtr „Modele 3D producenta — STEP” pokazuje gotowe pozycje. Po wybraniu
okucia można rozmieszczać je w kroku 5, a zawiasy i zamki również na złączach
w kroku 6. Podgląd używa całej geometrii produktu w metrach, bez skalowania okuć.
Siatki są ładowane na żądanie, sprawdzane SHA256 i dekompresowane w przeglądarce.
Zapis draftu przechowuje stabilne ID oraz rewizję definicji; modele nie są
wklejane do każdego JSON projektu. Brak/błąd siatki nadal wywołuje komunikat.

Zgodny kod zachowuje ID z katalogu firmowego. Rozbieżność kodu lub wariantu
tworzy osobne ID `supplier-*` z faktycznym kodem CAD producenta. Nie przypisuje
mu automatycznie ceny ani stanu innej pozycji. Rewizje istniejących draftów
pozostają dostępne. Dwa wcześniejsze przybliżenia (narożnik i wentylacja) mają
już rzeczywistą siatkę zamiast bryły koncepcyjnej.

Rama montażowa jest propozycją do podglądu. Pobrany model nie zatwierdza
orientacji montażowej, wycięcia, kinematyki ani produkcji. Materiały i niedostępne
modele Adam Hall nie zostały zastąpione podobnymi częściami Penn Elcom.

## Odtwarzanie

Konwersja działa w osobnym procesie OpenCascade, bez uruchamiania lub łączenia
z IronCAD. Opcjonalne środowisko narzędziowe: `cadquery-ocp==7.8.1.1` i Pillow;
nie jest zależnością serwera Studio. Polecenie:

```powershell
python scripts/prepare_supplier_meshes.py MANIFEST_LOKALNEJ_BIBLIOTEKI.json assets/supplier-parts
```

P2558 ma jedną powierzchnię, której OpenCascade nie triangulował. Dla tego
samego ID producenta 1044533 pobrano oficjalny eksport STL, zamiast pomijać
powierzchnię. Wszystkie trzy gabaryty sprawdzono z dokładnym obrysem STEP
(tolerancja 0,25 mm, bez skalowania; eksport ma przesunięty początek układu).
Opcja `--fallback-stl DOWOD.json` przyjmuje lokalny zapis pobrania z polami
`model_id` i `path` do ZIP producenta. Indeks zachowuje SHA STEP i dodatkowego STL.
Oryginały pozostają niezmienione. Nie rekonstruowano brakującej powierzchni AI.

Pochodzenie i prawa: modele Penn Elcom z jego zweryfikowanego katalogu
3D ContentCentral; bez zmiany właściciela praw i bez automatycznego
przelicencjonowania. Każda definicja zawiera publiczny link modelu i SHA wejścia.

## Sprawdzenie

- Pełny harness offline PASS: `artifacts/verification/20261028T221125627066Z/`.
- E2E przeglądarki PASS: wszystkie 74 siatki, 81 definicji, 2 441 821 trójkątów;
  dodawanie wystąpienia w kroku 5, zmiana wymiarów oraz zapis i odczyt draftu.
- Dowody: `artifacts/supplier-studio-check/result.json` i zrzuty podglądu.
- Natywny CAD: NOT RUN, zmiana dotyczy Studio i pobranych zasobów.

Test: `node scripts/test_supplier_studio.cjs http://127.0.0.1:PORT` z Playwright
dostępnym w `NODE_PATH`. Test uruchamia osobny kontekst przeglądarki i nie zmienia
otwartego projektu użytkownika. Produkcyjna paczka powstaje zwykłym
`scripts/build_vercel_studio.py --output artifacts/NOWE_WYDANIE`.
