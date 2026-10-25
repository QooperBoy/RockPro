# ROC-40 — pomiar ręcznej zmiany w rzeczywistym CAD

Źródło wymagań odczytane 24.10.2026:
[ROC-40](https://linear.app/rock-pro/issue/ROC-40/core-zachowac-reczne-zmiany-cad-przy-ponownym-przeliczaniu-skrzyni).
Nie zmieniano statusu ani nie publikowano komentarza.

## Bieżący przyrost

core_case/native_changes.py odczytuje macierze świata jawnie wskazanych
wystąpień za pomocą SDK. Łączy semantyczne ID, grupę, natywne ID, GUID dokumentu,
pochodzenie źródła i parametry sceny. Nie dopasowuje po nazwie ani indeksie drzewa.
Porównanie nie zapisuje CAD. Przesunięcie lub obrót któregokolwiek obserwowanego
członka daje SYMMETRY_MANUAL_CONFLICT, zgodnie z istniejącym planerem.
Nawet zgodne przesunięcie całej grupy wymaga decyzji, a nie automatycznej zgody.

Zmiana parametrów sceny daje NATIVE_REPLAN_REQUIRED: najpierw trzeba obliczyć
nowe oczekiwane pozycje. Nie porównujemy legalnego resize z nieruchomą bazą,
aby błędnie nazwać go ręcznym przesunięciem. Brak odczytu, niepełny lub
zduplikowany zestaw ID blokuje proces; nie udaje rozpoznania dodatku/usunięcia.

Cztery testy obejmują przesunięcie jednego uchwytu i niezmienność danych,
obrót/całą grupę, tolerancję pomiaru/resize oraz złą tożsamość/niepełny zestaw.

## Próba natywna

scripts/prove_native_manual_change.py przyjmuje przypięty hash i raport
prototypu. Bez --native pokazuje tylko plan. Własna kopia trafia do artifacts;
widoczna skrzynia nie jest przesuwana. Test obserwuje tylko dwa H7159, przesuwa
jeden o 12 mm w X, oczekuje blokady, sprawdza brak automatycznego cofnięcia,
zapisuje zmianę i sprawdza ją po ponownym otwarciu.

Pierwsze dwie próby zatrzymały się na błędzie otwarcia, ponieważ nowy skrypt
przekazywał ścieżkę względną do SDK. Komunikat IronCAD sugerował format pliku
lub utworzenie pliku tymczasowego. Poprawiono przyczynę: source i output są
rozwiązywane do pełnych ścieżek przed operacją. Usunięto zbędne obejście z
zamykaniem widocznej dostawy; nie był to potwierdzony konflikt GUID.
Nieudane kopie pozostają w artifacts/native-manual-change-20261024-01/ i -02/.
Osobno potwierdzono poprawność otwarcia końcowej dostawy po zapisie widoku.

## Granice

To kontrolowany dowód dwóch wystąpień, nie cały ROC-40. Moduł nie jest jeszcze
wpięty w działający panel/MCP. Nie ma pełnego trójstronnego porównania
poprzedni plan–aktualny CAD–nowy plan, akceptacji nowych kotew, ekranu decyzji,
rozpoznawania dowolnych ręcznych dodatków/usunięć ani odbioru B/C z ROC-19.
Brak pełnego pokrycia musi pozostać jawny. Nie zmieniano expected_revision,
nie oznaczono zgody montażowej ani produkcyjnej.

Następny krok: trwały sidecar stabilnych tożsamości pełnej rodziny, obliczenie
nowego oczekiwanego planu dla resize i dopiero potem ekran decyzji, który używa
istniejących wersji/CAS. Nie przenosić syntetycznych tokenów zgody na model Epson.

## Wynik natywny — PASS

artifacts/native-manual-change-20261024-03/manual_change_receipt.json:
jedno rzeczywiste przesunięcie H7159 o 12 mm w X, konflikt przed i po
zapisie/otwarciu, brak zapisu/cofnięcia przez guard, niezmieniony oryginał
prototypu, zamknięte własne dokumenty, aktywny dokument użytkownika zachowany.
Kopia ze zmianą jest zachowana wyłącznie w prywatnych artifacts.
To nie jest jeszcze test nowego planu przy zmianie szerokości ani pełny ROC-40.

PASS pełny harness po przyroście ROC-40:
artifacts/verification/20261024T155804147812Z/results.json.

## Kontynuacja: wszystkie uchwyty i zmiana gabarytu

review_handle_update / guard_handle_update porównują stan bazowy, aktualny
pomiar i propozycję nowych kotew dla całej zadeklarowanej grupy H7159.
Oczekiwane pozycje są ponownie obliczane według reguł przy aktualnych wymiarach,
więc prawidłowe przemieszczenie po zmianie gabarytu nie udaje ręcznej edycji.
Po zmianie gabarytu nadal można wykryć dodatkowy ruch pojedynczego uchwytu.
Wynik zawiera podgląd nowych pozycji, bez wykonania i bez zgody pełnej skrzyni.

Obsługiwany jest przypięty układ handles_per_wall=1/2, stabilne logiczne ID
lewy/prawy + numer i natywne ID z raportu. Baseline_sidecar.json zapisuje mapę,
źródłowy SHA, GUID i początkowe pomiary. To nie jest zatwierdzony sidecar
pełnego katalogu z ROC-42 i nie można go z nim zamieniać.

Polecenie próby: scripts/prove_handle_revision.py --source ... --receipt ...
--output-dir ... --native. Sam plan nie otwiera ani nie zmienia CAD.
Próba na kopii zmienia L/D/B, sprawdza legalne przeliczenie czterech uchwytów,
a potem przesuwa ostatni handles/right/2 o 12 mm wzdłuż boku. Zmiana blokuje
propozycję kolejnej zmiany szerokości i nie jest automatycznie cofana.

Nowe testy sprawdzają rozróżnienie resize/ręczne przesunięcie czwartego
uchwytu, podgląd nowych pozycji i brak modyfikacji wejścia. Nie interpretujemy
dowolnych wyrażeń wpisanych w CAD: nieznane formuły wymagają przeliczenia przez
adapter, zamiast zgadywania jednostek i wartości.

Pierwsza próba zachowała przesunięcie poprawnie, lecz runner porównywał całe
JSON-y dokładnie. Po otwarciu resztkowe przesunięcie X było rzędu 1e-13 mm.
Weryfikację trwałości poprawiono na porównanie tożsamości i wektora z tolerancją
0,003 mm. Próg wykrywania rzeczywistej zmiany pozostał 0,05 mm.

Nadal nie ma ekranu decyzji, akceptacji odsadzenia ani integracji guardu z
aktywną DLL/MCP. Zakres obejmuje uchwyty, nie płyty, profile i dowolne dodatki.
Nie oznaczamy całego ROC-40 jako ukończonego.

PASS natywny pełnej grupy czterech uchwytów:
artifacts/handle-revision-20261024-02/manual_change_receipt.json.
Legalny resize L/D/B nie powoduje konfliktu; dodatkowe 12 mm w Y na
handles/right/2 powoduje konflikt przed i po zapisie/otwarciu. Stan ręczny
zachowany, widoczny prototyp i aktywny kontekst bez zmian, własne dokumenty
zamknięte. Dla nowej szerokości powstaje tylko podgląd kotew, bez zapisu CAD.
PASS pełny harness: artifacts/verification/20261024T184304320032Z/results.json.

## 25.10 — trwałe decyzje i parametryczne odsadzenie H7159

`core_case/handle_decisions.py` porównuje bazę, aktualny zapisany pomiar oraz
nowe kotwy całej przypiętej grupy. Dostępne decyzje: zachowanie bezwzględnych
pozycji, powrót do reguły, przyjęcie zmierzonych odsadzeń albo pozostawienie
elementu ręcznego. Nie ma domyślnej akceptacji konfliktu. Przyjęte odsadzenie
jest dodawane do wyrażenia kotwy, a nie zamieniane na nieruchomą współrzędną.

Kontrola odmówi odsunięcia od płaszczyzny montażu, braku marginesu lub zbyt
małego rozstawu. Obrót wymaga osobnej kontroli; wykonawca translacji nie resetuje
obróconego ręcznie uchwytu. Element pozostawiony ręczny nadal wymaga zatwierdzonej
kotwy przed pełnym odbiorem. Stan nie obejmuje nieznanych dodatków ani innych rodzin.

`mcp/handle_decision_service.py` zapisuje niezmienne wersje decyzji i dowody w
tej samej SQLite co UI. Wymaga hasha podglądu, niezależnych rewizji karty/decyzji,
referencji decyzji oraz zgodnego hasha zapisanego źródła. Nie odświeża tokenów
po konflikcie. To oświadczenie operatora, nie uwierzytelniona zgoda produkcyjna.
Narzędzie zapisu nie jest dostępne przez bramkę propozycji AI.

WinForms `HandleDecisionForm` jest dostępny w źródle panelu Układ urządzeń pod
przyciskiem „Porównaj ręczne zmiany”. Pokazuje bazowe, zmierzone i proponowane
pozycje, wyróżnia zmianę ręczną i wymaga jawnej decyzji oraz uwagi konstruktora.
Wczytuje zapisany pomiar JSON lub wcześniejszą decyzję. Nie jest to bieżący odczyt
otwartej sceny; zapis nie wykonuje ruchu CAD. Automatyczne zebranie pomiaru w tym
oknie oraz pełne podłączenie do wykonawcy całej skrzyni pozostają NOT RUN.

PASS: 5 testów logiki odsadzeń, 4 testy SQLite/MCP (trwałość, oba CAS, hash
źródła/podglądu, brak uprawnień zapisu AI). PASS: pełny harness, kompilacja i
okna PL/EN 100/150 — artifacts/verification/20261025T071930707045Z/results.json.
Osobna kontrola okna z czterema uchwytami na obu ścianach: log i obrazy w
artifacts/overnight-20261024/handle-ui/. Nowa DLL nie została załadowana do hosta.

PASS natywny mechanizmu odsadzeń:
artifacts/overnight-20261024/handle-offset-native-01/verification.json.
Próba na nowej kopii zachowała ręczne 12 mm prawego uchwytu: zapis decyzji w
odrębnej bazie QA → wyrażenia kotew → zapis/otwarcie → zmiana L/D/B → ponowny
zapis/otwarcie. Źródło bez zmian, własne dokumenty zamknięte, kontekst użytkownika
zachowany. Wynik nie jest decyzją konstruktora ani pełnym odbiorem B/C i ROC-40.
Powtarzalny runner: scripts/prove_handle_offset_decision.py; bez --native tylko plan.

## 25.10 — pomiar SDK w oknie decyzji

Dodano „Zmierz uchwyty z IronCAD” i `measure_handle_reconciliation`. Operacja
używa bazy i mapy stabilnych ID z wcześniejszej zapisanej decyzji; nie zgaduje
pierwszego powiązania i nie wyszukuje podobnego modelu po nazwie.
`core_case/handle_measurement.py` dołącza wyłącznie do już otwartego pliku o
pełnej ścieżce i zgodnym GUID. Nie uruchamia, otwiera, zapisuje, zamyka ani
aktywuje dokumentów. Zbiera pozycje dwukrotnie i odrzuca zmianę w trakcie.
Flaga niezapisanych zmian jest zachowana i pokazana w oknie.

Pomiar dostaje niezmienny identyfikator w SQLite, związany z kartą, rewizją
decyzji, bazą, pozycjami i hashem pliku. Zapis z tym identyfikatorem ponownie
mierzy scenę. Zmiana pozycji, danych pomiaru, pliku lub rewizji blokuje zapis;
UI nie ponawia operacji ani nie odświeża tokenów. Nieaktualny pomiar wymaga
ponownego użycia przycisku. Zapisy offline nadal są oświadczeniem operatora,
bez flagi potwierdzonego odczytu SDK. Żaden zapis decyzji nie stosuje jej w CAD.

Fingerprint pomiaru zaokrągla translację do 0,001 mm i obrót do 1e-9, aby
szum COM nie udawał edycji. To token świeżości obserwacji, nie podpis geometrii.
Nie blokuje człowieka przed dalszą edycją; przyszły wykonawca nadal musi zrobić
kontrolę bezpośrednio przed zastosowaniem. Zakres pozostaje ograniczony do H7159.

PASS: 5 testów czytnika, 7 SQLite/MCP, pełny harness/build/UI
artifacts/verification/20261025T074755934057Z/results.json. Okna PL/EN 100/150
obejmują brak automatycznej decyzji, przeniesienie identyfikatora pomiaru,
odmowę starego odczytu, brak ponowienia i unieważnienie dowodu po błędzie.

NOT RUN: świeża próba tej ścieżki w hoście. Runner
scripts/prove_handle_live_measurement.py przygotował wyłącznie odrębną kopię
modelu/bazy w artifacts/handle-live-measurement-20261025/native-01. Próba
zatrzymała się przy dołączeniu do aplikacji (GetActiveObject, 0x800401E3),
przed otwarciem dokumentu. Uruchomiony pojedynczy host nie udostępnił COM;
nie powielano instancji ani rejestracji. Wcześniejszy natywny PASS odsadzenia
nie zastępuje tego dowodu. Nowa DLL nie została wdrożona do hosta.


## 25.10 — wątek okna decyzji przy braku kontekstu hosta

Regresja HandleDecisionForm odtworzyła dostęp do kontrolek z wątku roboczego
przy braku zastanego kontekstu WinForms. Konkretny FAIL w UpdateButtons:
artifacts/verification/20261025T091728777515Z/ui-checks.log.
Run wymaga teraz wątku właściciela i instaluje kontekst WinForms przed await.
Backend nadal działa poza wątkiem interfejsu. Zakres dotyczy obsługi okna;
nie zmienia algorytmu CAD, decyzji konstruktora ani uprawnień narzędzi.

PASS: pomiar, zapis i błąd pomiaru bez zastanego kontekstu, przy włączonym
wykrywaniu dostępu między wątkami. Test potwierdza pojedyncze wywołanie,
zachowanie rewizji karty/decyzji i uwagi konstruktora, brak automatycznej decyzji
po pomiarze oraz usunięcie starego tokenu i podglądu po błędzie odczytu.
Pełny harness/build/UI PL/EN 100/150 PASS:
artifacts/verification/20261025T091815069926Z/results.json.
To izolowane próby z backendem testowym, bez SDK, SQLite klienta i ruchu CAD.
Nowa DLL w hoście i świeży odczyt natywny nadal NOT RUN.
