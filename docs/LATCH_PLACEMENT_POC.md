# Zatrzaski 17251S — rozmieszczenie całych złożeń

`Integracja/rockpro_cad/core_case/latch_placement.py` udostępnia czystą funkcję:

```python
plan_latch_pairs(source_rows, case_min, source_size, target_size,
                 source_lid_height=104.13)
```

Wejście to cztery złożenia: `role` = `lid` / `base`, `side` = `left` / `right`,
unikalne całkowite `id`, `matrix_world_mm` i `local_bounds_mm` (sześć liczb: minXYZ,
maxXYZ). Wszystkie długości są w **mm**. Macierze 4×4 używają wektorów wierszowych
i translacji w ostatnim wierszu. `case_min` to minimalny narożnik osiowo ustawionej
skrzyni, a rozmiary są w kolejności XYZ. Planer nie przelicza metrów z API CAD.

Obie połówki pary muszą mieć wspólny początek źródłowy. Początki lewego i prawego
zatrzasku pozostają 150 mm od odpowiednich bocznych krawędzi. Plan dodaje wspólną
translację `[0, 0, ΔH]` do lewej pary i `[ΔW, 0, ΔH]` do prawej. Położenie względem
przedniej ściany i wysokość pokrywy pozostają stałe. Zachowuje wszystkie źródłowe
orientacje, także istniejącą parzystość, lokalne bbox oraz wzajemne położenie
połówek. Nie odczytuje ani nie tworzy otworów, śrub, szkiców czy historii części.

Wynik `occurrences` zawiera cztery wiersze w kolejności lewa pokrywa, lewa baza,
prawa pokrywa, prawa baza, z macierzami docelowymi, translacją i środkiem lokalnego
oraz światowego bbox. Sprawdzane są sztywność macierzy, skończone liczby, komplet
ról, wspólny początek pary i symetria środków bbox. Zbyt mały cel jest odrzucany,
gdy grupy nakładają się w X albo bbox wykracza poza szerokość lub wysokość skrzyni.
Wysunięcie okucia przed ścianę w Y jest dozwolone. Niepoprawne wejście zgłasza
`ValueError`; brak częściowego planu. `production_approved` zawsze ma wartość `false`.

## Dowody

- **PASS offline:** trzy testy smoke: identyczny rozmiar A, zmiana wymiarów ze
  wspólnym ruchem par i symetrią, odmowa niepoprawnych lub zdegenerowanych danych.
  Polecenie: `python -m unittest discover -s Integracja/rockpro_cad/core_case -p
  'test_latch_placement.py' -v`. Lokalne raporty: `artifacts/latch-placement-*.txt`.
- **PASS offline na danych historycznych:** cztery zapisane wiersze z
  `artifacts/core-native/source-poses.json`, ID 12631/12630 i 12782/12781.
  A zachowuje macierze; cel 1100×720×410 daje wspólne przesunięcie par
  `[0,0,58]` oraz `[186,0,58]` mm. Raport:
  `artifacts/latch-placement-historical-offline.json`. Stary odczyt zgłasza dwa
  błędy `improper ICAPI rotation` dla macierzy rodzica. Zapisane macierze świata
  nie dowodzą więc zachowania surowej parzystości oryginału. To próba wejścia
  offline, wymagająca świeżego potwierdzenia przed montażem.
- **PASS native09:** świeży odczyt czterech rzeczywistych złożeń, kopiowanie,
  dwa rozmiary, zapis i ponowne otwarcie ICS. Szczegóły bieżącego odbioru poniżej;
  wynik nie oznacza gotowości produkcyjnej ani oceny wyglądu.

Kontrola gabarytu obejmuje tylko bbox całych złożeń w X/Z i rozdzielenie lewej
oraz prawej grupy. Jest celowo zachowawcza dla bardzo małych skrzyń; nie jest
kontrolą kolizji z profilami, płytami ani sprawdzeniem zamknięcia zatrzasku.

