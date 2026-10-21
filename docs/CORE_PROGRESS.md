# Core skrzyni — stan przyrostu 21.10.2026

Kod realizuje deterministyczny prototyp skrzyni. Nie jest jeszcze zatwierdzonym
generatorem rzeczywistych okuć Epson. Sol implementował planer, serwis, wykonawcę
i formularz; Astra niezależnie sprawdzała wymagania, nowe przypadki i błędy.

## Co działa

- `core_case/planner.py`: interpretacja jawnej recepty, ramy ścian i podziału
  pokrywy, płyty, profile, kotwy, grupy symetrii, parowanie okuć i koło–gniazdo.
  Stałe grubości/przekroje; właściwe obroty; osobne pozycje prezentacyjne wieka.
- Pełna symetria zbioru punktów w każdej zadeklarowanej osi. Sama symetria
  rozkładów pojedynczych współrzędnych nie wystarcza i ma osobną regresję.
- Poprzedni plan jest odtwarzany i weryfikowany. Jawne decyzje ręczne całej grupy
  mogą przetrwać resize; nierozstrzygnięta zmiana jednego członka blokuje plan.
- `mcp/core_service.py`: wspólna baza UI–AI, CAS, wersje żądań, niezmienne plany,
  przypięcie karty/układu/źródła, dziennik operacji, idempotencja i odzyskiwanie
  bez kolejnego montażu. Niedokończona operacja blokuje nową operację CAD w tym projekcie.
- `cad_lock.py`: jedna blokada natywnego wykonawcy między procesami i lokalnymi
  checkoutami, z obsługą starych blokad plikowych wdrożenia.
- `CasePlanForm.cs`: osobny panel prototypu, tabele grup i części, przygotowanie,
  zapis planu, osobny przycisk tworzenia ICS i odczyt/odzyskanie operacji.
  Interfejs rozróżnia prototyp od odbioru produkcyjnego, ma PL/EN i testy DPI.

## Dowody i granice

| Obszar | Wynik | Co faktycznie sprawdzono |
|---|---|---|
| Zamrożone wymagania A/B/C | PASS | 173 testy planera; resize, symetria, kotwy, bilans ID i praca ręczna. |
| Niezależny weryfikator i układ | PASS | 9 testów; razem 182 w zwykłym harnessie. |
| Nowe przypadki Astra | PASS | 36 kombinacji nowych wymiarów, orientacji i osi, poza zamrożonymi oczekiwaniami. |
| Serwis i stdio MCP | PASS | Konflikty, integralność, wersje, idempotencja, awarie i brak ponownego wstawiania. Testowy wykonawca nie jest CAD. |
| Natywne A — punkt kontrolny A02 | PASS | 67 brył, zapis i ponowne otwarcie ICS, stabilne ID; maks. błąd pozycji/obrysu ok. 2e-12 mm. |
| Aktualny mostek po przeglądzie | PASS natywny | Istniejące-only ROT, kontrola obrysu i osobna tolerancja obrotu; A/B/C oraz resize zapisane i ponownie otwarte. |
| Rzeczywisty uchwyt H7159 | PASS osobnej próby | Natywny zespół 13 części zachował topologię, objętości i wewnętrzne transformacje po eksporcie/imporcie, obrocie, zapisie i ponownym otwarciu. Nie jest to jeszcze montaż na ścianie całej skrzyni. |
| Natywne A/B/C, resize, rejestracja SQLite | PASS | Cztery operacje i cztery snapshoty na izolowanej bazie; zgodne hashe kopii/archiwów, ponowienie bez duplikacji. Źródło to jawny wcześniejszy prototyp, nie model Epson. |
| Nowa DLL w działającym IronCAD | NOT RUN | Kompilacja nie przeładowuje dodatku. Nie restartowano hosta z otwartymi dokumentami. |
| Rzeczywisty katalog / produkcja | NOT READY | Nie zatwierdzono ram montażowych, odmian lustrzanych i nierozstrzygniętych części. |

Raport A02 jawnie podaje `catalog_reused=[]`, 67 zastępczych brył i
`production_approved=false`. Źródło było otwarte z `Modified=true`; zachowano jego
stan i wykonano kopię z pamięci, bez deklarowania zgodności pamięci z dyskiem.
Hash oryginału zgadzał się przed/po A02. Po późniejszej próbie otwarcia ciężkiej
kopii odczyt był chwilowo zablokowany. Host wrócił do pracy, a końcowa kontrola
oryginału potwierdziła zgodność SHA, GUID i flagi Modified z początkiem próby.
To kontrola źródła, a nie dowód poprawnego montażu uchwytu.

## Kolejność dalszego odbioru w Linearze

1. ROC-20: natywny przyrost prototypu A/B/C + resize z rejestracją snapshotu
   przez serwis jest sprawdzony. Zachować ten odbiór przy podłączaniu rzeczywistych
   części: kopia robocza, osobne archiwum, raport, SHA i powtórzenie operation_id.
2. ROC-42 i ROC-17: najpierw jedna rzeczywista rodzina okuć z zatwierdzoną bazą
   montażową. Nie prostować transformacji lustrzanych przez zgadywanie obrotu.
   Następnie pozostałe rodziny i rozliczenie każdego węzła.
