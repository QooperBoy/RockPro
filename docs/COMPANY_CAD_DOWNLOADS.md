# Modele CAD katalogu firmowego — 28.10.2026

Odczyt 265 rekordów zachowuje warianty i powtórzone kody. Katalog materiałów
nie oznacza biblioteki 265 modeli: płyty i pianki są surowcami parametrycznymi.

## Wynik lokalny

Biblioteka znajduje się w katalogu roboczym Ironcad:
`biblioteka_czesci/CAD_producenci/`. Pliki STEP i oryginalne archiwa są
pogrupowane według producenta i identyfikatora modelu. `manifest.json` zachowuje
źródła, konfigurację, SHA256 i mapę rekordów; `DOSTEPNOSC_MODELI.csv` pozwala
przejrzeć wszystkie pozycje w Excelu. Dane te pozostają poza Git.

- 74 unikalne pliki STEP, bez błędów kontroli kontenera/archiwów.
- 52 rekordy: pobrany kandydat; 31: kandydat ze sprzecznym/aliasowym kodem katalogu.
- 4: pobrano profil referencyjny, ale wariant długości/kod wymaga potwierdzenia.
- 7: znaleziono metadane STEP Adam Hall, pobieranie wymaga dostępu do konta.
- 106: nie znaleziono publicznego odsyłacza 3D na sprawdzonych stronach.
- 15: brak identyfikacji producenta lub konkretnego produktu; 1: dostawca do sprawdzenia.
- 49: surowce (26 płyt/sklejek, 23 pianek/wykładzin).

Rejestracja Adam Hall zakończona przez użytkownika. Portal informuje o weryfikacji
do 3 dni i wysłaniu dostępu w kolejnym e-mailu. Nie oznacza to aktywnego prawa
do pobierania. Wcześniejsze publiczne próby siedmiu plików zwróciły HTTP 401.

To **pobrane zasoby**, nie nowe siatki wdrożone do Studio ani zatwierdzenie
montażu, orientacji, wycięć czy CNC. Nie wykonano nowego testu natywnego CAD.
Przy rozbieżności kodu nie zastępuj automatycznie wariantu K/Z, długości ani SKU.
Skorygowany link EG-0500/2 zachowano wraz z pierwotnym błędnym URL; katalog
Excel pozostaje niezmieniony. E2220, E2226, E0490 i E2355 są referencjami,
nie potwierdzonymi wersjami magazynowymi 4 m.

## Powtarzalne narzędzia

`scripts/scan_company_cad.py KATALOG.json KATALOG_DOWODOW` czyta publiczne
strony producentów (maksymalnie cztery wątki), zachowuje HTML z SHA i wskazania
produktu głównego. Polecane produkty nie potwierdzają tożsamości SKU.
Pobieranie wymagające sesji odbywa się przez zalogowaną przeglądarkę, bez
kopiowania cookies/poświadczeń do skryptu i bez obchodzenia odmów dostępu.

`scripts/ingest_company_cad.py KATALOG_DOWODOW KATALOG_BIBLIOTEKI` kopiuje
pliki wskazane w `browser-downloads.json` i wcześniejsze przypięte zasoby.
Nie nadpisuje różnej zawartości, nie wykonuje archiwów, odrzuca traversal,
symlinki i nadmierne rozmiary, sprawdza nagłówek STEP i obecność geometrii.
Dowody bieżącej sesji: ignorowane `artifacts/company-cad-20261028/`.

Testy offline: `Integracja/.venv/Scripts/python.exe scripts/test_company_cad.py`.
Nowe pobranie nie jest automatyczną zgodą na publikację modeli lub push binariów.


## Lista do Tomka — przygotowana 31.10.2026

Zamknięto przygotowanie materiału do ROC-51: 16 pozycji do identyfikacji,
35 rozbieżności kodów/konfiguracji w osobnej sekcji oraz sześć pytań o produkcję.
Pakiet lokalny workspace: `raporty/Katalog_do_potwierdzenia_20261031/`.
`PYTANIA_DO_TOMKA.html` jest czytelny w przeglądarce i nadaje się do wydruku;
`ODPOWIEDZI_DO_UZUPELNIENIA.json` zachowuje stabilne ID, pola odpowiedzi i SHA źródła.
Nie wysłano wiadomości i nie zmieniono firmowego Excela, manifestu ani mapowań.
To stan danych z 28.10, nie nowy skan portali dostawców ani aktualizacja dostępu Adam Hall.

Powtarzalne generowanie (nowy, nieistniejący katalog wyjściowy):

```powershell
Integracja/.venv/Scripts/python.exe scripts/prepare_catalog_questions.py MANIFEST.json NOWY_KATALOG --date 2026-10-31
Integracja/.venv/Scripts/python.exe scripts/test_catalog_questions.py -v
```

Generator eksportuje wyłącznie dozwolone pola identyfikacyjne, bez cen, stanów,
ścieżek prywatnych zasobów, klientów i modeli. Warianty oraz powtórzone kody
zachowują osobne ID; żaden kandydat nie otrzymuje zatwierdzenia automatycznie.
Walidacja pakietu: 51 unikalnych rekordów, zgodność HTML/JSON, brak zmiany SHA
manifestu i sześć testów generatora PASS. Natywne CAD: NOT RUN, nie dotyczy.

Pełny harness offline: `artifacts/verification/20261031T152508363894Z` — siedem grup PASS. Pierwsze próby w sandboxie odmówiły dostępu do Windows Temp; powtórzenie w standardowym środowisku Windows przeszło.