Źródłowy model i zapisane dane klienta pozostają poza Git. Planer nie otwiera
plików ani dokumentów CAD. Starszy szkic `component_placement.py` nie jest tu
integrowany.

## Runner natywny i bieżąca blokada hosta — 22.10.2026

`scripts/accept_latch17251_poc.py` i `core_case/latch_native.py` przygotowują
dwa nowe modele: A 914×602×352 i B 1100×720×410 mm. Są to regularne kopie
z 10 prostymi płytami zastępczymi, 8 rzeczywistymi narożnikami i 4 kompletnymi
zespołami połówek zatrzasków, **nie pełny Epson ze wszystkimi profilami**.
Runner sprawdza środki i orientacje całych okuć, symetrię, zapis/otwarcie oraz
SHA źródła. Nie odczytuje BRep, otworów ani historii okuć. Własne dokumenty
zachowuje i zamyka w `finally`; źródło i nieznane dokumenty pozostają otwarte.

Kompilacja `LatchPanelBridge.cs` z oficjalnym SDK, składnia Python i trzy
podstawowe testy planera: **PASS**. Historyczny wykonawca out-of-process nadal
napotyka E_NOINTERFACE; nowy wykonawca in-process zakończył native09 **PASS**.
Przykład wykonania z katalogu repo, gdy dokładny zapisany kontekst jest już
otwarty i udostępnia działające ICAPI:

```powershell
& '..\Integracja\.venv\Scripts\python.exe' scripts/accept_latch17251_poc.py --native `
  --context '..\Integracja\skeleton\20261020T110925Z\Epson_source_snapshot.ics' `
  --source '..\AI_CAD\T_1_1\Showcase_Epson_parametry.ics' `
  --corner-receipt artifacts/corner410429-20261022/native-03/A-base/corner_native_receipt.json `
  --corner-assets artifacts/corner410429-20261022/native-03/assets/assets_receipt.json `
  --output artifacts/latch17251-native-20261022-01
