# ROC-33 — zmiana rewizji po rozkroju

`mcp/material_revisions.py` zapisuje niezmienny pakiet planu w tej samej SQLite:
zapotrzebowanie/BOM, arkusze, technologię, drzewo cięć i hash niezależnej kontroli.
Wiąże go z rewizją karty i układu, bieżącym BOM, hashem zapisanego źródła oraz
ostatnim snapshotem (ID, zarejestrowany i aktualny hash pliku). Tworzenie sprawdza
BOM ponownie w transakcji po obliczeniach; nie publikuje planu po równoczesnej zmianie.

`get_material_plan` wylicza effective_status: ready → outdated, started →
changed_in_progress, jeśli wejście się zmieniło. Nie przepisuje starego planu.
`start_material_plan` ma CAS i odrzuca przestarzały plan; zapisuje tylko oświadczenie
operatora o rozpoczęciu, nie steruje maszyną. Dane syntetyczne pozostają jawnie
syntetyczne, a production_approved=false. Niezapisana pamięć CAD nie jest tu
odczytywana; wymagany jest kontrolowany snapshot przed przekazaniem do produkcji.

`record_material_progress` dopisuje produced (group_index, quantity) albo
committed_order (reference, item_id, quantity, total_gross, currency, arrival_date).
Unikalny event_id chroni przed powtórzeniem; CAS chroni rewizję historii. Zdarzenia
są oświadczeniami operatora, nie telemetrią maszyny ani połączeniem z dostawcą.
Nie istnieje komenda cofająca zużycie lub anulująca zamówienie przez nową rewizję.
Rzeczywisty postęp można zapisać także po wykryciu zmiany już rozpoczętego planu.

Nowy plan może jawnie wskazać supersedes_plan_id, zachowując stary.
`compare_material_plans` zestawia wymagania, wykonane części, kandydatów do
ponownego użycia i braki. Dopasowanie wymaga tych samych wymiarów technologicznych,
materiału, wykończenia, grubości, technologii oraz polityki grain/obrotu. Nie
zatwierdza jakości i terminu użycia. Pokazuje braki zarówno bez reuse, jak i
warunkowo po jego akceptacji, oraz niewykorzystane wykonane części.

Zobowiązania zakupowe i wydatek w poszczególnych walutach pozostają widoczne.
Nowy koszt/zmiana ceny to null do czasu aktualnej wyceny i akceptacji reuse;
resztek nie przedstawiamy jako oszczędności gotówkowej. Daty nowych wymagań i
zachowanych dostaw są dostępne do oceny terminu. To niepełna wycena wpływu klienta,
nie automatyczna korekta kosztu. Pilotaż na rzeczywistych danych pozostaje otwarty.

PASS: pięć testów obejmuje zmianę BOM przed startem, rozpoczęty plan z wykonaniem
4 części i nowym popytem 3, zachowane zamówienie 123 PLN, brak zmian stanów,
zmianę zapisanego modelu/karty, CAS/replay historii i odmowę reuse innego wymiaru.
NOT RUN: rzeczywista produkcja, ceny, ocena jakości reuse i odbiór operatora.

## Przyrost 25.10 — odczyt wersji w dodatku

Źródłowy panel **Magazyn → Wersje planów materiałowych** otwiera
`MaterialPlanForm`. Korzysta z tej samej SQLite przez trzy narzędzia MCP:
`list_material_plans`, `get_material_plan` i `compare_material_plans`.
Ekran nie uruchamia planu i nie zapisuje postępu. Nie powstaje osobna baza C#.

Lista ma strony do 100 rekordów, kursor po ID i zapisany stan planu.
Nie hashuje plików CAD i jawnie pokazuje „Niesprawdzona — użyj Odczytaj”.
Wybór wiersza tylko wpisuje ID. Dopiero **Odczytaj plan** pobiera zweryfikowany
stan wejść, popyt, zapisany postęp i źródła; poprzednik może zostać podpowiedziany
z `supersedes_plan_id`. Porównanie wymaga osobnego kliknięcia i jawnego ID starego
planu. Odczyt planu oraz raport różnic mają oddzielne znaczniki czasu.

Tabele rozdzielają zapotrzebowanie, wykonanie według operatora, kandydatów reuse,
braki bez/warunkowo po akceptacji oraz zachowane zobowiązania z datami i walutą.
Koszt zmiany pozostaje nieznany; zachowany wydatek nie staje się oszczędnością.
Edycja ID unieważnia zależny wynik. Błąd odczytu usuwa poprzedni plan, a błąd
porównania usuwa różnice, zachowując osobno opisany wcześniejszy odczyt planu.
Eksport zapisuje jeden odczyt albo jedno porównanie z jego czasem i hashami;
`FileMode.CreateNew` chroni istniejące pliki. Nadal `production_approved=false`.

Przy udostępnianiu danych potwierdzono i naprawiono trzy braki backendu:

- Historia postępu była wczytywana bez porównania `event_sha256`. Uszkodzone
  zdarzenie odmawia teraz odczytu, replay i wyliczenia reuse/kosztu.
- Zmiana pliku snapshotu mogła zostać przyjęta jako nowe wejście mimo niezgodności
  z zarejestrowanym SHA. Diagnostyka oznacza stary plan jako nieaktualny i blokuje
  zapis/start nowego planu przy niezgodnym lub niedostępnym pliku. Historyczne
  payloady pozostają niezmienione.
- Porównanie nie oddzielało syntetycznego wykonania od planu `source_input`.
  `MATERIAL_SCOPE_MISMATCH` blokuje takie propozycje reuse.

Porównanie zawiera identyfikatory i rewizje obu planów oraz SHA payloadów
i odczytanych historii. Nie jest to blokada zmian plików na przyszłość ani WORM;
wynik opisuje konkretny odczyt, a nie bieżącą niezapisaną pamięć IronCAD.

PASS: dziewięć testów backendu, pełny harness, kompilacja dodatku i C# UI
`artifacts/verification/20261025T133758293539Z/results.json`. UI sprawdzono z
syntetycznym backendem testowym przy PL/EN i skali 100/150: 4 wykonane części,
3 kandydatów, 1 pozostała, zachowane 123 PLN, brak wymyślonego kosztu delta,
paging, pusty katalog, błędy, przełączenie języka oraz odmowa nadpisania eksportu.
Fixture wygenerowano rzeczywistym serwisem w izolowanej tymczasowej SQLite;
nie zasila bazy klienta. Zrzuty w `artifacts/material-plan-ui-20261025/`.

NOT RUN: formularz w IronCAD, przeładowanie DLL, rzeczywiste ceny i koszt delta,
pilotaż/ocena jakości oraz akceptacja produkcji. Host 20328 nadal nie odpowiada;
nie uruchomiono drugiej instancji ani operacji CAD. ROC-33 pozostaje otwarte.