3. ROC-16 i ROC-40: odbiór pełnego szablonu oraz trójstronne porównanie faktycznych
   ręcznych edycji CAD. Obecna logika decyzji planera nie zastępuje tego odczytu.
4. ROC-26: sprawdzenie nowego panelu i narzędzi MCP w przeładowanym dodatku.
5. ROC-19: trzy rzeczywiste kompletne skrzynie i negatywne scenariusze po zapisie
   i ponownym otwarciu, z potwierdzonymi okuciami.
6. ROC-34: konstruktor ocenia geometrię, montaż i proces; odbiór człowieka nie
   wynika automatycznie z zielonych testów.

Wycięcia pod okucia, styki profili, nośność, paletyzacja i dokumentacja
produkcyjna nie otrzymują automatycznej akceptacji z tego prototypu.

## Instrukcja testu nowego panelu

Po bezpiecznym przeładowaniu dodatku: **Układ urządzeń → Otwórz prototyp skrzyni**.
Przypisz otwartą kopię ICS do zapisanej karty. Zapisz układ: dwa urządzenia,
dodatnia grubość przegrody i komora X albo Y. Inne warianty mają zostać odrzucone,
a nie po cichu zmienione.

Przygotuj prototyp, sprawdź 37 grup i domyślnie 67 brył, zapisz i przypnij plan.
Dopiero **Utwórz prototyp ICS** uruchamia CAD. Po sukcesie sprawdź ścieżkę nowego
archiwum. Źródło projektu ma pozostać dotychczasowe. Prototyp nie jest plikiem
produkcyjnym i nie zawiera rzeczywistych geometrii okuć.

Przy konflikcie zmień kartę lub układ z drugiego klienta: starego planu nie wolno
wykonać. Przy utracie odpowiedzi zachowaj ID operacji; po ponownym otwarciu panel
odnajdzie nieukończony zapis. Odczytaj stan, następnie odzyskaj z istniejących
dowodów. Brak kompletnego raportu ma blokować odzyskanie i nowy montaż.

## Weryfikacja developerska

Uruchom `scripts/Verify.ps1 -WithAddinBuild -WithUiChecks` zgodnie z
[DEVELOPMENT.md](DEVELOPMENT.md). Szczegóły kontraktu i API:
[CORE_RUNTIME.md](CORE_RUNTIME.md). Bieżące wyniki, zrzuty UI, modele i dane
źródłowe pozostają lokalnie w ignorowanym `artifacts/`.

Prompt wznowienia: „Użyj $rockpro-scope-check i $rockpro-verification. Wróć do
ROC-20 i próby H7159. Najpierw potwierdź stan źródła oraz hosta, potem sprawdź
aktualny mostek na nowej kopii, A/B/C i resize przez serwis, z pomiarem po
ponownym otwarciu oraz zgodnością ICS–snapshot–SQLite. Zachowaj otwarte dokumenty,
symetrię, allowlistę starego szkieletu i brak zatwierdzenia produkcyjnego”.

## Natywny odbiór aktualnej wersji

Lokalny raport: `artifacts/core-native/native_acceptance/acceptance-20261021-01/acceptance.json`.
Astra niezależnie przeliczyła wszystkie macierze i osiem rogów obrysu każdej
części oraz odczytała SQLite tylko do odczytu: cztery operacje registered,
cztery archiwa prototype; maksymalny błąd obrysu ok. 4,69e-12 mm.
Źródło testu to wcześniejszy `case_prototype.ics`, bez podmiany jego tożsamości
na Epson i bez zatwierdzenia katalogowego. Powtórzenie: `scripts/accept_core_native.py`
z jawnymi `--source`, `--workspace` i nowym `--run-id`.

## Dokładna geometria katalogowa — pierwszy wycinek

`core_case/catalog_native.py` kopiuje natywne zespoły zamiast odtwarzać je z
obrysu. Próba H7159: `artifacts/core-native/real-H7159-20261021-03/native_receipt.json`
i `source_chain.json`. 13 części, obrót Rz90 i przesunięcie [100, 200, 300] mm,
zapis i ponowne otwarcie. Rzeczywista geometria jest zachowana; `proxies=[]`.
Zmienia się tylko rama montażowa całego zespołu. Wewnętrzne odbicia należące do
niezmienionej geometrii są zachowane, nie prostowane; światowa rama źródłowa
i docelowy ruch muszą być właściwymi obrotami.

Odbiór obejmuje każdą zagnieżdżoną transformację, topologię, obrysy i objętość
każdej bryły. Naprawiono odczyt ICAPI GetVolume: kolejność wyników to osiągnięta
dokładność, następnie objętość. Zero błędu dokładności nie oznacza zerowej objętości.
Testy obejmują ten przypadek i odrzucenie rzeczywiście zerowej objętości.

Ten moduł jest wewnętrznym wycinkiem integracji, nie narzędziem do dowolnego
montażu przez MCP. Następny krok: biblioteka części z ramami montażowymi oraz
połączenie tego kopiowania z kotwami i symetrią całej skrzyni. Obecny przycisk
prototypu nadal generuje jawne bryły zastępcze; nie podmienia ich automatycznie
na zatwierdzony katalog.
