# Studio → IronCAD 2027: zestaw Penn Elcom / Adam Hall

Lokalny prototyp dla draftu `3f8d90f0cea643868dc95072f32a7f8d`, rewizja 2.
To osobny, przypięty do pomiarów adapter jednej konfiguracji, nie nowy dowolny
executor MCP ani zatwierdzenie modelu do produkcji.

## Zakres

800 × 650 × 800 mm wymaganej przestrzeni korpusu, dodatkowe wieko zdejmowane
115 mm, sklejka 9,8 mm, kolor #408080. Sześć grup organizacyjnych ze wspólnego
rejestru `part_registry`; 52 wystąpienia: 10 płyt, 16 odcinków EG-0100,
8 narożników C1339/30, 4 kompletne zamki MOL3, 4 kompletne H2026,
2 wentylacje D0536/07 i 8 nóżek (jedno opakowanie 4903M8AH).

- C1339-30, L944-537-10MOL3 i D0536-07: STEP dostawcy Penn Elcom pobrane
  z zalogowanego 3D ContentCentral; import do ICS oraz zapis/odczyt sprawdzone.
  Czarny wariant K odwzorowany wykończeniem; CAD ma bazowy kod bez K.
- H2026: całe dwuczęściowe okucie z przypiętego modelu konstruktora M03,
  razem z transformacją i trzema wzorcowymi wycięciami: bok, dach, profil.
  Kotwa przeniesiona na rzeczywistą górną krawędź; koncepcyjny środek Studio
  nie jest przyjmowany za powierzchnię montażową narożnego uchwytu.
- EG-0100: rzeczywisty przekrój jednego profilu z M01, zmienna wyłącznie
  długość wyciągnięcia. Nie pobierać całego źródłowego zespołu jako jednego SKU.
- 4903M8AH: nominalna bryła Ø20 × 9 mm, otwór Ø4,4 mm z danych Adam Hall.
  Producent nie udostępniał CAD w centrum pobierania. To odtworzenie wymiarowe,
  nie model producenta; nie odtwarza nieznanych szczegółów wkładki stalowej.

## Obróbki i ograniczenia

22 operacje: 8 połówek wycięć zamków, 2 wentylacji i 12 pod H2026
(po 3 na uchwyt). Przez jedną kotwę wystąpienia wyliczane są pozycje okucia
oraz jego wycięć. Zmiana parametrów sceny nie skaluje katalogowego okucia.

Rysunek MOL3 podaje nominalny otwór 96 mm; płaszczyzna kołnierza pobranego CAD
ma gardziel 99,6 mm. Wentylacja ma analogiczną różnicę względem katalogowego
146 × 96 mm. Nominalne prostokąty wykazały interferencję i zostały odrzucone.
Przygotowany kontur montażowy korzysta z krawędzi gardzieli w płaszczyźnie
kołnierza. Naroża źródłowe B-spline są dopasowaniem łuku przez odczytane
początek, środek i koniec; dodatkowo przyjęto 0,5 mm zapasu w osiach obrysu.
To jawne przybliżenie prototypu, nie dokładna kopia splajnu ani zatwierdzony
kontur CNC. Wymagany jest test natywnych interferencji po wykonaniu.
Kołnierze zamków/wentylacji mają 0,05 mm szczeliny obliczeniowej od sklejki.

Nie dobrano jeszcze pary profili złącza korpus–wieko. Szczelina sklejki
0,5 mm jest wyłącznie roboczym luzem prototypu, nie modelem uszczelnienia.
Brak śrub, nitów, udźwigu i odbioru technologicznego. Zapas nominalny nóżki
9 mm nad dolnym narożnikiem wystającym 7,65 mm wynosi tylko 1,35 mm;
ugięcie nóżki i nośność wymagają decyzji konstruktora. `production_approved=false`.

## Weryfikacja i diagnostyka