```

Po uruchomieniu IronCAD przez użytkownika proces PID 48160 był dostępny.
Getter `Application.HWnd` wskazał HWND 270652 należący do tego samego PID,
więc odczytany ROT nie był pozostałością poprzedniego hosta. Podłączenie Python
i oficjalny interop C# odrzuciły `IZBaseApp` z `E_NOINTERFACE` (0x80004002).
Sprawdzono istniejące obiekty ROT, `Application` i `Application.ZIronCADApp`;
IID Python i SDK jest identyczny: `{A5B9AF7D-228B-4ED1-BA42-D51318F7EA20}`.
`ZIronCADApp.GetTypeInfo` dodatkowo zwrócił `TYPE_E_LIBNOTREGISTERED`.

Diagnostyka wyłącznie odczytowa wykazała:

- Oficjalny ICAPI TLB ma GUID `{0C40AF17-BFB7-4746-B9E6-AE387A3FDDEF}`,
  wersję 29.0, LCID 0 i SYS_WIN64. `LoadRegTypeLib` dla tej wersji działa.
  Działa także dla wszystkich sześciu bibliotek z lokalnego SDK:
  czterech DLL ICAPI, `ICApiFoundation.tlb` i `ICApiIronCAD.tlb`.
- HKCU ma wpisy ICAPI 29.0/win64 i interfejsu. HKLM ma stare wpisy 14/21
  wskazujące plik 29.0; ładowanie tych starych wersji nie działa. Nie ustalono,
  że to właśnie tych wersji żąda odrzucający połączenie obiekt hosta.
- Host i klient mają ten sam SID i token Limited/Medium, bez podwyższenia.
  Załadowane moduły ICAPI hosta pochodzą z poprawnej instalacji IronCAD 2027;
  nie znaleziono obcych starych DLL.

Dalsza diagnostyka wykazała, że statyczne i działające ATL holders Base/App
żądają metadanych 12.0, mimo TYPELIB29.0 w SDK. Odwracalne prywatne kopie TLB
z wersją12, rejestrowane wyłącznie w nowych HKCU TypeLib/c.0, dały klientowi
LoadRegTypeLib12 PASS, lecz nie naprawiły hosta. Próby oficjalnej fabryki
/Automation zatrzymało okno wersji testowej; nie wykonano UI ani restartu
oryginalnego hosta. Te eksperymenty i rollback są opisane w
[ICAPI_CONNECTION_RUNBOOK.md](ICAPI_CONNECTION_RUNBOOK.md). Nie są automatyczną
częścią instalacji.

**Przełom in-process:** stały getter przez normalny legacy AddOn/triFunction
uzyskał IZBaseApp i ApiVersion29.0.2.20605 w PID48160. W tym samym procesie
LoadRegTypeLib12 nadal FAIL. Sesyjny ROT nie naprawił typed marshaling klienta.
Dlatego osobny `scripts/accept_latch_inprocess.py` uruchamia ograniczony helper
CLR w istniejącym hoście: cztery całe źródłowe połówki oraz dokładnie A/B.
Stały assembly/type/method nie stanowi ogólnego exec endpointu. Unikatowy basename
assembly odSHA kodu zapobiega użyciu starej kompilacji z cacheCLR.

Stan roboczy: kompilacja C++ i C# PASS; in-process BaseApp, ukryte otwarcie kopii
i cleanup PASS. SDK IsReadOnly zwracał false mimo OpenFile2(asReadOnly=true), przy
zgodnym GUID/SHA i Modified=false. Próba z OS read-only zmieniła foreground
(07FAIL); następna08 także zakończyła się błędem foregroundguard po powrocie OpenFile2
z dialogu hosta. Nie obsługiwano tego dialogu automatycznie i nie rozpoczęto
A/B. Finally zamknął własną kopię (remaining_owned=0) i przywrócił konfigurację
własnego AddOn. Zachowany cancellation sentinel uniemożliwia drugi etap08. Kolejny wariant jest ograniczony
do **własnej kopii getter-only**, bez claimu read-onlySDK: źródło nie jest
otwierane do edycji, a GUID, SHA, Modified i tło pozostają bramkami. Nie zapisuje
samej kopii źródłowej; eksportuje wyłącznie nowe pliki.

Dowody lokalne: `artifacts/latch17251-compile-20261022-01/`,
`artifacts/latch17251-inprocess-probe-20261022-04/`,
`artifacts/latch17251-session-bridge-20261022-01/` i
`artifacts/latch17251-inprocess-native-20261022-*/`. OryginalnySHA pozostał
`e3a1fa951ff6214abf34a4ec2b9dbceb039a06c37311b8dc1d2ea540b3e083a1` w ukończonych
próbach. Historia prób01–08 nie dowodzi montażu. Bieżący odbiór09 poniżej potwierdza
zapis, otwarcie i zamknięcie własnych dokumentów.

Cztery eksperymentalne HKCU c.0 z próby04 zostały wycofane z kontrolą dokładnej
zgodności receipt; `artifacts/latch17251-api-compat-20261022-04/rollback_receipt.json`
ma PASS. Poprawne29/Interface/HKLM i SDK dostawcy nie zostały zmienione. Kompilacja
końcowego wariantu getter-only z cancel.marker gates: PASS w
`artifacts/latch17251-inprocess-final-compile-20261022-01/`.

## Odbiór native09 — PASS

Działający wykonawca: `scripts/accept_latch_inprocess.py`,
`core_case/LatchInProcess.cs` i stały export `RockProLatchManaged` w
`addin/LatchApiProbe.cpp`. Wywołanie użyło wyłącznie istniejącego hosta 48160,
bez uruchamiania nowej instancji, UI, aktywacji i zmiany widoczności.

W `artifacts/latch17251-inprocess-native-20261022-09/` zapisano:

- `POC_zatrzaski_A_914x602x352.ics`, SHA
  `88f063411a0e9c43e4064d6a1351ff128e54ddd99ca067b546df470e22627e06`;
- `POC_zatrzaski_B_1100x720x410.ics`, SHA
  `851065180b390c2f92df72e31d25c391a8737d26fbee7bfcdef4926ece247a31`.

Każdy model ma osobny byte-identyczny `*_snapshot.ics`. Odbiór
`acceptance.json` potwierdza macierze i całe bbox czterech połówek względem
świeżego źródła oraz planu, zachowanie ID/nazw/liczby bezpośrednich dzieci po
ponownym otwarciu i symetrię środków. Odstępy środków od lewej/prawej krawędzi wynoszą
150 mm (różnice numeryczne poniżej 0,000002 mm) w obu rozmiarach. Prawa para
przesuwa się o `[186,0,58]` mm, lewa o `[0,0,58]` mm; oba człony pary razem.

To regularna kopia z **10 płytami zastępczymi, 8 rzeczywistymi narożnikami
oraz 4 kompletnymi złożeniami połówek zatrzasków**. Nie jest pełnym źródłowym
Epsonem ze wszystkimi profilami. Nie odczytywano ani nie zmieniano BRep,
otworów i historii okuć. A/B są odtwarzane z parametrów; nie powstały trwałe
natywne więzy montażowe. Wygląd: **NOT RUN**, do obejrzenia przez użytkownika.

`source_receipt.json` i `execute_receipt.json` mają PASS i `remaining_owned=0`.
Obie fazy zachowały foreground 9442774, aktywny kontekst, jego GUID i
Modified=false. Oryginalny SHA pozostał zgodny. Źródłowa kopia była jawnie
własnym getter-only plikiem (`sdk_readonly=false`, `os_readonly=false`), po
odczycie/eksportach niezmodyfikowanym i zamkniętym. Modele wynikowe są zamknięte.

Pozostały oznaczone dane diagnostyczne hosta: AddOn
`RockProProbe_6ec608b840324bc799c957c7abfa5c00`, przywrócony do getterDLL04 i
`RockProLatchProbe`, oraz sesyjny ROTCLSID
`{6BCBAB61-4399-4FD1-86D1-5361B8395C52}` / cookie 262146. Nie zgadywano semantyki
Remove; pusty UNKNOWN zachowano. Sesyjny ROT nie jest otwartym prototypem i
znika z hostem. Szczegóły: `session_leftovers.json`; żadnych zadań native w toku.
Eksperymentalne cztery klucze HKCUcompat04 są wycofane (PASS), SDK/29/Interface/HKLM
pozostały nienaruszone.

Przykład powtórzenia w tej samej jawnie oznaczonej sesji diagnostycznej
(nowy katalog operacji; nie automatyczna instalacja):

Ten runner używa lokalnego, potwierdzonego wpisu diagnostycznego AddOn.
Nie jest przenośnym instalatorem ani gotowym narzędziem MCP. Na innym komputerze
nie wolno kopiować PID lub identyfikatora sesji z poniższego przykładu.

```powershell
& '..\Integracja\.venv\Scripts\python.exe' scripts/accept_latch_inprocess.py `
  --expected-pid 48160 `
  --context '..\Integracja\skeleton\20261020T110925Z\Epson_source_snapshot.ics' `
  --source '..\AI_CAD\T_1_1\Showcase_Epson_parametry.ics' `
  --corner-receipt artifacts/corner410429-20261022/native-03/A-base/corner_native_receipt.json `
  --corner-assets artifacts/corner410429-20261022/native-03/assets/assets_receipt.json `
  --output artifacts/latch17251-inprocess-native-NOWY
```

Po odbiorze09 poprawiono wyłącznie samodzielny diagnostyczny probe: brak
automatycznego Remove(Index); własny dokładnyUUID zachowany i sprawdzany, UNKNOWN
nietknięty. Funkcja build oraz wykonawca C++/C# nie zmieniły się. SkładniaPASS,
bez kolejnego CADrun. Historyczne hashe09 zachowane; zmiana opisana w
`postproof_probe_safety_change.json`.
