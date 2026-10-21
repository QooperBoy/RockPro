# RockPro CAD — plan rdzenia parametrycznego i TDD

Data: 2026-10-21. Status: projekt architektury i plan prac, bez implementacji nowych funkcji. Architektura przejrzana przez Astra high.

## Punkt startowy

Istnieją: konfigurator układu, szkielet 10 płyt i 6 parametrów, wersjonowanie i narzędzia MCP, czytnik wystąpień oraz jego testy. Nie ma jeszcze pełnego automatycznego montażu rodziny Epson ani samodzielnego agenta projektującego w tle. Szczegóły bieżącego kontraktu: [DEVELOPMENT.md](DEVELOPMENT.md), [LAYOUT.md](../LAYOUT.md), [PARTS_CATALOG_PLAN.md](PARTS_CATALOG_PLAN.md), [PARTS_IDENTIFICATION.md](PARTS_IDENTIFICATION.md).

## Kolejność w Linear

| Kolejność | Zadanie | Wynik |
|---|---|---|
| 1 | [ROC-43 — TDD-01](https://linear.app/rock-pro/issue/ROC-43/tdd-01-zamrozic-trzy-przypadki-i-napisac-pierwsze-testy-red) | Trzy fixture, kontrakty, niezależne oczekiwania i pierwsze RED; stan Todo |
| 2 | [ROC-15 — schemat](https://linear.app/rock-pro/issue/ROC-15/rp-05-zdefiniowac-schemat-parametrow-jednostek-i-rewizji) | Jednostki, semantyczne ID, wersje i walidacja |
| 3 | [ROC-42 — manifest](https://linear.app/rock-pro/issue/ROC-42/core-zbudowac-pelny-manifest-czesci-i-regul-szablonu-epson) | Wszystkie części wzorca mają rolę i politykę |
| 4 | [ROC-16 — geometria](https://linear.app/rock-pro/issue/ROC-16/rp-06-zbudowac-wzorzec-korpusu-i-wieka-ze-stabilnymi-odniesieniami) | Płyty, profile, ramy ścian, kotwy i test natywnych zależności |
| 5 | [ROC-17 — okucia](https://linear.app/rock-pro/issue/ROC-17/rp-07-sparametryzowac-katalog-uchwytow-zamkow-i-wzmocnien) | Narożnik, uchwyty, zamki/zawiasy, koła/gniazda, pozostałe role |
| 6 | [ROC-40 — praca ręczna](https://linear.app/rock-pro/issue/ROC-40/core-zachowac-reczne-zmiany-cad-przy-ponownym-przeliczaniu-skrzyni) + [ROC-20 — wykonawca](https://linear.app/rock-pro/issue/ROC-20/rp-10-zbudowac-lokalny-adapter-i-kolejke-operacji-cad) | Zachowanie zmian, wykonanie raz i odzyskanie po błędzie |
| 7 | [ROC-26 — harnessy AI](https://linear.app/rock-pro/issue/ROC-26/rp-16-udostepnic-ai-ograniczone-narzedzia-i-ocene-jakosci) | Koordynator z ograniczonymi narzędziami i oceną wyników |
| 8 | [ROC-19 — testy całości](https://linear.app/rock-pro/issue/ROC-19/rp-09-utworzyc-zestaw-wzorcowy-testow-geometrii-i-bom) + [ROC-34 — odbiór](https://linear.app/rock-pro/issue/ROC-34/rp-24-odebrac-pilotaz-jednej-rodziny-i-przeszkolic-tomasza) | Trzy próby natywne i odbiór konstruktora |
| Później | [ROC-41 — technologia](https://linear.app/rock-pro/issue/ROC-41/po-mvp-wyciecia-pod-okucia-i-styki-profili-aluminiowych) | Wycięcia oraz szczegółowe styki profili/okuć |

Plan nadrzędny: [ROC-6](https://linear.app/rock-pro/issue/ROC-6/rp-e2-parametryczna-rodzina-skrzyn-bez-ai). To kolejność realizacji przyrostów; dotychczasowe blokady ROC-19 dotyczą końcowego odbioru, nie przygotowania RED w ROC-43. Nie ustawiono fikcyjnych terminów ani nie przypisano zadań bez uzgodnienia.

## Architektura przepływu

### Wymaganie nadrzędne: symetria rozmieszczenia

Uzupełnienie użytkownika: symetria jest obowiązkowym niezmiennikiem konstrukcji,
nie tylko sugestią wizualną. Wszystkie elementy objęte regułą montażu mają jawną
grupę symetrii i odniesienie do środka ściany lub płaszczyzn skrzyni. Nie oznacza
to dodawania identycznych funkcji na każdej ścianie: zamki z przodu i zawiasy
z tyłu tworzą osobne grupy, a korpus i wieko mogą mieć różne wysokości.

- Jeden uchwyt: środek osi montażu ściany. Para: jednakowe odsunięcia od
  przeciwległych krawędzi i wspólna wysokość. Dla szerokości W oraz odsunięcia d:
  u_lewy = d, u_prawy = W - d; pojedynczy u = W / 2. Odsunięcie mierzymy do
  zatwierdzonego punktu montażowego części, nie przypadkowego brzegu bbox.
- Więcej elementów: układ wycentrowany, parami względem osi; przy nieparzystej
  liczbie środkowy element leży na osi. Rozstaw i minimalne odstępy są walidowane.
- Narożniki: komplet odpowiadających sobie naroży. Koła i gniazda: wspólna,
  symetryczna siatka X/Y i sprawdzone parowanie w układzie zamkniętym/stackingu.
- Zamki i zawiasy: symetria w obrębie odpowiedniej ściany oraz parowanie połówek
  góra/dół. RP_DisplayGap nie wpływa na regułę.
- Grupa zapisuje symmetry_group_id, datum/ramę, osie/płaszczyzny, członków,
  tryb centered/mirrored_pair/centered_pattern i wspólne odsadzenia. Członkowie
  wynikają z jednej reguły, nie z niezależnie edytowanych współrzędnych.
- Symetryczne położenie nie pozwala odbijać geometrii katalogowej przez skalę
  ujemną. Używamy poprawnych obrotów albo zatwierdzonych wariantów lewy/prawy.
- Ręczna zmiana członka grupy: propozycja aktualizacji całej grupy lub konflikt
  przed zapisem; bez cichego nadpisania pracy i bez automatycznej asymetrii.
  Nietypowe wymaganie funkcjonalne (np. boczna komora) wymaga jawnego zakresu
  grup i zatwierdzonego wyjątku; AI nie może samodzielnie wyłączyć symetrii.

TDD (ROC-43/19): pary mają tę samą wysokość i równe odsunięcia od przeciwległych
krawędzi, środek pary leży na osi; pojedynczy element pozostaje wycentrowany;
grupy zachowują symetrię przy zmianach X/Y/Z, liczności i po zapisie/otwarciu.
Testy negatywne: przesunięty jeden uchwyt, brak członka pary, błędna orientacja,
pomylona rama, brak miejsca i ręczne naruszenie grupy. Każdy ma zablokować PASS.
Sprawdzamy także poprawność obrotu i niezmienność bryły sztywnej. Zakres dotyczy
ROC-15/16/17/40/42 i wszystkich harnessów walidujących plan lub wynik CAD.

Status: wymaganie i plan testów; nie deklaracja już wdrożonej funkcji.

`CaseSpec → TemplateManifest → geometria/kotwy → ChangePlan → uzgodnienie zmian ręcznych → jeden wykonawca CAD → zapis/otwarcie → niezależny odbiór → snapshot + rewizja`

PLAN CORE / TDD — 21.10.2026
Cel pierwszego odbioru: trzy osobne skrzynie dla trzech produktów, w rodzinie konstrukcyjnej wzorca Showcase_Epson_parametry.ics. W każdej znane wymiary, liczba urządzeń, orientacja, przegrody i komora na akcesoria. Testujemy wykonanie automatyczne oraz ręczne poprawki konstruktora. Nie zakładamy jeszcze autonomicznego AI w dodatku: obecnie działa kod Python/ICAPI i narzędzia uruchamiane przez agenta.

Zakres: korpus i wieko, profile, narożniki, uchwyty, zamki, zawiasy, wzmocnienia, koła i gniazda, wnętrze oraz elementy własne. Każda rodzina z inwentarza musi mieć jawny sposób obsługi. Urządzenie referencyjne zastępujemy nowym produktem; pusty zespół nie jest fizyczną częścią. Nieznanej funkcji Część2648 ani geometrii importu nie zgadujemy. Odbiór pełnego wariantu jest zablokowany, dopóki wymagane elementy pozostają nierozstrzygnięte.

Poza bieżącym MVP: generowanie wycięć pod okucia i dokładne styki/przejścia profili z zamkami lub zawiasami. Zachowujemy je jako przyszłe etapy. Wynik jest kompletną koncepcją montażową w uzgodnionym zakresie, a nie zatwierdzeniem dokumentacji produkcyjnej.

ARCHITEKTURA
1. CaseSpec: wersjonowane wejście — urządzenia, układ, wnętrze, grubości, wysokości korpusu/wieka, wariant rodziny. Jawne mm i osie XYZ. Osobno wymiary przestrzeni użytkowej, konstrukcji ze sklejki i pełny gabaryt z okuciami/kołami.
2. TemplateManifest: wersjonowana definicja rodziny i ról wszystkich elementów. Stabilne identyfikatory semantyczne, np. base/front/handle/left; numery węzłów CAD tylko jako mapowanie konkretnej kopii dokumentu.
3. Graf zależności: CaseSpec → płyty i płaszczyzny ścian → krawędzie/naroża → okucia i pary. Płyty zmieniają dwa wymiary przy stałej grubości; profile długość cięcia przy stałym przekroju; katalogowe okucia są bryłami sztywnymi, bez skalowania.
4. AnchorSpec: ściana, lokalne osie u/v/n, krawędź odniesienia, odsunięcia, orientacja i tryb umieszczenia: od krawędzi, wyśrodkowanie lub jawny udział długości. Zamki i zawiasy mają wspólną kotwicę pary góra/dół. Koła i gniazda wspólny plan X/Y w pozycji zamkniętej; RP_DisplayGap służy wyłącznie prezentacji.
5. Planner: deterministyczny plan różnic przed zapisem. UI, CLI i AI używają jednego kontraktu i walidatorów. AI może proponować specyfikację i mapowanie, lecz nie wykonuje dowolnego kodu w CAD.
6. Executor: jeden wykonawca zapisujący, oczekiwana rewizja, kopia ICS, dziennik operacji, klucz zapobiegający duplikatom. Kontrola po wykonaniu, zapis i ponowne otwarcie. Snapshot zawiera wersję wejścia, szablonu i reguł.
7. Zmiany ręczne: porównanie ostatniego planu, aktualnego modelu i nowego planu. Element zarządzany automatycznie / ręcznie z przypisaną kotwicą / nierozpoznany. Konflikt pokazujemy przed zmianą; nic nie wraca po cichu do poprzedniej pozycji. Nieprzypisane części zostają zachowane i wymagają przeglądu.

TESTY NAJPIERW
ROC-19: najpierw kontrakty i trzy syntetyczne przypadki A/B/C; dane testowe nie udają specyfikacji producentów. Testy nowych funkcji mają pokazać RED z powodu brakującej reguły, następnie minimalna implementacja GREEN i refaktoryzacja. Nie zmieniamy wzorca oczekiwanego tylko po to, by test przeszedł. Obecny czytnik i jego 29 testów pozostają bazową regresją.
Dla A/B/C: zmiana X/Y/Z osobno i łącznie, powrót do rozmiaru wyjściowego, zgodność góra/dół, stałe grubości i gabaryty okuć, poprawne kotwice, kompletność ról, parowanie, zapis/otwarcie. Do tego ręczne przesunięcie/dodanie/usunięcie, konflikt UI–AI, ponowienie po timeout i awaria w połowie operacji. Niedopuszczalny zbyt mały wymiar ma dać czytelny błąd bez uszkodzenia kopii. Oczekiwany kontakt montażowy rozróżniamy od kolizji; brak wycięć nie może być ukrytym zaliczeniem testu produkcyjnego.

HARNESSY I AGENCI
H0 wejście i jednostki; H1 mapowanie szablonu/katalogu; H2 geometria i kotwice; H3 plan zmian i zachowanie pracy ręcznej; H4 wykonanie/snapshot/odzyskanie; H5 niezależny odbiór; H6 ocena zachowania AI.
Sol medium: opisy i kandydaci mapowania; Sol high: implementacja; Astra high: trudne reguły i przegląd; xhigh tylko złożone wyjątki. Obliczenia, pomiary i bramki zapisuje kod. Recenzent ma własny odczyt i nie zapisuje CAD. Na początek jeden koordynator z etapami, nie wiele agentów jednocześnie modyfikujących dokument.

STROJENIE
Wersjonujemy reguły, prompty, schematy, model i ustawienia. Logujemy wejścia przez referencje/hash, narzędzia, wynik, czas, zużycie jeśli dostępne i decyzję odbioru. Zestaw do rozwijania oddzielamy od zestawu odbiorowego. Każdy błąd zamieniamy w regresję; nową wersję porównujemy offline i na kopii przed włączeniem. Harness stroimy progami i regułami, a nie obniżaniem kryteriów. Fine-tuning modelu nie jest potrzebny na start; wrócimy do niego dopiero, gdy pomiary wykażą powtarzalny problem mimo dobrych narzędzi i instrukcji.

KOLEJNOŚĆ: ROC-19 (TDD) → ROC-15 (kontrakt) → ROC-16 (płyty/kotwice) → ROC-17 (rodziny okuć) → ręczne zmiany + ROC-20/22 (wykonanie i odzyskanie) → ROC-26 (AI przez ograniczone MCP) → ROC-34 (odbiór A/B/C). Excel ROC-18, eksporty ROC-21 i materiały rozwijamy po stabilnym rdzeniu. Nie oznaczamy istniejących epików jako ukończone tylko dlatego, że działa fragment MVP.

## Uszczegółowienie kontraktów i niezmienników

UZUPEŁNIENIE CORE / TDD — 21.10.2026
CaseSpec wersjonowany: case_id, schema_version, revision, template_version, devices/instances, orientation, arrangement, clearances, partitions, accessory_compartments, panel_thickness, lid/base dimensions. Rozszerzalny model wielu urządzeń; pierwszy UI i fixture A/B/C mogą pozostać przy jednym typie urządzenia powielonym w osobnej skrzyni.
Jawne mm, prawoskrętne osie XYZ i rozdział: obrys urządzenia, wolna przestrzeń wnętrza, zewnętrzny obrys sklejki, pełen obrys z profilem/okuciami/kołami. Nie używać jednego pola „wymiary skrzyni” do tych trzech znaczeń.
Osobne kontrakty: TemplateManifest, AnchorSpec, PartDefinition, PartOccurrence, ChangePlan, ManualOverride, ExecutionReceipt. Oddzielić identyfikator typu, wystąpienia, rolę semantyczną i aktualny uchwyt/ścieżkę CAD. Dla wymiarów zapisać źródło, pewność/stan potwierdzenia i odnośnik do materiału wejściowego. W testach dane jawnie syntetyczne.
UI/Excel/CLI/MCP używają wspólnej walidacji i rewizji. SQLite przechowuje zatwierdzony stan; dokument CAD ma własny odczyt stanu i fingerprint. Brak dwóch niezależnych prawd: rozbieżność oznacza drift do uzgodnienia, a nie automatyczne nadpisanie.
TDD: migracja wersji schematu, brak jednostki, NaN/inf, nieznana orientacja, niepoprawne grubości, ujemny prześwit, nieobsługiwany wariant, brak lub duplikat ID, stale expected_revision, rozróżnienie wymiarów użytkowych i transportowych. Najpierw zamrozić kontrakty ROC-19, potem implementować. Pełny szablon nie może wyłączać istniejących ograniczeń szkieletu.

UZUPEŁNIENIE CORE / TDD — 21.10.2026
Najpierw testy ROC-19 i kontrakt ROC-15; pełny manifest szablonu w osobnym zadaniu CORE. Zaimplementować kanoniczne układy korpusu i wieka, ścian i krawędzi, wspólną płaszczyznę zamykania oraz graf zależności od wymiarów skrzyni.
AnchorSpec: wall_id, datum (płyta/profil/płaszczyzna zamykania), lokalne u/v/n, semantyczna krawędź i offset w mm, tryb stały/centrowany/proporcjonalny, orientacja. P = O + u*a + v*b + n*c; kotwa od prawej ma a = szerokość ściany − odsadzenie. Nie opierać trwałych kotew wyłącznie na numerach powierzchni BREP.
Płyty: dwa wymiary i położenie z reguł łączenia, grubość stała podczas zmiany gabarytu. Profile: stały przekrój i zmienna długość; szczegółowe styki poza MVP (ROC-41). RP_DisplayGap jest transformacją prezentacji, nie zmienia parowania ani wysokości zamkniętej skrzyni.
Osobny spike ICAPI: zapisać natywne równania/parametry, przebudować, zapisać/otworzyć ICS i zmienić wymiar w tabeli IronCAD. Jeśli API umożliwia tylko regenerację przez dodatek, jawnie pokazać ten tryb; nie nazywać go natywną zależnością. Zmiany bezpośrednio w CAD muszą być wykrywane przed kolejnym planem.
Odbiór: X/Y/Z osobno i razem, minimalne dopuszczalne wymiary, round-trip do pierwotnego rozmiaru, stała grubość i przekrój, poprawna rama każdej ściany, brak odwróceń normalnych, odczyt po ponownym otwarciu. Na razie nie skalować całej sceny i nie dodawać wycięć.

UZUPEŁNIENIE CORE / TDD — 21.10.2026
Rozszerzenie istniejącego adaptera o pełny plan montażu, a nie dowolne skrypty. UI, CLI i MCP wywołują te same walidowane operacje. Jeden worker zapisuje CAD; pozostali agenci mają tylko odczyt lub przygotowują propozycję.
Plan zawiera plan_id, expected_revision, fingerprint dokumentu, wersję manifestu/reguł, jawne utworzenia/zmiany/usunięcia własnych wystąpień i warunki sprawdzenia. Wykonanie tylko na kopii. Podgląd zmian i uzgodnienie ręcznych modyfikacji ROC-40 przed zapisem. Zakres pełnego szablonu osobny od allowlisty szkieletu.
Dziennik: planned → applying → saved → reopened_verified → registered; dodatkowo failed i outcome_unknown. Snapshot powiązany z planem, specyfikacją, rewizją, szablonem, raportem i hashami. Transakcja SQLite nie obejmuje pliku ICS — potrzebna procedura uzgodnienia po awarii między ich zapisami.
TDD: awaria na każdej granicy, timeout po możliwym wstawieniu, utrata COM, restart procesu, powtórzenie plan_id, konflikt wersji, inny aktywny dokument, niezapisane zmiany, rozbieżność hash/ścieżki. Po nieznanym wyniku najpierw odczyt i uzgodnienie, dopiero decyzja o ponowieniu. Brak duplikatów, brak zapisu do oryginału, brak fałszywego sukcesu. Kooperacyjny timeout nie przerywa zawieszonego COM — osobna strategia izolacji procesu i odzyskania hosta wymaga testu.
Odbiór: raport dowodzący zgodności ICS–snapshot–SQLite po ponownym otwarciu. Zapis/odzyskanie współpracuje z ROC-22, ale nie zastępuje uzgadniania ręcznych zmian geometrii ROC-40.

## Plan testów

PLAN TDD CORE — 21.10.2026
To zadanie rozpoczynamy przed implementacją ROC-16/17. Dotychczasowe zależności od tych zadań dotyczą końcowego odbioru GREEN, nie przygotowania testów RED. Otwory i wycięcia z pierwotnego opisu przechodzą poza obecny MVP.

Trzy osobne przypadki syntetyczne, nie dane producentów. Każdy ma osobny case_id, specyfikację i kopię ICS. Stałe: luz przy ścianie 20 mm, odstęp między urządzeniami 10 mm, przegroda 9 mm, sklejka 9 mm. Grubość 9 mm jest daną testową; wzorzec Epson ma odczytaną inną grubość i nie wolno podmienić jej automatycznie.
A: 2 urządzenia 300×220×100 mm, XYZ, wzdłuż X; komora +X: 100×300×80; pokrywa 50. Oczekiwane wnętrze 808×340×140; zewnętrzny obrys sklejki 826×358×158 mm.
B: 2 urządzenia 600×350×160 mm, YXZ, wzdłuż X; komora +Y: 120×700×120; pokrywa 70. Wnętrze 759×809×200; sklejka 777×827×218 mm.
C: 2 urządzenia 500×450×250 mm, XZY, wzdłuż Z; komora +X: 150×400×200; pokrywa 80. Wnętrze 739×440×959; sklejka 757×458×977 mm. Test piętrowania nie zatwierdza nośności ani sposobu podparcia.
Wymiary komory podane zgodnie z kontraktem obecnego konfiguratora: szerokość w osi wybranej ściany, drugi wymiar i wysokość. Przy zamrażaniu fixture zapisać dokładne pola JSON, aby uniknąć niejednoznaczności.

KROK 1 — RED
Przygotować niezależnie wyliczone oczekiwania, kontrakty i testy: układ, rama ściany, kotwa narożnika, uchwytu i pary zamka. Pokazać, że test nowej funkcji pada z właściwego powodu. Obecne działające testy układu pozostają zieloną regresją. Nie wymuszamy RED na gotowej funkcji. Nie zmieniać oczekiwań, aby dopasować je do implementacji.

KROK 2 — GREEN ETAPAMI
1. Zmiany X/Y/Z osobno i razem, wzrost/zmniejszenie i powrót do wymiaru wyjściowego.
2. Spójny obrys korpusu i wieka; RP_DisplayGap nie wpływa na zamkniętą konstrukcję.
3. Stała grubość płyt przy zmianie gabarytu; stały przekrój profili; niezmienna geometria sztywnych okuć.
4. Uchwyty względem ściany i krawędzi; narożniki na właściwych narożach; normalne i orientacje poprawne. Parowanie zamków, zawiasów oraz kół/gniazd.
5. Wszystkie fizyczne elementy szablonu rozliczone w manifeście. Pusty 2643 nie jest zawiasem do zakupienia. Brak elementu lub niejednoznaczna tożsamość blokuje pełny odbiór.
6. Ręczne przesunięcie, dodanie i usunięcie: brak cichego nadpisania. Konflikt UI–AI przed zapisem.
7. Ten sam plan wykonany ponownie nie dubluje części. Awaria przed/po zapisie ICS i przed/po wpisie SQLite ma jednoznaczne odzyskanie; timeout o nieznanym wyniku nie powoduje ślepego ponowienia.
8. Zbyt mała skrzynia, brak miejsca na uchwyt, NaN/inf, pomylone jednostki i brak źródła wymiaru — czytelna odmowa bez zmiany oryginału.

KROK 3 — NATYWNY ODBIÓR
A: pełna ścieżka automatyczna na kopii. B: konstruktor zmienia odsadzenie uchwytu, potem zmiana wymiarów i zachowanie decyzji. C: ręcznie dodany element, przypisanie kotwy i ponowne przeliczenie; dodatkowo przypadek nierozstrzygnięty musi zostać zablokowany.
Dla każdego: niezależny odczyt API, pomiary przed zapisem i po ponownym otwarciu, porównanie ICS/snapshot/rewizji SQLite. Dodatkowo zmiana wymiaru z natywnej tabeli parametrów: dopiero jej poprawny wynik pozwala nazwać zależności natywną parametryzacją.

DOWÓD ODBIORU
Raport zawiera wersje specyfikacji, szablonu, kodu i reguł, hash źródła/kopii, stan przed/po, wykryte odstępstwa i wynik każdego sprawdzenia. Tolerancje testowe ustalamy jawnie przed uruchomieniem; nie są tolerancjami produkcyjnymi. AABB nie dowodzi braku kolizji. Oczekiwany kontakt montażowy ma własną regułę; wycięcia i dokładne styki są NOT RUN / poza MVP. Błąd zapisu, zgubiona część lub nadpisana zmiana ręczna blokuje odbiór niezależnie od liczby zielonych testów.
Recenzent Astra ma odczyt wyników i niezależne pomiary; nie modyfikuje CAD. Tomasz zatwierdza reguły montażu oraz przydatność końcowego wyniku.

Status tej aktualizacji: plan i kryteria; nowe testy core nie zostały jeszcze zaimplementowane ani zaliczone. Baza regresji: istniejący czytnik i 29 testów parts. Architektura nadrzędna: ROC-6.

## Sterowanie i ocena agentów

UZUPEŁNIENIE CORE / TDD — 21.10.2026
Stan: obecny MCP/API nie oznacza jeszcze samodzielnego agenta działającego w tle. Budujemy jeden koordynator etapów, a dopiero po stabilnym silniku uruchamiamy AI przez te same kontrakty co UI/CLI.

H0 — wejście: źródła i jednostki, liczba/orientacja, akcesoria, kompletność. Wynik CaseSpec; brak wymiarów nie jest uzupełniany zmyśleniem.
H1 — szablon: mapowanie definicji/wystąpień do ról, rama i status zatwierdzenia; pełny manifest. Nieznany element nie znika z modelu.
H2 — geometria: czysty kod liczy płyty, profile, kotwy i pary; zwraca plan oraz diagnostykę. LLM nie oblicza transformacji na oko.
H3 — zmiany: porównanie planu i aktualnego CAD, wykrycie zmian ręcznych, konfliktów wersji i podgląd; decyzja konstruktora w sporach.
H4 — wykonanie: jeden writer, ograniczone narzędzia, kopia ICS, journal, snapshot, idempotencja i odzyskanie.
H5 — odbiór: niezależny odczyt, testy niezmienników, pomiar przed/po otwarciu; PASS/PARTIAL/FAIL i NOT RUN dla odłożonego zakresu. Recenzent nie zapisuje CAD.
H6 — ewaluacja AI: stały zbiór zadań, spodziewane plany/odmowy, poprawność użycia narzędzi, skuteczność, czas, liczba wywołań, dostępne zużycie modeli, odsetek fałszywych zatwierdzeń.

Role: Sol medium do propozycji opisów/mapowania; Sol high do implementacji; Astra high do niejednoznacznej geometrii i niezależnego przeglądu; Astra xhigh tylko do wyjątków. Kryteria pomiarowe i blokady zapisuje kod. Oddzielić rolę recenzenta od procesu mającego uprawnienia zapisu.

Sterowanie: konfiguracja wersjonowana — model, effort, prompt_version, schema_version, rule_pack, allowlista narzędzi, max_tool_calls, timeout, max_retries, polityka eskalacji i zakres zatwierdzenia. Log: run/plan/case IDs, referencje/hash wejść, wersje, wywołane narzędzie, rezultat, błąd i decyzja; bez sekretów i niepotrzebnych treści e-maili. Odwołanie/stop nie może przerywać zapisu w połowie bez stanu recovery.

Strojenie: odtwarzalny zestaw rozwojowy plus osobny odbiorowy, zmiana jednej reguły/promptu naraz, porównanie wyników offline, potem próby na kopii. Każdy potwierdzony błąd staje się regresją. Nie modyfikować automatycznie reguł produkcyjnych na podstawie logu i nie obniżać progów dla zielonego testu. Fine-tuning modelu dopiero po wykazaniu powtarzalnego problemu i zebraniu zatwierdzonych przykładów; obecnie niepotrzebny.

TDD: prompt injection w nazwie części/załączniku, nieznane narzędzie, zbyt wiele prób, brak danych, niezatwierdzony katalog, konflikt rewizji, pominięta część, próba nadpisania ręcznej pracy, false PASS przy brakującym teście. Błąd integralności lub ciche pominięcie blokuje odbiór niezależnie od średniej skuteczności. Powiązania: ROC-6, ROC-19, ROC-20, ROC-40.

## Bramka wdrożenia

Nie przenosić całego projektu do innego stosu technologicznego. Osobny pakiet kontraktów i czystych obliczeń należy wydzielić w aktualnym backendzie, pozostawiając WinForms, MCP i adapter ICAPI. Jedna SQLite, migracje wersji i jawne uzgodnienie stanu CAD. Przed rozszerzeniem natywnych operacji wykonać spike API na kopii i utrzymać ograniczenia istniejącego szkieletu.

Panel powinien pokazywać: wersję specyfikacji/szablonu, stan mapowania części, plan różnic, właściciela ręcznych zmian, zakres walidacji, nierozstrzygnięte elementy, przebieg operacji i wynik odzyskiwania. Zielony status nie może oznaczać gotowości produkcyjnej, jeśli wycięcia lub technologia są poza zakresem.

Dokumentacja/plan: przygotowane. Nowe testy i implementacja core: NOT RUN / jeszcze do wykonania. Brak zmian źródłowego CAD i instalacji dodatku w ramach tego planowania.