Dowody prywatne: `artifacts/requested-native-20261028/`.

- `vendor-import-01`: trzy modele dostawcy import/zapis/odczyt PASS.
- `handle-02`: komplet H2026, dwa niepuste korpusy, źródło bez zmian PASS.
- `mount-survey-02`: kontury konstruktora i przekrój EG-0100 PASS.
- `complete-07-rebind`: pełne 52 wystąpienia; zmiana wymiarów, powrót,
  zapis/odczyt i zmiana po odczycie PASS. Ta wcześniejsza kopia ma zbyt małe
  nominalne otwory MOL3/wentylacji; nie traktować jej jako finalnej obróbki.
- `verify-final-01`: pomiary brył i kotew 22 wycięć PASS; wykryte interferencje
  nominalnych otworów zapisane osobno. `passed` odczytu nie zatwierdza montażu.
- **Finalna kopia `montaz_v2`:** `complete-09-contours` — zmiana wymiarów,
  powrót, zapis/odczyt i zmiana po odczycie PASS. `verify-final-02` — pomiar
  52 elementów i kotew 22 obróbek PASS; 18 par okucie–sklejka bez interferencji
  w bazowym i zmienionym układzie. `present-final-03` — widoczne otwarcie
  i eksport odświeżonego podglądu PASS. Poprzednia własna prezentacja zachowana
  w osobnym pliku przed zamknięciem; nie nadpisano zmian w pamięci.
  Plik, podgląd, manifest i osobny snapshot znajdują się w lokalnym katalogu
  `projekty/RPS_Penn_AdamHall_3f8d90f0/`; wskazanie aktualnej wersji jest w
  `TRANSFER_STATUS.json`. Wcześniejsze kopie pozostają historyczne.
- Harness `20261028T211201042145Z`: repository/backend/parts/core-design/
  core-contracts/qa/harness PASS. Poprzednie próby ograniczał sandbox (TEMP/HTTP).

Po wszystkich importach trzeba odtworzyć powiązania z planu. Kolejne importy
zewnętrznych części mogą zastąpić wcześniejsze wyrażenia pozycji. Oprócz
sprawdzenia pozycji początkowej obowiązkowy jest rzeczywisty test zmiany wymiarów.
Pusty host zwraca `GetAllOpenDocs() == null`; nie oznacza to błędu integracji.
Statyczne kolekcje adaptera muszą być czyszczone przed każdym wywołaniem,
ponieważ CLR może ponownie użyć już załadowanej biblioteki.

**Incydent diagnostyczny:** odczyt `GetBSplineDataCOM` przez interop .NET
z buforami `out double` zakończył proces IronCAD 2027. Kod odczytu usunięto.
Nie przywracać go na podstawie samej zgodności sygnatur. Przed podobnym
eksperymentem potrzebny jest osobny pusty host i snapshot otwartych dokumentów.
Zapisany prototyp i pliki źródłowe pozostały na dysku; po restarcie nie pojawiło
się automatyczne odzyskanie wcześniejszych niezapisanych dokumentów.

## Narzędzia

`prepare_requested_native_case.py` tworzy jawny lokalny plan i przypina hashe
zasobów. `RequestedCase2027.cs` buduje lub naprawia nową kopię; sprawdza PID,
wersję 29.x, odmawia nadpisania finalnego pliku i chroni inne dokumenty.
`VerifyRequestedCase2027.cs` mierzy zapisaną kopię niezależnie od generatora.
`PresentRequestedCase2027.cs` otwiera dokładny zapisany plik widocznie i odświeża
grafikę. Sam `ActiveDoc` nie pokazuje ukrytego dokumentu.

Uruchamianie przez istniejący `run_t1_machining_job.py`, z
`ROCKPRO_IRONCAD_YEAR=2027`, nowym katalogiem dowodów i aktualnym PID.
Tylko jeden wykonawca CAD; nie rejestrować ponownie głównego dodatku.
