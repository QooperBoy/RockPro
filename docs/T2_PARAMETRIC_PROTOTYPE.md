# T2 — pierwszy przyrost parametryczny w IronCAD 2023

26.10.2026. Osobna gałąź `codex/t2-parametryzacja`, oparta na `1cfd2f3`.
Źródłem jest dokładna rewizja z analizy T2, przypięta przez SHA modelu
i SHA bajtów inwentarza. Oryginalne modele i baza wdrożenia pozostają zachowane.

## Zakres

Wykonawca pracuje na nowej kopii źródła, przez SDK 2023 PU1 SP1. Nie zapisuje ICS.
Zachowuje 335 części fizycznych, historię okuć, pierwotne macierze i odbicia.
Dodatkowe zespoły sterujące położeniem formatek nie są pozycjami zakupowego BOM.
To eksperymentalny prototyp, nie promocja `reference_draft` do zatwierdzonego
szablonu rodziny. Kontrakt MCP i zainstalowana DLL nie zostały rozszerzone.

| Parametr sceny | Znaczenie |
|---|---|
| RP_GlebokoscObudowy | Obrys sklejki Y, 627–827 mm |
| RP_WysokoscObudowy | Obrys sklejki Z, 506,5–706,5 mm; zwiększa czapkę i klapę, zachowuje spód |
| RP_UniesienieCzapki | Prezentacyjne uniesienie czapki, bez automatycznego unoszenia racka |
| RP_OdsuniecieKlapy | Prezentacyjne odsunięcie przedniej klapy w −Y |
| RP_UniesienieRacka | Niezależne prezentacyjne uniesienie racka w +Z |
| RP_PrzesuniecieUchwytow | Przesunięcie bocznych uchwytów i wszystkich powiązanych obróbek w Y, ±10 mm |
| RP_PodniesienieUchwytow | Przesunięcie trzech uchwytów i obróbek w Z, ±10 mm |

Pełne polskie komentarze mają jedno źródło: `t2_parametric.NOTES`.
Wymiary dotyczą sklejki. Nie zastępują gabarytów z PDF ani obrysu wszystkich okuć.
Szerokość sklejki pozostaje 548 mm. Zmiana szerokości wymaga osobnego wariantu
standardowego racka i rozwiązania jego podparcia. Zachowano grubości wzorca,
w tym asymetrię podpór 15/18 mm, oraz trzy uchwyty T2. Brak zawiasów i gniazd kół T1.

## Architektura

- `core_case/t2_parametric.py`: deterministyczny plan przemieszczeń i wymiarów;
  właściwe ramy rodziców, kompensacja odbicia i niezależny ruch racka.
- `scripts/prepare_t2_parametric.py`: prywatny plan z istniejącej mapy i inwentarza,
  sześć zestawów oczekiwań do pomiaru natywnego.
- `scripts/native/T2ParametricPrototype.cs`: wykonanie na kopii, wiązania natywne,
  pomiary brył i macierzy, zamykanie nieudanych własnych kopii.
- `scripts/run_t2_parametric.py`: kolejka globalnego wykonawcy przed dotknięciem COM.
  Ponawiany jest tylko brak dostępu do blokady; uruchomiony job nie jest ponawiany.

Poszycie/profil rośnie przez dodatnią operację, z zachowaniem konturu źródłowego.
Wycięcia przesuwają się w układzie części. Uchwyt ma jawne powiązanie z otworem
poszycia i płytkim podfrezowaniem podpory. Gotowe okucia nie są skalowane.
Piany i rack przemieszczają się jako części; ich historyczne cechy pozostają
bez ponownego wiązania kotew. Dopasowanie pian do urządzenia nie jest zatwierdzone.

Niektóre części wzorca odrzucają bezpośrednie przypisanie wyrażenia położenia.
Przyczyna nie została sprowadzona wyłącznie do ustawienia stałej kotwy:
zmiana tego ustawienia nie rozwiązała problemu. Zastosowano jawne zespoły
sterujące, zachowując macierze i bryły części; porównanie bazowe jest obowiązkowe.

Formatki mają już wewnętrzne parametry S/H/L. Nadpisanie samego wyrażenia
SizeBox nie wystarczyło: długość nadal zależała od L. Wykonawca wiąże te
istniejące parametry z polskimi parametrami sceny przez lokalne parametry wymiarów.
W profilach bez S/H/L używa jawnych wyrażeń rozmiaru. Kontrolowane są rzeczywiste
obrysy cech, a nie sam tekst wyrażenia lub brak wyjątku.

## Pomiary

Natywnie przeszło sześć prób geometrii w `native-14/progress.json`:

1. Odtworzenie wzorca: zgodność 335 brył przed zmianą wymiarów.
2. Głębokość 667 mm i wysokość 536,5 mm; zachowane przekroje profili/grubości.
3. Uchwyty: przesunięcie Y +5 mm i Z +4 mm, z powiązanymi obróbkami.
4. Czapka +120 mm, klapa +180 mm, rack pozostaje nieruchomy względem spodu.
5. Rack +80 mm niezależnie od czapki i klapy.
6. Powrót do wymiarów i geometrii wzorca.

