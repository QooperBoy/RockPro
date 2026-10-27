# Studio → IronCAD 2027 — ROC-46

Zadanie: [ROC-46 — Generować kompletną skrzynię z kreatora w IronCAD 2027](https://linear.app/rock-pro/issue/ROC-46/studiocad-generowac-kompletna-skrzynie-z-kreatora-w-ironcad-2027),
podzadanie [ROC-20](https://linear.app/rock-pro/issue/ROC-20/rp-10-zbudowac-lokalny-adapter-i-kolejke-operacji-cad).
Status: **In Progress**. Pierwszy przyrost przygotowuje kompletny handoff i
kontrolę gotowości; pełny adapter montażu CAD pozostaje do implementacji.

## Docelowy rezultat

Konstruktor zapisuje rewizję w Studio, sprawdza plan i generuje nową skrzynię
w IronCAD 2027. Do CAD trafiają wszystkie wybrane parametry sekcji, rzeczywiste
okucia, profile, narożniki, podpory, koła/gniazda i wymagane obróbki. Nieobsługiwany
wybór daje konkretny błąd przed wykonaniem. Generator nie zmniejsza liczności,
nie podmienia SKU i nie pomija elementu, aby uzyskać sukces.

Aktualna zgoda na generowanie nie zmienia zakazu nadpisywania oryginałów.
Przed uruchomieniem trybu utrwalającego ICS trzeba potwierdzić aktualny zakres
zgody na zapis nowych plików; starsze skrypty prototypowe zapisują także w cleanup.
Nie uruchamiać ich jako niejawnego fallbacku przycisku Studio.

## Wykonane w pierwszym przyroście

- Kod bieżącego Studio połączono do izolowanej gałęzi `codex/t2-parametryzacja`.
  Snapshot kodu sprzed prac: `codex/snapshot-before-studio-cad-20261027`.
- `studio_cad.py`: plan `rockpro.studio-cad-plan/1` z ID/rewizją/SHA draftu,
  rewizją kompilatora i katalogu, hostem 2027/API29 oraz kontraktem rejestru.
  Plan rozlicza nominalne płyty, sekcje, złącza, wystąpienia, wszystkie wybrane
  definicje i intencje obróbek. Zachowuje właściciela każdej intencji.
- Wybrane, lecz nierozmieszczone części nie znikają z raportu. Brak wiedzy
  o wycięciu jest odróżniony od znanej recepty i braku jej natywnego powiązania.
  Recepta 27095 jest rozpoznana jako dostępna; nie jest zastępowana zamkiem.
- Ujęto także aktualne przełączniki konstrukcji, podpory, koła i gniazda.
  Kontrakt `studio_structure.py` przeniesiono jako kontrolowany snapshot
  z bieżącej pracy drugiego checkoutu, zachowując jego pliki. Naprawiono
  pomijanie przerw profili przy starszych rzędach zawiasów z `joint_id`.
- Plany zapisują się w tej samej bazie co drafty, w nowej tabeli. Kontrola
  rewizji działa podczas zapisu i przed wykonaniem. Samodzielne podmienienie
  planu i ponowne obliczenie SHA nie nadaje mu prawa wykonania.
- `studio_cad_jobs.py`: trwały dziennik operacji, idempotencja operation_id,
  jedno nierozstrzygnięte zlecenie i worker poza wątkiem HTTP/transakcją DB.
  Po awarii nie następuje automatyczne ponowienie operacji o nieznanych skutkach.
  Kwit musi potwierdzić dokładny SHA planu. Testowy executor nie jest CAD.
- Endpointy `wizard/native-plan`, `wizard/native-build`,
  `wizard/native-jobs/<id>` zachowują token sesji, Origin i ścisłe pola poleceń.
  Klient nie przekazuje ścieżki skryptu, DLL, pliku docelowego ani kodu do wykonania.
- Panel kreatora: „Sprawdź plan CAD”, rozliczenie części/lista braków,
  pobranie planu, przycisk generowania i odczyt statusu zlecenia.
  Edycja/wczytanie draftu unieważnia plan. Generowanie pozostaje niedostępne,
  dopóki cały plan nie jest wykonywalny.

**Ważna granica:** obecny kompilator nie ma zarejestrowanego pełnego adaptera
natywnego. Każdy rzeczywisty plan pozostaje `executable=false` z listą braków.
Nie wygenerowano nowego kompletnego ICS w tej rundzie. Kontrola bramek i kolejki
jest działającym kodem, nie dowodem ukończenia generatora.

## Dlaczego nie podłączamy wprost starego prototypu

1. Studio podaje wnętrze korpusu; T1 używa obrysu sklejki. Nominalne panele Studio
   nachodzą na siebie na krawędziach, a szczelina/formatki nie są jeszcze wynikiem
   receptury konstrukcyjnej. Wykonawca musi obliczyć je przed CAD.
2. Studio zapisuje ramę ściany UVN. Pozycja wycentrowanej siatki nie jest natywną
   kotwą. Dla każdego źródła potrzebne jest jawne przekształcenie source→mount.
3. Stary pełny T1 ma H7159 + 17251S + 270836. Naprawiona Scene14 ma H7159 +
   L905/915 + 27095. Studio może wybierać 17251S + 27095: źródła i kontury są
   dostępne, ale ten zestaw nie ma wspólnego wykonawcy ani mapy nowych ID.
4. Wizualne połówki zatrzasku/zawiasu są prezentacją. CAD wymaga rzeczywistych
   pełnych połówek i ich niesymetrycznych datumów, bez kadrowania siatki.
5. Stary T1 ma stałe liczności i zakresy. Studio obsługuje 1–16 uchwytów na
   ściankę; nie wolno po cichu sprowadzić wyboru do dwóch.
6. Historyczne `lid_height_override_authorized=true` nie jest zgodą na nowy
   projekt. Stosować aktualny `height_override` z zapisanego draftu.

## Kolejne przyrosty ROC-46

| Etap | Zakres | Dowód odbioru |
|---|---|---|
| 1 — bieżący | Plan, rozliczenie i kolejka | Odmowa niekompletnego/zmienionego planu, zachowany draft, brak wykonania CAD |
| 2 | Kontrakt wymiarów T1 i manifest rzeczywistych zasobów | Ramy wszystkich części; poprawne wymiary cięcia i styki bez wzrostu gabarytu |
| 3 | Montaż okuć i wycięcia | Każde wybrane wystąpienie ma nowy native_id, komplet operacji i wspólną kotwę |
| 4 | Profile, narożniki, podpory i transport | Poprawna orientacja, przerwy przy zawiasach, osadzenie gniazd, zgodny rozstaw kół |
| 5 | Uruchomienie z kreatora i odbiór natywny | Model zgodny z planem, resize→powrót, osobno zapis/reopen gdy dozwolone |
| 6 | Szafa i konstrukcja trzyczęściowa, dalsze moduły | Osobne adaptery i zakresy; brak podmiany rodziny na T1 |

Recepty i moduły do użycia: `core_case/t1_mounting.py`, `machining_rules.py`,
`scene_structure.py`, `prototype_t1_machining.py`, `prepare_scene14_repair.py`,
`prepare_t1_structure.py` oraz natywne operacje kopiowania/odejmowania.
Ujemne cechy należą do płyt/profili, nie do wnętrza katalogowego okucia.
Wspólny rejestr zachowuje koła, podpory i gniazda w etapie 6.

## Uruchomienie i dowody

Studio można jawnie skierować na istniejącą bazę przez `--database <projects.sqlite3>`.
Nie kopiować danych klienta do Gita ani nie zastępować wdrożenia demonstracją.
Nowa tabela jest migracją addytywną. Wyniki testów i przeglądu UI są w
`artifacts/studio-cad-20261027/`; pełny harness w `artifacts/verification/`.
Testy kolejki używają syntetycznego executora; natywne wykonanie tego przyrostu
pozostaje **NOT RUN**. Zadanie ROC-46 pozostaje otwarte.

Końcowa regresja: **PASS**, 12 kroków,
`artifacts/verification/20261027T214105313652Z/results.json` — 775 wykonań testów
unittest w tym konkretnym przebiegu, bez kompilacji i operacji CAD.
Nowe testy planera/HTTP: 9; kolejki: 11; konstrukcji: 5.

Sprawdzono rzeczywisty istniejący draft rewizji 5: 10 płyt nominalnych,
66 elementów montażu, 11 wybranych definicji. Plan objął również profile,
narożniki, podpory, koła i gniazda. Zwrócił 21 jawnych braków i nie uruchomił CAD.
Edycja nazwy bez zapisu unieważniła plan oraz jego pobieranie. Konsola nie
zgłosiła błędów JavaScript. Później drugi klient zapisał rewizję 6 — nie jest
to uszkodzenie ani zmiana wykonana przez ten przyrost. Wszystkie 16 historycznych
wersji obecnych przed sprawdzeniem pozostało identycznych. Wykonano backup SQLite.

Dowód UI/SQLite: `artifacts/studio-cad-20261027/ui-result.json`, plan przykładowy
`example-plan.json`, potwierdzenie zadania `ROC-46-created.png`. Po teście
interfejs przestał odpowiadać na sterowanie karty; próba odczytu okna aplikacji
wymagała zgody i wygasła. Nie wykonano dalszych działań w oknie. Nie jest to
pełny odbiór wizualny. Własny serwer testowy zatrzymano; działającego wcześniej
Studio użytkownika i hosta CAD nie przeładowywano. Kod jest w tej gałęzi,
nie został wdrożony do drugiego checkoutu.
