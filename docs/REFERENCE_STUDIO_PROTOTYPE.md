# Studio wzorców — pierwszy prototyp konfiguratora

Aktualizacja: workstation ma teraz [interaktywny podgląd 3D](WORKSTATION_3D_PREVIEW.md)
z rzeczywistych siatek, zmianą gabarytu i czterema wysuwanymi modułami.
Poniższe ograniczenia dotyczą pierwszego przyrostu galerii; pozostałe rodziny
nadal pokazują obrazy wzorców.

27.10.2026. Podstawa: siedem odczytanych modeli, pogrupowanych w sześć kandydatów
rodzin. M01/M07 to dwa oddzielne warianty ekranów, bez zatwierdzenia zamienności.
Pozostałe: mikser M02, wciągarki M03, workstation M04, wiele gniazd M05 i głowy M06.

Potwierdzenie użytkownika 27.10.2026: czerwone elementy wskazane na obrazie
workstation to wysuwane półki. Zapisujemy tę funkcję jako potwierdzoną przez
użytkownika, bez automatycznego rozpoznawania innych czerwonych części.
Liczba półek, osie prowadnic, poziomy, fizyczny skok, blokady i obciążenia
pozostają do mapowania. Formularz workstation zapisuje opcjonalnie żądaną
liczbę oraz wysuw; te wymagania nie zatwierdzają prowadnic ani nośności.

## Dostępne

- Wybór rodziny i konkretnego wariantu na podstawie istniejących obrazów CAD.
- Rzeczywiste liczby wystąpień części i płytka hierarchia zespołów z inwentarza.
- Wymagane wymiary wnętrza, wysokość głównej osłony, intencja otwierania/podstawy
  i uwagi kierowane do konkretnej rodziny. Zmiana typu otwierania zapisuje życzenie,
  nie zatwierdza kompatybilności istniejącego wzorca z takim mechanizmem.
- Oddzielne szkice wariantów w pamięci bieżącej sesji; eksport/import JSON
  sprawdzany przez Python, z przypięciem do rewizji katalogu i obu hashy wzorca.
- Loopback, sesja, allowlista zasobów i kontrola Origin przy walidacji. Usługa
  nie udostępnia ICS, baz ani dowolnych plików z dysku; nie wykonuje operacji CAD.

## Uruchomienie

Z `Integracja` w checkoutcie, z jego Pythonem:

```powershell
.\.venv\Scripts\python.exe -m rockpro_cad.reference_studio --bundle "<prywatny-folder-model-library-20261026>"
```

Pakiet musi zawierać `manifest.json`, przypięte `native-02/Mxx-inventory.json`,
`working-standard-v1/Mxx.json` oraz opcjonalne obrazy `images-full-2027/Mxx.png`
i `review-2027/Mxx.png`. Nie kopiujemy tych prywatnych danych do Gita.
Zmiana bajtów inwentarza względem standardu zatrzymuje wczytanie.

## Granice i dalsza kolejność

To interaktywny prototyp wyboru wzorca i zapisu wymagań. Obraz źródłowy jest stały:
formularz nie zmienia jego geometrii. Nie ma jeszcze edytora 3D/drag and drop,
wyliczania gabarytu, zatwierdzonych tolerancji ani przycisku generowania CAD.
Eksport jest szkicem koncepcji, nie planem wykonawczym, BOM ani rewizją w SQLite.
Sesja przeglądarki nie zastępuje trwałego projektu; do zachowania szkicu użyj eksportu.

Kolejny przyrost: przypisanie powierzchni i ruchomych zespołów rzeczywistych
wzorców do [architektury konfiguratora](CASE_CONFIGURATOR_ARCHITECTURE.md),
lekka geometria 3D i manipulacja kotwami. Wing jako pierwszy adapter ruchu,
następnie komory ChainMaster/Focus, podparcia Martin, ekrany i moduły workstation.
Nie stosujemy płytkiej pokrywy T1 do wysokiej czapki Wing ani domyślnego kompletu
czterech uchwytów do źródła z trzema. Nowe wzorce nadal dotyczą IronCAD 2027.

Testy: `python -m unittest rockpro_cad.mcp.test_reference_studio -v` z `Integracja`.
Testują wiązania źródeł, oddzielność wariantów, poprawność wymagań i granice HTTP.
Sprawdzenie UI i rzeczywistego pakietu raportujemy osobno. Native CAD: NOT RUN,
ponieważ ten przyrost nie wywołuje SDK i nie zapisuje modeli.

Wynik 27.10: PASS 6 testów jednostkowych/HTTP, audyt repozytorium oraz składnia JS.
PASS test przeglądarkowy na rzeczywistym pakiecie: sześć rodzin, siedem modeli,
2829 wystąpień części, wariant Hisense oddzielny od M01, zachowanie ustawień,
walidacja Python, import szkicu, wymagania półek, obrazy, szerokość mobilna i brak
błędów JS. Sprawdzono również link bezpośredni `#workstation` i widoczność pól.
Dowody prywatne: `artifacts/reference-studio-20261027/ui-result.json`,
`studio-desktop.png`, `studio-mobile.png` i `repository.json`.
