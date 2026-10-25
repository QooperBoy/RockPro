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