Każda próba sprawdza 164 elementy sterowane, 90 cech i pozycje/orientacje
335 części. W położeniu zamkniętym sprawdzane jest współpołożenie 6 par zamków.
Próby zachowują wszystkie bryły katalogowe. Wcześniejsze błędy nie zostały usunięte
z lokalnych dowodów ani zastąpione statusem PASS.

Pierwszy pełny harness i testy kolejki PASS. Po sześciu poprawnych próbach
`native-13` wymusił aktualizację historii każdej części przy odświeżaniu grafiki.
IronCAD zgłosił 38 błędów zaokrągleń, m.in. w części teleskopu. Ten job jest
odrzucony do odbioru: `native13-rejected.json`; PASS geometrii sprzed odświeżania
nie jest dowodem poprawnego wyniku po tej operacji.

Poprawiony kod unieważnia wyłącznie grafikę, bez `Part.Update`/`Assembly.Update`
wewnątrz gotowych okuć. Dodatkowo porównuje liczbę powierzchni brył katalogowych
przed operacją, w próbach i po odświeżeniu. Po zamknięciu okna przez użytkownika
`native-14/result.json` potwierdził PASS sześciu prób i grafiki oraz zachowanie
liczby powierzchni wszystkich 269 części katalogowych.
Nie należy usuwać ani edytować zaokrągleń w oryginalnych okuciach jako obejścia.

Niezależna próba `native-15-body/result.json` mierzy rzeczywiste bryły 13 płyt,
nie tylko położenia i rozmiary cech. Wyniki obrysu sklejki:
548 × 627 × 506,5 → 548 × 667 × 536,5 → 548 × 627 × 506,5 mm.
Źródło niezmienione; własna kopia kontrolna zamknięta. Grafika była w tej
próbie celowo NOT RUN; jej dowód pochodzi z native-14.

Użytkownik zmienił nazwę dostarczonej sceny na wariant `...v1_bezszer`.
Końcową kontrolę wymiarów wykonano na osobnej ukrytej kopii, zachowując tę wersję.
Nie wykonano zapisu CAD przez agenta ani ponownego otwarcia zapisanej przez
użytkownika wersji jako dowodu trwałości parametrów.

## Koordynacja i sprzątanie wykonawcy

Podczas uzgadniania kolejności z T1 anulowanie kolejki zbiegło się z uruchomieniem
native-14. Klient Python zakończył się, ale kod C# kończył pracę w hoście.
Nie restartowano IronCADa ani nie uruchamiano równoległej mutacji. Oczekiwano
na result.json i clr_result.json (managed_result=0), a następnie uzgodniono stan
i usunięto wyłącznie własny tymczasowy AddOn. Dowód:
`native-14/client-interruption-reconciliation.json`.

Kolejka obsługuje teraz kooperacyjne anulowanie przed dispatch: plik
`<katalog-wyjściowy>.cancel`. Po dispatch należy zaczekać na jednoznaczny wynik
hosta. Nie przerywać klienta jako sposobu anulowania już wykonywanego C#.
`run_t1_machining_job.py` usuwa jedyny własny wpis po pozycji kolekcji 0,
zamiast mylącego AddOn.Index=1, i sprawdza rzeczywisty Count po usunięciu.
Testy obejmują anulowanie przed startem, brak ponowienia wykonanego joba
i zachowanie cudzych AddOnów. Cleanup native-15-body potwierdza Count=0.
Dowody prywatne: `artifacts/t2-parametric-20261026/` w tym checkoutcie.

## Ograniczenia

Końcowa weryfikacja offline: `artifacts/verification/20261026T190937202881Z/results.json`
— PASS wszystkich siedmiu grup, w tym 242 testów kontraktów rdzenia.
Poprzedni przebieg `20261026T190721892208Z` zakończył się błędem usuwania
tymczasowego `Probe.exe` (WinError 5) po teście sprzątania. Powtórzenie bez
zmiany kodu przeszło; przyczyna chwilowej blokady pliku nie została ustalona.
Nie jest to dowód operacji natywnych CAD — te opisano osobno wyżej.

NOT RUN: zapis/ponowne otwarcie parametrycznej kopii (obowiązuje zakaz zapisu),
odbiór wizualny i produkcyjny, dobór do fizycznego urządzenia, nośność i bezkolizyjny
tor demontażu. Ruchy osłon są prezentacyjne. Teleskop zachowuje geometrię
źródłową; jego wysuw nie jest parametrem tego przyrostu. Złącza zachowują
osadzenia wzorca bez domniemania zatwierdzonych tolerancji. Zakresy wejść
sprawdza planer; dowolna ręczna edycja natywnej tabeli nie ma ciągłego strażnika kolizji.
