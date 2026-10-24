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
nie automatyczna korekta kosztu. Nie ma jeszcze zintegrowanego ekranu ani pilotażu.

PASS: pięć testów obejmuje zmianę BOM przed startem, rozpoczęty plan z wykonaniem
4 części i nowym popytem 3, zachowane zamówienie 123 PLN, brak zmian stanów,
zmianę zapisanego modelu/karty, CAS/replay historii i odmowę reuse innego wymiaru.
NOT RUN: rzeczywista produkcja, ceny, ocena jakości reuse i odbiór operatora.
